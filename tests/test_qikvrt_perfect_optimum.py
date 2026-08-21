import json
import unittest
from pathlib import Path

from tools.qikvrt_perfect_optimum import compare_metrics, evaluate, load_policy, self_check


class PerfectOptimumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = load_policy()

    def baseline(self):
        return {
            "deterministic_blockers": 2,
            "avoidable_human_interventions": 1,
            "productive_writer_count": 1,
            "stale_evidence_reuse": 0,
            "unbound_effect_claims": 0,
            "fresh_exact_head_gate_coverage": 6,
            "deterministically_closed_internal_loops": 3,
        }

    def invariants(self, value=True):
        return {k: value for k in self.policy["hard_invariants"]}

    def test_policy_self_applies_safely(self):
        result = self_check(self.policy)
        self.assertTrue(result["self_application_safe"])
        self.assertEqual(result["arbitrary_source_self_modification"], "HOLD")

    def test_later_without_improvement_is_hold(self):
        before = self.baseline()
        result = evaluate(before, dict(before), self.invariants(), self.policy)
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["strict_progress"])

    def test_pareto_progress_is_accepted(self):
        before = self.baseline()
        after = dict(before)
        after["deterministic_blockers"] = 1
        after["fresh_exact_head_gate_coverage"] = 7
        result = evaluate(before, after, self.invariants(), self.policy)
        self.assertEqual(result["decision"], "ACCEPT_CANDIDATE")

    def test_single_regression_forces_hold(self):
        before = self.baseline()
        after = dict(before)
        after["deterministic_blockers"] = 1
        after["stale_evidence_reuse"] = 1
        result = evaluate(before, after, self.invariants(), self.policy)
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["non_regression"])

    def test_missing_metric_is_hold(self):
        before = self.baseline()
        after = dict(before)
        del after["unbound_effect_claims"]
        result = evaluate(before, after, self.invariants(), self.policy)
        self.assertEqual(result["decision"], "HOLD")

    def test_failed_invariant_is_hold(self):
        before = self.baseline()
        after = dict(before)
        after["deterministic_blockers"] = 1
        invariants = self.invariants()
        invariants["reobserve_after_effect"] = False
        result = evaluate(before, after, invariants, self.policy)
        self.assertEqual(result["decision"], "HOLD")
        self.assertFalse(result["invariants_ok"])

    def test_only_registered_mutating_improver_is_integrity_trio(self):
        improvers = self.policy["registered_improvers"]
        self.assertEqual([x["id"] for x in improvers], ["integrity_trio_materializer"])
        self.assertEqual(
            improvers[0]["effect_scope"],
            [
                "REPOSITORY_FILE_MANIFEST.json",
                "REPOSITORY_FILE_MANIFEST.json.sha256",
                "SHA256SUMS.txt",
            ],
        )


if __name__ == "__main__":
    unittest.main()
