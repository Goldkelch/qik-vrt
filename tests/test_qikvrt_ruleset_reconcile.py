#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import unittest

from tools import qikvrt_ruleset_reconcile as reconcile


class RulesetReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = reconcile.load_policy()

    def current(self):
        return {
            "id": self.policy["ruleset_id"],
            "source": self.policy["repository"],
            **reconcile.desired_payload(self.policy),
        }

    def test_exact_desired_state_is_idempotent(self):
        result = reconcile.evaluate(self.current(), self.policy)
        self.assertEqual(result["state"], "CURRENT")
        self.assertEqual(result["mutation"], "NONE")
        self.assertFalse(result["effect_observed"])
        self.assertEqual(
            result["pre_state_sha256"], result["desired_state_sha256"]
        )

    def test_live_weak_review_rule_is_detected(self):
        current = self.current()
        pull_request = next(
            rule for rule in current["rules"] if rule["type"] == "pull_request"
        )
        pull_request["parameters"].update(
            {
                "required_approving_review_count": 0,
                "dismiss_stale_reviews_on_push": False,
                "require_code_owner_review": False,
                "require_last_push_approval": False,
            }
        )
        result = reconcile.evaluate(current, self.policy)
        self.assertEqual(result["state"], "DRIFT")
        self.assertIn("rules", result["changed_fields"])
        self.assertNotEqual(
            result["pre_state_sha256"], result["desired_state_sha256"]
        )

    def test_missing_required_review_status_is_detected(self):
        current = self.current()
        checks = next(
            rule
            for rule in current["rules"]
            if rule["type"] == "required_status_checks"
        )
        checks["parameters"]["required_status_checks"] = [
            {"context": "test", "integration_id": 15368}
        ]
        result = reconcile.evaluate(current, self.policy)
        self.assertEqual(result["state"], "DRIFT")

    def test_wrong_ruleset_identity_fails_closed(self):
        current = copy.deepcopy(self.current())
        current["id"] += 1
        with self.assertRaises(reconcile.RulesetBlock):
            reconcile.evaluate(current, self.policy)

    def test_reconciler_workflow_keeps_admin_token_separate(self):
        workflow = (
            reconcile.ROOT / ".github/workflows/qikvrt_ruleset_reconcile.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("QIKVRT_RULESET_ADMIN_TOKEN", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("--apply", workflow)
        self.assertIn("--receipt", workflow)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertNotIn("contents: write", workflow)


if __name__ == "__main__":
    unittest.main()
