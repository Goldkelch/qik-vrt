# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import unittest

from tools.qikvrt_pr_head_recovery import RecoveryDecision, classify_observations


def observation(
    *,
    run_id: int,
    name: str,
    status: str = "completed",
    conclusion: str | None = None,
    jobs_total: int = 0,
    created_at: str,
) -> dict[str, object]:
    return {
        "id": run_id,
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
            ),
        )

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
        self.assertEqual(decision.reason, "EXECUTED_FAILURE_PRESENT")

    def test_terminal_success_is_noop(self) -> None:
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
        self.assertEqual(decision.d0, 0)
        self.assertEqual(decision.state, "NOOP")
        self.assertEqual(decision.reason, "CONSISTENT_OR_ALREADY_TERMINAL")

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


if __name__ == "__main__":
    unittest.main()
