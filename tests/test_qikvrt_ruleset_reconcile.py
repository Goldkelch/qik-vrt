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
from tools.qikvrt_hold_contract import validate_hold_object


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

    def test_reobserve_reads_once_and_never_admits_a_put(self):
        calls = []

        def request(*args, **kwargs):
            calls.append(mock.call(*args, **kwargs))
            return self.current(), '"current-etag"'

        with mock.patch.object(reconcile, "_request", side_effect=request):
            result = reconcile.reobserve("admin-token", self.policy)

        self.assertEqual([call.args[0] for call in calls], ["GET"])
        self.assertEqual(result["state"], "CURRENT")
        self.assertEqual(result["mutation"], "NONE")

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
            with self.assertRaisesRegex(
                reconcile.RulesetMutationUncertain, "PUT_UNCONFIRMED_NOT_CURRENT"
            ) as raised:
                reconcile.reconcile("admin-token", self.policy)

        self.assertEqual([call.args[0] for call in calls], ["GET", "GET", "PUT", "GET"])
        self.assertTrue(raised.exception.effect_transport_attempted)
        self.assertEqual(raised.exception.mutation, "PUT_UNCONFIRMED_NOT_CURRENT")

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

    def test_installation_quota_retries_only_get_with_the_bounded_policy(self):
        def quota_error():
            return reconcile.urllib.error.HTTPError(
                "https://api.github.com/repos/Goldkelch/qik-vrt/rulesets/19344903",
                403,
                "forbidden",
                None,
                io.BytesIO(
                    b'{"message":"API rate limit exceeded for installation."}'
                ),
            )

        with mock.patch.object(
            reconcile.urllib.request,
            "urlopen",
            side_effect=[quota_error(), quota_error(), quota_error()],
        ) as urlopen, mock.patch.object(reconcile.time, "sleep") as sleeper:
            with self.assertRaises(reconcile.GitHubInstallationRateLimit) as raised:
                reconcile._request(
                    "GET",
                    "https://api.github.com/repos/Goldkelch/qik-vrt/rulesets/19344903",
                    "admin-token",
                )

        self.assertEqual(str(raised.exception), "GITHUB_INSTALLATION_RATE_LIMIT_EXHAUSTED")
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual(sleeper.call_args_list, [mock.call(15), mock.call(45)])

    def test_installation_quota_never_retries_a_conditional_put(self):
        quota = reconcile.urllib.error.HTTPError(
            "https://api.github.com/repos/Goldkelch/qik-vrt/rulesets/19344903",
            403,
            "forbidden",
            None,
            io.BytesIO(
                b'{"message":"API rate limit exceeded for installation."}'
            ),
        )
        with mock.patch.object(
            reconcile.urllib.request,
            "urlopen",
            side_effect=quota,
        ) as urlopen, mock.patch.object(reconcile.time, "sleep") as sleeper:
            with self.assertRaises(reconcile.GitHubInstallationRateLimit) as raised:
                reconcile._request(
                    "PUT",
                    "https://api.github.com/repos/Goldkelch/qik-vrt/rulesets/19344903",
                    "admin-token",
                    payload=reconcile.desired_payload(self.policy),
                    etag='"exact-etag"',
                )

        self.assertEqual(urlopen.call_count, 1)
        sleeper.assert_not_called()
        self.assertTrue(raised.exception.effect_transport_attempted)
        self.assertEqual(raised.exception.mutation, "PUT_UNCONFIRMED_RATE_LIMIT")

    def test_installation_id_quota_variant_is_typed_for_a_put(self):
        quota = reconcile.urllib.error.HTTPError(
            "https://api.github.com/repos/Goldkelch/qik-vrt/rulesets/19344903",
            403,
            "forbidden",
            None,
            io.BytesIO(
                b'{"message":"API rate limit exceeded for installation ID 12345."}'
            ),
        )
        with mock.patch.object(
            reconcile.urllib.request,
            "urlopen",
            side_effect=quota,
        ) as urlopen:
            with self.assertRaises(reconcile.GitHubInstallationRateLimit) as raised:
                reconcile._request(
                    "PUT",
                    "https://api.github.com/repos/Goldkelch/qik-vrt/rulesets/19344903",
                    "admin-token",
                    payload=reconcile.desired_payload(self.policy),
                    etag='"exact-etag"',
                )

        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(raised.exception.mutation, "PUT_UNCONFIRMED_RATE_LIMIT")

    def test_put_quota_reads_back_once_without_repeating_the_effect(self):
        drift = copy.deepcopy(self.current())
        drift["enforcement"] = "disabled"
        calls = []

        def request(method, *_args, **_kwargs):
            calls.append(method)
            if calls == ["GET"]:
                return drift, '"initial-etag"'
            if calls == ["GET", "GET"]:
                return drift, '"reobserved-etag"'
            if calls == ["GET", "GET", "PUT"]:
                raise reconcile.GitHubInstallationRateLimit(
                    mutation="PUT_UNCONFIRMED_RATE_LIMIT",
                    effect_transport_attempted=True,
                )
            if calls == ["GET", "GET", "PUT", "GET"]:
                return self.current(), '"final-etag"'
            self.fail(f"unexpected ruleset request sequence: {calls}")

        with mock.patch.object(reconcile, "_request", side_effect=request):
            result = reconcile.reconcile("admin-token", self.policy)

        self.assertEqual(calls, ["GET", "GET", "PUT", "GET"])
        self.assertEqual(result["state"], "CURRENT")
        self.assertEqual(result["mutation"], "PUT")
        self.assertTrue(result["effect_observed"])
        self.assertTrue(result["effect_transport_attempted"])
        self.assertEqual(result["put_response"], "INSTALLATION_RATE_LIMIT_REOBSERVED_CURRENT")

    def test_put_quota_with_noncurrent_readback_holds_without_a_second_put(self):
        drift = copy.deepcopy(self.current())
        drift["enforcement"] = "disabled"
        calls = []

        def request(method, *_args, **_kwargs):
            calls.append(method)
            if calls in (["GET"], ["GET", "GET"], ["GET", "GET", "PUT", "GET"]):
                return drift, '"exact-etag"'
            if calls == ["GET", "GET", "PUT"]:
                raise reconcile.GitHubInstallationRateLimit(
                    mutation="PUT_UNCONFIRMED_RATE_LIMIT",
                    effect_transport_attempted=True,
                )
            self.fail(f"unexpected ruleset request sequence: {calls}")

        with mock.patch.object(reconcile, "_request", side_effect=request):
            with self.assertRaises(reconcile.GitHubInstallationRateLimit) as raised:
                reconcile.reconcile("admin-token", self.policy)

        self.assertEqual(calls, ["GET", "GET", "PUT", "GET"])
        self.assertTrue(raised.exception.effect_transport_attempted)
        self.assertEqual(raised.exception.mutation, "PUT_UNCONFIRMED_RATE_LIMIT")

    def test_put_quota_with_quota_limited_readback_keeps_the_attempted_put(self):
        drift = copy.deepcopy(self.current())
        drift["enforcement"] = "disabled"
        calls = []

        def request(method, *_args, **_kwargs):
            calls.append(method)
            if calls in (["GET"], ["GET", "GET"]):
                return drift, '"exact-etag"'
            if calls == ["GET", "GET", "PUT"]:
                raise reconcile.GitHubInstallationRateLimit(
                    mutation="PUT_UNCONFIRMED_RATE_LIMIT",
                    effect_transport_attempted=True,
                )
            if calls == ["GET", "GET", "PUT", "GET"]:
                raise reconcile.GitHubInstallationRateLimit()
            self.fail(f"unexpected ruleset request sequence: {calls}")

        with mock.patch.object(reconcile, "_request", side_effect=request):
            with self.assertRaises(reconcile.GitHubInstallationRateLimit) as raised:
                reconcile.reconcile("admin-token", self.policy)

        self.assertEqual(calls, ["GET", "GET", "PUT", "GET"])
        self.assertTrue(raised.exception.effect_transport_attempted)
        self.assertEqual(raised.exception.mutation, "PUT_UNCONFIRMED_RATE_LIMIT")

    def test_successful_put_with_failed_readback_never_repeats_the_mutation(self):
        drift = copy.deepcopy(self.current())
        drift["enforcement"] = "disabled"
        calls = []

        def request(method, *_args, **_kwargs):
            calls.append(method)
            if calls in (["GET"], ["GET", "GET"]):
                return drift, '"exact-etag"'
            if calls == ["GET", "GET", "PUT"]:
                return drift, '"put-etag"'
            if calls == ["GET", "GET", "PUT", "GET"]:
                raise reconcile.RulesetBlock("GitHub ruleset API HTTP 500")
            self.fail(f"unexpected ruleset request sequence: {calls}")

        with mock.patch.object(reconcile, "_request", side_effect=request):
            with self.assertRaises(reconcile.RulesetMutationUncertain) as raised:
                reconcile.reconcile("admin-token", self.policy)

        self.assertEqual(calls, ["GET", "GET", "PUT", "GET"])
        self.assertEqual(raised.exception.mutation, "PUT_UNCONFIRMED_READBACK_FAILED")
        self.assertTrue(raised.exception.effect_transport_attempted)

    def test_put_urlerror_is_uncertain_and_never_repeated(self):
        drift = copy.deepcopy(self.current())
        drift["enforcement"] = "disabled"
        calls = []

        def request(method, *_args, **_kwargs):
            calls.append(method)
            if calls in (["GET"], ["GET", "GET"]):
                return drift, '"exact-etag"'
            if calls == ["GET", "GET", "PUT"]:
                raise reconcile.RulesetBlock("GitHub ruleset API PUT transport or response failure: timed out")
            self.fail(f"unexpected ruleset request sequence: {calls}")

        with mock.patch.object(reconcile, "_request", side_effect=request):
            with self.assertRaises(reconcile.RulesetMutationUncertain) as raised:
                reconcile.reconcile("admin-token", self.policy)

        self.assertEqual(calls, ["GET", "GET", "PUT"])
        self.assertEqual(raised.exception.mutation, "PUT_UNCONFIRMED_TRANSPORT_FAILED")
        self.assertTrue(raised.exception.effect_transport_attempted)

    def test_successful_put_then_urlerror_readback_preserves_the_attempt(self):
        drift = copy.deepcopy(self.current())
        drift["enforcement"] = "disabled"
        calls = []

        def request(method, *_args, **_kwargs):
            calls.append(method)
            if calls in (["GET"], ["GET", "GET"]):
                return drift, '"exact-etag"'
            if calls == ["GET", "GET", "PUT"]:
                return drift, '"put-etag"'
            if calls == ["GET", "GET", "PUT", "GET"]:
                raise reconcile.RulesetBlock("GitHub ruleset API GET transport or response failure: timed out")
            self.fail(f"unexpected ruleset request sequence: {calls}")

        with mock.patch.object(reconcile, "_request", side_effect=request):
            with self.assertRaises(reconcile.RulesetMutationUncertain) as raised:
                reconcile.reconcile("admin-token", self.policy)

        self.assertEqual(calls, ["GET", "GET", "PUT", "GET"])
        self.assertEqual(raised.exception.mutation, "PUT_UNCONFIRMED_READBACK_FAILED")
        self.assertTrue(raised.exception.effect_transport_attempted)

    def test_raw_urlerror_and_malformed_json_are_typed_as_ruleset_blocks(self):
        url = "https://api.github.com/repos/Goldkelch/qik-vrt/rulesets/19344903"
        with mock.patch.object(
            reconcile.urllib.request,
            "urlopen",
            side_effect=reconcile.urllib.error.URLError("timed out"),
        ) as urlopen:
            with self.assertRaisesRegex(reconcile.RulesetBlock, "transport or response failure"):
                reconcile._request(
                    "PUT",
                    url,
                    "admin-token",
                    payload=reconcile.desired_payload(self.policy),
                    etag='"exact-etag"',
                )
        self.assertEqual(urlopen.call_count, 1)

        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.headers = {}
        response.read.return_value = b"{"
        with mock.patch.object(reconcile.urllib.request, "urlopen", return_value=response):
            with self.assertRaisesRegex(reconcile.RulesetBlock, "transport or response failure"):
                reconcile._request("GET", url, "admin-token")

    def test_durable_put_intent_exists_before_the_network_call_and_survives_failure(self):
        drift = copy.deepcopy(self.current())
        drift["enforcement"] = "disabled"
        calls = []
        with tempfile.TemporaryDirectory() as directory:
            ledger = pathlib.Path(directory) / "effect-attempts.json"
            from tools import qikvrt_effect_attempts as effect_attempts

            effect_attempts.create_empty_ledger(ledger)

            def request(method, *_args, **_kwargs):
                calls.append(method)
                if calls in (["GET"], ["GET", "GET"]):
                    return drift, '"exact-etag"'
                if calls == ["GET", "GET", "PUT"]:
                    entries = effect_attempts.read_attempts(ledger)
                    self.assertEqual(entries[-1]["kind"], "ruleset_put")
                    self.assertEqual(entries[-1]["transport_outcome"], "ATTEMPTED_PENDING_READBACK")
                    raise reconcile.RulesetBlock("GitHub ruleset API PUT transport or response failure")
                self.fail(f"unexpected ruleset request sequence: {calls}")

            with mock.patch.object(reconcile, "_request", side_effect=request):
                with self.assertRaises(reconcile.RulesetMutationUncertain):
                    reconcile.reconcile(
                        "admin-token",
                        self.policy,
                        effect_attempt_ledger=ledger,
                    )
            entries = effect_attempts.read_attempts(ledger)

        self.assertEqual(calls, ["GET", "GET", "PUT"])
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["effect_transport_attempted"])
        self.assertFalse(entries[0]["effect_observed"])

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
        self.assertEqual(validate_hold_object(value)["d0"], 2)

    def test_installation_quota_emits_the_explicit_d0_two_hold_contract(self):
        class Output:
            def __init__(self) -> None:
                self.buffer = io.BytesIO()

        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "receipt.json"
            with mock.patch.dict(
                os.environ,
                {"QIKVRT_RULESET_ADMIN_TOKEN": "test-token"},
                clear=True,
            ), mock.patch.object(
                reconcile,
                "reconcile",
                side_effect=reconcile.GitHubInstallationRateLimit(
                    mutation="PUT_UNCONFIRMED_RATE_LIMIT",
                    effect_transport_attempted=True,
                ),
            ), mock.patch.object(reconcile.sys, "stdout", Output()):
                self.assertEqual(reconcile.main(["--apply", "--receipt", str(receipt)]), 2)
            value = json.loads(receipt.read_text(encoding="utf-8"))

        self.assertEqual(value["state"], "HOLD")
        self.assertEqual(value["verification_state"], "HOLD_UNVERIFIED")
        self.assertEqual(value["first_blocker"], "GITHUB_INSTALLATION_RATE_LIMIT_EXHAUSTED")
        self.assertEqual(value["d0"], 2)
        self.assertEqual(validate_hold_object(value)["d0"], 2)
        self.assertTrue(value["effect_transport_attempted"])
        self.assertEqual(value["mutation"], "PUT_UNCONFIRMED_RATE_LIMIT")

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
        hold = validate_hold_object(value)
        self.assertEqual(hold["d0"], 2)
        self.assertNotIn("installation quota", hold["retry_condition"]["predicate"])

    def test_uncertain_put_transport_emits_an_explicit_d0_two_hold(self):
        class Output:
            def __init__(self) -> None:
                self.buffer = io.BytesIO()

        with tempfile.TemporaryDirectory() as directory:
            receipt = pathlib.Path(directory) / "receipt.json"
            with mock.patch.dict(
                os.environ,
                {"QIKVRT_RULESET_ADMIN_TOKEN": "test-token"},
                clear=True,
            ), mock.patch.object(
                reconcile,
                "reconcile",
                side_effect=reconcile.RulesetMutationUncertain(
                    "PUT_UNCONFIRMED_READBACK_FAILED",
                    detail="GitHub ruleset API HTTP 500",
                ),
            ), mock.patch.object(reconcile.sys, "stdout", Output()):
                self.assertEqual(reconcile.main(["--apply", "--receipt", str(receipt)]), 2)
            value = json.loads(receipt.read_text(encoding="utf-8"))

        self.assertEqual(value["mutation"], "PUT_UNCONFIRMED_READBACK_FAILED")
        self.assertTrue(value["effect_transport_attempted"])
        self.assertFalse(value["effect_observed"])
        self.assertEqual(validate_hold_object(value)["d0"], 2)

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
