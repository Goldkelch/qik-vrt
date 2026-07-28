#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ALLOWED = {"FORMAL_PROVED", "EMPIRICALLY_EVIDENCED", "SOURCE_BOUND", "NORMATIVE", "INTERPRETATIVE", "OPEN"}
BATCH_ID = "CONTENT-DISPOSITION-BATCH-001"
EXPECTED_SUBJECTS = [
    "SUBJECT-187cfda66d1eda16",
    "SUBJECT-45b9d1b677568ae7",
    "SUBJECT-2beab714d1dc6019",
    "SUBJECT-51a0cfc51bcbd722",
    "SUBJECT-685123cd60e2fd7b",
    "SUBJECT-d2dad396615a4c7c",
]


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def execute(queue_path: Path, output_dir: Path) -> dict:
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    active = queue.get("active_batch", {})
    if active.get("batch_id") != BATCH_ID:
        raise SystemExit("BLOCK: wrong active batch")
    subjects = active.get("subjects")
    if not isinstance(subjects, list) or [x.get("subject_id") for x in subjects] != EXPECTED_SUBJECTS:
        raise SystemExit("BLOCK: exact subject order mismatch")

    receipts = []
    for subject in subjects:
        subject_id = subject["subject_id"]
        files = subject.get("content_candidate_files") or []
        candidate_binding = {
            "file_names": files,
            "file_name_multiset_sha256": hashlib.sha256(canonical(sorted(files))).hexdigest(),
            "payload_multiset_sha256": subject["payload_multiset_sha256"],
        }
        existing_machine_binding = subject.get("disposition_state") in {
            "EXISTING_CLAIM_GRAPH_REVALIDATION_PENDING",
            "MACHINE_PROOF_BUNDLE_BINDING_PENDING",
        }
        receipt = {
            "schema": "qikvrt_content_disposition_subject_receipt_v1",
            "batch_id": BATCH_ID,
            "subject_id": subject_id,
            "record_ids": subject.get("record_ids", []),
            "candidate_binding": candidate_binding,
            "execution": {
                "existing_machine_binding_detected": existing_machine_binding,
                "claim_extraction_executed": False,
                "terminal_claim_disposition_complete": False,
                "review_required": True,
                "review_reason": "EXACT_CANDIDATE_BYTES_NOT_PRESENT_IN_REPOSITORY_EXECUTION_SCOPE" if not existing_machine_binding else "EXISTING_MACHINE_BINDING_REVALIDATION_REQUIRED",
            },
            "content_change_required": "UNDETERMINED_PENDING_CLAIM_REVIEW",
            "completion_claims": {
                "pass": False,
                "final_pass": False,
                "effect_ack_done": False,
            },
            "next_deterministic_effect": "FETCH_AND_FREEZE_EXACT_PUBLIC_CANDIDATE_BYTES_THEN_DISPOSITION_CLAIMS",
        }
        write_json(output_dir / "subjects" / f"{subject_id}.json", receipt)
        receipts.append(receipt)

    batch = {
        "schema": "qikvrt_content_disposition_batch_receipt_v1",
        "batch_id": BATCH_ID,
        "subject_count": len(receipts),
        "subject_ids": EXPECTED_SUBJECTS,
        "state": "BLOCK_CANDIDATE_BYTES_AND_REVIEW",
        "execution": {
            "queue_binding_verified": True,
            "all_six_subject_receipts_created": True,
            "terminal_claim_disposition_complete_count": 0,
            "review_required_count": 6,
            "zenodo_mutation_executed": False,
            "secret_used": False,
        },
        "completion_claims": {
            "batch_executed": True,
            "batch_complete": False,
            "all_content_claims_dispositioned": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
        "next_deterministic_effect": "CREATE_EXACT_PUBLIC_CANDIDATE_BYTE_FREEZE_WORK_UNIT_FOR_BATCH_001",
    }
    write_json(output_dir / "CONTENT_DISPOSITION_BATCH_001_RECEIPT.json", batch)
    return batch


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    execute(args.queue, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
