#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest

from tools.qikvrt_continuation_obligation import classify_observations

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/CONTINUATION_OBLIGATION_CONTRACT_V1.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_continuation_obligation_watch.yml"
AI_CONTEXT = ROOT / "AI_CONTEXT.json"


def run(
    ident: int,
    name: str,
    *,
    workflow_id: int | None = None,
    status: str = "completed",
    conclusion: str | None = "success",
    created_at: str = "2026-09-24T06:00:00Z",
    attempt: int = 1,
) -> dict:
    return {
        "id": ident,
        "workflow_id": workflow_id if workflow_id is not None else ident,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "created_at": created_at,
        "run_attempt": attempt,
    }


class ContinuationObligationClassifierTests(unittest.TestCase):
    def subject(self, **updates) -> dict:
        value = {
            "open": True,
            "draft": False,
            "effect_ack_done": False,
            "requested_reviewers": [],
        }
        value.update(updates)
        return value

    def test_unknown_future_workflow_failure_is_never_silently_ignored(self) -> None:
        decision = classify_observations(
            self.subject(),
            [run(10, "QIKVRT Future Gate Never Registered", conclusion="failure")],
        )
        self.assertEqual((decision.d0, decision.state), (2, "REOBSERVE"))
        self.assertEqual(decision.reason, "TERMINAL_ADVERSE_RUN_WITHOUT_SUCCESSOR")
        self.assertEqual(decision.causal_run_id, 10)

    def test_pr1174_reference_gate_regression_requires_successor(self) -> None:
        decision = classify_observations(
            self.subject(requested_reviewers=["Goldkelch"]),
            [
                run(
                    35966199339,
                    "QIKVRT Reference Minimal Linux v1",
                    workflow_id=365020253,
                    conclusion="failure",
                    created_at="2026-09-24T06:59:58Z",
                )
            ],
        )
        self.assertEqual((decision.d0, decision.state), (2, "REOBSERVE"))
        self.assertEqual(decision.causal_run_id, 35966199339)
        self.assertEqual(
            decision.causal_workflow, "QIKVRT Reference Minimal Linux v1"
        )

    def test_active_transition_holds_without_claiming_terminal_state(self) -> None:
        decision = classify_observations(
            self.subject(),
            [run(11, "QIKVRT Any Gate", status="in_progress", conclusion=None)],
        )
        self.assertEqual((decision.d0, decision.state), (1, "HOLD"))
        self.assertTrue(decision.follow_up_required)
        self.assertFalse(decision.productive_effect)

    def test_newer_success_supersedes_older_failure_for_same_workflow_only(self) -> None:
        decision = classify_observations(
            self.subject(requested_reviewers=["Goldkelch"]),
            [
                run(
                    12,
                    "QIKVRT Gate",
                    workflow_id=77,
                    conclusion="failure",
                    created_at="2026-09-24T06:00:00Z",
                ),
                run(
                    13,
                    "renamed display text",
                    workflow_id=77,
                    conclusion="success",
                    created_at="2026-09-24T06:10:00Z",
                ),
            ],
        )
        self.assertEqual((decision.d0, decision.state), (3, "REQUEST_AUTHORITY"))
        self.assertEqual(decision.causal_run_id, 13)

    def test_observer_only_evidence_does_not_discharge_obligation(self) -> None:
        decision = classify_observations(
            self.subject(),
            [run(14, "QIKVRT live status watch", conclusion="success")],
        )
        self.assertEqual((decision.d0, decision.state), (2, "REOBSERVE"))
        self.assertEqual(decision.reason, "NO_EXACT_HEAD_EXECUTION_EVIDENCE")

    def test_closed_subject_is_not_reopened_by_detector(self) -> None:
        decision = classify_observations(
            self.subject(open=False),
            [run(15, "QIKVRT Gate", conclusion="failure")],
        )
        self.assertEqual((decision.d0, decision.state), (0, "NOOP"))
        self.assertFalse(decision.follow_up_required)


class ContinuationObligationRepositoryTests(unittest.TestCase):
    def test_contract_encodes_safety_liveness_duality_without_overclaim(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertIn("DEADLOCK", contract["problem_model"]["liveness_failure_classes"])
        self.assertIn(
            "CONTINUATION_OMISSION",
            contract["problem_model"]["liveness_failure_classes"],
        )
        self.assertIn(
            "OPEN_EXACT_SUBJECT && EFFECT_ACK_DONE=false => ACTIVE_TRANSITION || PERSISTED_SUCCESSOR_OBLIGATION",
            contract["invariants"],
        )
        self.assertIn("HOLD != DEADLOCK", contract["invariants"])
        self.assertFalse(contract["completion_claims"]["COMPLETE_AI_SAFETY_PROVED"])
        self.assertEqual(
            contract["normative_safety_invariant"]["name"],
            "CATEGORICAL_IMPERATIVE_MAXIM_ADMISSION",
        )

    def test_workflow_has_generic_repository_native_fallback_not_name_allowlist(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("schedule:", text)
        self.assertIn('cron: "*/5 * * * *"', text)
        self.assertIn("pull_request_target:", text)
        self.assertIn("actions/runs?head_sha=${{head}", text)
        self.assertNotIn("workflow_run:", text)
        self.assertNotIn("QIKVRT Reference Minimal Linux v1", text)
        self.assertIn("QIKVRT continuation obligation", text)
        self.assertIn("readback_verified:true", text)
        self.assertIn("cancel-in-progress: false", text)

    def test_ai_bootstrap_must_read_continuation_contract(self) -> None:
        context = json.loads(AI_CONTEXT.read_text(encoding="utf-8"))
        self.assertIn(
            "state/autonomy/CONTINUATION_OBLIGATION_CONTRACT_V1.json",
            context["required_read_order"],
        )


if __name__ == "__main__":
    unittest.main()
