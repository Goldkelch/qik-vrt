# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_required_review_gate",
    ROOT / "tools/qikvrt_required_review_gate.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RequiredCodeOwnerReviewGateTests(unittest.TestCase):
    head = "b" * 40

    def pr(self, **overrides):
        value = {
            "number": 641,
            "head": {"sha": self.head},
            "user": {"login": "integration-author"},
        }
        value.update(overrides)
        return value

    def enforced_rules(self):
        return [
            {
                "type": "pull_request",
                "parameters": {
                    "required_approving_review_count": 1,
                    "require_code_owner_review": True,
                    "dismiss_stale_reviews_on_push": True,
                    "require_last_push_approval": True,
                },
            }
        ]

    def approval(self, **overrides):
        value = {
            "id": 3,
            "submitted_at": "2026-08-16T16:00:00Z",
            "state": "APPROVED",
            "commit_id": self.head,
            "user": {"login": "Goldkelch"},
        }
        value.update(overrides)
        return value

    def evaluate(self, reviews, *, rules=None, pr=None):
        return MODULE.evaluate_required_review(
            self.pr() if pr is None else pr,
            self.enforced_rules() if rules is None else rules,
            reviews,
        )

    def test_native_rule_must_enforce_all_freshness_requirements(self):
        weak = self.enforced_rules()
        weak[0]["parameters"]["require_code_owner_review"] = False
        result = self.evaluate([], rules=weak)
        self.assertEqual(result["gate_state"], "failure")
        self.assertEqual(result["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")

    def test_native_rule_requires_stale_dismissal_and_last_push_approval(self):
        for field in ("dismiss_stale_reviews_on_push", "require_last_push_approval"):
            with self.subTest(field=field):
                weak = self.enforced_rules()
                weak[0]["parameters"][field] = False
                result = self.evaluate([], rules=weak)
                self.assertEqual(result["gate_state"], "failure")
                self.assertEqual(result["first_blocker"], "CODE_OWNER_RULE_NOT_ENFORCED")

    def test_no_review_is_pending_not_approval(self):
        result = self.evaluate([])
        self.assertEqual(result["gate_state"], "pending")
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_MISSING")

    def test_wrong_reviewer_cannot_satisfy_gate(self):
        result = self.evaluate([self.approval(user={"login": "someone-else"})])
        self.assertEqual(result["gate_state"], "pending")
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_MISSING")

    def test_old_head_approval_is_stale(self):
        result = self.evaluate([self.approval(commit_id="a" * 40)])
        self.assertEqual(result["gate_state"], "pending")
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_STALE")

    def test_exact_head_approval_passes(self):
        result = self.evaluate([self.approval()])
        self.assertEqual(result["gate_state"], "success")
        self.assertEqual(result["head_sha"], self.head)
        self.assertEqual(result["first_blocker"], None)
        self.assertEqual(result["review_mutation"], "FORBIDDEN")

    def test_current_head_changes_requested_supersedes_prior_approval(self):
        result = self.evaluate(
            [
                self.approval(id=3, submitted_at="2026-08-16T16:00:00Z"),
                self.approval(
                    id=4,
                    submitted_at="2026-08-16T16:01:00Z",
                    state="CHANGES_REQUESTED",
                ),
            ]
        )
        self.assertEqual(result["gate_state"], "failure")
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_CHANGES_REQUESTED")

    def test_dismissed_exact_head_review_requires_new_approval(self):
        result = self.evaluate([self.approval(state="DISMISSED")])
        self.assertEqual(result["gate_state"], "pending")
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_DISMISSED")

    def test_pr_author_cannot_satisfy_the_independent_gate(self):
        result = self.evaluate([self.approval()], pr=self.pr(user={"login": "Goldkelch"}))
        self.assertEqual(result["gate_state"], "failure")
        self.assertEqual(result["first_blocker"], "CODE_OWNER_REVIEW_SELF_APPROVAL")


if __name__ == "__main__":
    unittest.main()
