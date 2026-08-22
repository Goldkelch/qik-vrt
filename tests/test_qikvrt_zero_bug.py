import unittest

from tools.qikvrt_zero_bug import evaluate, self_check


class ZeroBugContinuousTests(unittest.TestCase):
    def good(self):
        return {
            "exact_head_and_tree_bound": True,
            "known_deterministic_defects": 0,
            "repository_integrity_verifies": True,
            "required_exact_head_gates_non_adverse": True,
            "productive_writer_count": 1,
            "stale_evidence_reuse": 0,
            "registered_improvers_only": True,
            "reobserve_after_every_mutation": True,
        }

    def test_self_check_preserves_hold_after_mutation(self):
        result = self_check()
        self.assertTrue(result["complete"])
        self.assertEqual(result["after_mutation"], "HOLD_UNVERIFIED")
        self.assertFalse(result["later_is_better"])
        self.assertEqual(result["arbitrary_unregistered_self_modification"], "HOLD")

    def test_fresh_exact_head_with_zero_known_defects_is_accepted_state(self):
        result = evaluate(self.good())
        self.assertEqual(result["state"], "ZERO_KNOWN_DETERMINISTIC_BUGS")
        self.assertFalse(result["universal_bug_freedom_claimed"])

    def test_any_known_deterministic_defect_forces_hold(self):
        obs = self.good()
        obs["known_deterministic_defects"] = 1
        result = evaluate(obs)
        self.assertEqual(result["state"], "HOLD_DEFECT_IDENTIFIED")

    def test_stale_evidence_forces_hold(self):
        obs = self.good()
        obs["stale_evidence_reuse"] = 1
        result = evaluate(obs)
        self.assertEqual(result["state"], "HOLD_DEFECT_IDENTIFIED")

    def test_multiple_productive_writers_force_hold(self):
        obs = self.good()
        obs["productive_writer_count"] = 2
        result = evaluate(obs)
        self.assertEqual(result["state"], "HOLD_DEFECT_IDENTIFIED")

    def test_missing_reobservation_forces_hold(self):
        obs = self.good()
        obs["reobserve_after_every_mutation"] = False
        result = evaluate(obs)
        self.assertEqual(result["state"], "HOLD_DEFECT_IDENTIFIED")


if __name__ == "__main__":
    unittest.main()
