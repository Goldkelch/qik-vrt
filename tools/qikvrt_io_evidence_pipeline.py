#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

"""Fail-closed QIK-VRT I/O evidence capture and publication-routing controller.

This controller intentionally separates four states:
1. repository persistence,
2. knowledge-candidate classification,
3. machine-checked eligibility,
4. external publication dispatch eligibility.

It never equates a machine check with empirical or scientific validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_ROOT = ROOT / "evidence" / "io-events"
REQUIREMENT = ROOT / "docs" / "requirements" / "UNIVERSAL_IO_PERSISTENCE_AND_PUBLICATION_V1.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise SystemExit(f"BLOCK: expected object at {path}")
    return value


def validate_event(event: dict[str, Any]) -> None:
    required = {
        "direction",
        "modality",
        "interface",
        "payload",
        "provenance",
        "rights",
        "privacy",
        "epistemic_type",
    }
    missing = sorted(required - set(event))
    if missing:
        raise SystemExit("BLOCK: missing event fields: " + ",".join(missing))
    if event["direction"] not in {"INPUT", "OUTPUT"}:
        raise SystemExit("BLOCK: direction must be INPUT or OUTPUT")
    if not isinstance(event["payload"], (str, dict, list, int, float, bool)) and event["payload"] is not None:
        raise SystemExit("BLOCK: unsupported payload type")
    for name in ("provenance", "rights", "privacy"):
        if not isinstance(event[name], dict):
            raise SystemExit(f"BLOCK: {name} must be an object")


def payload_bytes(payload: Any) -> bytes:
    if isinstance(payload, str):
        return payload.encode("utf-8")
    return canonical_json(payload)


def classify(event: dict[str, Any], payload_sha256: str) -> dict[str, Any]:
    knowledge = event.get("knowledge", {})
    if not isinstance(knowledge, dict):
        knowledge = {}
    novelty = knowledge.get("novelty", "UNASSESSED")
    granularity = knowledge.get("granularity", "UNASSESSED")
    connectivity = knowledge.get("connectivity", "UNASSESSED")
    proof = knowledge.get("machine_check", {})
    if not isinstance(proof, dict):
        proof = {}

    proof_status = proof.get("status", "MISSING")
    proof_scope = proof.get("scope", "NONE")
    proof_receipt_sha256 = proof.get("receipt_sha256")
    if proof_receipt_sha256 is not None and not HEX64.match(str(proof_receipt_sha256)):
        proof_status = "INVALID_RECEIPT_DIGEST"

    rights_clear = bool(event["rights"].get("publication_clear", False))
    provenance_complete = bool(event["provenance"].get("complete", False))
    scientific_status_explicit = bool(event.get("scientific_status"))
    stable_granularity = granularity in {"STABLE", "PUBLICATION_UNIT"}
    connected = connectivity in {"CONNECTED", "CANONICALLY_CONNECTED"}
    novel = novelty in {"NEW", "MATERIALLY_NEW"}
    machine_checked = proof_status == "PASS"

    if not novel:
        state = "NOT_A_KNOWLEDGE_CANDIDATE"
    elif all((stable_granularity, connected, provenance_complete, rights_clear, scientific_status_explicit, machine_checked)):
        state = "MACHINE_CHECKED"
    else:
        state = "CANDIDATE"

    publication_authorized = bool(event.get("publication_authorization", {}).get("authorized", False))
    exact_head_verified = bool(event.get("repository_state", {}).get("exact_head_verified", False))
    standards_relevance = bool(knowledge.get("standards_relevance", False))
    ietf_materialization_valid = bool(knowledge.get("ietf_materialization_valid", False))

    zenodo_eligible = all((state == "MACHINE_CHECKED", publication_authorized, exact_head_verified))
    ietf_eligible = all((zenodo_eligible, standards_relevance, ietf_materialization_valid))

    return {
        "payload_sha256": payload_sha256,
        "knowledge_state": state,
        "assessments": {
            "novelty": novelty,
            "granularity": granularity,
            "connectivity": connectivity,
            "provenance_complete": provenance_complete,
            "rights_clear": rights_clear,
            "scientific_status_explicit": scientific_status_explicit,
            "machine_check_status": proof_status,
            "machine_check_scope": proof_scope,
            "machine_check_receipt_sha256": proof_receipt_sha256,
        },
        "publication": {
            "publication_authorized": publication_authorized,
            "exact_head_verified": exact_head_verified,
            "zenodo_eligible": zenodo_eligible,
            "ietf_eligible": ietf_eligible,
            "standards_relevance": standards_relevance,
            "ietf_materialization_valid": ietf_materialization_valid,
            "scientific_validation_inferred": False,
            "ietf_acceptance_inferred": False,
        },
    }


def build_receipt(event: dict[str, Any]) -> dict[str, Any]:
    validate_event(event)
    raw = payload_bytes(event["payload"])
    payload_sha = sha256_bytes(raw)
    event_basis = {
        "direction": event["direction"],
        "modality": event["modality"],
        "interface": event["interface"],
        "payload_sha256": payload_sha,
        "provenance": event["provenance"],
        "rights": event["rights"],
        "privacy": event["privacy"],
        "epistemic_type": event["epistemic_type"],
        "parent_evidence": event.get("parent_evidence", []),
    }
    event_id = "io-" + sha256_bytes(canonical_json(event_basis))[:32]
    classification = classify(event, payload_sha)
    persist_payload = bool(event["privacy"].get("repository_payload_allowed", False))

    receipt = {
        "schema": "qikvrt_io_event_receipt_v1",
        "requirement": "QIKVRT-UNIVERSAL-IO-PERSISTENCE-PUBLICATION-V1",
        "event_id": event_id,
        "observed_at": event.get("observed_at") or utc_now(),
        "direction": event["direction"],
        "modality": event["modality"],
        "interface": event["interface"],
        "payload_sha256": payload_sha,
        "payload_bytes": len(raw),
        "payload_persistence": "INLINE" if persist_payload else "DIGEST_ONLY",
        "payload": event["payload"] if persist_payload else None,
        "payload_omission_reason": None if persist_payload else event["privacy"].get("omission_reason", "repository payload persistence not authorized"),
        "provenance": event["provenance"],
        "rights": event["rights"],
        "privacy": event["privacy"],
        "epistemic_type": event["epistemic_type"],
        "scientific_status": event.get("scientific_status", "UNSPECIFIED"),
        "parent_evidence": event.get("parent_evidence", []),
        "classification": classification,
        "boundaries": {
            "machine_check_is_not_empirical_validation": True,
            "repository_persistence_is_not_publication": True,
            "zenodo_deposit_is_not_scientific_consensus": True,
            "ietf_submission_is_not_ietf_acceptance": True,
        },
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_json(receipt))
    return receipt


def persist_receipt(receipt: dict[str, Any], root: Path = RECEIPT_ROOT) -> Path:
    event_id = receipt["event_id"]
    path = root / event_id[:5] / f"{event_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != encoded:
            raise SystemExit("BLOCK: event-id collision with different receipt bytes")
        return path
    path.write_text(encoded, encoding="utf-8")
    return path


def command_capture(args: argparse.Namespace) -> int:
    source = Path(args.event)
    event = load_json(source)
    receipt = build_receipt(event)
    path = persist_receipt(receipt, Path(args.receipt_root) if args.receipt_root else RECEIPT_ROOT)
    result = {
        "state": "PERSISTED",
        "event_id": receipt["event_id"],
        "receipt": str(path),
        "receipt_sha256": receipt["receipt_sha256"],
        "knowledge_state": receipt["classification"]["knowledge_state"],
        "zenodo_eligible": receipt["classification"]["publication"]["zenodo_eligible"],
        "ietf_eligible": receipt["classification"]["publication"]["ietf_eligible"],
    }
    print(json.dumps(result, sort_keys=True))
    return 0


def command_verify(args: argparse.Namespace) -> int:
    path = Path(args.receipt)
    receipt = load_json(path)
    expected = receipt.pop("receipt_sha256", None)
    observed = sha256_bytes(canonical_json(receipt))
    if expected != observed:
        raise SystemExit("BLOCK: receipt SHA-256 mismatch")
    print(json.dumps({"state": "VALID", "receipt": str(path), "receipt_sha256": observed}, sort_keys=True))
    return 0


def command_route(args: argparse.Namespace) -> int:
    receipt = load_json(Path(args.receipt))
    publication = receipt.get("classification", {}).get("publication", {})
    route = []
    if publication.get("zenodo_eligible"):
        route.append("ZENODO")
    if publication.get("ietf_eligible"):
        route.append("IETF")
    state = "READY_FOR_EFFECT_DISPATCH" if route else "BLOCKED_NO_AUTHORIZED_PUBLICATION_ROUTE"
    print(json.dumps({"state": state, "route": route, "receipt": args.receipt}, sort_keys=True))
    return 0 if route else 3


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--event", required=True)
    capture.add_argument("--receipt-root")
    capture.set_defaults(func=command_capture)
    verify = sub.add_parser("verify")
    verify.add_argument("--receipt", required=True)
    verify.set_defaults(func=command_verify)
    route = sub.add_parser("route")
    route.add_argument("--receipt", required=True)
    route.set_defaults(func=command_route)
    return p


def main(argv: list[str] | None = None) -> int:
    if not REQUIREMENT.exists():
        raise SystemExit("BLOCK: universal I/O requirement missing")
    args = parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
