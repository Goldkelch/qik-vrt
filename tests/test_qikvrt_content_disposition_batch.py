#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tools.qikvrt_content_disposition_batch import EXPECTED_SUBJECTS, execute


def main() -> int:
    queue = Path("release/zenodo-corpus-proof-2026-07-28/canonical-union/CONTENT_CLAIM_DISPOSITION_QUEUE.json")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        receipt = execute(queue, out)
        assert receipt["batch_id"] == "CONTENT-DISPOSITION-BATCH-001"
        assert receipt["subject_count"] == 6
        assert receipt["subject_ids"] == EXPECTED_SUBJECTS
        assert receipt["state"] == "BLOCK_CANDIDATE_BYTES_AND_REVIEW"
        assert receipt["execution"]["queue_binding_verified"] is True
        assert receipt["execution"]["all_six_subject_receipts_created"] is True
        assert receipt["execution"]["review_required_count"] == 6
        assert receipt["execution"]["zenodo_mutation_executed"] is False
        assert receipt["completion_claims"]["batch_executed"] is True
        assert receipt["completion_claims"]["batch_complete"] is False
        assert receipt["completion_claims"]["pass"] is False
        assert receipt["completion_claims"]["final_pass"] is False
        assert receipt["completion_claims"]["effect_ack_done"] is False
        for subject_id in EXPECTED_SUBJECTS:
            path = out / "subjects" / f"{subject_id}.json"
            assert path.is_file()
            subject = json.loads(path.read_text(encoding="utf-8"))
            assert subject["subject_id"] == subject_id
            assert subject["execution"]["review_required"] is True
            assert subject["completion_claims"]["pass"] is False
    print("CONTENT_DISPOSITION_BATCH_001_TESTS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
