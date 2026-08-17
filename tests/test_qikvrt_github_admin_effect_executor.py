# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import unittest
from unittest.mock import patch

from tools.qikvrt_github_admin_effect_executor import AdminEffectError, build_put_payload, execute


REQUEST = {
    "schema": "qikvrt_github_admin_effect_request_v1",
    "request_id": "r1",
    "authorization_id": "a1",
    "effect_type": "RULESET_PULL_REQUEST_REVIEW_POLICY",
    "repository": "Goldkelch/qik-vrt",
    "admin_principal": {
        "account_login": "Goldkelch",
        "installation_id": 147849532,
        "required_repository_permission": "administration:write",
    },
    "ruleset_id": 19344903,
    "ruleset_name": "QIK-VRT main protection",
    "expected_conditions": {"ref_name": {"exclude": [], "include": ["refs/heads/main"]}},
    "expected_before": {
        "required_approving_review_count": 0,
        "require_code_owner_review": False,
        "dismiss_stale_reviews_on_push": False,
        "require_last_push_approval": False,
    },
    "desired_after": {
        "required_approving_review_count": 1,
        "require_code_owner_review": True,
        "dismiss_stale_reviews_on_push": True,
        "require_last_push_approval": True,
    },
    "force": False,
}


def live(after: bool = False):
    values = REQUEST["desired_after"] if after else REQUEST["expected_before"]
    return {
        "id": 19344903,
        "name": "QIK-VRT main protection",
        "target": "branch",
        "enforcement": "active",
        "bypass_actors": [],
        "conditions": copy.deepcopy(REQUEST["expected_conditions"]),
        "rules": [
            {"type": "pull_request", "parameters": {
                **values,
                "required_review_thread_resolution": True,
                "allowed_merge_methods": ["merge", "squash", "rebase"],
                "required_reviewers": [],
            }},
            {"type": "required_status_checks", "parameters": {
                "strict_required_status_checks_policy": True,
                "do_not_enforce_on_create": False,
                "required_status_checks": [{"context": "test", "integration_id": 15368}],
            }},
            {"type": "non_fast_forward"},
            {"type": "deletion"},
        ],
        "updated_at": "2026-07-21T07:53:09.362+02:00",
    }


class AdminEffectExecutorTests(unittest.TestCase):
    def test_patch_changes_only_four_review_parameters(self):
        before = live()
        plan = build_put_payload(before, REQUEST)
        self.assertFalse(plan["already_applied"])
        payload = plan["payload"]
        self.assertEqual(payload["rules"][1:], before["rules"][1:])
        params = payload["rules"][0]["parameters"]
        for key, value in REQUEST["desired_after"].items():
            self.assertEqual(params[key], value)
        self.assertTrue(params["required_review_thread_resolution"])
        self.assertEqual(params["allowed_merge_methods"], ["merge", "squash", "rebase"])

    def test_compare_and_swap_rejects_drift(self):
        drift = live()
        drift["rules"][0]["parameters"]["required_approving_review_count"] = 2
        with self.assertRaises(AdminEffectError):
            build_put_payload(drift, REQUEST)

    def test_already_applied_is_idempotent(self):
        plan = build_put_payload(live(after=True), REQUEST)
        self.assertTrue(plan["already_applied"])
        self.assertIsNone(plan["payload"])

    def test_force_true_is_rejected(self):
        request = copy.deepcopy(REQUEST)
        request["force"] = True
        with self.assertRaises(AdminEffectError):
            build_put_payload(live(), request)

    def test_wrong_principal_account_is_rejected(self):
        request = copy.deepcopy(REQUEST)
        request["admin_principal"]["account_login"] = "ingolf-lohmann"
        with self.assertRaises(AdminEffectError):
            build_put_payload(live(), request)

    def test_invalid_installation_id_is_rejected(self):
        request = copy.deepcopy(REQUEST)
        request["admin_principal"]["installation_id"] = 0
        with self.assertRaises(AdminEffectError):
            build_put_payload(live(), request)

    def test_execute_is_get_put_get_and_verifies(self):
        calls = []
        def fake_api(base, token, method, path, payload=None):
            calls.append((method, path, payload))
            if method == "GET" and len(calls) == 1:
                return live()
            if method == "PUT":
                return live(after=True)
            return live(after=True)
        with patch("tools.qikvrt_github_admin_effect_executor._api", side_effect=fake_api):
            receipt = execute(REQUEST, token="secret", credential_source="github_app_installation:147849532")
        self.assertEqual([item[0] for item in calls], ["GET", "PUT", "GET"])
        self.assertEqual(receipt["state"], "APPLIED_VERIFIED")
        self.assertTrue(receipt["verified"])
        self.assertFalse(receipt["credential_serialized"])
        self.assertEqual(receipt["admin_principal"]["installation_id"], 147849532)
        self.assertEqual(receipt["credential_source"], "github_app_installation:147849532")
        self.assertNotIn("secret", str(receipt))

    def test_dry_run_performs_only_get(self):
        calls = []
        def fake_api(base, token, method, path, payload=None):
            calls.append(method)
            return live()
        with patch("tools.qikvrt_github_admin_effect_executor._api", side_effect=fake_api):
            receipt = execute(REQUEST, token="secret", dry_run=True)
        self.assertEqual(calls, ["GET"])
        self.assertEqual(receipt["state"], "DRY_RUN")


if __name__ == "__main__":
    unittest.main()
