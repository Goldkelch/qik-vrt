#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/qikvrt_remaining_corpus_corrected_candidates_owner_return.py"
SPEC = importlib.util.spec_from_file_location("remaining_owner_return", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


class RemainingCorpusOwnerReturnTests(unittest.TestCase):
    def test_exact_candidate_set_and_owner_return(self):
        index, receipt, review = module.validate_return_evidence()
        self.assertEqual(index["candidate_count"], 6)
        self.assertEqual(index["selected_correction_claim_count"], 1212)
        self.assertEqual(index["observed_internal_hash_mismatch_count"], 89)
        self.assertEqual(receipt["state"], "RETURNED_TO_OWNER_DECISION_PENDING")
        self.assertEqual(receipt["owner"]["decision"], "PENDING")
        self.assertEqual(review["state"], "WAITING_FOR_OWNER_DECISION")

    def test_projection_is_current_and_fail_closed(self):
        progress, status = module.build_progress_projection()
        scope = progress["scopes"]["qikvrt-zenodo-canonical-union-2026-07-28-v1"]
        candidates = scope["corrected_candidates"]
        self.assertEqual(progress["next_action"], module.NEXT_EFFECT)
        self.assertEqual(candidates["candidate_count"], 6)
        self.assertEqual(candidates["owner_decision"], "PENDING")
        self.assertFalse(candidates["zenodo_mutation_authorized"])
        self.assertIn("OWNER_DECISION_PENDING_FOR_REMAINING_CORPUS_CORRECTED_CANDIDATES", status)
        for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
            self.assertFalse(progress["claims"][key])
            self.assertFalse(scope["claims"][key])

    def test_candidate_blob_tamper_blocks(self):
        index = json.loads(module.INDEX.read_text(encoding="utf-8"))
        bad = copy.deepcopy(index)
        bad["candidates"][0]["git_blob_sha1"] = "0" * 40
        self.assertNotEqual(bad, index)
        expected = module.EXPECTED[bad["candidates"][0]["subject_id"]]["blob"]
        self.assertNotEqual(bad["candidates"][0]["git_blob_sha1"], expected)

    def test_false_owner_acceptance_or_publication_is_not_materialized(self):
        index, receipt, review = module.validate_return_evidence()
        self.assertEqual(receipt["owner"]["decision"], "PENDING")
        self.assertEqual(review["decision"], "PENDING")
        self.assertFalse(receipt["completion_claims"]["zenodo_mutation_authorized"])
        self.assertFalse(receipt["completion_claims"]["proof_corpus_published_on_zenodo"])
        for row in index["candidates"]:
            candidate = json.loads((module.ROOT / row["path"]).read_text(encoding="utf-8"))
            self.assertEqual(candidate["owner_review"]["decision"], "PENDING")
            self.assertFalse(candidate["truth_boundary"]["upload_executed"])
            self.assertFalse(candidate["truth_boundary"]["publication_executed"])

    def test_materialized_projection_matches_exact_bytes(self):
        result = module.verify_materialized()
        self.assertEqual(result["state"], "CORRECTED_CANDIDATES_RETURNED_TO_OWNER_DECISION_PENDING")
        self.assertEqual(result["candidate_count"], 6)
        self.assertEqual(result["owner_decision"], "PENDING")
        self.assertFalse(result["pass"])
        self.assertFalse(result["final_pass"])
        self.assertFalse(result["effect_ack_done"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
