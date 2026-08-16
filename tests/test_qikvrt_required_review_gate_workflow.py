# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_required_review_gate.yml"


class RequiredCodeOwnerReviewGateWorkflowTests(unittest.TestCase):
    def test_gate_uses_trusted_main_and_reacts_to_review_events(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request_target:", workflow)
        self.assertIn("pull_request_review:", workflow)
        self.assertIn("types: [submitted, edited, dismissed]", workflow)
        self.assertIn("ref: main", workflow)
        self.assertIn("never executes bytes from a PR head", workflow)

    def test_gate_posts_only_an_observed_exact_head_status(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("statuses: write", workflow)
        self.assertIn("QIKVRT required code-owner review", workflow)
        self.assertIn("HEAD_DRIFT_NO_STATUS", workflow)
        self.assertIn("/statuses/{head}", workflow)
        self.assertIn("evaluate_required_review", workflow)

    def test_gate_cannot_submit_or_fabricate_a_review(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("gh pr review", workflow)
        self.assertNotIn('"event": "APPROVE"', workflow)
        self.assertNotIn('"event": "REQUEST_CHANGES"', workflow)
        self.assertNotIn("APPROVE", workflow)


if __name__ == "__main__":
    unittest.main()
