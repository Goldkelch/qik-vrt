# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / ".github/workflows/qikvrt_required_review_gate.yml"
OBSERVER = ROOT / ".github/workflows/qikvrt_code_owner_review_observer.yml"


class RequiredCodeOwnerReviewGateWorkflowTests(unittest.TestCase):
    def test_unprivileged_observer_reacts_to_pr_and_review_events(self) -> None:
        workflow = OBSERVER.read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("pull_request_review:", workflow)
        self.assertIn("types: [submitted, edited, dismissed]", workflow)
        self.assertIn("permissions: {}", workflow)
        self.assertNotIn("actions/checkout", workflow)
        self.assertNotIn("statuses: write", workflow)

    def test_publisher_uses_trusted_workflow_run_and_schedule_fallback(self) -> None:
        workflow = PUBLISHER.read_text(encoding="utf-8")
        self.assertIn("workflow_run:", workflow)
        self.assertIn('workflows: ["QIKVRT code-owner review observer"]', workflow)
        self.assertIn('cron: "*/5 * * * *"', workflow)
        self.assertNotIn("pull_request_review:", workflow)
        self.assertIn("workflow_run may have zero/multiple PRs", workflow)
        self.assertIn("publish nothing unless exactly one", workflow)
        self.assertIn("ref: main", workflow)
        self.assertIn("never consumes observer output or PR-head code", workflow)

    def test_publisher_is_main_ref_bound_and_only_observes_live_pr_state(self) -> None:
        workflow = PUBLISHER.read_text(encoding="utf-8")
        self.assertIn("if: github.ref == 'refs/heads/main'", workflow)
        self.assertIn("target must be an open main-based pull request", workflow)
        self.assertIn("target must remain an open main-based pull request", workflow)
        self.assertIn("/repos/{repository}/pulls/{number}", workflow)
        self.assertIn("/rules/branches/main", workflow)
        self.assertIn("evaluate_required_review", workflow)

    def test_gate_posts_only_an_observed_exact_head_status(self) -> None:
        workflow = PUBLISHER.read_text(encoding="utf-8")
        self.assertIn("statuses: write", workflow)
        self.assertIn("QIKVRT required code-owner review", workflow)
        self.assertIn("HEAD_DRIFT_NO_STATUS", workflow)
        self.assertIn("/statuses/{head}", workflow)

    def test_gate_cannot_submit_or_fabricate_a_review(self) -> None:
        workflow = PUBLISHER.read_text(encoding="utf-8") + OBSERVER.read_text(encoding="utf-8")
        self.assertNotIn("gh pr review", workflow)
        self.assertNotIn('"event": "APPROVE"', workflow)
        self.assertNotIn('"event": "REQUEST_CHANGES"', workflow)
        self.assertNotIn("APPROVE", workflow)


if __name__ == "__main__":
    unittest.main()
