#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import base64
import hashlib
import io
import json
import re
import unittest
import zipfile
from unittest import mock

from tools import qikvrt_ruleset_reconcile as reconcile


class RulesetReconcileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = reconcile.load_policy()
        self.authority_proof = {
            "schema": "qikvrt_ruleset_authority_environment_readback_v1",
            "state": "VERIFIED_FOR_THIS_EFFECT_ONLY",
        }

    def current(self):
        return {
            "id": self.policy["ruleset_id"],
            "source": self.policy["repository"],
            **reconcile.desired_payload(self.policy),
        }

    def source_run(self, *, status="completed", conclusion="success"):
        return {
            "path": ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml",
            "workflow_id": 4242,
            "name": "mutable display title for run 17",
            "event": "workflow_run",
            "head_branch": "main",
            "head_sha": "a" * 40,
            "repository": {"full_name": self.policy["repository"]},
            "run_attempt": 3,
            "status": status,
            "conclusion": conclusion,
        }

    def source_jobs(self, *, status="completed", conclusion="success"):
        return {
            "total_count": 1,
            "jobs": [
                {
                    "id": 7171,
                    "name": reconcile.SOURCE_BRIDGE_JOB_NAME,
                    "run_attempt": 3,
                    "status": status,
                    "conclusion": conclusion,
                    "steps": [
                        {
                            "number": 3,
                            "name": reconcile.SOURCE_INTENT_STEP_NAME,
                            "status": "completed",
                            "conclusion": "success",
                        },
                        {
                            "number": 4,
                            "name": reconcile.SOURCE_TRANSPORT_STEP_NAME,
                            "status": "in_progress",
                            "conclusion": None,
                        },
                    ],
                }
            ],
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

    def test_absent_bypass_actors_is_incomplete_visibility_not_empty(self):
        hidden = self.current()
        hidden.pop("bypass_actors")
        hidden_result = reconcile.evaluate(hidden, self.policy)
        visible_result = reconcile.evaluate(self.current(), self.policy)
        self.assertEqual(hidden_result["state"], reconcile.INCOMPLETE_VISIBILITY)
        self.assertEqual(
            hidden_result["first_blocker"],
            "RULESET_BYPASS_ACTORS_VISIBILITY_INCOMPLETE",
        )
        self.assertNotEqual(
            hidden_result["pre_state_sha256"], visible_result["pre_state_sha256"]
        )

    def test_explicit_empty_bypass_actors_can_be_current(self):
        current = self.current()
        self.assertEqual(current["bypass_actors"], [])
        self.assertEqual(reconcile.evaluate(current, self.policy)["state"], "CURRENT")

    def test_non_list_bypass_visibility_fails_closed(self):
        current = self.current()
        current["bypass_actors"] = None
        with self.assertRaisesRegex(reconcile.RulesetBlock, "explicit list"):
            reconcile.evaluate(current, self.policy)

    def test_repository_http_layer_rejects_missing_token_and_foreign_origin(self):
        with self.assertRaisesRegex(reconcile.RulesetBlock, "token is unavailable"):
            reconcile.github_get("https://api.github.com/repos/Goldkelch/qik-vrt", "")
        with self.assertRaisesRegex(reconcile.RulesetBlock, "outside api.github.com"):
            reconcile.github_get("https://example.invalid/repos/Goldkelch/qik-vrt", "x")

    def test_reconciler_workflow_keeps_admin_token_separate(self):
        workflow = (
            reconcile.ROOT / ".github/workflows/qikvrt_ruleset_reconcile.yml"
        ).read_text(encoding="utf-8")
        bridge = (
            reconcile.ROOT
            / ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("environment: qikvrt-ruleset-authority", workflow)
        self.assertIn("QIKVRT_ENV_RULESET_ADMIN_TOKEN", workflow)
        self.assertNotIn("secrets.QIKVRT_RULESET_ADMIN_TOKEN", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("--apply", workflow)
        self.assertIn("--receipt", workflow)
        permissions = workflow[workflow.index("permissions:") : workflow.index("concurrency:")]
        self.assertIn("contents: read", permissions)
        self.assertNotIn("actions:", permissions)
        self.assertNotIn("actions: write", permissions)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("QIKVRT_ENV_RULESET_ADMIN_TOKEN", bridge)

    def test_event_bridge_is_exact_trusted_main_bound(self):
        bridge = (
            reconcile.ROOT
            / ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('- "QIKVRT required code-owner review"', bridge)
        self.assertIn(
            "github.event.workflow_run.path == '.github/workflows/qikvrt_required_review_gate.yml'",
            bridge,
        )
        self.assertIn("github.event.workflow_run.head_branch == 'main'", bridge)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", bridge)
        self.assertNotIn(
            "github.event.workflow_run.name == 'QIKVRT required code-owner review'",
            bridge,
        )
        self.assertIn(
            "  hold-ruleset-reconciliation-for-manual-authority:", bridge
        )
        self.assertIn("qikvrt_ruleset_manual_authority_hold_v1", bridge)
        self.assertIn(
            'reason:"AUTOMATIC_BRANCH_PROTECTION_CHANGE_NOT_AUTHORIZED"',
            bridge,
        )
        self.assertIn("automatic_ruleset_dispatch:false", bridge)
        self.assertIn("automatic_reconciler_rerun:false", bridge)
        self.assertIn("automatic_requested_review_resume:false", bridge)
        self.assertNotIn('event_type:"qikvrt_ruleset_reconcile"', bridge)
        self.assertNotIn("qikvrt_ruleset_reconcile_dispatch_v1", bridge)
        self.assertNotIn("dispatch-ruleset-reconciliation:", bridge)
        ruleset_job = bridge[
            bridge.index("  hold-ruleset-reconciliation-for-manual-authority:") :
        ]
        permissions = ruleset_job[
            ruleset_job.index("    permissions:") : ruleset_job.index("    env:")
        ]
        self.assertIn("actions: read", permissions)
        self.assertIn("contents: read", permissions)
        self.assertNotIn("contents: write", permissions)
        self.assertNotIn("actions: write", permissions)
        self.assertNotIn("QIKVRT_ENV_RULESET_ADMIN_TOKEN", bridge)

    def test_active_reconciler_failure_or_cancel_cannot_consume_fresh_edge(self):
        bridge = (
            reconcile.ROOT
            / ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
        ).read_text(encoding="utf-8")
        workflow = (
            reconcile.ROOT / ".github/workflows/qikvrt_ruleset_reconcile.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Suppress an already active exact reconciler", bridge)
        self.assertNotIn("steps.active.outputs", bridge)
        self.assertNotIn("steps.plan.outputs.dispatch", bridge)
        self.assertNotIn("repository_dispatch:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("group: qikvrt-main-ruleset-manual-authority", workflow)
        self.assertIn("cancel-in-progress: false", workflow)

    def test_ruleset_evidence_uploads_include_hidden_paths_fail_closed(self):
        bridge = (
            reconcile.ROOT
            / ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
        ).read_text(encoding="utf-8")
        workflow = (
            reconcile.ROOT / ".github/workflows/qikvrt_ruleset_reconcile.yml"
        ).read_text(encoding="utf-8")
        bridge_upload = bridge[
            bridge.index("Preserve the manual ruleset Authority HOLD") :
        ]
        workflow_upload = workflow[
            workflow.index("Preserve the exact manual reconciliation receipt") :
        ]
        for upload in (bridge_upload, workflow_upload):
            self.assertIn("include-hidden-files: true", upload)
            self.assertIn("if-no-files-found: error", upload)

    def test_secret_workflow_validates_envelope_before_admin_token_step(self):
        workflow = (
            reconcile.ROOT / ".github/workflows/qikvrt_ruleset_reconcile.yml"
        ).read_text(encoding="utf-8")
        validation = workflow.index(
            "Bind the sealed evaluator to live main without admin authority"
        )
        secret = workflow.index("QIKVRT_ENV_RULESET_ADMIN_TOKEN")
        self.assertLess(validation, secret)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("github.workflow_sha == github.sha", workflow)
        self.assertNotIn("github.event.client_payload", workflow)
        self.assertNotIn("classify_dispatch_source_run", workflow)
        self.assertNotIn("classify_dispatch_source_jobs", workflow)
        self.assertIn('live_main=', workflow)
        self.assertIn('live_main_after=', workflow)
        apply_invocation = workflow.index(
            "python3 -B tools/qikvrt_ruleset_reconcile.py"
        )
        self.assertLess(workflow.index('live_main='), apply_invocation)
        self.assertGreater(workflow.index('live_main_after='), apply_invocation)
        self.assertNotIn("candidate_bytes_consumed", workflow)
        self.assertIn("github_get", workflow)
        self.assertNotIn("gh api", workflow)
        self.assertIn("ref: ${{ github.workflow_sha }}", workflow)
        self.assertNotIn("github.event.workflow_run.head_sha }}", workflow)
        for trigger in ("pull_request:", "pull_request_target:", "issue_comment:", "schedule:"):
            self.assertNotIn(trigger, workflow)

    def test_apply_uses_double_read_put_and_exact_post_readback(self):
        drift = self.current()
        pull_request = next(
            rule for rule in drift["rules"] if rule["type"] == "pull_request"
        )
        pull_request["parameters"]["required_approving_review_count"] = 0
        desired = self.current()
        calls = []

        def request(method, url, token, *, payload=None):
            calls.append((method, payload))
            if len(calls) <= 3:
                return copy.deepcopy(drift)
            return copy.deepcopy(desired)

        with mock.patch.object(reconcile, "_request", side_effect=request), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            return_value=self.authority_proof,
        ):
            result = reconcile.reconcile("token", self.policy)

        self.assertEqual(
            [call[0] for call in calls],
            ["GET", "GET", "GET", "PUT", "GET"],
        )
        self.assertEqual(calls[3][1], reconcile.desired_payload(self.policy))
        self.assertEqual(result["state"], "CURRENT")
        self.assertEqual(result["mutation"], "PUT")
        self.assertTrue(result["pre_effect_double_read"])
        self.assertTrue(result["immediate_pre_effect_reobservation"])
        self.assertEqual(result["write_concurrency"], "LAST_WRITER_WINS")
        self.assertFalse(result["conditional_update_used"])
        self.assertFalse(result["get_put_race_eliminated"])
        self.assertFalse(result["converged_before_mutation"])
        self.assertTrue(result["post_update_readback"])
        self.assertTrue(result["effect_observed"])

    def test_apply_rejects_pre_effect_drift_without_put(self):
        initial = self.current()
        next_state = self.current()
        initial_pr = next(rule for rule in initial["rules"] if rule["type"] == "pull_request")
        next_pr = next(rule for rule in next_state["rules"] if rule["type"] == "pull_request")
        initial_pr["parameters"]["required_approving_review_count"] = 0
        next_pr["parameters"]["require_code_owner_review"] = False
        calls = []

        def request(method, url, token, *, payload=None):
            calls.append(method)
            if len(calls) == 1:
                return copy.deepcopy(initial)
            return copy.deepcopy(next_state)

        with mock.patch.object(reconcile, "_request", side_effect=request), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            return_value=self.authority_proof,
        ):
            with self.assertRaisesRegex(reconcile.RulesetBlock, "drifted after planning"):
                reconcile.reconcile("token", self.policy)
        self.assertEqual(calls, ["GET", "GET"])

    def test_admin_visibility_absence_blocks_without_put(self):
        hidden = self.current()
        hidden.pop("bypass_actors")
        calls = []

        def request(method, url, token, *, payload=None):
            calls.append(method)
            return copy.deepcopy(hidden)

        with mock.patch.object(reconcile, "_request", side_effect=request), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            return_value=self.authority_proof,
        ):
            with self.assertRaisesRegex(reconcile.RulesetBlock, "omitted bypass_actors"):
                reconcile.reconcile("token", self.policy)
        self.assertEqual(calls, ["GET"])

    def test_apply_rejects_unconfirmed_post_state(self):
        drift = self.current()
        pull_request = next(
            rule for rule in drift["rules"] if rule["type"] == "pull_request"
        )
        pull_request["parameters"]["required_approving_review_count"] = 0
        calls = []

        def request(method, url, token, *, payload=None):
            calls.append(method)
            return copy.deepcopy(drift)

        with mock.patch.object(reconcile, "_request", side_effect=request), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            return_value=self.authority_proof,
        ):
            with self.assertRaisesRegex(reconcile.RulesetBlock, "not confirmed"):
                reconcile.reconcile("token", self.policy)
        self.assertEqual(calls, ["GET", "GET", "GET", "PUT", "GET"])

    def test_attempt_advance_in_immediate_source_reobservation_blocks_put(self):
        drift = self.current()
        next(rule for rule in drift["rules"] if rule["type"] == "pull_request")[
            "parameters"
        ]["required_approving_review_count"] = 0
        admin_calls = []
        advanced = self.source_run()
        advanced["run_attempt"] = 4

        def admin_request(method, url, token, *, payload=None):
            admin_calls.append(method)
            return copy.deepcopy(drift)

        def pre_effect():
            return reconcile.reobserve_dispatch_source(
                "technical-token",
                repository=self.policy["repository"],
                head_sha="a" * 40,
                run_id=9090,
                run_attempt=3,
                workflow_id=4242,
            )

        with mock.patch.object(reconcile, "_request", side_effect=admin_request), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            return_value=self.authority_proof,
        ):
            with mock.patch.object(
                reconcile, "github_get", return_value=advanced
            ):
                with self.assertRaisesRegex(reconcile.RulesetBlock, "attempt mismatch"):
                    reconcile.reconcile(
                        "admin-token", self.policy, pre_effect_check=pre_effect
                    )
        self.assertEqual(admin_calls, ["GET", "GET"])

    def test_bridge_job_attempt_drift_in_immediate_reobservation_blocks_put(self):
        drift = self.current()
        next(rule for rule in drift["rules"] if rule["type"] == "pull_request")[
            "parameters"
        ]["required_approving_review_count"] = 0
        admin_calls = []
        jobs = self.source_jobs()
        jobs["jobs"][0]["run_attempt"] = 2

        def admin_request(method, url, token, *, payload=None):
            admin_calls.append(method)
            return copy.deepcopy(drift)

        def pre_effect():
            return reconcile.reobserve_dispatch_source(
                "technical-token",
                repository=self.policy["repository"],
                head_sha="a" * 40,
                run_id=9090,
                run_attempt=3,
                workflow_id=4242,
            )

        with mock.patch.object(reconcile, "_request", side_effect=admin_request), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            return_value=self.authority_proof,
        ):
            with mock.patch.object(
                reconcile,
                "github_get",
                side_effect=[self.source_run(), jobs],
            ):
                with self.assertRaisesRegex(reconcile.RulesetBlock, "attempt mismatch"):
                    reconcile.reconcile(
                        "admin-token", self.policy, pre_effect_check=pre_effect
                    )
        self.assertEqual(admin_calls, ["GET", "GET"])

    def test_exact_source_is_reobserved_after_double_read_before_put(self):
        drift = self.current()
        next(rule for rule in drift["rules"] if rule["type"] == "pull_request")[
            "parameters"
        ]["required_approving_review_count"] = 0
        desired = self.current()
        admin_calls = []
        effect_order = []

        def admin_request(method, url, token, *, payload=None):
            admin_calls.append(method)
            effect_order.append(method)
            if method == "GET" and len(admin_calls) <= 3:
                return copy.deepcopy(drift)
            return copy.deepcopy(desired)

        def pre_effect():
            effect_order.append("SOURCE")
            return reconcile.reobserve_dispatch_source(
                "technical-token",
                repository=self.policy["repository"],
                head_sha="a" * 40,
                run_id=9090,
                run_attempt=3,
                workflow_id=4242,
            )

        def authority_environment(*_args):
            effect_order.append("AUTHORITY")
            return self.authority_proof

        with mock.patch.object(reconcile, "_request", side_effect=admin_request), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            side_effect=authority_environment,
        ):
            with mock.patch.object(
                reconcile,
                "github_get",
                side_effect=[
                    self.source_run(),
                    self.source_jobs(),
                    {"object": {"sha": "a" * 40}},
                ],
            ):
                result = reconcile.reconcile(
                    "admin-token", self.policy, pre_effect_check=pre_effect
                )
        self.assertEqual(admin_calls, ["GET", "GET", "GET", "PUT", "GET"])
        self.assertEqual(
            effect_order,
            ["GET", "GET", "AUTHORITY", "SOURCE", "GET", "PUT", "GET"],
        )
        self.assertTrue(result["pre_effect_source_reobservation"])

    def test_third_ruleset_read_blocks_drift_after_authority_source_checks(self):
        initial = self.current()
        next(
            rule for rule in initial["rules"] if rule["type"] == "pull_request"
        )["parameters"]["required_approving_review_count"] = 0
        changed = copy.deepcopy(initial)
        next(
            rule for rule in changed["rules"] if rule["type"] == "pull_request"
        )["parameters"]["require_code_owner_review"] = False
        calls = []

        def request(method, url, token, *, payload=None):
            calls.append(method)
            if method == "PUT":
                self.fail("PUT must not follow a changed immediate observation")
            if len(calls) <= 2:
                return copy.deepcopy(initial)
            return copy.deepcopy(changed)

        with mock.patch.object(
            reconcile, "_request", side_effect=request
        ), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            return_value=self.authority_proof,
        ):
            with self.assertRaisesRegex(
                reconcile.RulesetBlock,
                "drifted during authority/source readback",
            ):
                reconcile.reconcile(
                    "admin-token",
                    self.policy,
                    pre_effect_check=lambda: {"state": "TERMINAL_SUCCESS"},
                )
        self.assertEqual(calls, ["GET", "GET", "GET"])

    def test_third_ruleset_read_observes_external_convergence_without_put(self):
        drift = self.current()
        next(
            rule for rule in drift["rules"] if rule["type"] == "pull_request"
        )["parameters"]["required_approving_review_count"] = 0
        current = self.current()
        calls = []

        def request(method, url, token, *, payload=None):
            calls.append(method)
            if method == "PUT":
                self.fail("already-current ruleset must not be overwritten")
            return copy.deepcopy(drift if len(calls) <= 2 else current)

        with mock.patch.object(
            reconcile, "_request", side_effect=request
        ), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            return_value=self.authority_proof,
        ):
            result = reconcile.reconcile("admin-token", self.policy)
        self.assertEqual(calls, ["GET", "GET", "GET"])
        self.assertEqual(result["state"], "CURRENT")
        self.assertEqual(result["mutation"], "NONE")
        self.assertTrue(result["converged_before_mutation"])
        self.assertFalse(result["effect_observed"])

    def test_source_run_nonterminal_statuses_never_authorize_secret(self):
        for status in sorted(reconcile.ACTIVE_RUN_STATUSES):
            with self.subTest(status=status):
                result = reconcile.classify_dispatch_source_run(
                    self.source_run(status=status, conclusion=None),
                    repository=self.policy["repository"],
                    head_sha="a" * 40,
                    run_attempt=3,
                    workflow_id=4242,
                )
                self.assertEqual(result["state"], reconcile.SOURCE_RUN_NONTERMINAL)

    def test_source_run_failed_or_cancelled_is_blocked(self):
        for conclusion in ("failure", "cancelled"):
            with self.subTest(conclusion=conclusion):
                with self.assertRaisesRegex(
                    reconcile.RulesetBlock, "completed without success"
                ):
                    reconcile.classify_dispatch_source_run(
                        self.source_run(conclusion=conclusion),
                        repository=self.policy["repository"],
                        head_sha="a" * 40,
                        run_attempt=3,
                        workflow_id=4242,
                    )

    def test_source_run_completed_success_is_authorized(self):
        result = reconcile.classify_dispatch_source_run(
            self.source_run(),
            repository=self.policy["repository"],
            head_sha="a" * 40,
            run_attempt=3,
            workflow_id=4242,
        )
        self.assertEqual(result["state"], reconcile.SOURCE_RUN_TERMINAL_SUCCESS)

    def test_source_run_uses_stable_id_and_path_not_mutable_name(self):
        source = self.source_run()
        source["name"] = "arbitrary custom run-name"
        result = reconcile.classify_dispatch_source_run(
            source,
            repository=self.policy["repository"],
            head_sha="a" * 40,
            run_attempt=3,
            workflow_id=4242,
        )
        self.assertEqual(result["state"], reconcile.SOURCE_RUN_TERMINAL_SUCCESS)
        with self.assertRaisesRegex(reconcile.RulesetBlock, "identity mismatch"):
            reconcile.classify_dispatch_source_run(
                source,
                repository=self.policy["repository"],
                head_sha="a" * 40,
                run_attempt=3,
                workflow_id=9999,
            )

    def test_source_bridge_job_must_be_unique_complete_and_successful(self):
        result = reconcile.classify_dispatch_source_jobs(
            self.source_jobs(), run_attempt=3
        )
        self.assertEqual(result["state"], reconcile.SOURCE_RUN_TERMINAL_SUCCESS)
        self.assertEqual(result["job_name"], reconcile.SOURCE_BRIDGE_JOB_NAME)

        adverse = (
            self.source_jobs(status="completed", conclusion="failure"),
            self.source_jobs(status="completed", conclusion="cancelled"),
            self.source_jobs(status="completed", conclusion="skipped"),
        )
        for jobs in adverse:
            with self.subTest(conclusion=jobs["jobs"][0]["conclusion"]):
                with self.assertRaisesRegex(reconcile.RulesetBlock, "successfully"):
                    reconcile.classify_dispatch_source_jobs(jobs, run_attempt=3)

    def test_source_bridge_job_missing_duplicate_or_incomplete_is_blocked(self):
        missing = {"total_count": 0, "jobs": []}
        duplicate = self.source_jobs()
        duplicate["jobs"].append(copy.deepcopy(duplicate["jobs"][0]))
        duplicate["jobs"][1]["id"] += 1
        duplicate["total_count"] = 2
        incomplete = self.source_jobs()
        incomplete["total_count"] = 101
        attempt_drift = self.source_jobs()
        attempt_drift["jobs"][0]["run_attempt"] = 2
        for label, jobs, pattern in (
            ("missing", missing, "not unique"),
            ("duplicate", duplicate, "not unique"),
            ("incomplete", incomplete, "incomplete"),
            ("attempt", attempt_drift, "attempt mismatch"),
        ):
            with self.subTest(label=label):
                with self.assertRaisesRegex(reconcile.RulesetBlock, pattern):
                    reconcile.classify_dispatch_source_jobs(jobs, run_attempt=3)

    def test_durable_intent_survives_active_or_cancelled_source_transport(self):
        for status, conclusion in (
            ("in_progress", None),
            ("completed", "cancelled"),
            ("completed", "failure"),
        ):
            with self.subTest(status=status, conclusion=conclusion):
                result = reconcile.classify_dispatch_source_run(
                    self.source_run(status=status, conclusion=conclusion),
                    repository=self.policy["repository"],
                    head_sha="a" * 40,
                    run_attempt=3,
                    workflow_id=4242,
                    allow_durable_intent=True,
                )
                self.assertEqual(result["state"], reconcile.SOURCE_RUN_DURABLE_INTENT)
        jobs = self.source_jobs(status="in_progress", conclusion=None)
        result = reconcile.classify_dispatch_source_jobs(
            jobs, run_attempt=3, require_durable_intent=True
        )
        self.assertEqual(result["state"], reconcile.SOURCE_RUN_DURABLE_INTENT)
        jobs["jobs"][0]["steps"][0]["conclusion"] = "cancelled"
        with self.assertRaisesRegex(reconcile.RulesetBlock, "durably preserved"):
            reconcile.classify_dispatch_source_jobs(
                jobs, run_attempt=3, require_durable_intent=True
            )

    def test_completed_effect_keeps_original_intent_after_source_attempt_advance(self):
        advanced = self.source_run()
        advanced["run_attempt"] = 4
        original = self.source_jobs()
        newer = copy.deepcopy(original["jobs"][0])
        newer["id"] += 1
        newer["run_attempt"] = 4
        all_jobs = {"total_count": 2, "jobs": [original["jobs"][0], newer]}
        with mock.patch.object(
            reconcile, "github_get", side_effect=[advanced, all_jobs]
        ):
            result = reconcile.reobserve_durable_source_intent_after_effect(
                "token",
                repository=self.policy["repository"],
                head_sha="a" * 40,
                run_id=9090,
                run_attempt=3,
                workflow_id=4242,
            )
        self.assertEqual(result["bound_run_attempt"], 3)
        self.assertEqual(result["observed_run_attempt"], 4)
        self.assertTrue(result["attempt_advance_is_chronology_only"])

    def test_reconciler_locator_is_exact_and_not_a_display_name_authority(self):
        title = (
            f"qikvrt-ruleset intent={'b' * 64} seq=17 transport-attempt=1"
        )
        value = reconcile.parse_ruleset_reconciler_locator(title)
        self.assertEqual(value["intent_sha256"], "b" * 64)
        self.assertEqual(value["sequence"], 17)
        self.assertEqual(value["transport_attempt"], 1)
        with self.assertRaisesRegex(reconcile.RulesetBlock, "locator is invalid"):
            reconcile.parse_ruleset_reconciler_locator(title + " altered")
        with self.assertRaisesRegex(reconcile.RulesetBlock, "locator is invalid"):
            reconcile.parse_ruleset_reconciler_locator(
                f"qikvrt-ruleset intent={'b' * 64} seq=17 transport-attempt=2"
            )

    def test_blocked_review_plan_requires_exact_ruleset_blocker_and_subject(self):
        from tools.qikvrt_native_account_review import _base_plan, _sealed

        plan = _sealed(
            _base_plan(
                repository=self.policy["repository"],
                pr_number=935,
                expected_base="b" * 40,
                expected_head="a" * 40,
                expected_tree="c" * 40,
                fingerprint="d" * 64,
                first_blocker="CODE_OWNER_RULE_NOT_ENFORCED",
                detail="blocked by the exact native rule",
            )
        )
        selection = {
            "schema": "qikvrt_native_account_review_event_v1",
            "state": "CANDIDATE",
            "artifact_pr_number": 935,
            "artifact_head": "a" * 40,
            "artifact_fingerprint": "d" * 64,
            "upstream_run_id": 81,
            "upstream_run_attempt": 1,
        }
        pr = {
            "number": 935,
            "state": "open",
            "head": {
                "sha": "a" * 40,
                "ref": "review/935",
                "repo": {"full_name": self.policy["repository"]},
            },
            "base": {
                "sha": "b" * 40,
                "ref": "main",
                "repo": {"full_name": self.policy["repository"]},
            },
        }
        commit = {"tree": {"sha": "c" * 40}}
        subject = reconcile._required_review_subject_from_plan(
            plan, selection, pr, commit
        )
        self.assertEqual(subject["evidence_fingerprint"], "d" * 64)
        adverse = copy.deepcopy(plan)
        adverse["first_blocker"] = "SOMETHING_ELSE"
        adverse.pop("plan_sha256")
        adverse = _sealed(adverse)
        with self.assertRaisesRegex(reconcile.RulesetBlock, "exact ruleset blocker"):
            reconcile._required_review_subject_from_plan(
                adverse, selection, pr, commit
            )

    def test_ruleset_resume_workflow_is_subject_specific_and_secret_free(self):
        continuation = (
            reconcile.ROOT
            / ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
        ).read_text(encoding="utf-8")
        reconciler = (
            reconcile.ROOT / ".github/workflows/qikvrt_ruleset_reconcile.yml"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "group: qikvrt-autonomous-pr-head-continuation-${{ github.repository }}",
            continuation,
        )
        self.assertNotIn("ruleset-bridge-{0}-{1}", continuation)
        self.assertNotIn("ruleset-resume-{0}-{1}", continuation)
        top_permissions = continuation[
            continuation.index("permissions:") : continuation.index("concurrency:")
        ]
        self.assertIn("contents: read", top_permissions)
        self.assertNotIn("contents: write", top_permissions)
        self.assertIn("group: qikvrt-main-ruleset-manual-authority", reconciler)
        self.assertIn("queue: max", reconciler)
        reconciler_permissions = reconciler[
            reconciler.index("permissions:") : reconciler.index("concurrency:")
        ]
        self.assertIn("contents: read", reconciler_permissions)
        self.assertNotIn("pull-requests:", reconciler_permissions)
        generic_if = continuation[
            continuation.index("  continue-one-stalled-internal-pr:") :
            continuation.index("    runs-on:", continuation.index("  continue-one-stalled-internal-pr:"))
        ]
        self.assertIn("qikvrt_ruleset_reconcile.yml", generic_if)
        hold = continuation[
            continuation.index(
                "  hold-ruleset-reconciliation-for-manual-authority:"
            ) :
        ]
        self.assertIn("automatic_ruleset_dispatch:false", hold)
        self.assertIn("automatic_reconciler_rerun:false", hold)
        self.assertIn("automatic_requested_review_resume:false", hold)
        self.assertIn("productive_effect:false", hold)
        self.assertNotIn("actions: write", hold)
        self.assertNotIn("contents: write", hold)
        self.assertNotIn("QIKVRT_ENV_RULESET_ADMIN_TOKEN", continuation)
        self.assertNotIn("repository_dispatch:", reconciler)
        self.assertIn("workflow_dispatch:", reconciler)
        self.assertIn('cron: "17 * * * *"', continuation)
        for job in (
            "recover-ruleset-reconcile-transport:",
            "recover-ruleset-review-resume-transport:",
            "recover-ruleset-reconciler-rerun-transport:",
        ):
            self.assertNotIn(job, continuation)
        for action in (
            "REPLAY_REPOSITORY_DISPATCH_ONCE",
            "REPLAY_REQUESTED_REVIEW_ONCE",
            "REPLAY_RECONCILER_RERUN_ONCE",
        ):
            self.assertNotIn(action, continuation)
        self.assertIn("/attempts/{run_attempt}", (
            reconcile.ROOT / "tools/qikvrt_ruleset_reconcile.py"
        ).read_text(encoding="utf-8"))
        self.assertIn("jobs?filter=all&per_page=100", continuation)
        self.assertIn(
            "AUTOMATIC_BRANCH_PROTECTION_CHANGE_NOT_AUTHORIZED", continuation
        )

    def test_successor_scan_never_uses_display_title_as_authority(self):
        title = "exact successor locator"
        run = {
            "id": 42,
            "run_attempt": 1,
            "workflow_id": 7,
            "path": reconcile.REQUESTED_REVIEW_EXECUTOR_PATH,
            "event": "workflow_dispatch",
            "head_branch": "main",
            "head_sha": "a" * 40,
            "repository": {"full_name": self.policy["repository"]},
            "display_title": title,
            "created_at": "2026-09-01T01:00:01Z",
            "status": "queued",
            "conclusion": None,
        }
        kwargs = {
            "scan_complete": True,
            "title": title,
            "workflow_id": 7,
            "workflow_path": reconcile.REQUESTED_REVIEW_EXECUTOR_PATH,
            "event": "workflow_dispatch",
            "repository": self.policy["repository"],
            "main_head_sha": "a" * 40,
            "not_before": "2026-09-01T01:00:00Z",
        }
        accepted = reconcile.classify_bound_successor_scan([run], **kwargs)
        self.assertEqual(accepted["state"], "TRANSPORT_PENDING")
        completed = reconcile.classify_bound_successor_scan(
            [{**run, "status": "completed", "conclusion": "cancelled"}], **kwargs
        )
        self.assertEqual(completed["state"], "TRANSPORT_COMPLETED")
        self.assertEqual(completed["match"]["conclusion"], "cancelled")
        self.assertEqual(
            reconcile.classify_bound_successor_scan([], **kwargs)["state"], "ORPHAN"
        )
        self.assertEqual(
            reconcile.classify_bound_successor_scan(
                [], **{**kwargs, "scan_complete": False}
            )["state"],
            "SCAN_INCOMPLETE",
        )
        duplicate = reconcile.classify_bound_successor_scan(
            [run, {**run, "id": 43}], **kwargs
        )
        self.assertEqual(duplicate["state"], "AMBIGUOUS_ACCEPTED_RUNS")
        with self.assertRaisesRegex(reconcile.RulesetBlock, "conflicting stable"):
            reconcile.classify_bound_successor_scan(
                [{**run, "workflow_id": 99}], **kwargs
            )

    def test_outbox_discovery_has_no_fixed_newest_thousand_window(self):
        target_name = "qikvrt-ruleset-reconcile-intent-17-1"

        def get(url, token):
            page = int(url.rsplit("page=", 1)[1])
            if page <= 10:
                return {
                    "artifacts": [
                        {
                            "id": page * 1000 + offset,
                            "name": f"newer-consumed-evidence-{page}-{offset}",
                            "digest": "sha256:" + "a" * 64,
                            "expired": False,
                            "created_at": f"2026-09-{12 - page:02d}T00:00:00Z",
                            "workflow_run": {"id": page * 1000 + offset},
                        }
                        for offset in range(100)
                    ]
                }
            self.assertEqual(page, 11)
            return {
                "artifacts": [
                    {
                        "id": 17,
                        "name": target_name,
                        "digest": "sha256:" + "b" * 64,
                        "expired": False,
                        "created_at": "2026-09-01T00:00:00Z",
                        "workflow_run": {"id": 17},
                    }
                ]
            }

        with mock.patch.object(reconcile, "github_get", side_effect=get):
            matches, complete = reconcile._bounded_repository_artifacts(
                "token",
                repository=self.policy["repository"],
                name_pattern=re.compile(
                    r"qikvrt-ruleset-reconcile-intent-[1-9][0-9]*-[1-9][0-9]*"
                ),
            )
        self.assertTrue(complete)
        self.assertEqual([item["name"] for item in matches], [target_name])

    def test_completed_requested_review_requires_exact_job_artifact_and_ledger(self):
        from tools.qikvrt_native_account_review import (
            build_trusted_executor_producer_binding,
        )
        from tools.qikvrt_requested_review_executor import _canonical_sha256

        repository = self.policy["repository"]
        main = "a" * 40
        head = "b" * 40
        fingerprint = "c" * 64
        ledger_commit = "d" * 40
        run_id = 5151
        workflow_id = 6161
        artifact_name = (
            f"qikvrt-mesh-review-pr-935-{head}-{fingerprint}-"
            f"run-{run_id}-attempt-1"
        )
        plan = {
            "schema": "qikvrt_ruleset_review_resume_plan_v1",
            "state": "REOBSERVE",
            "d0": 2,
            "action": "DISPATCH_REQUESTED_REVIEW_EXECUTOR",
            "target_workflow_id": workflow_id,
            "evaluator_sha": main,
            "pull_request": 935,
            "head_sha": head,
            "evidence_fingerprint": fingerprint,
            "productive_effect": False,
        }
        diff = b"exact review diff\n"
        review = {
            "schema": "qikvrt_mesh_repository_review_receipt_v1",
            "repository": repository,
            "pr_number": 935,
            "head_sha": head,
            "evidence_fingerprint": fingerprint,
            "diff_sha256": hashlib.sha256(diff).hexdigest(),
            "ledger_path": f"state/mesh/reviews/pr-935/{head}/{fingerprint}.json",
        }
        review["receipt_payload_sha256"] = _canonical_sha256(review)
        review_bytes = (json.dumps(review, sort_keys=True, indent=2) + "\n").encode()
        ledger = {
            "schema": "qikvrt_mesh_review_ledger_write_v1",
            "persisted": True,
            "projection_current": True,
            "first_blocker": None,
            "ledger_commit": ledger_commit,
        }
        ledger_bytes = (json.dumps(ledger, sort_keys=True, indent=2) + "\n").encode()
        review_transport_bytes = (json.dumps(
            {
                "schema": "qikvrt_mesh_review_transport_provenance_v1",
                "productive_effect": False,
            },
            sort_keys=True,
            indent=2,
        ) + "\n").encode()
        bound_files = {
            "review.json": review_bytes,
            "review.diff": diff,
            "ledger-write.json": ledger_bytes,
            "review-transport.json": review_transport_bytes,
        }
        producer = build_trusted_executor_producer_binding(
            repository=repository,
            run_id=run_id,
            run_attempt=1,
            artifact_name=artifact_name,
            pr_number=935,
            head_sha=head,
            evidence_fingerprint=fingerprint,
            files=bound_files,
        )
        archive_io = io.BytesIO()
        with zipfile.ZipFile(archive_io, "w") as package:
            for name, raw in bound_files.items():
                package.writestr(name, raw)
            package.writestr(
                "producer-binding.json",
                (json.dumps(producer, sort_keys=True, indent=2) + "\n").encode(),
            )
        archive = archive_io.getvalue()
        run = {
            "id": run_id,
            "run_attempt": 1,
            "workflow_id": workflow_id,
            "path": reconcile.REQUESTED_REVIEW_EXECUTOR_PATH,
            "event": "workflow_dispatch",
            "head_branch": "main",
            "head_sha": main,
            "repository": {"full_name": repository},
            "status": "completed",
            "conclusion": "success",
            "display_title": reconcile.requested_review_executor_title(plan),
        }
        jobs = {
            "total_count": 1,
            "jobs": [
                {
                    "id": 7171,
                    "name": reconcile.REQUESTED_REVIEW_EXECUTOR_JOB_NAME,
                    "run_attempt": 1,
                    "status": "completed",
                    "conclusion": "success",
                }
            ],
        }
        artifacts = {
            "total_count": 1,
            "artifacts": [
                {
                    "id": 8181,
                    "name": artifact_name,
                    "digest": "sha256:" + hashlib.sha256(archive).hexdigest(),
                    "expired": False,
                    "workflow_run": {"id": run_id},
                }
            ],
        }

        def get(url, token):
            if "/actions/workflows/qikvrt_requested_review_executor.yml" in url:
                return {"id": workflow_id, "path": reconcile.REQUESTED_REVIEW_EXECUTOR_PATH}
            if url.endswith(f"/actions/runs/{run_id}"):
                return run
            if url.endswith("/git/ref/heads/main"):
                return {"object": {"sha": main}}
            if "/jobs?filter=all" in url:
                return jobs
            if "/artifacts?per_page=100" in url:
                return artifacts
            if url.endswith("/git/ref/heads/qikvrt/mesh-review-ledger-v1"):
                return {"object": {"sha": "e" * 40}}
            if "/compare/" in url:
                return {"status": "ahead"}
            if "/contents/" in url:
                return {"sha": "f" * 40}
            if url.endswith("/git/blobs/" + "f" * 40):
                return {
                    "encoding": "base64",
                    "content": base64.b64encode(review_bytes).decode(),
                }
            raise AssertionError(url)

        with mock.patch.object(reconcile, "github_get", side_effect=get), mock.patch.object(
            reconcile, "github_get_bytes", return_value=archive
        ):
            result = reconcile.validate_completed_requested_review_successor(
                "token",
                repository=repository,
                main_head_sha=main,
                workflow_id=workflow_id,
                run_id=run_id,
                run_attempt=1,
                plan=plan,
            )
        self.assertEqual(result["first_blocker"], "REQUESTED_REVIEW_EXACT_LEDGER_CONTINUATION_OBSERVED")

        jobs["total_count"] = 0
        jobs["jobs"] = []
        with mock.patch.object(reconcile, "github_get", side_effect=get), mock.patch.object(
            reconcile, "github_get_bytes", return_value=archive
        ):
            with self.assertRaisesRegex(reconcile.RulesetBlock, "job is not unique"):
                reconcile.validate_completed_requested_review_successor(
                    "token",
                    repository=repository,
                    main_head_sha=main,
                    workflow_id=workflow_id,
                    run_id=run_id,
                    run_attempt=1,
                    plan=plan,
                )

    def test_ruleset_outboxes_require_successful_intent_before_transport(self):
        jobs = {
            "total_count": 1,
            "jobs": [
                {
                    "id": 1,
                    "name": reconcile.RULESET_REVIEW_RESUME_JOB_NAME,
                    "run_attempt": 1,
                    "steps": [
                        {
                            "number": 4,
                            "name": reconcile.RULESET_REVIEW_RESUME_INTENT_STEP_NAME,
                            "status": "completed",
                            "conclusion": "success",
                        },
                        {
                            "number": 5,
                            "name": reconcile.RULESET_REVIEW_RESUME_TRANSPORT_STEP_NAME,
                            "status": "in_progress",
                            "conclusion": None,
                        },
                    ],
                }
            ],
        }
        proof = reconcile.classify_review_resume_source_jobs(jobs, run_attempt=1)
        self.assertEqual(proof["intent_step_conclusion"], "success")
        jobs["jobs"][0]["steps"][0]["conclusion"] = "cancelled"
        with self.assertRaisesRegex(reconcile.RulesetBlock, "not durably preserved"):
            reconcile.classify_review_resume_source_jobs(jobs, run_attempt=1)

        jobs["jobs"][0]["steps"] = [
            {
                "number": 4,
                "name": reconcile.RULESET_RECONCILER_RERUN_INTENT_STEP_NAME,
                "status": "completed",
                "conclusion": "success",
            },
            {
                "number": 5,
                "name": reconcile.RULESET_RECONCILER_RERUN_TRANSPORT_STEP_NAME,
                "status": "cancelled",
                "conclusion": "cancelled",
            },
        ]
        rerun = reconcile.classify_review_resume_source_jobs(
            jobs,
            run_attempt=1,
            intent_step_name=reconcile.RULESET_RECONCILER_RERUN_INTENT_STEP_NAME,
            transport_step_name=reconcile.RULESET_RECONCILER_RERUN_TRANSPORT_STEP_NAME,
        )
        self.assertEqual(rerun["transport_step_conclusion"], "cancelled")

    def test_lost_reconciler_handler_mints_exact_bounded_successor_outbox(self):
        source_artifact = {"id": 1, "name": "source"}
        successor = {
            "state": "TRANSPORT_COMPLETED",
            "match": {"id": 81, "run_attempt": 1, "status": "completed"},
        }
        review = {
            "schema": "qikvrt_ruleset_review_resume_plan_v1",
            "state": "REOBSERVE",
            "d0": 2,
            "action": "DISPATCH_REQUESTED_REVIEW_EXECUTOR",
            "reconciler_run_id": 81,
            "reconciler_run_attempt": 1,
            "target_workflow_id": 91,
            "evaluator_sha": "c" * 40,
            "pull_request": 935,
            "head_sha": "a" * 40,
            "evidence_fingerprint": "b" * 64,
            "productive_effect": False,
        }
        with mock.patch.object(
            reconcile, "plan_ruleset_review_resume", return_value=review
        ), mock.patch.object(
            reconcile, "_unique_recovery_review_intent_for_target", return_value=None
        ):
            plan = reconcile._plan_completed_reconciler_for_scheduled_recovery(
                "token",
                repository=self.policy["repository"],
                main_head_sha="c" * 40,
                workflow_id=71,
                title="locator",
                successor=successor,
                source_artifact=source_artifact,
                allow_new_outbox_effect=False,
            )
        self.assertEqual(plan["action"], "DISPATCH_REQUESTED_REVIEW_EXECUTOR")
        self.assertTrue(plan["dispatch_request"]["return_run_details"])

        rerun = {
            "schema": "qikvrt_ruleset_review_resume_plan_v1",
            "state": "REOBSERVE",
            "d0": 2,
            "action": "RERUN_RECONCILER_ONCE",
            "reconciler_run_id": 81,
            "reconciler_run_attempt": 1,
            "source_artifact": source_artifact,
            "review_resume": {"subject": {"pull_request": 935}},
            "productive_effect": False,
        }
        with mock.patch.object(
            reconcile, "plan_ruleset_review_resume", return_value=rerun
        ), mock.patch.object(
            reconcile, "_unique_recovery_rerun_intent_for_target", return_value=None
        ):
            plan = reconcile._plan_completed_reconciler_for_scheduled_recovery(
                "token",
                repository=self.policy["repository"],
                main_head_sha="c" * 40,
                workflow_id=71,
                title="locator",
                successor=successor,
                source_artifact=source_artifact,
                allow_new_outbox_effect=False,
            )
        self.assertEqual(plan["action"], "RERUN_RECONCILER_ONCE")
        self.assertEqual(plan["rerun_request"]["target_attempt"], 2)

        authority = {
            "schema": "qikvrt_ruleset_review_resume_plan_v1",
            "state": "REQUEST_AUTHORITY",
            "d0": 3,
            "action": "NONE",
            "first_blocker": "RULESET_RECONCILER_CANCELLED",
            "reconciler_run_id": 81,
            "reconciler_run_attempt": 2,
            "productive_effect": False,
        }
        with mock.patch.object(
            reconcile, "plan_ruleset_review_resume", return_value=authority
        ):
            plan = reconcile._plan_completed_reconciler_for_scheduled_recovery(
                "token",
                repository=self.policy["repository"],
                main_head_sha="c" * 40,
                workflow_id=71,
                title="locator",
                successor={
                    "state": "TRANSPORT_COMPLETED",
                    "match": {"id": 81, "run_attempt": 2, "status": "completed"},
                },
                source_artifact=source_artifact,
                allow_new_outbox_effect=False,
            )
        self.assertEqual(plan["d0"], 3)
        self.assertEqual(plan["action"], "NONE")

    def test_lost_requested_review_handler_replays_once_then_authority(self):
        candidate = {
            "id": 11,
            "name": "qikvrt-ruleset-review-resume-intent-17-1",
            "digest": "sha256:" + "a" * 64,
            "expired": False,
            "created_at": "2026-09-01T00:00:00Z",
            "producer_run_id": 17,
        }
        plan = {
            "schema": "qikvrt_ruleset_review_resume_plan_v1",
            "state": "REOBSERVE",
            "d0": 2,
            "action": "DISPATCH_REQUESTED_REVIEW_EXECUTOR",
            "reconciler_run_id": 71,
            "reconciler_run_attempt": 1,
            "target_workflow_id": 91,
            "evaluator_sha": "b" * 40,
            "pull_request": 935,
            "head_sha": "c" * 40,
            "evidence_fingerprint": "d" * 64,
            "productive_effect": False,
        }
        intent = {
            "main_head_sha": "b" * 40,
            "source_created_at": "2026-09-01T00:00:00Z",
            "source_job": {"transport_step_conclusion": "success"},
            "plan": plan,
            "dispatch_request": reconcile._requested_review_dispatch_request(plan),
        }
        successor = {
            "state": "TRANSPORT_COMPLETED",
            "match": {
                "id": 101,
                "run_attempt": 1,
                "status": "completed",
                "conclusion": "cancelled",
            },
        }
        common = (
            mock.patch.object(
                reconcile, "_bounded_repository_artifacts", return_value=([candidate], True)
            ),
            mock.patch.object(
                reconcile, "_exact_repository_artifact_exists", return_value=False
            ),
            mock.patch.object(
                reconcile, "reobserve_ruleset_review_resume_intent", return_value=intent
            ),
            mock.patch.object(
                reconcile,
                "github_get",
                return_value={
                    "id": 91,
                    "path": reconcile.REQUESTED_REVIEW_EXECUTOR_PATH,
                },
            ),
            mock.patch.object(
                reconcile, "_bounded_workflow_runs_since", return_value=([], True)
            ),
            mock.patch.object(
                reconcile, "classify_bound_successor_scan", return_value=successor
            ),
            mock.patch.object(
                reconcile,
                "validate_completed_requested_review_successor",
                side_effect=reconcile.RulesetBlock("terminal child adverse"),
            ),
        )
        with common[0], common[1], common[2], common[3], common[4], common[5], common[6], mock.patch.object(
            reconcile, "_exact_repository_artifact", return_value=None
        ):
            first = reconcile.select_ruleset_review_resume_transport_recovery(
                "token",
                repository=self.policy["repository"],
                main_head_sha="b" * 40,
            )
        self.assertEqual(first["action"], "REPLAY_REQUESTED_REVIEW_ONCE")
        self.assertEqual(first["d0"], 2)

        # Recreate patches because unittest.mock patchers are single-use.
        with mock.patch.object(
            reconcile, "_bounded_repository_artifacts", return_value=([candidate], True)
        ), mock.patch.object(
            reconcile, "_exact_repository_artifact_exists", return_value=False
        ), mock.patch.object(
            reconcile, "reobserve_ruleset_review_resume_intent", return_value=intent
        ), mock.patch.object(
            reconcile,
            "github_get",
            return_value={"id": 91, "path": reconcile.REQUESTED_REVIEW_EXECUTOR_PATH},
        ), mock.patch.object(
            reconcile, "_bounded_workflow_runs_since", return_value=([], True)
        ), mock.patch.object(
            reconcile, "classify_bound_successor_scan", return_value=successor
        ), mock.patch.object(
            reconcile,
            "validate_completed_requested_review_successor",
            side_effect=reconcile.RulesetBlock("terminal child adverse"),
        ), mock.patch.object(
            reconcile,
            "_exact_repository_artifact",
            return_value={"created_at": "2026-09-01T00:00:01Z"},
        ):
            second = reconcile.select_ruleset_review_resume_transport_recovery(
                "token",
                repository=self.policy["repository"],
                main_head_sha="b" * 40,
            )
        self.assertEqual(second["action"], "NONE")
        self.assertEqual(second["d0"], 3)
        self.assertIn("ATTEMPT_2_TERMINAL_ADVERSE", second["first_blocker"])

    def test_ruleset_recovery_binds_immutable_attempt_and_rejects_latest_advance(self):
        attempt = self.source_run(status="completed", conclusion="cancelled")
        attempt["created_at"] = "2026-09-01T01:00:00Z"
        latest = copy.deepcopy(attempt)
        jobs = self.source_jobs(status="completed", conclusion="cancelled")
        live = {"object": {"sha": "a" * 40}}
        urls = []

        def get(url, token):
            urls.append(url)
            return [attempt, latest, jobs, live][len(urls) - 1]

        with mock.patch.object(reconcile, "github_get", side_effect=get):
            proof = reconcile.reobserve_dispatch_source_attempt_for_recovery(
                "token",
                repository=self.policy["repository"],
                head_sha="a" * 40,
                run_id=9090,
                run_attempt=3,
                workflow_id=4242,
            )
        self.assertEqual(proof["state"], reconcile.SOURCE_RUN_DURABLE_INTENT)
        self.assertIn("/attempts/3", urls[0])
        self.assertIn("jobs?filter=all&per_page=100", urls[2])

        advanced = copy.deepcopy(latest)
        advanced["run_attempt"] = 4
        with mock.patch.object(
            reconcile, "github_get", side_effect=[attempt, advanced]
        ):
            with self.assertRaisesRegex(reconcile.RulesetBlock, "attempt mismatch"):
                reconcile.reobserve_dispatch_source_attempt_for_recovery(
                    "token",
                    repository=self.policy["repository"],
                    head_sha="a" * 40,
                    run_id=9090,
                    run_attempt=3,
                    workflow_id=4242,
                )

    def test_automatic_ruleset_effect_lanes_are_absent_and_one_shot(self):
        workflow = (
            reconcile.ROOT
            / ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
        ).read_text(encoding="utf-8")
        for obsolete in (
            "dispatch-ruleset-reconciliation:",
            "recover-ruleset-reconcile-transport:",
            "recover-ruleset-review-resume-transport:",
            "recover-ruleset-reconciler-rerun-transport:",
            "REPLAY_REPOSITORY_DISPATCH_ONCE",
            "REPLAY_REQUESTED_REVIEW_ONCE",
            "REPLAY_RECONCILER_RERUN_ONCE",
            "allow_recovery_attempt_2=True",
        ):
            self.assertNotIn(obsolete, workflow)
        hold = workflow[
            workflow.index("  hold-ruleset-reconciliation-for-manual-authority:") :
        ]
        self.assertIn("d0:3", hold)
        self.assertIn("automatic_ruleset_dispatch:false", hold)
        self.assertIn("automatic_reconciler_rerun:false", hold)
        self.assertIn("automatic_requested_review_resume:false", hold)

    def test_manual_boundary_contains_no_scheduled_ruleset_selectors(self):
        workflow = (
            reconcile.ROOT
            / ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
        ).read_text(encoding="utf-8")
        hold = workflow[
            workflow.index("  hold-ruleset-reconciliation-for-manual-authority:") :
        ]
        self.assertIn("REQUEST_AUTHORITY", hold)
        self.assertIn("effect_ack:\"NOT_REQUIRED\"", hold)
        self.assertIn("qikvrt-ruleset-authority", hold)
        for forbidden in (
            "DISPATCH_REQUESTED_REVIEW_EXECUTOR",
            "RERUN_RECONCILER_ONCE",
            "REPLAY_REPOSITORY_DISPATCH_ONCE",
            "Reobserve and rerun one exact transient reconciler attempt",
            'gh api --method POST "repos/${GITHUB_REPOSITORY}/dispatches"',
        ):
            self.assertNotIn(forbidden, hold)

    def test_admin_secret_is_injected_only_into_fixed_apply_process(self):
        workflow = (
            reconcile.ROOT / ".github/workflows/qikvrt_ruleset_reconcile.yml"
        ).read_text(encoding="utf-8")
        step = workflow[
            workflow.index("Reconcile through the protected manual Authority boundary") :
        ]
        capture = step.index('admin_token="${QIKVRT_ENV_RULESET_ADMIN_TOKEN-}"')
        unset = step.index("unset QIKVRT_ENV_RULESET_ADMIN_TOKEN")
        first_validation = step.index("git rev-parse")
        injection = step.index('QIKVRT_ENV_RULESET_ADMIN_TOKEN="$admin_token"')
        apply_process = step.index("python3 -B tools/qikvrt_ruleset_reconcile.py", injection)
        self.assertLess(capture, unset)
        self.assertLess(unset, first_validation)
        self.assertLess(injection, apply_process)
        self.assertEqual(step.count('QIKVRT_ENV_RULESET_ADMIN_TOKEN="$admin_token"'), 1)
        self.assertNotIn("set -x", step)

    def test_ruleset_admin_secret_is_environment_only_and_externally_held(self):
        workflow = (
            reconcile.ROOT / ".github/workflows/qikvrt_ruleset_reconcile.yml"
        ).read_text(encoding="utf-8")
        authority = self.policy["authority"]
        external = authority["required_external_readback"]
        self.assertIn("environment: qikvrt-ruleset-authority", workflow)
        self.assertIn(
            "QIKVRT_ENV_RULESET_ADMIN_TOKEN: ${{ secrets.QIKVRT_ENV_RULESET_ADMIN_TOKEN }}",
            workflow,
        )
        self.assertNotIn("secrets.QIKVRT_RULESET_ADMIN_TOKEN", workflow)
        self.assertEqual(authority["credential_scope"], "ENVIRONMENT_ONLY")
        self.assertFalse(authority["external_configuration_verified"])
        self.assertEqual(
            authority["external_configuration_hold"],
            "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED",
        )
        self.assertEqual(external["deployment_branch_policy"], "SELECTED_BRANCHES_ONLY")
        self.assertEqual(external["selected_branch"], "main")
        self.assertTrue(external["environment_protection_rules_required"])
        self.assertEqual(
            external["repository_owner"],
            {"login": "Goldkelch", "id": 293941403, "type": "User"},
        )
        self.assertEqual(
            external["organization_scope_resolution"], "OWNER_TYPE_AWARE"
        )
        for scope in (
            "repository_scope_secret_names_absent",
            "organization_scope_secret_names_absent",
        ):
            self.assertEqual(
                external[scope],
                ["QIKVRT_ENV_RULESET_ADMIN_TOKEN", "QIKVRT_RULESET_ADMIN_TOKEN"],
            )

    def test_runtime_authority_environment_readback_blocks_secret_fallbacks(self):
        environment = {
            "name": "qikvrt-ruleset-authority",
            "deployment_branch_policy": {
                "protected_branches": False,
                "custom_branch_policies": True,
            },
            "protection_rules": [{"type": "required_reviewers"}],
        }

        def inventory(names):
            return {
                "total_count": len(names),
                "secrets": [{"name": name} for name in names],
            }

        def get(
            url,
            token,
            *,
            repo_names=(),
            org_names=(),
            env_names=("QIKVRT_ENV_RULESET_ADMIN_TOKEN",),
            owner_type="User",
            owner_id=293941403,
        ):
            if url == "https://api.github.com/repos/Goldkelch/qik-vrt":
                return {
                    "owner": {
                        "login": "Goldkelch",
                        "id": owner_id,
                        "type": owner_type,
                    }
                }
            if url.endswith("/environments/qikvrt-ruleset-authority"):
                return environment
            if "deployment-branch-policies" in url:
                return {"total_count": 1, "branch_policies": [{"name": "main", "type": "branch"}]}
            if "/environments/qikvrt-ruleset-authority/secrets" in url:
                return inventory(env_names)
            if "/repos/Goldkelch/qik-vrt/actions/secrets" in url:
                return inventory(repo_names)
            if "/orgs/Goldkelch/actions/secrets" in url:
                return inventory(org_names)
            raise AssertionError(url)

        with mock.patch.object(reconcile, "github_get", side_effect=get):
            proof = reconcile.reobserve_ruleset_authority_environment(
                "admin-token", self.policy
            )
        self.assertEqual(proof["state"], "VERIFIED_FOR_THIS_EFFECT_ONLY")
        self.assertEqual(
            proof["repository_owner"],
            {"login": "Goldkelch", "id": 293941403, "type": "User"},
        )
        self.assertEqual(
            proof["organization_scope_readback"],
            "NOT_APPLICABLE_USER_OWNER",
        )
        self.assertFalse(proof["secret_values_observed"])

        with mock.patch.object(
            reconcile,
            "github_get",
            side_effect=lambda url, token: get(
                url, token, repo_names=("QIKVRT_ENV_RULESET_ADMIN_TOKEN",)
            ),
        ):
            with self.assertRaisesRegex(
                reconcile.RulesetBlock,
                "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED: repository-scope",
            ):
                reconcile.reobserve_ruleset_authority_environment(
                    "admin-token", self.policy
                )

        organization_policy = copy.deepcopy(self.policy)
        organization_policy["authority"]["required_external_readback"][
            "repository_owner"
        ] = {"login": "Goldkelch", "id": 293941403, "type": "Organization"}
        with mock.patch.object(
            reconcile,
            "github_get",
            side_effect=lambda url, token: (
                (_ for _ in ()).throw(reconcile.RulesetBlock("GitHub API HTTP 403"))
                if "/orgs/Goldkelch/actions/secrets" in url
                else get(url, token, owner_type="Organization")
            ),
        ):
            with self.assertRaisesRegex(
                reconcile.RulesetBlock,
                "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED: GitHub API HTTP 403",
            ):
                reconcile.reobserve_ruleset_authority_environment(
                    "admin-token", organization_policy
                )

        with mock.patch.object(
            reconcile,
            "github_get",
            side_effect=lambda url, token: get(
                url,
                token,
                owner_type="Organization",
                org_names=(),
            ),
        ):
            organization_proof = reconcile.reobserve_ruleset_authority_environment(
                "admin-token", organization_policy
            )
        self.assertEqual(
            organization_proof["organization_scope_readback"],
            "COMPLETE_ORGANIZATION_INVENTORY",
        )

        unknown_policy = copy.deepcopy(self.policy)
        unknown_policy["authority"]["required_external_readback"][
            "repository_owner"
        ] = {"login": "Goldkelch", "id": 293941403, "type": "Enterprise"}
        with mock.patch.object(
            reconcile,
            "github_get",
            side_effect=lambda url, token: get(url, token, owner_type="Enterprise"),
        ):
            with self.assertRaisesRegex(
                reconcile.RulesetBlock,
                "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED: repository owner",
            ):
                reconcile.reobserve_ruleset_authority_environment(
                    "admin-token", unknown_policy
                )

        with mock.patch.object(
            reconcile,
            "github_get",
            side_effect=lambda url, token: get(url, token, env_names=()),
        ):
            with self.assertRaisesRegex(
                reconcile.RulesetBlock,
                "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED: environment admin secret",
            ):
                reconcile.reobserve_ruleset_authority_environment(
                    "admin-token", self.policy
                )

        with mock.patch.object(
            reconcile,
            "github_get",
            side_effect=lambda url, token: get(
                url,
                token,
                repo_names=tuple(f"SAFE_SECRET_{index}" for index in range(101)),
            ),
        ):
            with self.assertRaisesRegex(
                reconcile.RulesetBlock,
                "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED:.*bounded page",
            ):
                reconcile.reobserve_ruleset_authority_environment(
                    "admin-token", self.policy
                )

        repository_inventory_reads = 0

        def moving_get(url, token):
            nonlocal repository_inventory_reads
            if "/repos/Goldkelch/qik-vrt/actions/secrets" in url:
                repository_inventory_reads += 1
                return inventory(
                    ("SAFE_SECRET",)
                    if repository_inventory_reads == 1
                    else ("QIKVRT_ENV_RULESET_ADMIN_TOKEN",)
                )
            return get(url, token)

        with mock.patch.object(reconcile, "github_get", side_effect=moving_get):
            with self.assertRaisesRegex(
                reconcile.RulesetBlock,
                "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED:.*changed",
            ):
                reconcile.reobserve_ruleset_authority_environment(
                    "admin-token", self.policy
                )

    def test_environment_readback_hold_precedes_ruleset_put(self):
        drift = self.current()
        next(rule for rule in drift["rules"] if rule["type"] == "pull_request")[
            "parameters"
        ]["required_approving_review_count"] = 0
        calls = []

        def request(method, url, token, *, payload=None):
            calls.append(method)
            return copy.deepcopy(drift)

        with mock.patch.object(reconcile, "_request", side_effect=request), mock.patch.object(
            reconcile,
            "reobserve_ruleset_authority_environment",
            side_effect=reconcile.RulesetBlock(
                "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED: org readback"
            ),
        ):
            with self.assertRaisesRegex(
                reconcile.RulesetBlock, "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED"
            ):
                reconcile.reconcile("admin-token", self.policy)
        self.assertEqual(calls, ["GET", "GET"])

    def test_resume_receipt_accepts_only_exact_current_none_or_put(self):
        review = {"schema": "review"}
        source = {
            "source": {
                "run_id": 1,
                "run_attempt": 1,
                "workflow_id": 2,
                "workflow_path": ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml",
            },
            "binding": {
                "main_head_sha": "a" * 40,
                "main_tree_sha": "b" * 40,
                "policy_blob_sha": "c" * 40,
                "desired_state_sha256": "d" * 64,
            },
            "review": review,
        }
        execution = {
            "schema": "qikvrt_ruleset_reconcile_execution_binding_v1",
            "event": "repository_dispatch",
            "main_head_sha": "a" * 40,
            "main_tree_sha": "b" * 40,
            "policy_blob_sha": "c" * 40,
            "ruleset_id": 19344903,
            "desired_state_sha256": "d" * 64,
            "source": source["source"],
            "review_resume": review,
            "candidate_bytes_consumed": False,
        }
        base_receipt = {
            "schema": reconcile.SCHEMA,
            "repository": self.policy["repository"],
            "ruleset_id": 19344903,
            "state": "CURRENT",
            "desired_state_sha256": "d" * 64,
            "pre_state_sha256": "d" * 64,
            "mutation": "NONE",
            "effect_observed": False,
        }
        artifact = {"id": 8, "name": "intent", "digest": "sha256:" + "e" * 64}
        source["artifact"] = artifact
        artifact_proof = {
            **source,
            "secret_boundary_crossed": False,
        }
        run_proof = {
            "state": reconcile.SOURCE_RUN_DURABLE_INTENT,
            "secret_boundary_crossed": False,
        }
        job_proof = {
            "state": reconcile.SOURCE_RUN_DURABLE_INTENT,
            "intent_step_name": reconcile.SOURCE_INTENT_STEP_NAME,
            "intent_step_conclusion": "success",
            "secret_boundary_crossed": False,
        }
        reconcile._validate_current_reconciler_receipt(
            execution=execution,
            receipt=base_receipt,
            review_file=review,
            source_binding=source,
            source_artifact_proof=artifact_proof,
            source_run_proof=run_proof,
            source_job_proof=job_proof,
        )
        put = {
            **base_receipt,
            "mutation": "PUT",
            "effect_observed": True,
            "post_update_readback": True,
            "pre_effect_double_read": True,
            "immediate_pre_effect_reobservation": True,
            "pre_effect_source_reobservation": True,
            "write_concurrency": "LAST_WRITER_WINS",
            "conditional_update_used": False,
            "get_put_race_eliminated": False,
            "converged_before_mutation": False,
            "authority_environment_readback": {
                "schema": "qikvrt_ruleset_authority_environment_readback_v1",
                "state": "VERIFIED_FOR_THIS_EFFECT_ONLY",
                "environment": "qikvrt-ruleset-authority",
                "credential_name": "QIKVRT_ENV_RULESET_ADMIN_TOKEN",
                "deployment_branch": "main",
                "environment_secret_name_present": True,
                "repository_scope_fallback_names_absent": True,
                "organization_scope_fallback_names_absent": True,
                "repository_owner": {
                    "login": "Goldkelch",
                    "id": 293941403,
                    "type": "User",
                },
                "organization_scope_readback": "NOT_APPLICABLE_USER_OWNER",
                "secret_values_observed": False,
            },
        }
        pre_effect = {
            "dispatch_artifact": artifact,
            "review_resume": review,
            "run_id": 1,
            "run_attempt": 1,
            "intent_step_name": reconcile.SOURCE_INTENT_STEP_NAME,
            "secret_boundary_crossed": False,
        }
        reconcile._validate_current_reconciler_receipt(
            execution=execution,
            receipt=put,
            review_file=review,
            source_binding=source,
            source_artifact_proof=artifact_proof,
            source_run_proof=run_proof,
            source_job_proof=job_proof,
            pre_effect_proof=pre_effect,
        )
        with self.assertRaisesRegex(
            reconcile.RulesetBlock, "PUT receipt lacks exact readback"
        ):
            reconcile._validate_current_reconciler_receipt(
                execution=execution,
                receipt={**put, "get_put_race_eliminated": True},
                review_file=review,
                source_binding=source,
                source_artifact_proof=artifact_proof,
                source_run_proof=run_proof,
                source_job_proof=job_proof,
                pre_effect_proof=pre_effect,
            )
        adverse = {**base_receipt, "state": "DRIFT"}
        with self.assertRaisesRegex(reconcile.RulesetBlock, "did not prove CURRENT"):
            reconcile._validate_current_reconciler_receipt(
                execution=execution,
                receipt=adverse,
                review_file=review,
                source_binding=source,
                source_artifact_proof=artifact_proof,
                source_run_proof=run_proof,
                source_job_proof=job_proof,
            )

    def test_policy_and_work_unit_do_not_claim_unsupported_cas(self):
        policy = self.policy["effect_contract"]
        self.assertTrue(policy["immediate_pre_effect_reobservation_required"])
        self.assertFalse(policy["conditional_update_supported"])
        self.assertFalse(policy["conditional_update_used"])
        self.assertFalse(policy["get_put_race_eliminated"])
        self.assertEqual(
            policy["final_get_to_put_boundary"],
            "IRREDUCIBLE_NO_DOCUMENTED_CAS_LAST_WRITER_CONVERGENCE",
        )
        self.assertEqual(policy["write_concurrency_model"], "LAST_WRITER_WINS")
        paths = [
            reconcile.ROOT / "tools/qikvrt_ruleset_reconcile.py",
            reconcile.ROOT / ".github/workflows/qikvrt_ruleset_reconcile.yml",
            reconcile.ROOT / "policy/GITHUB_MAIN_RULESET_V1.json",
            reconcile.ROOT
            / "state/work_units/AUTHORITY_MIRROR_ATARI_FIREFOX_PORTABILITY_V1.json",
        ]
        combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        self.assertNotIn("If-Match", combined)
        self.assertNotIn("ETag", combined)

    def test_work_unit_marks_self_heal_as_post_promotion_only(self):
        work = json.loads(
            (
                reconcile.ROOT
                / "state/work_units/AUTHORITY_MIRROR_ATARI_FIREFOX_PORTABILITY_V1.json"
            ).read_text(encoding="utf-8")
        )["reobservation_and_gate_repairs"]["ruleset_self_repair"]
        self.assertEqual(
            work["activation_scope"],
            "MANUAL_WORKFLOW_DISPATCH_PROTECTED_ENVIRONMENT_ONLY",
        )
        self.assertFalse(work["can_bootstrap_current_weak_ruleset_before_own_promotion"])
        self.assertEqual(
            work["irreducible_current_bootstrap"],
            "MANUAL_EXISTING_MAIN_RECONCILER_OR_EXTERNAL_AUTHORITY_ADMIN_REQUIRED",
        )
        self.assertEqual(
            work["concurrency_model"],
            "PROTECTED_MANUAL_WORKFLOW_DISPATCH_SERIAL_QUEUE",
        )
        self.assertFalse(work["pending_replacement_is_lossless_queue"])
        self.assertTrue(work["continuation_concurrency_is_repository_wide"])
        self.assertFalse(
            work["ruleset_bridge_concurrency_is_gate_run_and_attempt_specific"]
        )
        self.assertEqual(work["scheduled_ruleset_reconcile_transport_attempts"], 0)
        self.assertEqual(work["scheduled_ruleset_reconciler_rerun_transport_attempts"], 0)
        self.assertEqual(work["scheduled_ruleset_review_resume_transport_attempts"], 0)
        self.assertFalse(
            work["scheduled_transport_attempt_2_requires_pre_post_durable_intent"]
        )
        self.assertEqual(
            work["scheduled_transport_attempt_2_orphan_disposition"],
            "NOT_APPLICABLE_AUTOMATIC_RULESET_EFFECTS_DISABLED",
        )
        self.assertTrue(work["ruleset_current_mints_subject_bound_noop_reconciler_receipt"])
        self.assertTrue(work["admin_secret_is_injected_only_into_fixed_apply_process"])
        self.assertEqual(work["ruleset_authority_secret_scope"], "ENVIRONMENT_ONLY")
        self.assertFalse(work["ruleset_authority_external_configuration_verified"])
        self.assertEqual(
            work["ruleset_authority_external_hold"],
            "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED",
        )
        self.assertFalse(work["blocked_review_resume_is_post_promotion_only"])


if __name__ == "__main__":
    unittest.main()
