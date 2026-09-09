#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import io
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

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

    def test_current_reconcile_is_authenticated_get_only(self):
        calls = []

        def request(*args, **kwargs):
            calls.append(mock.call(*args, **kwargs))
            return self.current(), '"current-etag"'

        with mock.patch.object(reconcile, "_request", side_effect=request):
            result = reconcile.reconcile("admin-token", self.policy)

        self.assertEqual(result["state"], "CURRENT")
        self.assertEqual(result["mutation"], "NONE")
        self.assertEqual([call.args[0] for call in calls], ["GET"])
        self.assertNotIn("PUT", [call.args[0] for call in calls])

    def test_drift_reconcile_uses_get_get_conditional_put_then_current_readback(self):
        drift = copy.deepcopy(self.current())
        drift["enforcement"] = "disabled"
        responses = iter(
            [
                (drift, '"initial-etag"'),
                (drift, '"reobserved-etag"'),
                (drift, '"put-etag"'),
                (self.current(), '"final-etag"'),
            ]
        )
        calls = []

        def request(*args, **kwargs):
            calls.append(mock.call(*args, **kwargs))
            return next(responses)

        with mock.patch.object(reconcile, "_request", side_effect=request):
            result = reconcile.reconcile("admin-token", self.policy)

        self.assertEqual(result["state"], "CURRENT")
        self.assertEqual(result["mutation"], "PUT")
        self.assertTrue(result["effect_observed"])
        self.assertEqual([call.args[0] for call in calls], ["GET", "GET", "PUT", "GET"])
        self.assertEqual(calls[2].kwargs["etag"], '"reobserved-etag"')
        self.assertEqual(calls[2].kwargs["payload"], reconcile.desired_payload(self.policy))

    def test_second_get_drift_race_fails_before_put(self):
        initial = copy.deepcopy(self.current())
        initial["enforcement"] = "disabled"
        changed = copy.deepcopy(initial)
        changed["name"] = "different live ruleset"
        calls = []

        def request(*args, **kwargs):
            calls.append(mock.call(*args, **kwargs))
            return [(initial, '"first-etag"'), (changed, '"second-etag"')][len(calls) - 1]

        with mock.patch.object(reconcile, "_request", side_effect=request):
            with self.assertRaisesRegex(reconcile.RulesetBlock, "drifted after planning"):
                reconcile.reconcile("admin-token", self.policy)

        self.assertEqual([call.args[0] for call in calls], ["GET", "GET"])

    def test_post_put_noncurrent_readback_fails_closed(self):
        drift = copy.deepcopy(self.current())
        drift["enforcement"] = "disabled"
        responses = iter(
            [
                (drift, '"initial-etag"'),
                (drift, '"reobserved-etag"'),
                (drift, '"put-etag"'),
                (drift, '"final-etag"'),
            ]
        )
        calls = []

        def request(*args, **kwargs):
            calls.append(mock.call(*args, **kwargs))
            return next(responses)

        with mock.patch.object(reconcile, "_request", side_effect=request):
            with self.assertRaisesRegex(reconcile.RulesetBlock, "not confirmed"):
                reconcile.reconcile("admin-token", self.policy)

        self.assertEqual([call.args[0] for call in calls], ["GET", "GET", "PUT", "GET"])

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

    def test_api_requests_use_the_ruleset_admin_token(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'{"id": 19344903}'
        response.headers = {}
        with mock.patch.object(
            reconcile.urllib.request,
            "urlopen",
            return_value=response,
        ) as urlopen:
            reconcile._request(
                "GET",
                "https://api.github.com/repos/Goldkelch/qik-vrt/rulesets/19344903",
                "admin-token",
            )
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer " + "admin-token")

    def test_only_missing_admin_credential_requests_authority(self):
        class Output:
            def __init__(self) -> None:
                self.buffer = io.BytesIO()

        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "receipt.json"
            with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(
                reconcile.sys, "stdout", Output()
            ):
                self.assertEqual(reconcile.main(["--apply", "--receipt", str(receipt)]), 2)
            value = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(value["state"], "REQUEST_AUTHORITY")
        self.assertEqual(value["first_blocker"], "QIKVRT_RULESET_ADMIN_TOKEN is unavailable")

    def test_api_or_readback_failure_remains_hold(self):
        class Output:
            def __init__(self) -> None:
                self.buffer = io.BytesIO()

        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "receipt.json"
            with mock.patch.dict(os.environ, {"QIKVRT_RULESET_ADMIN_TOKEN": "test-token"}, clear=True), mock.patch.object(
                reconcile, "reconcile", side_effect=reconcile.RulesetBlock("GitHub ruleset API HTTP 403")
            ), mock.patch.object(reconcile.sys, "stdout", Output()):
                self.assertEqual(reconcile.main(["--apply", "--receipt", str(receipt)]), 2)
            value = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["next_action"], "REOBSERVE_EXACT_RULESET_API_AND_READBACK_EVIDENCE")

    def test_policy_load_failure_writes_structured_hold_receipt(self):
        class Output:
            def __init__(self) -> None:
                self.buffer = io.BytesIO()

        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "receipt.json"
            with mock.patch.object(
                reconcile,
                "load_policy",
                side_effect=reconcile.RulesetBlock("ruleset policy schema mismatch"),
            ), mock.patch.object(reconcile.sys, "stdout", Output()):
                self.assertEqual(reconcile.main(["--apply", "--receipt", str(receipt)]), 2)
            value = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["repository"], reconcile.DEFAULT_REPOSITORY)
        self.assertEqual(value["ruleset_id"], reconcile.DEFAULT_RULESET_ID)
        self.assertEqual(value["first_blocker"], "ruleset policy schema mismatch")

    def test_app_mint_failure_override_remains_hold(self):
        class Output:
            def __init__(self) -> None:
                self.buffer = io.BytesIO()

        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "receipt.json"
            with mock.patch.dict(
                os.environ,
                {
                    "QIKVRT_RULESET_AUTHORITY_STATE": "HOLD",
                    "QIKVRT_RULESET_AUTHORITY_BLOCKER": "QIKVRT_RULESET_GITHUB_APP_TOKEN_MINT_FAILED",
                },
                clear=True,
            ), mock.patch.object(reconcile.sys, "stdout", Output()):
                self.assertEqual(reconcile.main(["--apply", "--receipt", str(receipt)]), 2)
            value = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["first_blocker"], "QIKVRT_RULESET_GITHUB_APP_TOKEN_MINT_FAILED")

    def test_missing_app_configuration_override_requests_authority(self):
        class Output:
            def __init__(self) -> None:
                self.buffer = io.BytesIO()

        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "receipt.json"
            with mock.patch.dict(
                os.environ,
                {
                    "QIKVRT_RULESET_AUTHORITY_STATE": "REQUEST_AUTHORITY",
                    "QIKVRT_RULESET_AUTHORITY_BLOCKER": "QIKVRT_RULESET_GITHUB_APP_CONFIGURATION_MISSING",
                },
                clear=True,
            ), mock.patch.object(reconcile.sys, "stdout", Output()):
                self.assertEqual(reconcile.main(["--apply", "--receipt", str(receipt)]), 2)
            value = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(value["state"], "REQUEST_AUTHORITY")
        self.assertEqual(value["first_blocker"], "QIKVRT_RULESET_GITHUB_APP_CONFIGURATION_MISSING")

if __name__ == "__main__":
    unittest.main()
