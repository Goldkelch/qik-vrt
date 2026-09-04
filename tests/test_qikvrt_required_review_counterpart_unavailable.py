# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_required_review_gate_counterpart_regression",
    ROOT / "tools/qikvrt_required_review_gate.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RequiredReviewCounterpartUnavailableRegression(unittest.TestCase):
    def test_single_matching_code_owner_author_fails_closed_with_bound_pr(self):
        head = "b" * 40
        rules = [
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "require_code_owner_review": True,
                    "dismiss_stale_reviews_on_push": True,
                    "require_last_push_approval": True,
                },
            },
            {
                "type": "required_status_checks",
                "parameters": {
                    "required_status_checks": [
                        {"context": "test", "integration_id": 15368},
                        {
                            "context": "QIKVRT required code-owner review",
                            "integration_id": 15368,
                        },
                    ]
                },
            },
        ]
        with mock.patch.object(MODULE, "_code_owners", return_value=("Goldkelch",)):
            result = MODULE.evaluate_required_review(
                {
                    "number": 99,
                    "head": {"sha": head},
                    "user": {"login": "Goldkelch"},
                },
                rules,
                [],
                required_code_owners=["Goldkelch"],
            )
        self.assertEqual(result["gate_state"], "failure")
        self.assertEqual(result["first_blocker"], "CODE_OWNER_COUNTERPART_UNAVAILABLE")
        self.assertEqual(result["pr_number"], 99)


if __name__ == "__main__":
    unittest.main()
