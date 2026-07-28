#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Non-regression checks for the canonical Zenodo union/disposition transaction."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = ROOT / "release" / "zenodo-corpus-proof-2026-07-28"
OUTPUT = BASE / "canonical-union"
TOOL = ROOT / "tools" / "qikvrt_zenodo_union_disposition.py"
RECEIPT = OUTPUT / "CANONICAL_UNION_AND_DISPOSITION_RECEIPT.json"
UNION = OUTPUT / "CANONICAL_UNION_CORPUS.json"
INDEX = OUTPUT / "CONTENT_CLAIM_DISPOSITION_INDEX.json"
QUEUE = OUTPUT / "CONTENT_CLAIM_DISPOSITION_QUEUE.json"
REPORT = OUTPUT / "CANONICAL_UNION_REPORT_DE.md"
FIXED_OBSERVED_AT = "2026-07-28T16:20:00+02:00"

EXPECTED_IDS = {
    20712301, 21244412, 21245282, 21245951, 21247297, 21247388,
    21252415, 21252649, 21266670, 21267021, 21482023, 21488116,
    21498773, 21498774, 21500322, 21501365, 21515074, 21518464,
    21529081, 21582781, 21633411, 21636774, 21640160, 21640173,
}


def load(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), path
    return value


def main() -> int:
    assert TOOL.is_file()
    if not RECEIPT.is_file():
        print("SKIP: canonical union outputs have not yet been materialized")
        return 0

    subprocess.run(
        [sys.executable, "-B", str(TOOL), "--observed-at", FIXED_OBSERVED_AT, "--check"],
        cwd=ROOT,
        check=True,
    )

    union = load(UNION)
    index = load(INDEX)
    queue = load(QUEUE)
    receipt = load(RECEIPT)

    assert union["schema"] == "qikvrt_zenodo_canonical_union_corpus_v1"
    assert union["record_count"] == 24
    assert set(union["record_ids"]) == EXPECTED_IDS
    assert union["source_corpora"]["authenticated_observation_record_count"] == 11
    assert union["source_corpora"]["public_reconciliation_record_count"] == 13
    assert union["source_corpora"]["source_sets_disjoint"] is True
    assert len(union["records"]) == 24
    assert len({record["record_id"] for record in union["records"]}) == 24
    assert all(record["public_files"] for record in union["records"])
    assert all(
        public_file["public_byte_redownload_verified"] is True
        for record in union["records"]
        for public_file in record["public_files"]
    )

    assert index["schema"] == "qikvrt_content_claim_disposition_index_v1"
    assert index["state"] == "STARTED"
    assert index["record_count"] == 24
    assert len(index["records"]) == 24
    assert index["claim_subject_count"] <= 24
    assert index["completion_claims"]["content_claim_disposition_started"] is True
    assert index["completion_claims"]["all_content_claims_dispositioned"] is False

    assert queue["schema"] == "qikvrt_content_claim_disposition_queue_v1"
    assert queue["state"] == "ACTIVE"
    assert queue["active_batch"]["batch_id"] == "CONTENT-DISPOSITION-BATCH-001"
    assert queue["active_batch"]["state"] == "READY"
    assert 1 <= queue["active_batch"]["subject_count"] <= 6
    assert queue["completion_claims"]["first_batch_executed"] is False
    assert queue["next_deterministic_effect"] == "EXECUTE_CONTENT_DISPOSITION_BATCH_001"

    assert receipt["schema"] == "qikvrt_canonical_union_and_disposition_receipt_v1"
    assert receipt["state"] == "CANONICAL_UNION_BUILT_CONTENT_DISPOSITION_STARTED"
    assert receipt["record_count"] == 24
    assert receipt["validation"]["authenticated_source_set_exact"] is True
    assert receipt["validation"]["reconciled_source_set_exact"] is True
    assert receipt["validation"]["source_sets_disjoint"] is True
    assert receipt["validation"]["canonical_union_record_count"] is True
    assert receipt["validation"]["all_records_have_verified_public_files"] is True
    assert receipt["validation"]["one_disposition_row_per_record"] is True
    assert receipt["validation"]["first_batch_selected"] is True

    completion = receipt["completion_claims"]
    assert completion["canonical_union_built"] is True
    assert completion["content_claim_disposition_started"] is True
    for key in (
        "all_content_claims_dispositioned",
        "content_correction_review_complete",
        "all_required_corrected_candidates_returned_to_owner",
        "proof_corpus_published_on_zenodo",
        "mirror_synchronized",
        "pass",
        "final_pass",
        "effect_ack_done",
    ):
        assert completion[key] is False, key

    report = REPORT.read_text(encoding="utf-8")
    assert "Kein `PASS`, `FINAL_PASS` oder `EFFECT_ACK_DONE`" in report
    assert "EXECUTE_CONTENT_DISPOSITION_BATCH_001" in report
    print("CANONICAL_UNION_DISPOSITION_TEST=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
