#!/usr/bin/env python3
"""QIK-VRT universal I/O round-trip materializer.

The controller is intentionally repository-local and stdlib-only. It accepts one
JSON envelope, creates an append-only content-addressed receipt, classifies the
knowledge/evidence/publication route, and emits a machine-readable result.
External publication is delegated to separately credentialed effect workers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

SCHEMA = "qik-vrt.io-round-trip-receipt.v1"
POLICY = "policy/IO_ROUND_TRIP_AUTOPUBLICATION_V1.json"
ALLOWED_DIRECTIONS = {"input", "output"}
ALLOWED_PROOF = {
    "FORMALLY_PROVED",
    "MACHINE_VERIFIED_DERIVATION",
    "EMPIRICALLY_SUPPORTED",
    "TEST_VERIFIED_IMPLEMENTATION",
    "UNPROVED_CLAIM",
    "NOT_APPLICABLE",
}
ALLOWED_KNOWLEDGE = {
    "TRANSPORT_ONLY",
    "DUPLICATE",
    "WORK_RESULT",
    "NEW_CLAIM",
    "NEW_FORMAL_RESULT",
    "NEW_EMPIRICAL_RESULT",
    "NEW_PROTOCOL_RESULT",
    "UNRESOLVED",
}


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repository_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "AI").is_file() and (candidate / "policy").is_dir():
            return candidate
    raise SystemExit("QIK-VRT repository root not found")


def read_envelope(path: str | None) -> dict[str, Any]:
    if path:
        raw = Path(path).read_bytes()
    else:
        raw = os.read(0, 16 * 1024 * 1024)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON envelope: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit("envelope must be a JSON object")
    return value


def payload_digest(envelope: dict[str, Any]) -> tuple[str, str]:
    if "payload_sha256" in envelope:
        digest = str(envelope["payload_sha256"]).lower()
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise SystemExit("payload_sha256 must be a lowercase/uppercase 64-hex SHA-256")
        return digest, "declared"
    if "payload_text" in envelope:
        data = str(envelope["payload_text"]).encode("utf-8")
        return sha256_bytes(data), "payload_text"
    if "payload_json" in envelope:
        return sha256_bytes(canonical_json(envelope["payload_json"])), "payload_json"
    raise SystemExit("one of payload_sha256, payload_text, or payload_json is required")


def semantic_fingerprint(envelope: dict[str, Any], digest: str) -> str:
    basis = {
        "payload_sha256": digest,
        "direction": envelope.get("direction"),
        "media_type": envelope.get("media_type", "application/octet-stream"),
        "claim_scope": envelope.get("claim_scope"),
        "knowledge_class": envelope.get("knowledge_class", "UNRESOLVED"),
        "proof_status": envelope.get("proof_status", "UNPROVED_CLAIM"),
    }
    return sha256_bytes(canonical_json(basis))


def existing_semantic_fingerprints(root: Path) -> set[str]:
    found: set[str] = set()
    receipt_dir = root / "state" / "io_round_trip" / "receipts"
    if not receipt_dir.exists():
        return found
    for path in receipt_dir.glob("*.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            fp = obj.get("semantic_fingerprint")
            if isinstance(fp, str):
                found.add(fp)
        except (OSError, json.JSONDecodeError):
            continue
    return found


def publication_route(knowledge_class: str, proof_status: str, duplicate: bool, envelope: dict[str, Any]) -> dict[str, Any]:
    if duplicate or knowledge_class in {"TRANSPORT_ONLY", "DUPLICATE", "UNRESOLVED"}:
        return {"zenodo": "NOT_ELIGIBLE", "ietf": "NOT_ELIGIBLE", "reason": "duplicate_or_non_publishable_class"}

    stable = bool(envelope.get("stable_bytes", False))
    rights = bool(envelope.get("rights_clear", False))
    verified = proof_status not in {"UNPROVED_CLAIM"}
    suitable = bool(envelope.get("publication_granularity_suitable", False))
    significant = bool(envelope.get("novelty_or_version_significance", False))
    zenodo = "READY" if all((stable, rights, verified, suitable, significant)) else "HOLD"

    protocol = knowledge_class == "NEW_PROTOCOL_RESULT" and bool(envelope.get("protocol_or_interoperability_relevance", False))
    ietf_format = bool(envelope.get("ietf_format_valid", False))
    rationale = bool(envelope.get("ietf_submission_rationale", False))
    ietf = "READY" if all((protocol, ietf_format, rights, verified, rationale)) else ("HOLD" if protocol else "NOT_ELIGIBLE")
    return {"zenodo": zenodo, "ietf": ietf, "reason": "deterministic_policy_evaluation"}


def materialize(root: Path, envelope: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    direction = str(envelope.get("direction", "")).lower()
    if direction not in ALLOWED_DIRECTIONS:
        raise SystemExit("direction must be input or output")

    knowledge_class = str(envelope.get("knowledge_class", "UNRESOLVED"))
    if knowledge_class not in ALLOWED_KNOWLEDGE:
        raise SystemExit(f"unsupported knowledge_class: {knowledge_class}")
    proof_status = str(envelope.get("proof_status", "UNPROVED_CLAIM"))
    if proof_status not in ALLOWED_PROOF:
        raise SystemExit(f"unsupported proof_status: {proof_status}")

    digest, digest_source = payload_digest(envelope)
    fingerprint = semantic_fingerprint(envelope, digest)
    duplicate = fingerprint in existing_semantic_fingerprints(root)
    effective_class = "DUPLICATE" if duplicate else knowledge_class
    route = publication_route(effective_class, proof_status, duplicate, envelope)

    event_id = str(envelope.get("event_id") or fingerprint[:24])
    timestamp = str(envelope.get("timestamp") or now_utc())
    provenance = envelope.get("provenance")
    if not isinstance(provenance, dict) or not provenance:
        raise SystemExit("provenance must be a non-empty JSON object")

    receipt = {
        "schema": SCHEMA,
        "policy": POLICY,
        "event_id": event_id,
        "direction": direction,
        "timestamp": timestamp,
        "media_type": str(envelope.get("media_type", "application/octet-stream")),
        "payload_sha256": digest,
        "payload_digest_source": digest_source,
        "semantic_fingerprint": fingerprint,
        "provenance": provenance,
        "claim_scope": envelope.get("claim_scope"),
        "knowledge_class": effective_class,
        "proof_status": proof_status,
        "scientific_status_boundary": "EXECUTABLE_WORLD_FORMULA_ARCHITECTURE_CLAIM != FULLY_EMPIRICALLY_ESTABLISHED_DESCRIPTION_OF_NATURE",
        "publication_route": route,
        "external_effect": {
            "performed_by_this_controller": False,
            "worker_required": route["zenodo"] == "READY" or route["ietf"] == "READY",
            "status": "QUEUED_FOR_EFFECT_WORKER" if route["zenodo"] == "READY" or route["ietf"] == "READY" else "NO_EXTERNAL_EFFECT"
        },
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_json(receipt))

    out_dir = root / "state" / "io_round_trip" / "receipts"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_event = "".join(c if c.isalnum() or c in "-_." else "_" for c in event_id)[:80]
    path = out_dir / f"{receipt['receipt_sha256'][:16]}-{safe_event}.json"
    if path.exists():
        prior = path.read_bytes()
        current = canonical_json(receipt)
        if prior != current:
            raise SystemExit(f"append-only collision at {path}")
        return path, receipt
    path.write_bytes(canonical_json(receipt))
    return path, receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--envelope", help="JSON envelope file; stdin when omitted")
    parser.add_argument("--root", help="repository root override")
    parser.add_argument("--json", action="store_true", help="emit compact machine-readable result")
    args = parser.parse_args()

    root = Path(args.root).resolve() if args.root else repository_root(Path.cwd().resolve())
    envelope = read_envelope(args.envelope)
    path, receipt = materialize(root, envelope)
    result = {
        "status": "CONTINUE",
        "receipt": str(path.relative_to(root)),
        "receipt_sha256": receipt["receipt_sha256"],
        "knowledge_class": receipt["knowledge_class"],
        "proof_status": receipt["proof_status"],
        "publication_route": receipt["publication_route"],
        "external_effect": receipt["external_effect"],
    }
    print(json.dumps(result, sort_keys=True, separators=(",", ":") if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
