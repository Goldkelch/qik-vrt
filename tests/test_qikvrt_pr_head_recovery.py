# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest
import re

from tools.qikvrt_pr_head_recovery import (
    RecoveryDecision,
    classify_observations,
    flatten_run_pages,
    validate_publisher_receipt,
)


def observation(
    *,
    run_id: int,
    name: str,
    status: str = "completed",
    conclusion: str | None = None,
    jobs_total: int = 0,
    created_at: str,
    workflow_id: int | None = None,
    workflow_path: str | None = None,
    event: str = "pull_request",
) -> dict[str, object]:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    stable_id = sum((index + 1) * ord(char) for index, char in enumerate(name))
    return {
        "id": run_id,
        "workflow_id": stable_id if workflow_id is None else workflow_id,
        "workflow_path": workflow_path or f".github/workflows/{slug}.yml",
        "event": event,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "jobs_total": jobs_total,
        "created_at": created_at,
    }


class PrHeadRecoveryClassifierTests(unittest.TestCase):
    def test_zero_job_action_required_reobserves(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=10,
                    name="QIKVRT CI",
                    conclusion="action_required",
                    jobs_total=0,
                    created_at="2026-08-21T03:40:14Z",
                )
            ]
        )
        self.assertEqual(
            decision,
            RecoveryDecision(
                d0=2,
                state="REOBSERVE",
                reason="ZERO_JOB_ACTION_REQUIRED",
                active_workflows=0,
                executed_failures=0,
                zero_job_action_required=1,
                continuation_mode="EXECUTE_REOBSERVATION",
                continuation_owner="REPOSITORY_EVENT_LOOP",
                continuation_next_action="DISPATCH_EXACT_HEAD_REOBSERVATION",
                continuation_resume_events=(),
                persistence_run_terminal=False,
                client_return_allowed=False,
            ),
        )

    def test_reobserve_is_an_active_persistence_continuation(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=11,
                    name="QIKVRT CI",
                    conclusion="action_required",
                    jobs_total=0,
                    created_at="2026-08-21T03:40:15Z",
                )
            ]
        ).to_mapping()
        continuation = decision["continuation"]
        self.assertEqual(continuation["mode"], "EXECUTE_REOBSERVATION")
        self.assertFalse(continuation["persistence_run_terminal"])
        self.assertFalse(continuation["client_return_allowed"])

    def test_success_does_not_mask_a_different_stalled_workflow(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=20,
                    name="QIKVRT code-owner review observer",
                    conclusion="success",
                    jobs_total=1,
                    created_at="2026-08-21T03:40:10Z",
                ),
                observation(
                    run_id=21,
                    name="QIKVRT CI",
                    conclusion="action_required",
                    jobs_total=0,
                    created_at="2026-08-21T03:40:14Z",
                ),
            ]
        )
        self.assertEqual(decision.state, "REOBSERVE")
        self.assertEqual(decision.zero_job_action_required, 1)

    def test_latest_run_per_workflow_supersedes_stale_success(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=30,
                    name="QIKVRT CI",
                    conclusion="success",
                    jobs_total=1,
                    created_at="2026-08-21T03:30:00Z",
                ),
                observation(
                    run_id=31,
                    name="QIKVRT CI",
                    conclusion="action_required",
                    jobs_total=0,
                    created_at="2026-08-21T03:40:14Z",
                ),
            ]
        )
        self.assertEqual(decision.state, "REOBSERVE")
        self.assertEqual(decision.zero_job_action_required, 1)

    def test_newer_success_supersedes_stale_action_required(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=32,
                    name="QIKVRT CI",
                    conclusion="action_required",
                    jobs_total=0,
                    created_at="2026-08-21T03:30:00Z",
                ),
                observation(
                    run_id=33,
                    name="QIKVRT CI",
                    conclusion="success",
                    jobs_total=1,
                    created_at="2026-08-21T03:45:00Z",
                ),
            ]
        )
        self.assertEqual(decision.state, "HOLD")
        self.assertEqual(
            decision.reason, "OBSERVED_WORKFLOW_SCOPE_COMPLETE_GATES_PENDING"
        )
        self.assertEqual(decision.zero_job_action_required, 0)

    def test_active_workflow_holds(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=40,
                    name="QIKVRT CI",
                    status="in_progress",
                    jobs_total=1,
                    created_at="2026-08-21T03:41:00Z",
                )
            ]
        )
        self.assertEqual(decision.d0, 1)
        self.assertEqual(decision.state, "HOLD")
        self.assertEqual(decision.reason, "ACTIVE_WORKFLOW")
        continuation = decision.to_mapping()["continuation"]
        self.assertEqual(continuation["mode"], "AWAIT_EXACT_EVENT")
        self.assertIn("workflow_run.completed", continuation["resume_events"])
        self.assertFalse(continuation["persistence_run_terminal"])
        self.assertFalse(continuation["client_return_allowed"])

    def test_executed_failure_holds_instead_of_blind_retry(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=50,
                    name="QIKVRT CI",
                    conclusion="failure",
                    jobs_total=1,
                    created_at="2026-08-21T03:42:00Z",
                ),
                observation(
                    run_id=51,
                    name="QIKVRT Collective Proposal Review",
                    conclusion="action_required",
                    jobs_total=0,
                    created_at="2026-08-21T03:42:01Z",
                ),
            ]
        )
        self.assertEqual(decision.d0, 1)
        self.assertEqual(decision.state, "HOLD")
        self.assertEqual(decision.reason, "ADVERSE_TERMINAL_RESULT_PRESENT")
        continuation = decision.to_mapping()["continuation"]
        self.assertEqual(continuation["mode"], "EXECUTE_REPAIR")
        self.assertIn("workflow_run.completed", continuation["resume_events"])
        self.assertFalse(continuation["client_return_allowed"])

    def test_observed_workflow_success_waits_for_independent_gates(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=60,
                    name="QIKVRT CI",
                    conclusion="success",
                    jobs_total=1,
                    created_at="2026-08-21T03:43:00Z",
                )
            ]
        )
        self.assertEqual(decision.d0, 1)
        self.assertEqual(decision.state, "HOLD")
        self.assertEqual(
            decision.reason, "OBSERVED_WORKFLOW_SCOPE_COMPLETE_GATES_PENDING"
        )
        continuation = decision.to_mapping()["continuation"]
        self.assertIn(
            "workflow_run.code_owner_review_observer.completed",
            continuation["resume_events"],
        )
        self.assertIn(
            "workflow_run.main_ruleset_reconciler.completed",
            continuation["resume_events"],
        )
        self.assertFalse(continuation["persistence_run_terminal"])
        self.assertFalse(continuation["client_return_allowed"])

    def test_trusted_exact_head_success_closes_recovery_loop(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=61,
                    name="QIKVRT CI",
                    conclusion="action_required",
                    jobs_total=0,
                    created_at="2026-08-21T03:43:00Z",
                )
            ],
            exact_head_status="success",
            trusted_exact_head_source=True,
            terminal_gates_bound=True,
        )
        self.assertEqual(decision.d0, 0)
        self.assertEqual(decision.state, "NOOP")
        self.assertEqual(decision.reason, "TRUSTED_EXACT_HEAD_VERIFIED")

    def test_trusted_exact_head_success_without_terminal_gates_holds(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=610,
                    name="QIKVRT CI",
                    conclusion="success",
                    jobs_total=1,
                    created_at="2026-08-21T03:43:00Z",
                )
            ],
            exact_head_status="success",
            trusted_exact_head_source=True,
        )
        self.assertEqual(decision.d0, 1)
        self.assertEqual(
            decision.reason, "TRUSTED_EXACT_HEAD_SCOPE_COMPLETE_GATES_PENDING"
        )
        self.assertIn(
            "workflow_run.main_ruleset_reconciler.completed",
            decision.continuation_resume_events,
        )
        self.assertFalse(decision.persistence_run_terminal)
        self.assertFalse(decision.client_return_allowed)

    def test_adverse_terminal_result_precedes_trusted_success_statuses(self) -> None:
        for exact_head_status in ("self_check_success", "success"):
            with self.subTest(exact_head_status=exact_head_status):
                decision = classify_observations(
                    [
                        observation(
                            run_id=611,
                            name="QIKVRT CI",
                            conclusion="failure",
                            jobs_total=1,
                            created_at="2026-08-21T03:43:01Z",
                        )
                    ],
                    exact_head_status=exact_head_status,
                    trusted_exact_head_source=True,
                )
                self.assertEqual(decision.d0, 1)
                self.assertEqual(decision.state, "HOLD")
                self.assertEqual(
                    decision.reason, "ADVERSE_TERMINAL_RESULT_PRESENT"
                )
                self.assertFalse(decision.client_return_allowed)

    def test_pending_exact_head_verification_holds_without_duplicate_dispatch(self) -> None:
        decision = classify_observations(
            [], exact_head_status="pending", trusted_exact_head_source=True
        )
        self.assertEqual(decision.d0, 1)
        self.assertEqual(decision.reason, "TRUSTED_EXACT_HEAD_VERIFICATION_PENDING")
        continuation = decision.to_mapping()["continuation"]
        self.assertEqual(continuation["mode"], "AWAIT_EXACT_EVENT")
        self.assertTrue(continuation["resume_events"])
        self.assertFalse(continuation["client_return_allowed"])

    def test_unbound_verifier_completion_waits_for_external_edge(self) -> None:
        decision = classify_observations(
            [],
            exact_head_status="unbound_verifier_completion",
            trusted_exact_head_source=True,
        )
        self.assertEqual(decision.d0, 1)
        self.assertEqual(
            decision.reason, "UNBOUND_VERIFIER_COMPLETION_AWAITS_EXTERNAL_EDGE"
        )
        self.assertNotIn("workflow_run.completed", decision.continuation_resume_events)
        self.assertIn("workflow_dispatch", decision.continuation_resume_events)
        self.assertFalse(decision.client_return_allowed)

    def test_unbound_verifier_never_authorizes_a_new_run_retry(self) -> None:
        with self.assertRaises(ValueError):
            classify_observations(
                [],
                exact_head_status="unbound_verifier_retry_once",
                trusted_exact_head_source=True,
            )
        repeated = classify_observations(
            [],
            exact_head_status="repeated_unbound_verifier_completion",
            trusted_exact_head_source=True,
        )
        self.assertEqual(repeated.d0, 3)
        self.assertEqual(repeated.state, "REQUEST_AUTHORITY")
        self.assertEqual(repeated.continuation_mode, "REQUEST_AUTHORITY")
        self.assertNotIn("workflow_run.completed", repeated.continuation_resume_events)
        self.assertFalse(repeated.client_return_allowed)

    def test_failed_exact_head_verification_holds_for_repair(self) -> None:
        decision = classify_observations(
            [], exact_head_status="failure", trusted_exact_head_source=True
        )
        self.assertEqual(decision.d0, 1)
        self.assertEqual(decision.reason, "TRUSTED_EXACT_HEAD_VERIFICATION_FAILED")
        continuation = decision.to_mapping()["continuation"]
        self.assertEqual(continuation["mode"], "EXECUTE_REPAIR")
        self.assertTrue(continuation["next_action"].startswith("DIAGNOSE_"))
        self.assertFalse(continuation["client_return_allowed"])

    def test_same_display_name_cannot_collapse_distinct_workflow_identities(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=62,
                    workflow_id=1001,
                    workflow_path=".github/workflows/first.yml",
                    name="mutable title",
                    conclusion="failure",
                    jobs_total=0,
                    created_at="2026-08-21T03:43:00Z",
                ),
                observation(
                    run_id=63,
                    workflow_id=1002,
                    workflow_path=".github/workflows/second.yml",
                    name="mutable title",
                    conclusion="success",
                    jobs_total=1,
                    created_at="2026-08-21T03:44:00Z",
                ),
            ]
        )
        self.assertEqual(decision.reason, "ADVERSE_TERMINAL_RESULT_PRESENT")
        self.assertEqual(decision.executed_failures, 1)

    def test_dynamic_title_does_not_split_one_stable_workflow_identity(self) -> None:
        decision = classify_observations(
            [
                observation(
                    run_id=64,
                    workflow_id=1003,
                    workflow_path=".github/workflows/stable.yml@refs/heads/main",
                    name="old display title",
                    conclusion="failure",
                    jobs_total=0,
                    created_at="2026-08-21T03:43:00Z",
                ),
                observation(
                    run_id=65,
                    workflow_id=1003,
                    workflow_path=".github/workflows/stable.yml@refs/heads/feature",
                    name="new display title",
                    conclusion="success",
                    jobs_total=1,
                    created_at="2026-08-21T03:44:00Z",
                ),
            ]
        )
        self.assertEqual(
            decision.reason, "OBSERVED_WORKFLOW_SCOPE_COMPLETE_GATES_PENDING"
        )

    def test_non_pr_events_cannot_mask_pr_event_for_same_workflow(self) -> None:
        for later_event in ("push", "workflow_dispatch"):
            with self.subTest(later_event=later_event):
                decision = classify_observations(
                    [
                        observation(
                            run_id=651,
                            workflow_id=1004,
                            workflow_path=".github/workflows/stable.yml",
                            event="pull_request",
                            name="PR display title",
                            conclusion="failure",
                            jobs_total=1,
                            created_at="2026-08-21T03:43:00Z",
                        ),
                        observation(
                            run_id=652,
                            workflow_id=1004,
                            workflow_path=".github/workflows/stable.yml",
                            event=later_event,
                            name="non-PR display title",
                            conclusion="success",
                            jobs_total=1,
                            created_at="2026-08-21T03:44:00Z",
                        ),
                    ]
                )
                self.assertEqual(
                    decision.reason, "ADVERSE_TERMINAL_RESULT_PRESENT"
                )
                self.assertEqual(decision.executed_failures, 1)

    def test_unpermitted_observation_event_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "permitted server workflow event"):
            classify_observations(
                [
                    observation(
                        run_id=653,
                        name="QIKVRT CI",
                        event="not_a_server_event",
                        conclusion="success",
                        jobs_total=1,
                        created_at="2026-08-21T03:45:00Z",
                    )
                ]
            )

    def test_spoofed_exact_status_context_cannot_terminalize(self) -> None:
        decision = classify_observations([], exact_head_status="success")
        self.assertEqual(decision.d0, 2)
        self.assertEqual(decision.reason, "UNTRUSTED_EXACT_HEAD_STATUS_SOURCE")
        self.assertFalse(decision.client_return_allowed)

    def test_candidate_self_check_holds_for_independent_gates(self) -> None:
        decision = classify_observations(
            [],
            exact_head_status="self_check_success",
            trusted_exact_head_source=True,
        )
        self.assertEqual(decision.d0, 1)
        self.assertEqual(decision.state, "HOLD")
        self.assertEqual(decision.reason, "CANDIDATE_SELF_CHECK_SCOPE_COMPLETE")
        self.assertNotEqual(decision.reason, "TRUSTED_EXACT_HEAD_VERIFIED")
        self.assertFalse(decision.persistence_run_terminal)
        self.assertFalse(decision.client_return_allowed)
        self.assertIn(
            "workflow_run.code_owner_review_observer.completed",
            decision.continuation_resume_events,
        )
        self.assertIn(
            "workflow_run.main_ruleset_reconciler.completed",
            decision.continuation_resume_events,
        )

    def test_every_zero_job_adverse_or_unknown_terminal_holds(self) -> None:
        for conclusion in (
            "failure",
            "startup_failure",
            "cancelled",
            "timed_out",
            "skipped",
            "stale",
            "neutral",
            None,
            "future_terminal",
        ):
            with self.subTest(conclusion=conclusion):
                decision = classify_observations(
                    [
                        observation(
                            run_id=66,
                            name="QIKVRT CI",
                            conclusion=conclusion,
                            jobs_total=0,
                            created_at="2026-08-21T03:44:00Z",
                        )
                    ]
                )
                self.assertEqual(decision.d0, 1)
                self.assertEqual(
                    decision.reason, "ADVERSE_TERMINAL_RESULT_PRESENT"
                )
                self.assertFalse(decision.client_return_allowed)

    def test_101_run_pages_must_be_complete_before_classification(self) -> None:
        runs = [
            {
                "id": index + 1,
                "workflow_id": 1000 + index,
                "path": f".github/workflows/test-{index}.yml",
            }
            for index in range(101)
        ]
        flattened = flatten_run_pages(
            [
                {"total_count": 101, "workflow_runs": runs[:100]},
                {"total_count": 101, "workflow_runs": runs[100:]},
            ]
        )
        self.assertEqual(flattened["total_count"], 101)
        self.assertEqual(len(flattened["workflow_runs"]), 101)
        with self.assertRaisesRegex(ValueError, "incomplete run pagination"):
            flatten_run_pages(
                [{"total_count": 101, "workflow_runs": runs[:100]}]
            )

    def test_shared_sha_cannot_transfer_publisher_receipt_between_prs_or_bases(self) -> None:
        shared_sha = "a" * 40
        expected = {
            "repository": "Goldkelch/qik-vrt",
            "pull_request": 935,
            "head_repository": "Goldkelch/qik-vrt",
            "head_ref": "release-a",
            "head_sha": shared_sha,
            "head_tree_sha": "b" * 40,
            "base_ref": "main",
            "base_sha": "c" * 40,
            "run_id": 2001,
            "run_attempt": 1,
            "workflow_ref": "Goldkelch/qik-vrt/.github/workflows/qikvrt_autonomous_exact_head_verify.yml@refs/heads/main",
            "workflow_sha": "d" * 40,
        }
        receipt = {
            **expected,
            "schema": "qikvrt.autonomous-candidate-self-check-publisher.v2",
            "status_context": "QIKVRT autonomous candidate self-check",
            "classification": "CANDIDATE_SELF_CHECK_ONLY",
            "trusted_terminal_verification": False,
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
            "published_state": "success",
            "dispatch_binding": {
                "artifact": {
                    "id": 1997,
                    "digest": "sha256:" + "2" * 64,
                },
                "run_attempt": 1,
                "receipt_outcome": "success",
            },
            "review_dispatch_outcome": "pending",
            "review_transport": {
                "attempt": 1,
                "outcome": "intent_persisted",
                "intent_artifact": {
                    "id": 1996,
                    "digest": "sha256:" + "3" * 64,
                },
            },
            "producer": {
                "run_id": 1999,
                "run_attempt": 1,
                "workflow_id": 99,
                "workflow_path": ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml",
                "workflow_sha": "e" * 40,
                "continuation_artifact": {
                    "id": 1998,
                    "digest": "sha256:" + "1" * 64,
                },
            },
        }
        self.assertEqual(
            validate_publisher_receipt(receipt, expected),
            {"valid": True, "published_state": "success"},
        )
        for drift in (
            {"pull_request": 936},
            {"base_sha": "f" * 40},
            {"head_ref": "release-b"},
        ):
            with self.subTest(drift=drift):
                with self.assertRaisesRegex(ValueError, "mismatch"):
                    validate_publisher_receipt(receipt, {**expected, **drift})

        specific_job_rerun = {
            **receipt,
            "run_attempt": 2,
            "dispatch_binding": {**receipt["dispatch_binding"], "run_attempt": 1},
        }
        self.assertEqual(
            validate_publisher_receipt(
                specific_job_rerun, {**expected, "run_attempt": 2}
            ),
            {"valid": True, "published_state": "success"},
        )
        with self.assertRaisesRegex(ValueError, "binding attempt"):
            validate_publisher_receipt(
                {
                    **specific_job_rerun,
                    "dispatch_binding": {
                        **specific_job_rerun["dispatch_binding"],
                        "run_attempt": 3,
                    },
                },
                {**expected, "run_attempt": 2},
            )

    def test_adverse_publisher_receipt_has_no_review_transport(self) -> None:
        expected = {
            "repository": "Goldkelch/qik-vrt",
            "pull_request": 935,
            "head_repository": "Goldkelch/qik-vrt",
            "head_ref": "release-a",
            "head_sha": "a" * 40,
            "head_tree_sha": "b" * 40,
            "base_ref": "main",
            "base_sha": "c" * 40,
            "run_id": 2001,
            "run_attempt": 2,
            "workflow_ref": "Goldkelch/qik-vrt/.github/workflows/qikvrt_autonomous_exact_head_verify.yml@refs/heads/main",
            "workflow_sha": "d" * 40,
        }
        receipt = {
            **expected,
            "schema": "qikvrt.autonomous-candidate-self-check-publisher.v2",
            "status_context": "QIKVRT autonomous candidate self-check",
            "classification": "CANDIDATE_SELF_CHECK_ONLY",
            "trusted_terminal_verification": False,
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
            "published_state": "error",
            "dispatch_binding": {
                "artifact": {"id": 1997, "digest": "sha256:" + "2" * 64},
                "run_attempt": 1,
                "receipt_outcome": "success",
            },
            "review_dispatch_outcome": "not_applicable",
            "review_transport": {
                "attempt": None,
                "outcome": "not_applicable",
                "intent_artifact": None,
            },
            "producer": {
                "run_id": 1999,
                "run_attempt": 1,
                "workflow_id": 99,
                "workflow_path": ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml",
                "workflow_sha": "e" * 40,
                "continuation_artifact": {
                    "id": 1998,
                    "digest": "sha256:" + "1" * 64,
                },
            },
        }
        self.assertEqual(
            validate_publisher_receipt(receipt, expected),
            {"valid": True, "published_state": "error"},
        )
        with self.assertRaisesRegex(ValueError, "must not claim"):
            validate_publisher_receipt(
                {**receipt, "review_dispatch_outcome": "pending"}, expected
            )

    def test_empty_observation_set_reobserves_instead_of_returning(self) -> None:
        decision = classify_observations([])
        self.assertEqual(decision.d0, 2)
        self.assertEqual(decision.state, "REOBSERVE")
        self.assertEqual(decision.reason, "NO_EXACT_HEAD_WORKFLOW_OBSERVATIONS")
        self.assertFalse(decision.persistence_run_terminal)
        self.assertFalse(decision.client_return_allowed)

    def test_terminal_gate_claim_without_trusted_success_is_rejected(self) -> None:
        for exact_head_status, trusted in (
            ("missing", False),
            ("success", False),
            ("pending", True),
        ):
            with self.subTest(
                exact_head_status=exact_head_status,
                trusted_exact_head_source=trusted,
            ):
                with self.assertRaisesRegex(
                    ValueError, "terminal_gates_bound requires trusted exact-head success"
                ):
                    classify_observations(
                        [],
                        exact_head_status=exact_head_status,
                        trusted_exact_head_source=trusted,
                        terminal_gates_bound=True,
                    )

    def test_invalid_job_count_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "jobs_total"):
            classify_observations(
                [
                    observation(
                        run_id=70,
                        name="QIKVRT CI",
                        conclusion="action_required",
                        jobs_total=-1,
                        created_at="2026-08-21T03:44:00Z",
                    )
                ]
            )

    def test_invalid_exact_head_status_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "exact_head_status"):
            classify_observations([], exact_head_status="green")


if __name__ == "__main__":
    unittest.main()
