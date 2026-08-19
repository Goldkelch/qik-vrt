# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.qikvrt_zero_bug_backlog import Issue, plan


class ZeroBugBacklogTests(unittest.TestCase):
    def test_reuses_active_and_persisted_issue_state_before_cold_dispatch(self) -> None:
        issues = [Issue(76, "a"), Issue(79, "b"), Issue(704, "c")]
        active = {79}
        persisted = {704}
        with patch(
            "tools.qikvrt_zero_bug_backlog.has_active_issue_pr",
            side_effect=lambda _repo, number: number in active,
        ), patch(
            "tools.qikvrt_zero_bug_backlog.has_issue_branch",
            side_effect=lambda _repo, number: number in persisted,
        ):
            result = plan("Goldkelch/qik-vrt", issues)
        self.assertEqual(result["open_issue_count"], 3)
        self.assertEqual(result["active_issue_prs"], [79])
        self.assertEqual(result["resume_issue_numbers"], [704])
        self.assertEqual(result["cold_dispatch_issue_numbers"], [76])
        self.assertEqual(result["dispatch_issue_numbers"], [704, 76])
        self.assertEqual(result["optimization"]["reused_work_items"], 2)
        self.assertEqual(result["optimization"]["cold_work_items"], 1)
        self.assertAlmostEqual(result["optimization"]["reuse_ratio"], 2 / 3)
        self.assertEqual(result["terminal_frame"]["OPTIMIZE"], "reuse_persisted_state_before_new_work")
        self.assertFalse(result["completion_claims"]["PASS"])
        self.assertFalse(result["completion_claims"]["FINAL_PASS"])
        self.assertFalse(result["completion_claims"]["EFFECT_ACK_DONE"])

    def test_empty_backlog_is_not_completion_claim(self) -> None:
        result = plan("Goldkelch/qik-vrt", [])
        self.assertEqual(result["open_issue_count"], 0)
        self.assertEqual(result["dispatch_issue_numbers"], [])
        self.assertEqual(result["optimization"]["reuse_ratio"], 1.0)
        self.assertFalse(any(result["completion_claims"].values()))


if __name__ == "__main__":
    unittest.main()
