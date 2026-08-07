#!/usr/bin/env python3
"""Create deterministic repository work-unit receipts for QIK-VRT I/O events.

This tool is repository-local and performs no network or external publication effect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any

SCHEMA = "qikvrt_io_work_unit_v1"
CLAIM_CLASSES = {
    "transport_context",
    "attributed_claim",
    "derived_result",
    "formalizable_proposition",
    "machine_checked_result",
    "empirical_observation",
    "protocol_delta",
    "publication_candidate",
    "unresolved",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def build_receipt(args: argparse.Namespace) -> dict[str, Any]:
    payload: bytes | None = None
    media_type = args.media_type
    byte_length = args.byte_length
    digest = args.sha256
    availability = "DIGEST_ONLY"

    if args.file:
        path = Path(args.file)
        payload = path.read_bytes()
        digest = sha256_bytes(payload)
        byte_length = len(payload)
        media_type = media_type or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        availability = "LOCAL_BYTES_OBSERVED"

    if not digest or byte_length is None:
        raise SystemExit("exact sha256 and byte_length are required when --file is not supplied")

    receipt = {
        "schema": SCHEMA,
        "work_unit_id": args.work_unit_id,
        "timestamp": args.timestamp,
        "direction": args.direction,
        "modality": args.modality,
        "media_type": media_type or "application/octet-stream",
        "sha256": digest,
        "byte_length": int(byte_length),
        "byte_availability": availability,
        "source_or_generator": args.source_or_generator,
        "human_attribution": args.human_attribution,
        "model_or_tool_identity": args.model_or_tool_identity,
        "antecedents": args.antecedent,
        "derived_objects": args.derived_object,
        "claim_classification": args.claim_classification,
        "verification_state": args.verification_state,
        "repository_binding": args.repository_binding,
        "zenodo_disposition": args.zenodo_disposition,
        "ietf_disposition": args.ietf_disposition,
        "effect_state": args.effect_state,
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_json(receipt))
    return receipt


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    p.add_argument("--work-unit-id", required=True)
    p.add_argument("--timestamp", required=True)
    p.add_argument("--direction", choices=("INPUT", "OUTPUT", "TOOL_RESULT", "MIXED"), required=True)
    p.add_argument("--modality", required=True)
    p.add_argument("--media-type")
    p.add_argument("--file")
    p.add_argument("--sha256")
    p.add_argument("--byte-length", type=int)
    p.add_argument("--source-or-generator", required=True)
    p.add_argument("--human-attribution", default="unresolved")
    p.add_argument("--model-or-tool-identity", default="unresolved")
    p.add_argument("--antecedent", action="append", default=[])
    p.add_argument("--derived-object", action="append", default=[])
    p.add_argument("--claim-classification", choices=sorted(CLAIM_CLASSES), default="unresolved")
    p.add_argument("--verification-state", default="UNVERIFIED")
    p.add_argument("--repository-binding", default="PENDING")
    p.add_argument("--zenodo-disposition", default="EVALUATION_PENDING")
    p.add_argument("--ietf-disposition", default="EVALUATION_PENDING")
    p.add_argument("--effect-state", default="EFFECT_ACK_CONTINUE")
    p.add_argument("--output", required=True)
    return p


def main() -> int:
    args = parser().parse_args()
    receipt = build_receipt(args)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if out.exists() and out.read_text(encoding="utf-8") == data:
        print("NOOP")
        return 0
    out.write_text(data, encoding="utf-8")
    print(receipt["receipt_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
