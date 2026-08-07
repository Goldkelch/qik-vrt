#!/usr/bin/env python3
"""QIK-VRT I/O round-trip persistence controller.

This controller is intentionally fail-closed. It materializes repository-visible
receipts for interface traffic, classifies knowledge candidates, and produces
publication routing decisions. It never performs a Zenodo/IETF write unless an
exact-artifact-and-target authorization receipt is supplied by a caller/adaptor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE_ROOT = ROOT / "state" / "io_roundtrip"
EVENTS_DIR = STATE_ROOT / "events"
QUEUE_DIR = STATE_ROOT / "publication_queue"
RECON_DIR = STATE_ROOT / "publication_receipts"

STATES = (
    "TRACE_ONLY",
    "KNOWLEDGE_CANDIDATE",
    "PROVED_KNOWLEDGE_CANDIDATE",
    "PUBLICATION_READY",
    "PUBLISHED",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bool_field(obj: Dict[str, Any], key: str) -> bool:
    return obj.get(key) is True


def classify(meta: Dict[str, Any]) -> str:
    if not bool_field(meta, "claim_bearing"):
        return "TRACE_ONLY"
    if not meta.get("proof_receipt_sha256"):
        return "KNOWLEDGE_CANDIDATE"
    return "PROVED_KNOWLEDGE_CANDIDATE"


def target_blockers(meta: Dict[str, Any], target: str) -> List[str]:
    blockers: List[str] = []
    required = (
        "exact_artifact_binding",
        "proof_or_evidence_receipt",
        "provenance_complete",
        "rights_clear",
        "scientific_status_explicit",
        "granularity_suitable",
        "connectivity_suitable",
        "target_authorized",
        "credentials_available",
    )
    if target == "ietf" and not bool_field(meta, "protocol_or_specification_applicable"):
        blockers.append("protocol_or_specification_applicable=false")
    for field in required:
        if not bool_field(meta, field):
            blockers.append(f"{field}=false")
    return blockers


def publication_decision(meta: Dict[str, Any], knowledge_state: str) -> Dict[str, Any]:
    decision: Dict[str, Any] = {"targets": {}, "ready_targets": []}
    if knowledge_state not in ("PROVED_KNOWLEDGE_CANDIDATE", "PUBLICATION_READY", "PUBLISHED"):
        decision["global_blocker"] = "machine-checkable proof/evidence receipt not bound"
        return decision
    requested: Iterable[str] = meta.get("publication_targets") or []
    for target in requested:
        if target not in ("zenodo", "ietf"):
            decision["targets"][target] = {"status": "BLOCK", "blockers": ["unsupported_target"]}
            continue
        blockers = target_blockers(meta, target)
        status = "READY" if not blockers else "BLOCK"
        decision["targets"][target] = {"status": status, "blockers": blockers}
        if status == "READY":
            decision["ready_targets"].append(target)
    return decision


def safe_event_id(base: Dict[str, Any]) -> str:
    stable = dict(base)
    stable.pop("observed_at_utc", None)
    return sha256(canonical_bytes(stable))[:24]


def write_json(path: pathlib.Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False).encode("utf-8") + b"\n")
    os.replace(tmp, path)


def observe(args: argparse.Namespace) -> int:
    payload = pathlib.Path(args.payload_file).read_bytes() if args.payload_file else sys.stdin.buffer.read()
    meta = json.loads(pathlib.Path(args.meta).read_text(encoding="utf-8")) if args.meta else {}
    retention = args.retention
    if retention == "raw" and not bool_field(meta, "raw_payload_authorized"):
        raise SystemExit("raw retention requested without raw_payload_authorized=true")

    receipt: Dict[str, Any] = {
        "schema": "qik-vrt.io-roundtrip-event.v1",
        "direction": args.direction,
        "media_type": args.media_type,
        "observed_at_utc": utc_now(),
        "origin": args.origin,
        "payload_sha256": sha256(payload),
        "payload_size_bytes": len(payload),
        "retention": retention,
        "provenance_status": meta.get("provenance_status", "UNRESOLVED"),
        "parents": meta.get("parents", []),
        "repository_binding": meta.get("repository_binding"),
        "uncertainty": meta.get("uncertainty"),
    }
    if retention == "raw":
        receipt["payload_utf8"] = payload.decode("utf-8")
    elif retention == "pointer":
        pointer = meta.get("retention_pointer")
        if not pointer:
            raise SystemExit("pointer retention requires retention_pointer")
        receipt["retention_pointer"] = pointer

    knowledge_state = classify(meta)
    receipt["knowledge_state"] = knowledge_state
    receipt["proof_receipt_sha256"] = meta.get("proof_receipt_sha256")
    receipt["publication"] = publication_decision(meta, knowledge_state)
    if receipt["publication"].get("ready_targets"):
        receipt["knowledge_state"] = "PUBLICATION_READY"

    event_id = safe_event_id(receipt)
    receipt["event_id"] = event_id
    event_path = EVENTS_DIR / f"{event_id}.json"
    write_json(event_path, receipt)

    for target in receipt["publication"].get("ready_targets", []):
        queue = {
            "schema": "qik-vrt.publication-queue-item.v1",
            "event_id": event_id,
            "target": target,
            "exact_payload_sha256": receipt["payload_sha256"],
            "state": "READY_AWAITING_EXACT_EFFECT_ADAPTER",
            "idempotency_key": sha256(canonical_bytes({"event_id": event_id, "target": target})),
        }
        write_json(QUEUE_DIR / f"{event_id}.{target}.json", queue)

    print(json.dumps({"status": "PERSISTED", "event": str(event_path.relative_to(ROOT)), "receipt": receipt}, sort_keys=True))
    return 0


def reconcile(args: argparse.Namespace) -> int:
    event_path = EVENTS_DIR / f"{args.event_id}.json"
    if not event_path.is_file():
        raise SystemExit("unknown event_id")
    event = json.loads(event_path.read_text(encoding="utf-8"))
    queue_path = QUEUE_DIR / f"{args.event_id}.{args.target}.json"
    if not queue_path.is_file():
        raise SystemExit("no ready queue item for target")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    external = json.loads(pathlib.Path(args.external_receipt).read_text(encoding="utf-8"))
    if external.get("target") != args.target:
        raise SystemExit("external receipt target mismatch")
    if external.get("exact_payload_sha256") != event.get("payload_sha256"):
        raise SystemExit("external receipt exact payload mismatch")
    if external.get("effect_verified") is not True:
        raise SystemExit("external effect is not verified")
    result = {
        "schema": "qik-vrt.publication-reconciliation.v1",
        "event_id": args.event_id,
        "target": args.target,
        "exact_payload_sha256": event["payload_sha256"],
        "external_receipt_sha256": sha256(canonical_bytes(external)),
        "effect_verified": True,
        "reconciled_at_utc": utc_now(),
        "external_locator": external.get("external_locator"),
    }
    write_json(RECON_DIR / f"{args.event_id}.{args.target}.json", result)
    queue["state"] = "PUBLISHED_RECONCILED"
    write_json(queue_path, queue)
    print(json.dumps({"status": "PUBLISHED_RECONCILED", "receipt": result}, sort_keys=True))
    return 0


def check(_: argparse.Namespace) -> int:
    malformed = []
    for path in sorted(EVENTS_DIR.glob("*.json")) if EVENTS_DIR.exists() else []:
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
            if obj.get("knowledge_state") not in STATES:
                malformed.append(str(path.relative_to(ROOT)))
            if not obj.get("payload_sha256") or not obj.get("event_id"):
                malformed.append(str(path.relative_to(ROOT)))
        except Exception:
            malformed.append(str(path.relative_to(ROOT)))
    status = "PASS" if not malformed else "BLOCK"
    print(json.dumps({"status": status, "malformed": sorted(set(malformed))}, sort_keys=True))
    return 0 if status == "PASS" else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("observe")
    o.add_argument("--direction", required=True, choices=("INPUT", "OUTPUT"))
    o.add_argument("--media-type", required=True)
    o.add_argument("--origin", required=True)
    o.add_argument("--retention", choices=("commitment", "pointer", "raw"), default="commitment")
    o.add_argument("--payload-file")
    o.add_argument("--meta")
    o.set_defaults(func=observe)
    r = sub.add_parser("reconcile")
    r.add_argument("--event-id", required=True)
    r.add_argument("--target", required=True, choices=("zenodo", "ietf"))
    r.add_argument("--external-receipt", required=True)
    r.set_defaults(func=reconcile)
    c = sub.add_parser("check")
    c.set_defaults(func=check)
    return p


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
