import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / "publications" / "observation-bandwidth-causal-order-falsification-v1"
RECEIPT = ROOT / "evidence" / "systemtest" / "UNIVERSAL_TERMINAL_SYSTEMTEST_RECEIPT_V1.json"
RECEIPT_SHA = ROOT / "evidence" / "systemtest" / "UNIVERSAL_TERMINAL_SYSTEMTEST_RECEIPT_V1.sha256"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class PhysicalHypothesisPackageTests(unittest.TestCase):
    def test_required_files_exist_and_parse(self):
        required = [
            PUB / "MANUSCRIPT_EN.md",
            PUB / "STATUS_QUO_DE.md",
            PUB / "HYPOTHESIS_REGISTRY.json",
            PUB / "EXPERIMENT_PROTOCOL.md",
            PUB / "CLAIM_EVIDENCE_MATRIX.json",
            PUB / "SOURCE_BINDING.json",
            PUB / "SUBMISSION_STATUS.json",
            PUB / "SUBMISSION_ZENODO.json",
            PUB / "IEEE_SUBMISSION.md",
            PUB / "arxiv" / "main.tex",
        ]
        for path in required:
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 0, path)

        for name in [
            "HYPOTHESIS_REGISTRY.json",
            "CLAIM_EVIDENCE_MATRIX.json",
            "SOURCE_BINDING.json",
            "SUBMISSION_STATUS.json",
            "SUBMISSION_ZENODO.json",
        ]:
            self.assertIsInstance(load_json(PUB / name), dict)

    def test_source_binding_matches_persisted_systemtest_receipt(self):
        binding = load_json(PUB / "SOURCE_BINDING.json")
        receipt_bytes = RECEIPT.read_bytes()
        receipt = json.loads(receipt_bytes)
        expected_digest = binding["executed_systemtest"]["receipt_sha256"]

        self.assertEqual(hashlib.sha256(receipt_bytes).hexdigest(), expected_digest)
        self.assertIn(expected_digest, RECEIPT_SHA.read_text(encoding="utf-8"))
        self.assertEqual(receipt["integrated_head"], binding["executed_systemtest"]["head"])
        self.assertEqual(receipt["integrated_tree"], binding["executed_systemtest"]["tree"])
        self.assertEqual(receipt["run_id"], binding["executed_systemtest"]["run_id"])
        self.assertEqual(receipt["causal_source_head"], binding["causal_m68000_source"]["head"])
        self.assertTrue(receipt["post_effect_reobservation_observed"])
        self.assertFalse(receipt["authority_main_effect"])
        self.assertFalse(receipt["physical_megast_execution"])
        self.assertFalse(receipt["general_effect_ack_done"])
        self.assertEqual(receipt["external_effect"], "NONE")

    def test_active_hypotheses_are_falsifiable_and_unexecuted(self):
        registry = load_json(PUB / "HYPOTHESIS_REGISTRY.json")
        active = registry["active_hypotheses"]
        self.assertEqual(
            [item["id"] for item in active],
            ["H-OBS-01", "H-EFF-02", "H-CAU-03", "H-ORD-04", "H-PHY-05"],
        )
        required_fields = {
            "id",
            "tier",
            "status",
            "claim",
            "null_hypothesis",
            "alternative_hypothesis",
            "independent_variables",
            "dependent_variables",
            "primary_endpoint",
            "controls",
            "minimum_trials",
            "decision_rule",
            "falsification_condition",
            "not_claimed",
        }
        for hypothesis in active:
            self.assertTrue(required_fields.issubset(hypothesis), hypothesis["id"])
            self.assertEqual(hypothesis["status"], "PROPOSED_NOT_EXECUTED")
            self.assertTrue(hypothesis["null_hypothesis"].strip())
            self.assertTrue(hypothesis["decision_rule"].strip())
            self.assertTrue(hypothesis["falsification_condition"].strip())
            self.assertTrue(hypothesis["primary_endpoint"].strip())
            self.assertTrue(hypothesis["minimum_trials"])

    def test_physical_identity_claim_fails_closed(self):
        registry = load_json(PUB / "HYPOTHESIS_REGISTRY.json")
        blocked = {item["id"]: item for item in registry["blocked_claims"]}
        self.assertEqual(blocked["H-PHYS-00"]["status"], "HOLD_NO_OPERATIONALIZATION")
        self.assertIn("PHYSICAL_TIME == QIKVRT_CAUSAL_TIME", blocked["H-PHYS-00"]["statement"])

        matrix = load_json(PUB / "CLAIM_EVIDENCE_MATRIX.json")
        claims = {item["claim_id"]: item for item in matrix["entries"]}
        self.assertEqual(claims["C-PHYS-00"]["status"], "HOLD_NO_OPERATIONALIZATION")
        self.assertEqual(claims["C-BOUND-01"]["status"], "NOT_SUPPORTED")
        self.assertEqual(claims["C-BOUND-02"]["status"], "NOT_SUPPORTED")

    def test_submission_channels_remain_pre_effect(self):
        status = load_json(PUB / "SUBMISSION_STATUS.json")
        self.assertEqual(status["external_effect"], "NONE")
        self.assertEqual(status["channels"]["zenodo"], "PREPARED_NOT_UPLOADED")
        self.assertEqual(status["channels"]["arxiv"], "PREPARED_NOT_SUBMITTED")
        self.assertEqual(status["channels"]["ieee"], "PREPARED_NOT_SUBMITTED")
        self.assertIsNone(status["identifiers"]["doi"])
        self.assertIsNone(status["identifiers"]["arxiv_id"])
        self.assertEqual(status["review"]["independent_scientific_review"], "NOT_OBSERVED")

        zenodo = load_json(PUB / "SUBMISSION_ZENODO.json")
        self.assertEqual(zenodo["submission_status"], "PREPARED_NOT_UPLOADED")
        self.assertNotIn("doi", zenodo["metadata"])

    def test_prose_preserves_observation_and_physics_boundaries(self):
        manuscript = (PUB / "MANUSCRIPT_EN.md").read_text(encoding="utf-8")
        status_de = (PUB / "STATUS_QUO_DE.md").read_text(encoding="utf-8")
        protocol = (PUB / "EXPERIMENT_PROTOCOL.md").read_text(encoding="utf-8")
        tex = (PUB / "arxiv" / "main.tex").read_text(encoding="utf-8")

        for token in [
            "REPOSITORY_EVIDENCE != PHYSICAL_EVIDENCE",
            "PHYSICAL_TIME == QIKVRT_CAUSAL_TIME",
            "HOLD_NO_OPERATIONALIZATION",
            "PROPOSED_NOT_EXECUTED",
            "CAUSALITY != SEQUENCE",
        ]:
            self.assertIn(token, manuscript)

        self.assertIn("Verantwortung braucht eine Abtastrate", status_de)
        self.assertIn("Repository-Evidenz", status_de)
        self.assertIn("SUPPORTED_WITHIN_REGISTERED_SCOPE", protocol)
        self.assertIn("Repository evidence motivates this chain", tex)

    def test_formal_manuscript_and_physical_program_do_not_transfer_evidence(self):
        binding = load_json(PUB / "SOURCE_BINDING.json")
        formal = binding["formal_computational_manuscript"]
        self.assertEqual(formal["pr"], 797)
        self.assertFalse(formal["evidence_transfer"])
        self.assertEqual(binding["new_physical_results"], [])
        self.assertEqual(binding["hypotheses_status"], "PROPOSED_NOT_EXECUTED")


if __name__ == "__main__":
    unittest.main()
