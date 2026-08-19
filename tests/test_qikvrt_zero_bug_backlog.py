# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import unittest
from unittest.mock import patch

from tools.qikvrt_zero_bug_backlog import Issue, plan


class ZeroBugBacklogTests(unittest.TestCase):
    def test_dispatches_only_issues_without_active_issue_pr(self) -> None:
        issues = [Issue(76, "a"), Issue(79, "b"), Issue(704, "c")]
        active = {79}
        with patch(
            "tools.qikvrt_zero_bug_backlog.has_active_issue_pr",
            side_effect=lambda _repo, number: number in active,
        ):
            result = plan("Goldkelch/qik-vrt", issues)
        self.assertEqual(result["open_issue_count"], 3)
        self.assertEqual(result["active_issue_prs"], [79])
        self.assertEqual(result["dispatch_issue_numbers"], [76, 704])
        self.assertFalse(result["completion_claims"]["PASS"])
        self.assertFalse(result["completion_claims"]["FINAL_PASS"])
        self.assertFalse(result["completion_claims"]["EFFECT_ACK_DONE"])

    def test_empty_backlog_is_not_completion_claim(self) -> None:
        result = plan("Goldkelch/qik-vrt", [])
        self.assertEqual(result["open_issue_count"], 0)
        self.assertEqual(result["dispatch_issue_numbers"], [])
        self.assertFalse(any(result["completion_claims"].values()))


if __name__ == "__main__":
    unittest.main()
