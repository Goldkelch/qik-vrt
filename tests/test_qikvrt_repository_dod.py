# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import copy
import unittest

from tools.qikvrt_repository_dod import evaluate


class RepositoryDodTests(unittest.TestCase):
    def good(self):
        head = "a" * 40
        tree = "b" * 40
        return {
            "repository": "Goldkelch/qik-vrt",
            "subject_head": head,
            "subject_tree": tree,
            "inventory_complete": True,
            "zero_bugs": {
                "fresh": True,
                "head": head,
                "tree": tree,
                "state": "ZERO_KNOWN_DETERMINISTIC_BUGS_LOCAL",
                "known_deterministic_defects_zero": True,
            },
            "pull_requests": [
                {"number": 1, "state": "closed", "disposition": "SUPERSEDE"},
                {"number": 2, "state": "open", "disposition": "REJECT_WITH_EVIDENCE"},
            ],
            "branches": [
                {"name": "main"},
                {"name": "historical/x", "disposition": "HISTORICAL/RETAINED_BY_POLICY"},
            ],
            "all_productive_branches_merged": True,
            "main_validation": {"fresh": True, "head": head, "tree": tree, "state": "PASS"},
            "effect_readback": {
                "fresh": True,
                "head": head,
                "tree": tree,
                "observed": True,
                "effect_ack": "EFFECT_ACK_DONE",
            },
        }

    def assert_excluded(self, obs, blocker):
        result = evaluate(obs)
        self.assertFalse(result["done"])
        self.assertIn(blocker, result["blockers"])

    def test_exact_six_conjuncts_are_done(self):
        result = evaluate(self.good())
        self.assertEqual("DONE", result["state"])
        self.assertTrue(result["done"])
        self.assertTrue(result["effect_ack_done"])
        self.assertEqual(
            list(result["conjuncts"]),
            [
                "ZERO_BUGS",
                "ALL_PULL_REQUESTS_REGARDED",
                "ALL_BRANCHES_REGARDED",
                "ALL_PRODUCTIVE_BRANCHES_MERGED",
                "FRESH_EXACT_MAIN_VALIDATION_PASS",
                "FRESH_EXACT_MAIN_EFFECT_READBACK",
            ],
        )

    def test_open_regarded_pr_does_not_add_hidden_done_conjunct(self):
        obs = self.good()
        obs["pull_requests"] = [{"number": 3, "state": "open", "disposition": "MERGE"}]
        self.assertTrue(evaluate(obs)["conjuncts"]["ALL_PULL_REQUESTS_REGARDED"])

    def test_unregarded_pr_blocks_exact_conjunct(self):
        obs = self.good()
        obs["pull_requests"] = [{"number": 3, "state": "open"}]
        self.assert_excluded(obs, "ALL_PULL_REQUESTS_REGARDED")

    def test_unregarded_branch_blocks_exact_conjunct(self):
        obs = self.good()
        obs["branches"].append({"name": "feature/x"})
        self.assert_excluded(obs, "ALL_BRANCHES_REGARDED")

    def test_current_candidate_branch_is_regarded_but_not_merged(self):
        obs = self.good()
        obs["branches"].append({"name": "integration/final", "disposition": "PRODUCTIVE_CURRENT_CANDIDATE"})
        obs["all_productive_branches_merged"] = False
        result = evaluate(obs)
        self.assertTrue(result["conjuncts"]["ALL_BRANCHES_REGARDED"])
        self.assertFalse(result["conjuncts"]["ALL_PRODUCTIVE_BRANCHES_MERGED"])

    def test_regarded_productive_unmerged_branch_keeps_branch_regard_separate(self):
        obs = self.good()
        obs["branches"].append({"name": "feature/x", "disposition": "PRODUCTIVE_UNMERGED"})
        obs["all_productive_branches_merged"] = False
        result = evaluate(obs)
        self.assertTrue(result["conjuncts"]["ALL_BRANCHES_REGARDED"])
        self.assertFalse(result["conjuncts"]["ALL_PRODUCTIVE_BRANCHES_MERGED"])

    def test_productive_branch_outside_final_state_blocks(self):
        obs = self.good()
        obs["all_productive_branches_merged"] = False
        self.assert_excluded(obs, "ALL_PRODUCTIVE_BRANCHES_MERGED")

    def test_zero_bug_must_be_fresh_and_exact(self):
        obs = self.good()
        obs["zero_bugs"]["head"] = "c" * 40
        self.assert_excluded(obs, "ZERO_BUGS")

    def test_main_validation_cannot_be_replaced_by_candidate_pass(self):
        obs = self.good()
        obs["main_validation"]["fresh"] = False
        self.assert_excluded(obs, "FRESH_EXACT_MAIN_VALIDATION_PASS")

    def test_effect_cannot_compensate_repository_red(self):
        obs = self.good()
        obs["all_productive_branches_merged"] = False
        self.assertTrue(obs["effect_readback"]["observed"])
        self.assert_excluded(obs, "ALL_PRODUCTIVE_BRANCHES_MERGED")

    def test_main_pass_does_not_imply_effect(self):
        obs = self.good()
        obs["effect_readback"]["observed"] = False
        obs["effect_readback"]["effect_ack"] = "EFFECT_ACK_CONTINUE"
        self.assert_excluded(obs, "FRESH_EXACT_MAIN_EFFECT_READBACK")

    def test_open_issues_queue_and_ruleset_are_not_hidden_dod_conjuncts(self):
        obs = self.good()
        obs["open_issues"] = [{"number": 1072}]
        obs["queue_empty"] = False
        obs["ruleset_current"] = False
        result = evaluate(obs)
        self.assertTrue(result["done"])

    def test_incomplete_inventory_fails_closed(self):
        obs = self.good()
        obs["inventory_complete"] = False
        result = evaluate(obs)
        self.assertEqual("HOLD_UNVERIFIED", result["state"])
        self.assertFalse(result["done"])

    def test_missing_input_fails_closed(self):
        obs = self.good()
        del obs["branches"]
        result = evaluate(obs)
        self.assertEqual("HOLD_UNVERIFIED", result["state"])


if __name__ == "__main__":
    unittest.main()
