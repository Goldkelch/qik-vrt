# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTINUATION = ROOT / ".github" / "workflows" / "qikvrt_autonomous_pr_head_continuation.yml"
REVIEW_EXECUTOR = ROOT / ".github" / "workflows" / "qikvrt_requested_review_executor.yml"


class RequestedReviewDispatchTypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.continuation = CONTINUATION.read_text(encoding="utf-8")
        cls.review_executor = REVIEW_EXECUTOR.read_text(encoding="utf-8")

    def test_requested_review_executor_declares_pr_as_string(self) -> None:
        self.assertIn("workflow_dispatch:", self.review_executor)
        self.assertIn("inputs:", self.review_executor)
        self.assertIn("type: string", self.review_executor)

    def test_continuation_dispatches_pr_as_string_not_typed_number(self) -> None:
        target = (
            '"repos/${GITHUB_REPOSITORY}/actions/workflows/'
            'qikvrt_requested_review_executor.yml/dispatches"'
        )
        self.assertIn(target, self.continuation)
        self.assertIn('-f ref=main -f "inputs[pr]=$PR_NUMBER"', self.continuation)
        self.assertNotIn('-f ref=main -F "inputs[pr]=$PR_NUMBER"', self.continuation)

    def test_dispatch_remains_non_productive_and_review_authority_separate(self) -> None:
        self.assertIn("REQUEST_AUTHORITY/D0=3", self.continuation)
        self.assertIn("is not fabricated", self.continuation)
        self.assertIn("productive_effect:false", self.continuation)
        self.assertIn('effect_ack:"NOT_REQUIRED"', self.continuation)


if __name__ == "__main__":
    unittest.main()
