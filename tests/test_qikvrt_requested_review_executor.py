# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_executor",
    ROOT / "tools/qikvrt_requested_review_executor.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RequestedReviewExecutorTests(unittest.TestCase):
    def snapshot(self, **overrides):
        value = {
            "repository": "example/qik-vrt",
            "pr_number": 349,
            "current_main_sha": "a" * 40,
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "observed_head_sha": "b" * 40,
            "tree_sha": "c" * 40,
            "draft": False,
            "requested_reviewers": ["Goldkelch"],
            "requested_team_reviewers": [],
            "changed_paths": ["src/a.py", "tests/test_a.py"],
            "unresolved_review_threads": 0,
            "required_gates": [
                "QIKVRT CI",
                "QIKVRT repository evidence materialization",
                "QIKVRT Collective Proposal Review",
                "QIK-VRT global claim completion",
            ],
            "workflow_runs": [
                {"name": "QIKVRT CI", "status": "completed", "conclusion": "success", "run_number": 10},
                {"name": "QIKVRT repository evidence materialization", "status": "completed", "conclusion": "success", "run_number": 20},
                {"name": "QIKVRT Collective Proposal Review", "status": "completed", "conclusion": "success", "run_number": 30},
                {"name": "QIK-VRT global claim completion", "status": "completed", "conclusion": "success", "run_number": 40},
                {"name": "QIKVRT conditional probe", "status": "completed", "conclusion": "skipped", "run_number": 1},
                {"name": "QIKVRT requested review executor", "status": "in_progress", "conclusion": None, "run_number": 1},
            ],
        }
        value.update(overrides)
        return value

    def test_terminal_green_requested_review_approves(self):
        result = MODULE.evaluate(self.snapshot())
        self.assertEqual(result["state"], "APPROVE")
        self.assertIsNone(result["first_blocker"])

    def test_nonterminal_gate_waits_without_false_review(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "in_progress", "conclusion": None, "run_number": 11}
        )
        result = MODULE.evaluate(snap)
        self.assertEqual(result["state"], "WAIT")
        self.assertEqual(result["first_blocker"], "REQUIRED_GATE_NOT_TERMINAL")

    def test_failed_gate_requests_changes(self):
        snap = self.snapshot()
        snap["workflow_runs"].append(
            {"name": "QIKVRT CI", "status": "completed", "conclusion": "failure", "run_number": 11}
        )
        result = MODULE.evaluate(snap)
        self.assertEqual(result["state"], "REQUEST_CHANGES")
        self.assertEqual(result["first_blocker"], "REQUIRED_GATE_FAILED")

    def test_head_drift_blocks(self):
        result = MODULE.evaluate(self.snapshot(observed_head_sha="d" * 40))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "HEAD_DRIFT")

    def test_base_drift_blocks(self):
        result = MODULE.evaluate(self.snapshot(current_main_sha="d" * 40))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "BASE_DRIFT")

    def test_unresolved_thread_blocks(self):
        result = MODULE.evaluate(self.snapshot(unresolved_review_threads=1))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "UNRESOLVED_REVIEW_THREADS")

    def test_draft_waits(self):
        result = MODULE.evaluate(self.snapshot(draft=True))
        self.assertEqual(result["state"], "WAIT")
        self.assertEqual(result["first_blocker"], "DRAFT")

    def test_no_active_request_is_noop_wait(self):
        result = MODULE.evaluate(self.snapshot(requested_reviewers=[]))
        self.assertEqual(result["state"], "WAIT")
        self.assertEqual(result["first_blocker"], "NO_ACTIVE_REVIEW_REQUEST")


if __name__ == "__main__":
    unittest.main()
