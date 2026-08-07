# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "UNIVERSAL_IO_KNOWLEDGE_PUBLICATION_PIPELINE_V1.json"
DOC = ROOT / "docs" / "UNIVERSAL_IO_KNOWLEDGE_PUBLICATION_PIPELINE.md"
AI = ROOT / "AI"
RECEIPT = ROOT / "state" / "io" / "receipts" / "2026-08-07T1543+0200-product-owner-universal-io-publication-requirement.json"


class UniversalIOKnowledgePublicationPipelineTest(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_acceptance_criterion_is_explicit(self):
        acceptance = self.policy["acceptance_criterion"]
        self.assertTrue(acceptance["all_interface_io_is_persisted"])
        self.assertTrue(acceptance["all_modalities"])
        self.assertTrue(acceptance["durable_repository_receipt_required"])
        self.assertTrue(acceptance["machine_proof_when_formalizable"])
        self.assertTrue(acceptance["automation_required"])

    def test_pipeline_orders_persistence_before_proof_and_publication(self):
        pipeline = self.policy["pipeline"]
        self.assertLess(pipeline.index("PERSIST"), pipeline.index("PROVE_OR_MARK_NONFORMALIZABLE"))
        self.assertLess(pipeline.index("PROVE_OR_MARK_NONFORMALIZABLE"), pipeline.index("BUILD_PUBLICATION_CANDIDATE"))
        self.assertLess(pipeline.index("RUN_APPLICABLE_GATES"), pipeline.index("REQUEST_OR_CONSUME_SEPARATE_EXTERNAL_EFFECT_AUTHORIZATION"))
        self.assertLess(pipeline.index("REQUEST_OR_CONSUME_SEPARATE_EXTERNAL_EFFECT_AUTHORIZATION"), pipeline.index("PUBLISH_ZENODO_IF_ELIGIBLE"))

    def test_external_effects_remain_fail_closed(self):
        self.assertEqual(self.policy["publication"]["zenodo"]["default_effect"], "DISABLED")
        self.assertEqual(self.policy["publication"]["ietf"]["default_effect"], "DISABLED")
        self.assertIn("separate_external_effect_authorization", self.policy["publication"]["zenodo"]["eligibility_requires"])
        self.assertIn("separate_external_effect_authorization", self.policy["publication"]["ietf"]["eligibility_requires"])

    def test_machine_proof_and_empirical_status_are_distinct(self):
        candidate = self.policy["knowledge_candidate"]
        self.assertIn("FORMALLY_PROVED_MODEL_RELATIVE", candidate["required_statuses"])
        self.assertIn("EMPIRICALLY_SUPPORTED", candidate["required_statuses"])
        self.assertIn("does not by itself establish physical correspondence", candidate["empirical_boundary"].lower())

    def test_ai_entrypoint_binds_contract(self):
        text = AI.read_text(encoding="utf-8")
        self.assertIn("UNIVERSAL INPUT/OUTPUT PERSISTENCE AND KNOWLEDGE PUBLICATION", text)
        self.assertIn("policy/UNIVERSAL_IO_KNOWLEDGE_PUBLICATION_PIPELINE_V1.json", text)
        self.assertIn("Manual copying from chat is not a conforming substitute", text)

    def test_product_owner_input_is_persisted(self):
        receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(receipt["actor_class"], "HUMAN_PRODUCT_OWNER")
        self.assertEqual(receipt["authorization"]["repository_internal_implementation"], "APPROVED_BY_PRODUCT_OWNER")
        self.assertFalse(receipt["authorization"]["zenodo_external_effect"] == "AUTHORIZED")
        self.assertFalse(receipt["nonclaims"]["deployed_interface_capture_complete"])

    def test_human_document_rejects_manual_copy_as_full_automation(self):
        text = DOC.read_text(encoding="utf-8")
        self.assertIn("Manual copying from a chat transcript", text)
        self.assertIn("does not satisfy the fully automated acceptance criterion", text)


if __name__ == "__main__":
    unittest.main()
