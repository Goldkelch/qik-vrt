# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_autonomous_requested_review_receiver.yml"


class AutonomousRequestedReviewReceiverContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_is_event_driven_from_trusted_contract(self):
        self.assertIn('"QIKVRT requested review contract"', self.text)
        self.assertIn("types: [completed]", self.text)
        self.assertNotIn("schedule:", self.text)

    def test_requires_successful_workflow_dispatch_contract(self):
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.text)
        self.assertIn("github.event.workflow_run.event == 'workflow_dispatch'", self.text)

    def test_exact_head_is_rebound_before_dispatch(self):
        self.assertIn("EXACT_SUBJECT_DRIFT", self.text)
        self.assertIn('test "$current_head" = "$HEAD_SHA"', self.text)

    def test_review_request_must_remain_active(self):
        self.assertIn("NO_ACTIVE_REQUESTED_REVIEWER", self.text)
        self.assertIn("requested_reviewers", self.text)

    def test_dispatches_executor_not_review_effect(self):
        self.assertIn("qikvrt_requested_review_executor.yml/dispatches", self.text)
        self.assertIn("inputs:{pr:$pr,head:$head}", self.text)
        self.assertNotIn("APPROVE", self.text)
        self.assertNotIn("REQUEST_CHANGES", self.text)


if __name__ == "__main__":
    unittest.main()
