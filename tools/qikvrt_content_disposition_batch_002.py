#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

EXPECTED_AUTHORITY = "98194f453cee0ddf4dd0a44b1d12b1d9f20a9709"
EXPECTED_MIRROR = "1bb5af6597e1d90075396a9abf6c61e993388a59"
EXPECTED_BATCH = "CONTENT-DISPOSITION-BATCH-002"
EXPECTED_SUBJECTS = [
    "SUBJECT-5d4c516db0fdaaf5",
    "SUBJECT-59493a8ae380798d",
    "SUBJECT-3e026c784df87b95",
    "SUBJECT-c9d87f4435178b09",
    "SUBJECT-77146b895ce38de4",
    "SUBJECT-43c59da1cfd26267",
]


def canonical_sha256(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def execute(queue_path: Path, out: Path) -> dict:
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    active = queue.get("active_batch", {})
    subjects = active.get("subjects", [])
    subject_ids = [item.get("subject_id") for item in subjects]
    if active.get("batch_id") != EXPECTED_BATCH:
        raise RuntimeError("active queue batch is not Batch 002")
    if active.get("state") != "READY":
        raise RuntimeError("Batch 002 is not READY")
    if subject_ids != EXPECTED_SUBJECTS:
        raise RuntimeError("Batch 002 subject order mismatch")
    if queue.get("next_deterministic_effect") != "EXECUTE_CONTENT_DISPOSITION_BATCH_002":
        raise RuntimeError("queue next effect mismatch")

    subject_receipts = []
    for subject in subjects:
        candidate_files = subject.get("content_candidate_files") or []
        receipt = {
            "schema": "qikvrt_content_disposition_subject_receipt_v2",
            "batch_id": EXPECTED_BATCH,
            "subject_id": subject["subject_id"],
            "record_ids": subject.get("record_ids", []),
            "conceptdois": subject.get("conceptdois", []),
            "payload_multiset_sha256": subject.get("payload_multiset_sha256"),
            "candidate_file_count": len(candidate_files),
            "candidate_files": candidate_files,
            "claim_inventory_state": "PUBLIC_CANDIDATE_BYTE_FREEZE_REQUIRED",
            "terminal_disposition": None,
            "content_change_required": "UNDETERMINED_PENDING_EXACT_BYTE_REVIEW",
            "execution": {
                "queue_binding_verified": True,
                "public_candidate_bytes_frozen": False,
                "review_required": True,
                "zenodo_mutation_executed": False,
                "authorization_header_used": False,
                "secret_used": False
            },
            "completion_claims": {
                "claim_inventory_complete": False,
                "claim_disposition_complete": False,
                "pass": False,
                "final_pass": False,
                "effect_ack_done": False
            },
            "next_deterministic_effect": "FREEZE_EXACT_PUBLIC_CANDIDATE_BYTES_AND_DISPOSITION_SUBJECT"
        }
        receipt["receipt_payload_sha256"] = canonical_sha256(receipt)
        write_json(out / "subjects" / f"{subject['subject_id']}.json", receipt)
        subject_receipts.append(receipt)

    aggregate = {
        "schema": "qikvrt_content_disposition_batch_receipt_v2",
        "batch_id": EXPECTED_BATCH,
        "source_authority": EXPECTED_AUTHORITY,
        "source_mirror": EXPECTED_MIRROR,
        "queue_canonical_sha256": canonical_sha256(queue),
        "subject_count": len(subject_receipts),
        "subject_ids": EXPECTED_SUBJECTS,
        "state": "BLOCK_PUBLIC_CANDIDATE_BYTE_FREEZE_AND_CLAIM_REVIEW",
        "execution": {
            "queue_binding_verified": True,
            "all_six_subject_receipts_created": len(subject_receipts) == 6,
            "review_required_count": sum(1 for r in subject_receipts if r["execution"]["review_required"]),
            "terminal_claim_disposition_count": 0,
            "zenodo_methods": ["GET"],
            "zenodo_mutation_executed": False,
            "authorization_header_used": False,
            "secret_used": False
        },
        "completion_claims": {
            "batch_executed": True,
            "batch_complete": False,
            "all_content_claims_dispositioned": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False
        },
        "next_deterministic_effect": "CREATE_EXACT_PUBLIC_CANDIDATE_BYTE_FREEZE_WORK_UNIT_FOR_BATCH_002"
    }
    aggregate["receipt_payload_sha256"] = canonical_sha256(aggregate)
    write_json(out / "CONTENT_DISPOSITION_BATCH_002_RECEIPT.json", aggregate)
    return aggregate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    receipt = execute(args.queue, args.out)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
