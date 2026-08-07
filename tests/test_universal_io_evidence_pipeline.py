# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "qikvrt_io_evidence_pipeline.py"
spec = importlib.util.spec_from_file_location("qikvrt_io_evidence_pipeline", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class UniversalIOEvidencePipelineTests(unittest.TestCase):
    def event(self):
        return {
            "direction": "INPUT",
            "modality": "text",
            "interface": "human_machine",
            "payload": "A bounded test assertion.",
            "provenance": {"complete": True, "actor": "test-human"},
            "rights": {"publication_clear": True},
            "privacy": {"repository_payload_allowed": True},
            "epistemic_type": "ASSERTION",
            "scientific_status": "FORMAL_TEST_ONLY",
            "parent_evidence": ["test-parent"],
            "knowledge": {
                "novelty": "NEW",
                "granularity": "PUBLICATION_UNIT",
                "connectivity": "CANONICALLY_CONNECTED",
                "machine_check": {
                    "status": "PASS",
                    "scope": "REGRESSION_PREDICATE",
                    "receipt_sha256": "a" * 64
                },
                "standards_relevance": True,
                "ietf_materialization_valid": True
            },
            "publication_authorization": {"authorized": True},
            "repository_state": {"exact_head_verified": True}
        }

    def test_machine_checked_candidate_routes_to_both_targets(self):
        receipt = module.build_receipt(self.event())
        classification = receipt["classification"]
        self.assertEqual(classification["knowledge_state"], "MACHINE_CHECKED")
        self.assertTrue(classification["publication"]["zenodo_eligible"])
        self.assertTrue(classification["publication"]["ietf_eligible"])
        self.assertFalse(classification["publication"]["scientific_validation_inferred"])
        self.assertFalse(classification["publication"]["ietf_acceptance_inferred"])

    def test_missing_effect_authorization_persists_but_blocks_publication(self):
        event = self.event()
        event["publication_authorization"]["authorized"] = False
        receipt = module.build_receipt(event)
        self.assertEqual(receipt["classification"]["knowledge_state"], "MACHINE_CHECKED")
        self.assertFalse(receipt["classification"]["publication"]["zenodo_eligible"])
        self.assertFalse(receipt["classification"]["publication"]["ietf_eligible"])

    def test_sensitive_payload_can_be_digest_only(self):
        event = self.event()
        event["privacy"] = {
            "repository_payload_allowed": False,
            "omission_reason": "sensitive test payload"
        }
        receipt = module.build_receipt(event)
        self.assertEqual(receipt["payload_persistence"], "DIGEST_ONLY")
        self.assertIsNone(receipt["payload"])
        self.assertEqual(len(receipt["payload_sha256"]), 64)

    def test_receipt_is_idempotently_persisted_and_verifiable(self):
        receipt = module.build_receipt(self.event())
        with tempfile.TemporaryDirectory() as directory:
            path1 = module.persist_receipt(receipt, Path(directory))
            path2 = module.persist_receipt(receipt, Path(directory))
            self.assertEqual(path1, path2)
            loaded = json.loads(path1.read_text(encoding="utf-8"))
            expected = loaded.pop("receipt_sha256")
            observed = module.sha256_bytes(module.canonical_json(loaded))
            self.assertEqual(expected, observed)

    def test_machine_check_never_infers_scientific_validation(self):
        receipt = module.build_receipt(self.event())
        self.assertTrue(receipt["boundaries"]["machine_check_is_not_empirical_validation"])
        self.assertTrue(receipt["boundaries"]["zenodo_deposit_is_not_scientific_consensus"])
        self.assertTrue(receipt["boundaries"]["ietf_submission_is_not_ietf_acceptance"])


if __name__ == "__main__":
    unittest.main()
