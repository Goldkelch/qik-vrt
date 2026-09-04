# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import json
from pathlib import Path
import unittest

from tools.qikvrt_execution_precedence import (
    evaluate_repository_convergence,
    next_eligible,
    validate_policy,
)

POLICY = Path("policy/QIKVRT_EXECUTION_PRECEDENCE_V1.json")


class ExecutionPrecedenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    @staticmethod
    def _zero_observation(repository: str) -> dict[str, object]:
        return {
            "repository": repository,
            "observed_at": "2026-09-04T12:00:00Z",
            "exact_main_sha": "a" * 40,
            "exact_main_tree": "b" * 40,
            "counts": {
                "open_issues": 0,
                "open_pull_requests": 0,
                "open_work_branches": 0,
                "unclassified_branch_refs": 0,
            },
        }

    def test_policy_is_acyclic_and_fail_closed(self):
        validate_policy(self.policy)
        self.assertEqual(self.policy["semantics"]["unspecified_relation"], "HOLD_UNVERIFIED")
        self.assertFalse(self.policy["semantics"]["predecessor_evidence_transfer"])

    def test_first_step_is_manifest_latest_knowledge(self):
        result = next_eligible(self.policy, {})
        self.assertEqual(result["eligible"], ["P0_MANIFEST_LATEST_KNOWLEDGE"])

    def test_validation_cannot_precede_integration_head(self):
        states = {"P0_MANIFEST_LATEST_KNOWLEDGE": "SATISFIED"}
        result = next_eligible(self.policy, states)
        self.assertEqual(result["eligible"], ["P1_BUILD_ONE_INTEGRATION_HEAD"])
        self.assertNotIn("P2_VALIDATE_EXACT_INTEGRATION_HEAD", result["eligible"])

    def test_review_cannot_precede_validation(self):
        states = {
            "P0_MANIFEST_LATEST_KNOWLEDGE": "SATISFIED",
            "P1_BUILD_ONE_INTEGRATION_HEAD": "SATISFIED",
        }
        result = next_eligible(self.policy, states)
        self.assertEqual(result["eligible"], ["P2_VALIDATE_EXACT_INTEGRATION_HEAD"])

    def test_promotion_cannot_precede_post_review_reobservation(self):
        satisfied = self.policy["canonical_spine"][:4]
        result = next_eligible(self.policy, {node: "SATISFIED" for node in satisfied})
        self.assertEqual(result["eligible"], ["P4_REOBSERVE_POST_REVIEW_EXACT_HEAD"])
        self.assertNotIn("P5_LEGITIMATE_PROMOTION_TO_TRUSTED_MAIN", result["eligible"])

    def test_external_edges_open_only_after_common_barrier(self):
        before = self.policy["canonical_spine"][:-1]
        result = next_eligible(self.policy, {node: "SATISFIED" for node in before})
        self.assertEqual(result["eligible"], ["P7_DERIVE_BOUND_EXTERNAL_OBLIGATIONS"])

        all_spine = {node: "SATISFIED" for node in self.policy["canonical_spine"]}
        result = next_eligible(self.policy, all_spine)
        self.assertEqual(
            set(result["eligible"]),
            {"E1_WIKIPEDIA", "E2_ZENODO", "E3_ARXIV"},
        )

    def test_stale_or_unknown_predecessor_never_opens_successor(self):
        states = {
            "P0_MANIFEST_LATEST_KNOWLEDGE": "SATISFIED",
            "P1_BUILD_ONE_INTEGRATION_HEAD": "STALE",
        }
        result = next_eligible(self.policy, states)
        self.assertEqual(result["eligible"], ["P1_BUILD_ONE_INTEGRATION_HEAD"])
        self.assertNotIn("P2_VALIDATE_EXACT_INTEGRATION_HEAD", result["eligible"])

    def test_convergence_policy_targets_authority_and_mirror_at_zero(self):
        convergence = self.policy["repository_convergence"]
        self.assertEqual(
            set(convergence["repositories"]),
            {"Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"},
        )
        self.assertEqual(
            convergence["target_counts"],
            {
                "open_issues": 0,
                "open_pull_requests": 0,
                "open_work_branches": 0,
                "unclassified_branch_refs": 0,
            },
        )

    def test_nonzero_carrier_count_blocks_convergence(self):
        observations = {
            repository: self._zero_observation(repository)
            for repository in self.policy["repository_convergence"]["repositories"]
        }
        observations["Goldkelch/qik-vrt"]["counts"]["open_pull_requests"] = 1
        result = evaluate_repository_convergence(self.policy, observations)
        self.assertEqual(result["state"], "HOLD")
        self.assertFalse(result["repository_convergence_satisfied"])
        self.assertIn(
            "NONZERO_OPEN_CARRIER_COUNT",
            {blocker["code"] for blocker in result["blockers"]},
        )

    def test_missing_mirror_observation_fails_closed(self):
        observations = {
            "Goldkelch/qik-vrt": self._zero_observation("Goldkelch/qik-vrt"),
        }
        result = evaluate_repository_convergence(self.policy, observations)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(
            result["repository_states"]["ingolf-lohmann/qik-vrt"]["state"],
            "HOLD",
        )

    def test_zero_carriers_satisfies_only_repository_prerequisite(self):
        observations = {
            repository: self._zero_observation(repository)
            for repository in self.policy["repository_convergence"]["repositories"]
        }
        result = evaluate_repository_convergence(self.policy, observations)
        self.assertEqual(result["state"], "SATISFIED")
        self.assertTrue(result["repository_convergence_satisfied"])
        self.assertEqual(
            result["completion_claims"],
            {
                "GLOBAL_REPOSITORY_CONVERGED": False,
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
