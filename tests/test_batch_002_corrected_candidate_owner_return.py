#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Regression checks for the Batch-002 corrected-candidate owner return."""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import unittest
from typing import Any

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = REPOSITORY_ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import qikvrt_zenodo_machine_proof as machine_proof  # noqa: E402

BASE = pathlib.PurePosixPath(
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-002/corrected-candidate-owner-return"
)
RECEIPT_PATH = str(BASE / "PREPUBLICATION_RETURN_RECEIPT.json")
CANDIDATE_PATH = str(BASE / "PUBLICATION_CORRECTED_CANDIDATE.json")
CHANGE_NOTICE_PATH = str(BASE / "CHANGE_NOTICE.md")
MACHINE_CHANGE_NOTICE_PATH = str(BASE / "CHANGE_NOTICE.json")
BOUNDARY_PATH = str(BASE / "EVIDENCE_BOUNDARY.md")
CLAIM_MATRIX_PATH = (
    "release/zenodo-corpus-proof-2026-07-28/canonical-union/"
    "content-disposition-batch-002/terminal-disposition/subjects/"
    "SUBJECT-43c59da1cfd26267/CLAIM_MATRIX.json"
)
PUBLICATION_ID = "ontology-des-unterschieds-reverse-engineering-v2-candidate"
EXPECTED_CHANGED_CLAIMS = {
    "21582781-META-REVIEW-md-0002",
    "21582781-META-REVIEW-md-0003",
    "21582781-META-REVIEW-md-0012",
    "21582781-META-REVIEW-md-0013",
    "21582781-ORIGINAL-ARTICLE-md-0001",
    "21582781-ORIGINAL-ARTICLE-md-0065",
    "21582781-ORIGINAL-ARTICLE-md-0067",
}


def load_json(relative: str) -> dict[str, Any]:
    path = REPOSITORY_ROOT / pathlib.PurePosixPath(relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected object in {relative}")
    return value


def identity(relative: str) -> dict[str, Any]:
    path = REPOSITORY_ROOT / pathlib.PurePosixPath(relative)
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": hashlib.sha1(  # noqa: S324 - canonical Git identity
            f"blob {len(data)}\0".encode("ascii") + data
        ).hexdigest(),
    }


class Batch002CorrectedCandidateOwnerReturnTests(unittest.TestCase):
    def test_return_receipt_binds_every_candidate_byte(self) -> None:
        receipt = load_json(RECEIPT_PATH)
        candidate_files = receipt["candidate_files"]
        self.assertIsInstance(candidate_files, list)
        self.assertGreater(len(candidate_files), 0)
        candidate_by_path = {item["path"]: item for item in candidate_files}
        self.assertEqual(len(candidate_by_path), len(candidate_files))

        validated = machine_proof.validate_return_receipt(
            REPOSITORY_ROOT,
            RECEIPT_PATH,
            PUBLICATION_ID,
            candidate_by_path,
            True,
            CHANGE_NOTICE_PATH,
        )
        self.assertEqual(validated, receipt)
        for relative, declared in candidate_by_path.items():
            observed = identity(relative)
            self.assertEqual(observed["bytes"], declared["bytes"])
            self.assertEqual(observed["sha256"], declared["sha256"])
            self.assertEqual(observed["git_blob_sha1"], declared["git_blob_sha1"])

    def test_return_is_owner_specific_and_has_visible_notice(self) -> None:
        receipt = load_json(RECEIPT_PATH)
        self.assertEqual(receipt["schema"], "qikvrt_prepublication_return_receipt_v1")
        self.assertEqual(receipt["publication_id"], PUBLICATION_ID)
        self.assertTrue(receipt["content_changed"])
        self.assertEqual(set(receipt["changed_claim_ids"]), EXPECTED_CHANGED_CLAIMS)
        self.assertEqual(receipt["change_notice_path"], CHANGE_NOTICE_PATH)
        returned = receipt["return"]
        self.assertIs(returned["candidate_returned_to_owner"], True)
        self.assertEqual(returned["owner_name"], "Ingolf Lohmann")
        self.assertEqual(returned["owner_type"], "NATURAL_PERSON")
        self.assertIs(returned["visible_change_notice_returned"], True)
        self.assertTrue(returned["return_channel"])
        self.assertTrue(returned["returned_at"].endswith("Z"))

    def test_candidate_preserves_truth_boundary_and_blocks_upload(self) -> None:
        candidate = load_json(CANDIDATE_PATH)
        self.assertEqual(candidate["publication_id"], PUBLICATION_ID)
        self.assertEqual(candidate["batch_id"], "CONTENT-DISPOSITION-BATCH-002")
        self.assertEqual(candidate["subject_id"], "SUBJECT-43c59da1cfd26267")
        self.assertFalse(candidate["historical_record"]["historical_bytes_mutated"])
        self.assertTrue(candidate["completion_claims"]["corrected_candidate_materialized"])
        self.assertTrue(candidate["completion_claims"]["candidate_returned_to_owner"])
        self.assertFalse(candidate["completion_claims"]["zenodo_corpus_complete"])
        self.assertFalse(candidate["completion_claims"]["pass"])
        self.assertFalse(candidate["completion_claims"]["final_pass"])
        self.assertFalse(candidate["completion_claims"]["effect_ack_done"])
        self.assertFalse(candidate["authorization"]["proof_bundle_complete"])
        self.assertFalse(candidate["authorization"]["exact_upload_authorization"])
        self.assertFalse(candidate["authorization"]["production_upload_authorized"])
        self.assertFalse(candidate["authorization"]["zenodo_mutation_performed"])
        self.assertEqual(
            candidate["next_deterministic_effect"],
            "OWNER_ACCEPT_OR_REJECT_BATCH_002_CORRECTED_CANDIDATE",
        )

    def test_machine_change_notice_matches_exact_candidate(self) -> None:
        notice = load_json(MACHINE_CHANGE_NOTICE_PATH)
        self.assertEqual(notice["publication_id"], PUBLICATION_ID)
        self.assertEqual(set(notice["changed_claim_ids"]), EXPECTED_CHANGED_CLAIMS)
        self.assertEqual(notice["corrected_candidate"]["exact_candidate_path"], CANDIDATE_PATH)
        candidate_identity = identity(CANDIDATE_PATH)
        self.assertEqual(notice["corrected_candidate"]["bytes"], candidate_identity["bytes"])
        self.assertEqual(notice["corrected_candidate"]["sha256"], candidate_identity["sha256"])
        self.assertEqual(
            notice["corrected_candidate"]["git_blob_sha1"],
            candidate_identity["git_blob_sha1"],
        )
        self.assertFalse(notice["effects"]["historical_zenodo_bytes_mutated"])
        self.assertFalse(notice["effects"]["new_zenodo_version_created"])
        self.assertFalse(notice["effects"]["production_upload_authorized"])
        self.assertFalse(notice["effects"]["zenodo_corpus_complete"])

    def test_boundary_covers_only_existing_claims(self) -> None:
        matrix = load_json(CLAIM_MATRIX_PATH)
        claim_ids = {claim["claim_id"] for claim in matrix["claims"]}
        self.assertTrue(EXPECTED_CHANGED_CLAIMS.issubset(claim_ids))
        self.assertEqual(matrix["claim_count"], len(matrix["claims"]))
        boundary = (REPOSITORY_ROOT / pathlib.PurePosixPath(BOUNDARY_PATH)).read_text(
            encoding="utf-8"
        )
        for claim_id in EXPECTED_CHANGED_CLAIMS:
            self.assertIn(claim_id, boundary)
        self.assertIn("PRODUCTION_UPLOAD_AUTHORIZED = false", boundary)
        self.assertIn("FINAL_PASS                   = false", boundary)


if __name__ == "__main__":
    unittest.main()
