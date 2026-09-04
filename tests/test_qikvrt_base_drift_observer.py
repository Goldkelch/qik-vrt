#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
import unittest

from tools.qikvrt_base_drift_observer import classify_all, classify_pull_request


REPO = "Goldkelch/qik-vrt"
MAIN = "d" * 40
HEAD = "7" * 40


def pr(number=941, base="4" * 40, *, base_ref="main", head_repo=REPO):
    return {
        "number": number,
        "state": "open",
        "base": {"ref": base_ref, "sha": base},
        "head": {"sha": HEAD, "repo": {"full_name": head_repo}},
    }


class BaseDriftObserverTests(unittest.TestCase):
    def test_base_drift_is_first_blocker_and_rebind_is_only_next_action(self):
        result = classify_pull_request(REPO, MAIN, pr())
        self.assertEqual(result["first_blocker"], "BASE_DRIFT")
        self.assertEqual(result["state"], "HOLD_UNVERIFIED")
        self.assertEqual(result["next_action"], "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN")
        self.assertFalse(result["candidate_branch_mutation"])
        self.assertFalse(result["evidence_transfer_allowed"])
        self.assertEqual(result["head_sha"], HEAD)
        self.assertEqual(result["base_sha"], "4" * 40)
        self.assertEqual(result["current_main_sha"], MAIN)
        self.assertEqual(
            result["completion_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False, "MERGE": False},
        )

    def test_current_base_is_noop(self):
        result = classify_pull_request(REPO, MAIN, pr(base=MAIN))
        self.assertEqual(result["state"], "CURRENT_BASE")
        self.assertIsNone(result["first_blocker"])
        self.assertEqual(result["next_action"], "NOOP")

    def test_non_main_base_is_outside_observer_scope(self):
        result = classify_pull_request(REPO, MAIN, pr(base_ref="release"))
        self.assertEqual(result["state"], "NOOP_NON_MAIN_BASE")
        self.assertIsNone(result["first_blocker"])

    def test_cross_repository_head_fails_closed(self):
        result = classify_pull_request(REPO, MAIN, pr(head_repo="fork/qik-vrt"))
        self.assertEqual(result["first_blocker"], "HEAD_REPOSITORY_NOT_ROLE_LOCAL")
        self.assertEqual(result["next_action"], "HOLD")

    def test_output_order_is_stable_by_pr_number(self):
        results = classify_all(REPO, MAIN, [pr(950), pr(941), pr(943)])
        self.assertEqual([item["pr_number"] for item in results], [941, 943, 950])


if __name__ == "__main__":
    unittest.main()
