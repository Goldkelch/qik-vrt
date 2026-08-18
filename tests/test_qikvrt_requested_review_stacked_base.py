# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_requested_review_executor_stacked",
    ROOT / "tools/qikvrt_requested_review_executor.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def snapshot(**overrides):
    value = {
        "repository": "example/qik-vrt",
        "pr_number": 680,
        "current_main_sha": "a" * 40,
        "base_ref": "agent/metagrammar-of-understanding-v1",
        "current_base_sha": "d" * 40,
        "base_sha": "d" * 40,
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
        ],
    }
    value.update(overrides)
    return value


class StackedRequestedReviewTests(unittest.TestCase):
    def test_stacked_base_uses_live_base_ref_not_main(self):
        result = MODULE.evaluate(snapshot())
        self.assertEqual(result["state"], "APPROVE")
        self.assertIsNone(result["first_blocker"])
        self.assertEqual(result["base_ref"], "agent/metagrammar-of-understanding-v1")

    def test_stacked_base_drift_remains_fail_closed(self):
        result = MODULE.evaluate(snapshot(current_base_sha="e" * 40))
        self.assertEqual(result["state"], "COMMENT_WITH_BLOCKER")
        self.assertEqual(result["first_blocker"], "BASE_DRIFT")
        self.assertIn("agent/metagrammar-of-understanding-v1", result["detail"])

    def test_workflow_selector_is_not_main_only(self):
        workflow = (ROOT / ".github/workflows/qikvrt_requested_review_executor.yml").read_text(encoding="utf-8")
        self.assertIn("pulls?state=open&per_page=100", workflow)
        self.assertNotIn("pulls?state=open&base=main&per_page=100", workflow)
        self.assertNotIn("pr.get('base',{}).get('ref')!='main'", workflow)
        self.assertIn("'base_ref':base_ref", workflow)
        self.assertIn("'current_base_sha':current_base", workflow)


if __name__ == "__main__":
    unittest.main()
