#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Repository-native QIK-VRT input/output persistence and publication router.

This tool persists provenance receipts for conforming I/O events and derives
reviewable publication-queue receipts for already machine-proved, connectable
new-knowledge claims. It performs no Zenodo or IETF network mutation itself;
those effects remain delegated to the existing exact-artifact effect tools.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy/AI_IO_ROUND_TRIP_AUTOPUBLISH_V1.json"
CLAIM_DIR = ROOT / "state/io_claims"
QUEUE_DIR = ROOT / "state/publication_queue"
EVENT_DIR = ROOT / "state/io_events"
ARTIFACT_DIR = ROOT / "artifacts/io"
HEX64 = set("0123456789abcdef")


class IORoundTripBlock(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IORoundTripBlock(f"cannot read {path.relative_to(ROOT)}: {exc}") from exc
    if not isinstance(value, dict):
        raise IORoundTripBlock(f"{path.relative_to(ROOT)} must contain an object")
    return value


def policy() -> dict[str, Any]:
    value = load_json(POLICY_PATH)
    if value.get("schema") != "qikvrt_ai_io_round_trip_autopublish_v1":
        raise IORoundTripBlock("I/O policy schema mismatch")
    if value.get("capture", {}).get("silent_drop") != "FORBIDDEN":
        raise IORoundTripBlock("silent I/O drop is not fail-closed")
    if value.get("machine_proof", {}).get("no_proof_no_publication") is not True:
        raise IORoundTripBlock("machine-proof publication boundary weakened")
    return value


def git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    if completed.returncode:
        raise IORoundTripBlock("cannot resolve Git HEAD")
    value = completed.stdout.strip()
    if len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise IORoundTripBlock("Git HEAD is not a lowercase SHA-1")
    return value


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def safe_name(raw: str) -> str:
    name = pathlib.PurePath(raw).name
    if not name or name in {".", ".."} or "\x00" in name:
        raise IORoundTripBlock("unsafe artifact basename")
    return name


def persist_event(args: argparse.Namespace) -> dict[str, Any]:
    p = policy()
    allowed_directions = set(p["capture"]["directions"])
    allowed_modes = set(p["capture"]["persistence_modes"])
    if args.direction not in allowed_directions:
        raise IORoundTripBlock("unsupported I/O direction")
    if args.persistence_mode not in allowed_modes:
        raise IORoundTripBlock("unsupported persistence mode")
    if sum(value is not None for value in (args.text, args.file)) != 1:
        raise IORoundTripBlock("exactly one of --text or --file is required")

    if args.text is not None:
        raw = args.text.encode("utf-8")
        source_name = args.safe_name or "payload.txt"
    else:
        source = pathlib.Path(args.file)
        if not source.is_file() or source.is_symlink():
            raise IORoundTripBlock("input file must be a regular file")
        raw = source.read_bytes()
        source_name = args.safe_name or source.name

    sha = digest(raw)
    observed = args.observed_at or now_utc()
    event_core = {
        "schema": "qikvrt_io_event_v1",
        "correlation_id": args.correlation_id,
        "direction": args.direction,
        "media_type": args.media_type,
        "actor_class": args.actor_class,
        "observed_at": observed,
        "repository": "Goldkelch/qik-vrt",
        "git_commit": git_head(),
        "byte_count": len(raw),
        "sha256": sha,
        "persistence_mode": args.persistence_mode,
        "provenance": args.provenance,
    }
    event_id = digest(canonical(event_core))
    event_core["event_id"] = event_id

    artifact_path: str | None = None
    if args.persistence_mode == "EXACT_BYTES":
        target = ARTIFACT_DIR / sha / safe_name(source_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != raw:
            raise IORoundTripBlock("content-addressed artifact collision")
        if not target.exists():
            target.write_bytes(raw)
        artifact_path = target.relative_to(ROOT).as_posix()
    elif not args.redaction_reason:
        raise IORoundTripBlock("redacted/digest-only persistence requires --redaction-reason")

    event_core["artifact_path"] = artifact_path
    event_core["redaction_reason"] = args.redaction_reason
    day = observed[:10] if len(observed) >= 10 else "unknown-date"
    event_path = EVENT_DIR / day / f"{event_id}.json"
    event_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(event_core, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if event_path.exists() and event_path.read_text(encoding="utf-8") != rendered:
        raise IORoundTripBlock("event identity collision")
    event_path.write_text(rendered, encoding="utf-8")
    return {"state": "PERSISTED", "event_id": event_id, "event_path": event_path.relative_to(ROOT).as_posix(), "artifact_path": artifact_path, "sha256": sha}


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in HEX64 for ch in value)


def validate_claim(path: pathlib.Path, p: dict[str, Any]) -> dict[str, Any]:
    claim = load_json(path)
    required = set(p["connectivity"]["required_fields"])
    missing = required - set(claim)
    if missing:
        raise IORoundTripBlock(f"{path.relative_to(ROOT)} missing connectivity fields: {sorted(missing)}")
    if not isinstance(claim.get("source_event_ids"), list) or not claim["source_event_ids"]:
        raise IORoundTripBlock(f"{path.relative_to(ROOT)} has no source event membership")
    proof = claim.get("machine_proof")
    if claim.get("state") == "MACHINE_PROVED_NEW_KNOWLEDGE":
        if not isinstance(proof, dict) or proof.get("proof_class") not in set(p["machine_proof"]["accepted_proof_classes"]):
            raise IORoundTripBlock(f"{path.relative_to(ROOT)} lacks an accepted machine proof")
        if not valid_sha256(proof.get("sha256")):
            raise IORoundTripBlock(f"{path.relative_to(ROOT)} machine-proof digest invalid")
    return claim


def route_claim(path: pathlib.Path, claim: dict[str, Any], apply: bool) -> dict[str, Any]:
    state = claim.get("state")
    if state != "MACHINE_PROVED_NEW_KNOWLEDGE":
        return {"claim": claim.get("claim_id"), "route": "NOOP", "reason": f"state={state}"}
    if claim.get("connectable") is not True or claim.get("rights_clear") is not True:
        return {"claim": claim.get("claim_id"), "route": "HOLD", "reason": "connectivity_or_rights_gate"}
    if claim.get("exact_head_gates_terminal_green") is not True:
        return {"claim": claim.get("claim_id"), "route": "HOLD", "reason": "exact_head_gates"}

    ietf = claim.get("ietf_relevance") in {"NORMATIVE_PROTOCOL_DELTA", "INTEROPERABILITY_SPEC_DELTA"}
    route = "ZENODO_AND_IETF_READY" if ietf else "ZENODO_READY"
    queue = {
        "schema": "qikvrt_io_publication_queue_v1",
        "claim_id": claim["claim_id"],
        "route": route,
        "source_claim_path": path.relative_to(ROOT).as_posix(),
        "source_claim_sha256": digest(path.read_bytes()),
        "source_event_ids": claim["source_event_ids"],
        "machine_proof": claim["machine_proof"],
        "publication_manifest_path": claim.get("publication_manifest_path"),
        "ietf_candidate_path": claim.get("ietf_candidate_path") if ietf else None,
        "effect_authorization": "DERIVE_ONLY_AFTER_FINAL_BYTES_AND_PREPUBLICATION_RETURN",
        "post_effect_reobservation_required": True,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }
    if apply:
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        target = QUEUE_DIR / f"{claim['claim_id']}.json"
        rendered = json.dumps(queue, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        if target.exists() and target.read_text(encoding="utf-8") != rendered:
            raise IORoundTripBlock(f"publication queue collision for {claim['claim_id']}")
        target.write_text(rendered, encoding="utf-8")
    return {"claim": claim["claim_id"], "route": route}


def sweep(apply: bool) -> dict[str, Any]:
    p = policy()
    results: list[dict[str, Any]] = []
    if CLAIM_DIR.is_dir():
        for path in sorted(CLAIM_DIR.glob("*.json")):
            results.append(route_claim(path, validate_claim(path, p), apply))
    return {"state": "CONTINUE" if any(item["route"] != "NOOP" for item in results) else "NOOP", "apply": apply, "claims": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--direction", required=True)
    capture.add_argument("--actor-class", required=True, choices=("HUMAN", "ARTIFICIAL_COGNITIVE_SYSTEM", "TOOL", "EXTERNAL_SYSTEM"))
    capture.add_argument("--media-type", required=True)
    capture.add_argument("--correlation-id", required=True)
    capture.add_argument("--provenance", required=True)
    capture.add_argument("--persistence-mode", default="EXACT_BYTES")
    capture.add_argument("--text")
    capture.add_argument("--file")
    capture.add_argument("--safe-name")
    capture.add_argument("--redaction-reason")
    capture.add_argument("--observed-at")
    sweep_parser = sub.add_parser("sweep")
    sweep_parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        result = persist_event(args) if args.command == "capture" else sweep(args.apply)
    except (IORoundTripBlock, OSError, ValueError) as exc:
        print(json.dumps({"state": "BLOCK", "detail": str(exc)}, ensure_ascii=False, sort_keys=True))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
