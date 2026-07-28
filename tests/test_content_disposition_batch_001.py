#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "release/zenodo-corpus-proof-2026-07-28/canonical-union"
OUT = BASE / "content-disposition-batch-001"
EXPECTED = [
    "SUBJECT-187cfda66d1eda16",
    "SUBJECT-45b9d1b677568ae7",
    "SUBJECT-2beab714d1dc6019",
    "SUBJECT-51a0cfc51bcbd722",
    "SUBJECT-685123cd60e2fd7b",
    "SUBJECT-d2dad396615a4c7c",
]
ALLOWED = {"FORMAL_PROVED", "EMPIRICALLY_EVIDENCED", "SOURCE_BOUND", "NORMATIVE", "INTERPRETATIVE", "OPEN"}


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> None:
    receipt = load(OUT / "CONTENT_DISPOSITION_BATCH_001_RECEIPT.json")
    batch_index = load(OUT / "CONTENT_DISPOSITION_BATCH_001_SUBJECT_INDEX.json")
    decisions = load(OUT / "CONTENT_CHANGE_DECISIONS.json")
    queue = load(BASE / "CONTENT_CLAIM_DISPOSITION_QUEUE.json")
    index = load(BASE / "CONTENT_CLAIM_DISPOSITION_INDEX.json")
    union_receipt = load(BASE / "CANONICAL_UNION_AND_DISPOSITION_RECEIPT.json")
    work_unit = load(ROOT / "work-units/EXECUTE_CONTENT_DISPOSITION_BATCH_001.json")

    assert receipt["schema"] == "qikvrt_content_disposition_batch_receipt_v1"
    assert receipt["state"] == "BATCH_001_DISPOSITIONED_NO_CONTENT_CHANGE"
    assert receipt["subject_count"] == 6
    assert [row["subject_id"] for row in receipt["subjects"]] == EXPECTED
    assert receipt["validation"]["all_public_files_byte_reverified"] is True
    assert receipt["validation"]["all_claims_terminally_classified"] is True
    assert receipt["validation"]["formal_claims_have_machine_proof_bindings"] is True
    assert receipt["completion_claims"]["batch_001_executed"] is True
    assert receipt["completion_claims"]["all_content_claims_dispositioned"] is False
    assert receipt["completion_claims"]["pass"] is False
    assert receipt["completion_claims"]["final_pass"] is False
    assert receipt["completion_claims"]["effect_ack_done"] is False

    matrices = []
    for sid in EXPECTED:
        matrix = load(OUT / "subjects" / sid / "CLAIM_MATRIX.json")
        matrices.append(matrix)
        assert matrix["subject_id"] == sid
        assert matrix["claim_count"] == len(matrix["claims"])
        assert matrix["claim_count"] > 0
        assert sum(matrix["classification_summary"].values()) == matrix["claim_count"]
        assert set(matrix["classification_summary"]) == ALLOWED
        assert matrix["content_change_decision"]["required"] is False
        assert matrix["completion_claims"]["claim_disposition_complete"] is True
        for claim in matrix["claims"]:
            assert claim["epistemic_class"] in ALLOWED
            assert claim["statement"].strip()
            if claim["epistemic_class"] == "FORMAL_PROVED":
                assert claim["proof_refs"]
    assert receipt["claim_count"] == sum(matrix["claim_count"] for matrix in matrices)
    assert batch_index["claim_count"] == receipt["claim_count"]
    assert decisions["changed_document_count"] == 0
    assert decisions["owner_return_required"] is False
    assert all(row["content_change_required"] is False for row in decisions["decisions"])

    by_subject = {row["subject_id"]: row for row in index["claim_subjects"]}
    for sid in EXPECTED:
        row = by_subject[sid]
        assert row["claim_disposition_complete"] is True
        assert row["content_change_required"] is False
        assert row["disposition_state"] == "DISPOSITIONED_NO_CONTENT_CHANGE"
        matrix = load(ROOT / row["claim_matrix_path"])
        digest = hashlib.sha256(canonical(matrix)).hexdigest()
        assert digest == row["claim_matrix_sha256"]

    assert queue["completion_claims"]["first_batch_executed"] is True
    assert queue["active_batch"]["batch_id"] == "CONTENT-DISPOSITION-BATCH-002"
    assert queue["active_batch"]["state"] == "READY"
    assert queue["remaining_subject_count"] == 7
    assert queue["next_deterministic_effect"] == "EXECUTE_CONTENT_DISPOSITION_BATCH_002"
    assert union_receipt["completion_claims"]["content_disposition_batch_001_completed"] is True
    assert union_receipt["completion_claims"]["all_content_claims_dispositioned"] is False
    assert union_receipt["completion_claims"]["pass"] is False
    assert work_unit["work_unit_id"] == "EXECUTE-CONTENT-DISPOSITION-BATCH-001-20260728"
    assert work_unit["pass"] is False
    print("test_content_disposition_batch_001: PASS")


if __name__ == "__main__":
    main()
