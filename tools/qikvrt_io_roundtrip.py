#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "IO_EVIDENCE_PUBLICATION_ROUNDTRIP_V1.json"
EVENT_DIR = ROOT / "state" / "io_roundtrip" / "events"
CANDIDATE_DIR = ROOT / "state" / "io_roundtrip" / "publication_candidates"


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_policy() -> dict[str, Any]:
    value = json.loads(POLICY.read_text(encoding="utf-8"))
    if value.get("policy_id") != "IO_EVIDENCE_PUBLICATION_ROUNDTRIP_V1":
        raise SystemExit("BLOCK: unexpected IO round-trip policy")
    return value


def atomic_create(path: pathlib.Path, payload: bytes) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise SystemExit(f"BLOCK: hash-address collision at {path}")
        return "NOOP"
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(payload)
    tmp.replace(path)
    return "CREATED"


def capture(args: argparse.Namespace) -> int:
    policy = load_policy()
    raw = sys.stdin.buffer.read()
    payload_hash = sha256_bytes(raw)
    retention = args.retention
    inline_payload: str | None = None
    if retention == "INLINE" and len(raw) <= args.inline_limit:
        try:
            inline_payload = raw.decode("utf-8")
        except UnicodeDecodeError:
            retention = "REPOSITORY_ARTIFACT"

    identity = {
        "schema": "qikvrt-io-event-identity/1.0",
        "direction": args.direction,
        "modality": args.modality,
        "actor": args.actor,
        "source": args.source,
        "payload_sha256": payload_hash,
        "payload_retention": retention,
        "work_unit": args.work_unit,
        "parent_event": args.parent_event,
        "epistemic_class": args.epistemic_class,
    }
    event_id = sha256_bytes(canonical_json(identity))
    event: dict[str, Any] = {
        "schema": "qikvrt-io-event/1.0",
        "event_id": event_id,
        "timestamp": args.timestamp or dt.datetime.now(dt.timezone.utc).isoformat(),
        "direction": args.direction,
        "modality": args.modality,
        "actor": args.actor,
        "source": args.source,
        "payload_sha256": payload_hash,
        "payload_retention": retention,
        "provenance": {"work_unit": args.work_unit, "parent_event": args.parent_event},
        "epistemic_class": args.epistemic_class,
        "verification_state": "UNVERIFIED",
        "publication_state": "NOT_ASSESSED",
    }
    if inline_payload is not None:
        event["payload_utf8"] = inline_payload

    path = EVENT_DIR / f"{event_id}.json"
    if path.exists():
        prior = json.loads(path.read_text(encoding="utf-8"))
        prior_comparable = {k: prior.get(k) for k in event if k != "timestamp"}
        event_comparable = {k: event.get(k) for k in event if k != "timestamp"}
        if prior_comparable != event_comparable:
            raise SystemExit(f"BLOCK: semantic event identity collision at {path}")
        result = "NOOP"
    else:
        result = atomic_create(
            path,
            json.dumps(event, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n",
        )
    print(json.dumps({"state": result, "event_id": event_id, "path": str(path.relative_to(ROOT)), "policy": policy["policy_id"]}, sort_keys=True))
    return 0


def candidate(args: argparse.Namespace) -> int:
    load_policy()
    event_path = EVENT_DIR / f"{args.event_id}.json"
    if not event_path.is_file():
        raise SystemExit("BLOCK: event does not exist")
    event = json.loads(event_path.read_text(encoding="utf-8"))
    if event.get("event_id") != args.event_id:
        raise SystemExit("BLOCK: event identity mismatch")
    gates = {
        "novelty_review_complete": args.novelty,
        "provenance_complete": args.provenance,
        "rights_clear": args.rights,
        "machine_verification_complete": args.machine_verified,
        "scientific_status_boundary_preserved": args.scientific_status,
        "exact_bytes_frozen": args.exact_bytes_frozen,
        "ietf_relevant": args.ietf_relevant,
    }
    zenodo_ready = all(gates[k] for k in [
        "novelty_review_complete", "provenance_complete", "rights_clear",
        "machine_verification_complete", "scientific_status_boundary_preserved",
        "exact_bytes_frozen",
    ])
    candidate_core = {
        "schema": "qikvrt-publication-candidate/1.0",
        "source_event_id": args.event_id,
        "claim": args.claim,
        "claim_sha256": sha256_bytes(args.claim.encode("utf-8")),
        "assumptions": args.assumption,
        "gates": gates,
        "routing": {
            "zenodo": "READY_FOR_PRE_EFFECT_GATES" if zenodo_ready else "HOLD",
            "ietf": "READY_FOR_PRE_EFFECT_GATES" if zenodo_ready and args.ietf_relevant else "NOT_APPLICABLE_OR_HOLD",
        },
        "effect_boundary": "No external publication is performed by this repository-internal candidate materialization step.",
    }
    candidate_id = sha256_bytes(canonical_json(candidate_core))
    candidate = dict(candidate_core, candidate_id=candidate_id)
    path = CANDIDATE_DIR / f"{candidate_id}.json"
    result = atomic_create(path, json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    print(json.dumps({"state": result, "candidate_id": candidate_id, "path": str(path.relative_to(ROOT)), "zenodo_ready": zenodo_ready, "ietf_ready": bool(zenodo_ready and args.ietf_relevant)}, sort_keys=True))
    return 0


def verify(_: argparse.Namespace) -> int:
    policy = load_policy()
    required = policy["acceptance_criteria"]
    failures = [key for key, value in required.items() if value is not True]
    if failures:
        print(json.dumps({"state": "BLOCK", "failures": failures}, sort_keys=True))
        return 2
    print(json.dumps({"state": "CONTINUE", "policy": policy["policy_id"], "reason": "contract-valid; end-to-end external publication effects require separate exact-artifact/effect/credential receipts"}, sort_keys=True))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="QIK-VRT I/O evidence and publication round-trip controller")
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--direction", required=True, choices=["INGRESS", "EGRESS", "INTERNAL_TOOL_BOUNDARY"])
    c.add_argument("--modality", required=True)
    c.add_argument("--actor", required=True)
    c.add_argument("--source", required=True)
    c.add_argument("--work-unit", required=True)
    c.add_argument("--parent-event")
    c.add_argument("--epistemic-class", default="UNRESOLVED")
    c.add_argument("--retention", default="INLINE", choices=["INLINE", "REPOSITORY_ARTIFACT", "EXTERNAL_CONTENT_ADDRESSED", "REDACTED_METADATA_ONLY"])
    c.add_argument("--inline-limit", type=int, default=262144)
    c.add_argument("--timestamp")
    c.set_defaults(func=capture)
    k = sub.add_parser("candidate")
    k.add_argument("--event-id", required=True)
    k.add_argument("--claim", required=True)
    k.add_argument("--assumption", action="append", default=[])
    k.add_argument("--novelty", action="store_true")
    k.add_argument("--provenance", action="store_true")
    k.add_argument("--rights", action="store_true")
    k.add_argument("--machine-verified", action="store_true")
    k.add_argument("--scientific-status", action="store_true")
    k.add_argument("--exact-bytes-frozen", action="store_true")
    k.add_argument("--ietf-relevant", action="store_true")
    k.set_defaults(func=candidate)
    v = sub.add_parser("verify")
    v.set_defaults(func=verify)
    return p


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
