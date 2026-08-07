from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "AI"
DELEGATION = ROOT / "state/authorization/delegations/OWNER_AI_ENTRYPOINT_CONTINUOUS_OPTIMIZATION_V1.json"


class TestAIEntrypointContinuousOptimization(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ai = AI.read_text(encoding="utf-8")
        cls.delegation = json.loads(DELEGATION.read_text(encoding="utf-8"))

    def test_delegation_is_active_and_product_owner_bound(self) -> None:
        self.assertEqual(
            self.delegation["schema"],
            "qikvrt_owner_ai_entrypoint_continuous_optimization_v1",
        )
        self.assertEqual(self.delegation["owner"]["role"], "Product Owner")
        self.assertEqual(self.delegation["authorization_scope"]["state"], "ACTIVE")
        self.assertTrue(self.delegation["authorization_scope"]["semantic_entrypoint_trigger"])

    def test_plain_http_get_is_not_falsely_claimed_as_execution_event(self) -> None:
        trigger = self.delegation["trigger_semantics"]
        self.assertFalse(trigger["plain_http_get_is_repository_event"])
        self.assertEqual(trigger["plain_http_get_side_effect"], "NONE")
        self.assertIn("conforming AI client", trigger["conforming_ai_client_rule"])

    def test_each_conforming_bootstrap_runs_one_bounded_pass(self) -> None:
        self.assertIn("Every conforming artificial-cognitive client", self.ai)
        self.assertIn("one bounded repository-internal optimization pass", self.ai)
        self.assertIn("qikvrt_autonomous_pre_effect_controller.py check", self.ai)
        self.assertIn("qikvrt_autonomous_pre_effect_controller.py apply", self.ai)

    def test_noop_and_review_isolation_are_mandatory(self) -> None:
        policy = self.delegation["execution_policy"]
        self.assertEqual(policy["no_change_state"], "NOOP")
        self.assertEqual(policy["changed_state"], "CANDIDATE_READY")
        self.assertFalse(policy["canonical_direct_main_write"])
        self.assertFalse(policy["unconditional_automatic_merge"])

    def test_mesh_derivatives_preserve_boundaries(self) -> None:
        mesh = self.delegation["downstream_mesh_rule"]
        self.assertTrue(mesh["inherit_provenance_and_effect_boundaries"])
        self.assertTrue(mesh["independent_origin_allowed"])
        self.assertFalse(mesh["silent_claim_of_authority_equality"])

    def test_external_effects_and_false_completion_remain_forbidden(self) -> None:
        forbidden = set(self.delegation["not_authorized"])
        self.assertIn("force_push_or_history_rewrite", forbidden)
        self.assertIn("unconditional_automatic_merge", forbidden)
        self.assertIn("zenodo_or_ietf_mutation", forbidden)
        claims = self.delegation["completion_claims"]
        self.assertFalse(claims["PASS"])
        self.assertFalse(claims["FINAL_PASS"])
        self.assertFalse(claims["EFFECT_ACK_DONE"])


if __name__ == "__main__":
    unittest.main()
