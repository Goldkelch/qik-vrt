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
            "main_head": head,
            "main_tree": tree,
            "inventory_complete": True,
            "queue_empty": True,
            "open_issues": [],
            "pull_requests": [],
            "branches": [{"name": "main"}],
            "known_productive_defects": [],
            "all_productive_changes_on_main": True,
            "ruleset_current": True,
            "main_validation": {"fresh": True, "head": head, "tree": tree, "state": "PASS"},
            "effect_readback": {"fresh": True, "head": head, "tree": tree, "observed": True,
                                "effect_ack": "EFFECT_ACK_DONE"}
        }

    def assert_excluded(self, obs, blocker):
        result = evaluate(obs)
        self.assertFalse(result["done"])
        self.assertFalse(result["noop_allowed"])
        self.assertIn(blocker, result["blockers"])

    def test_all_fresh_closed_predicates_are_done(self):
        result = evaluate(self.good())
        self.assertEqual("DONE", result["state"])
        self.assertTrue(result["done"])
        self.assertTrue(result["effect_ack_done"])

    def test_open_issue_excludes_noop(self):
        obs = self.good(); obs["open_issues"] = [{"number": 1100}]
        self.assert_excluded(obs, "OPEN_ISSUE_EXISTS")

    def test_open_pr_excludes_noop_even_when_regarded(self):
        obs = self.good(); obs["pull_requests"] = [{"number": 1, "state": "open", "disposition": "MERGE"}]
        self.assert_excluded(obs, "OPEN_PULL_REQUEST_EXISTS")

    def test_unregarded_open_pr_is_explicit_blocker(self):
        obs = self.good(); obs["pull_requests"] = [{"number": 1, "state": "open"}]
        self.assert_excluded(obs, "OPEN_PULL_REQUEST_UNREGARDED")

    def test_unclassified_branch_excludes_noop(self):
        obs = self.good(); obs["branches"].append({"name": "feature/x"})
        self.assert_excluded(obs, "UNCLASSIFIED_BRANCH_EXISTS")

    def test_queue_excludes_noop(self):
        obs = self.good(); obs["queue_empty"] = False
        self.assert_excluded(obs, "PRODUCTIVE_QUEUE_NONEMPTY")

    def test_known_productive_defect_excludes_noop(self):
        obs = self.good(); obs["known_productive_defects"] = ["RULESET_DRIFT"]
        self.assert_excluded(obs, "KNOWN_PRODUCTIVE_DEFECT_EXISTS")

    def test_ruleset_drift_excludes_done(self):
        obs = self.good(); obs["ruleset_current"] = False
        self.assert_excluded(obs, "AUTHORITY_CONTROL_PLANE_DRIFT")

    def test_stale_predecessor_main_validation_is_rejected(self):
        obs = self.good(); obs["main_validation"]["head"] = "c" * 40
        self.assert_excluded(obs, "EXACT_MAIN_VALIDATION_MISSING_OR_STALE")

    def test_transport_without_effect_readback_is_rejected(self):
        obs = self.good(); obs["effect_readback"] = {"fresh": True, "head": obs["main_head"],
            "tree": obs["main_tree"], "observed": False, "effect_ack": "EFFECT_ACK_CONTINUE",
            "transport_ack": True}
        self.assert_excluded(obs, "EFFECT_READBACK_MISSING_STALE_OR_WRONG_MAIN")

    def test_incomplete_inventory_fails_closed(self):
        obs = self.good(); obs["inventory_complete"] = False
        result = evaluate(obs)
        self.assertEqual("HOLD_UNVERIFIED", result["state"])
        self.assertFalse(result["noop_allowed"])

    def test_missing_input_fails_closed(self):
        obs = self.good(); del obs["branches"]
        result = evaluate(obs)
        self.assertEqual("HOLD_UNVERIFIED", result["state"])


if __name__ == "__main__":
    unittest.main()
