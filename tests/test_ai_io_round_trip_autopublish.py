import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy/AI_IO_ROUND_TRIP_AUTOPUBLISH_V1.json"
DELEGATION = ROOT / "state/authorization/delegations/OWNER_AI_IO_ROUND_TRIP_AUTOPUBLISH_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_io_round_trip_autopublish.yml"
AI = ROOT / "AI"


class TestAIInputOutputRoundTripAutopublish(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        self.delegation = json.loads(DELEGATION.read_text(encoding="utf-8"))

    def test_every_declared_io_direction_is_receipted_and_silent_drop_forbidden(self):
        capture = self.policy["capture"]
        self.assertTrue(capture["mandatory"])
        self.assertEqual(capture["silent_drop"], "FORBIDDEN")
        for required in ("HUMAN_INPUT", "AI_OUTPUT", "TOOL_INPUT", "TOOL_OUTPUT", "AUDIO_INPUT", "IMAGE_INPUT", "DOCUMENT_INPUT", "EXTERNAL_EFFECT_RESULT"):
            self.assertIn(required, capture["directions"])

    def test_secret_bytes_are_never_repository_payload(self):
        capture = self.policy["capture"]
        self.assertIn("Secrets", capture["secret_rule"])
        self.assertIn("DIGEST_ONLY_SECRET_OR_RIGHTS_BOUND", capture["persistence_modes"])
        self.assertEqual(self.delegation["credential_policy"]["repository_storage"], "FORBIDDEN")
        self.assertEqual(self.delegation["credential_policy"]["chat_request"], "FORBIDDEN")

    def test_granularity_preserves_atomic_membership(self):
        self.assertEqual(self.policy["granularity"]["levels"], ["EVENT", "WORK_UNIT", "CLAIM", "PROOF_BUNDLE", "PUBLICATION_BUNDLE"])
        self.assertIn("never erase", self.policy["granularity"]["rule"])
        self.assertTrue(self.policy["acceptance_criteria"]["claim_aggregation_preserves_event_membership"])

    def test_machine_proof_is_mandatory_before_zenodo(self):
        proof = self.policy["machine_proof"]
        self.assertTrue(proof["mandatory_before_publication"])
        self.assertTrue(proof["no_proof_no_publication"])
        self.assertIn("LEAN_KERNEL_PROOF", proof["accepted_proof_classes"])
        self.assertIn("EVIDENCE_BOUND_CORRESPONDENCE_TEST", proof["accepted_proof_classes"])
        self.assertIn("tools/qikvrt_zenodo_publish.py", self.policy["publication_routing"]["zenodo"]["generic_publisher"])

    def test_ietf_is_conditional_on_normative_interoperability_delta(self):
        ietf = self.policy["publication_routing"]["ietf"]
        joined = " ".join(ietf["required_when"])
        self.assertIn("NORMATIVE_PROTOCOL_DELTA", joined)
        self.assertIn("INTEROPERABILITY_SPEC_DELTA", joined)
        self.assertIn("purely scientific claims without a normative protocol delta", ietf["not_required_for"])

    def test_standing_delegation_derives_only_final_exact_single_use_effect(self):
        constraints = self.delegation["derived_authorization_constraints"]
        self.assertTrue(constraints["unknown_future_bytes_are_not_exactly_authorized"])
        self.assertTrue(constraints["derive_only_after_final_artifact_freeze"])
        self.assertTrue(constraints["derive_only_after_machine_proof_acceptance"])
        self.assertTrue(constraints["derive_only_after_prepublication_return"])
        self.assertTrue(constraints["single_use"])
        self.assertEqual(constraints["natural_person_principal"], "Ingolf Lohmann")

    def test_workflow_is_recurring_and_calls_existing_exact_zenodo_publisher(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cron: "41 * * * *"', text)
        self.assertIn("qikvrt_io_round_trip.py sweep --apply", text)
        self.assertIn("qikvrt_io_zenodo_authorize.py", text)
        self.assertIn("qikvrt_zenodo_publish.py", text)
        self.assertNotIn("git push --force", text)

    def test_completion_claims_remain_false(self):
        for value in (self.policy["completion_claims"], self.delegation["completion_claims"]):
            self.assertIs(value["PASS"], False)
            self.assertIs(value["FINAL_PASS"], False)
            self.assertIs(value["EFFECT_ACK_DONE"], False)


if __name__ == "__main__":
    unittest.main()
