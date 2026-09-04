#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/qikvrt_live_status_watch.yml"


class LiveStatusCarrierClassificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_surface_failures_are_classification_inputs_not_terminal_hold(self) -> None:
        self.assertIn(
            "failure|cancelled|action_required|timed_out) verb='CLASSIFY'",
            self.text,
        )
        self.assertNotIn("verb='HOLD'", self.text)

    def test_surface_documents_missing_carrier_exhaustion_proof(self) -> None:
        self.assertIn("all issue, PR and branch", self.text)
        self.assertIn("cannot authoritatively emit HOLD", self.text)

    def test_projection_remains_event_driven(self) -> None:
        self.assertIn("workflow_run:", self.text)
        self.assertIn("issue_comment:", self.text)
        self.assertIn("pull_request:", self.text)
        self.assertNotIn("schedule:", self.text)


if __name__ == "__main__":
    unittest.main()
