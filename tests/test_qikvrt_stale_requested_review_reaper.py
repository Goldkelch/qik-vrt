# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_stale_requested_review_reaper.yml"


class StaleRequestedReviewReaperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_event_driven_by_head_change_or_close(self) -> None:
        self.assertIn("pull_request_target:", self.text)
        self.assertIn("types: [synchronize, closed]", self.text)
        self.assertNotIn("schedule:", self.text)
        self.assertNotIn("cron:", self.text)

    def test_reuses_existing_actions_write_authority_only_for_cancel(self) -> None:
        self.assertIn("actions: write", self.text)
        self.assertIn("contents: read", self.text)
        self.assertIn("pull-requests: read", self.text)
        self.assertNotIn("contents: write", self.text)
        self.assertNotIn("pull-requests: write", self.text)
        self.assertIn('/actions/runs/${run_id}/cancel', self.text)

    def test_never_cancels_an_in_progress_writer(self) -> None:
        self.assertIn("queued|pending|waiting|requested", self.text)
        self.assertNotIn("queued|pending|waiting|requested|in_progress", self.text)
        self.assertIn("in_progress_cancelled:false", self.text)

    def test_only_matches_exact_pr_requested_review_dispatches(self) -> None:
        self.assertIn("qikvrt_requested_review_executor.yml", self.text)
        self.assertIn("event=workflow_dispatch", self.text)
        self.assertIn('test "$run_event" = workflow_dispatch', self.text)
        self.assertIn('test "$head_branch" = main', self.text)
        self.assertIn('prefix="QIKVRT requested review pr=${PR_NUMBER} head="', self.text)

    def test_head_drift_or_close_is_required(self) -> None:
        self.assertIn('if test "$PR_ACTION" = closed', self.text)
        self.assertIn('elif test "$bound_head" != "$LIVE_HEAD"', self.text)
        self.assertIn('test "$stale" = true || continue', self.text)

    def test_receipt_preserves_non_terminal_boundaries(self) -> None:
        self.assertIn('STALE_NOT_STARTED_WORK_UNIT_CANCEL_REQUESTED', self.text)
        self.assertIn('PASS:false', self.text)
        self.assertIn('FINAL_PASS:false', self.text)
        self.assertIn('EFFECT_ACK_DONE:false', self.text)
        self.assertIn('MERGE:false', self.text)


if __name__ == "__main__":
    unittest.main()
