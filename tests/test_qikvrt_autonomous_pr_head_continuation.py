# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from tools.qikvrt_pr_head_recovery import classify_observations

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_autonomous_pr_head_continuation.yml"
EXACT_HEAD_WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_autonomous_exact_head_verify.yml"
RECOVERY_TOOL = ROOT / "tools" / "qikvrt_pr_head_recovery.py"
ABI = ROOT / "state" / "autonomy" / "CAUSAL_D0_ABI_V1.json"


class AutonomousPrHeadContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.exact_head_text = EXACT_HEAD_WORKFLOW.read_text(encoding="utf-8")
        cls.recovery_text = RECOVERY_TOOL.read_text(encoding="utf-8")
        cls.abi = json.loads(ABI.read_text(encoding="utf-8"))

    def test_is_event_driven_with_five_minute_lost_event_watchdog(self) -> None:
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("pull_request_target:", self.text)
        self.assertIn("workflow_run:", self.text)
        self.assertIn('cron: "*/5 * * * *"', self.text)
        self.assertNotIn('cron: "7,22,37,52 * * * *"', self.text)
        self.assertIn("Productive reobservation is normally interrupt/event driven", self.text)

    def test_relevant_repository_edges_are_interrupt_sources(self) -> None:
        for workflow_name in (
            "QIKVRT repository evidence materialization",
            "QIKVRT adaptive stacked successor integrity materialization",
            "QIKVRT CI",
            "QIKVRT Collective Proposal Review",
            "QIK-VRT global claim completion",
            "QIKVRT requested review executor",
            "QIKVRT code-owner review observer",
            "QIKVRT workflow executor watchdog",
        ):
            self.assertIn(workflow_name, self.text)
        self.assertIn("types: [completed]", self.text)

    def test_m68000_four_state_abi_is_exact(self) -> None:
        self.assertEqual(self.abi["architecture_reference"], "M68000")
        self.assertEqual(self.abi["endianness"], "big")
        self.assertEqual(self.abi["register"], "D0")
        expected = {
            "NOOP": (0, "70004E75", ["MOVEQ #0,D0", "RTS"]),
            "HOLD": (1, "70014E75", ["MOVEQ #1,D0", "RTS"]),
            "REOBSERVE": (2, "70024E75", ["MOVEQ #2,D0", "RTS"]),
            "REQUEST_AUTHORITY": (3, "70034E75", ["MOVEQ #3,D0", "RTS"]),
        }
        for state, (d0, bytes_hex, instructions) in expected.items():
            entry = self.abi["states"][state]
            self.assertEqual(entry["d0"], d0)
            self.assertEqual(entry["bytes_hex"], bytes_hex)
            self.assertEqual(entry["instructions"], instructions)

    def test_effect_gate_preserves_transport_effect_separation(self) -> None:
        gate = self.abi["productive_effect_gate"]
        self.assertEqual(gate["required_d0"], 0)
        self.assertEqual(gate["required_effect_ack"], "DONE")
        self.assertEqual(gate["expression"], "D0 == 0 && EFFECT_ACK == DONE")
        self.assertIn("TRANSPORT_ACK != EFFECT_ACK", self.abi["invariants"])
        self.assertIn("productive_effect:false", self.text)
        self.assertIn('effect_ack:"NOT_REQUIRED"', self.text)

    def test_authority_is_minimal_and_does_not_merge_or_review(self) -> None:
        self.assertIn("actions: write", self.text)
        self.assertIn("contents: write", self.text)
        self.assertIn("pull-requests: read", self.text)
        self.assertIn("statuses: write", self.text)
        self.assertNotIn("pull-requests: write", self.text)
        self.assertNotIn("/merges", self.text)
        self.assertNotIn("/reviews", self.text)
        self.assertIn("persist-credentials: false", self.text)

    def test_repository_dispatch_permission_is_explicit_and_bounded(self) -> None:
        self.assertIn('"repos/${GITHUB_REPOSITORY}/dispatches"', self.text)
        self.assertIn("create-repository-dispatch endpoint requires Contents: write", self.text)
        self.assertIn("used only to emit the exact bound dispatch", self.text)
        self.assertNotIn("contents: write\n  pull-requests: write", self.text)
        self.assertNotIn("git push", self.text)
        self.assertNotIn("gh api --method PUT", self.text)
        self.assertNotIn("gh api --method PATCH", self.text)

    def test_discovery_and_productive_edge_are_bounded(self) -> None:
        self.assertIn("per_page=30", self.text)
        self.assertIn("one REOBSERVE edge per run", self.text)
        self.assertIn('test "$live_ref" = "$selected_head"', self.text)
        self.assertIn('test "$live_ref" = "$HEAD_SHA"', self.text)

    def test_workflow_delegates_classification_to_one_tested_module(self) -> None:
        self.assertIn("tools/qikvrt_pr_head_recovery.py classify", self.text)
        self.assertIn("--exact-head-status", self.text)
        self.assertIn("decision-${pr}.json", self.text)
        self.assertIn("classify_observations", self.recovery_text)
        self.assertNotIn('elif [ "$zero_job_action_required"', self.text)
        self.assertNotIn("useful_terminal=$((useful_terminal + 1))", self.text)

    def test_only_latest_run_per_workflow_drives_the_decision(self) -> None:
        self.assertIn("latest run per workflow", self.recovery_text)
        self.assertIn("created_at", self.recovery_text)
        self.assertIn("run_id", self.recovery_text)

    def test_null_conclusion_transport_preserves_created_at(self) -> None:
        self.assertIn("IFS= read -r -d '' conclusion", self.text)
        self.assertIn("IFS= read -r -d '' created_at", self.text)
        self.assertNotIn(
            ".workflow_runs[] | [.id,.name,.status,(.conclusion // \"\"),.created_at] | @tsv",
            self.text,
        )

        payload = {
            "workflow_runs": [
                {
                    "id": 32897677800,
                    "name": "QIKVRT autonomous PR head continuation",
                    "status": "in_progress",
                    "conclusion": None,
                    "created_at": "2026-08-25T20:48:00Z",
                }
            ]
        }
        script = r'''
set -euo pipefail
while
  IFS= read -r -d '' run_id &&
    IFS= read -r -d '' name &&
    IFS= read -r -d '' status &&
    IFS= read -r -d '' conclusion &&
    IFS= read -r -d '' created_at
do
  jq -nc \
    --argjson id "$run_id" \
    --arg name "$name" \
    --arg status "$status" \
    --arg conclusion "$conclusion" \
    --arg created_at "$created_at" \
    '{id:$id,name:$name,status:$status,conclusion:(if $conclusion == "" then null else $conclusion end),created_at:$created_at}'
done < <(
  jq -j '
    .workflow_runs[] |
    (.id | tostring), "\u0000",
    .name, "\u0000",
    .status, "\u0000",
    (.conclusion // ""), "\u0000",
    .created_at, "\u0000"
  '
)
'''
        completed = subprocess.run(
            ["bash", "-c", script],
            input=json.dumps(payload),
            check=True,
            capture_output=True,
            text=True,
        )
        observation = json.loads(completed.stdout)
        self.assertIsNone(observation["conclusion"])
        self.assertEqual(
            observation["created_at"], payload["workflow_runs"][0]["created_at"]
        )

    def test_false_noop_regression_runs_in_canonical_suite(self) -> None:
        decision = classify_observations(
            [
                {
                    "id": 100,
                    "name": "QIKVRT CI",
                    "status": "completed",
                    "conclusion": "success",
                    "jobs_total": 1,
                    "created_at": "2026-08-21T03:30:00Z",
                },
                {
                    "id": 101,
                    "name": "QIKVRT CI",
                    "status": "completed",
                    "conclusion": "action_required",
                    "jobs_total": 0,
                    "created_at": "2026-08-21T03:40:14Z",
                },
            ]
        )
        self.assertEqual(decision.d0, 2)
        self.assertEqual(decision.state, "REOBSERVE")
        self.assertEqual(decision.reason, "ZERO_JOB_ACTION_REQUIRED")

    def test_executed_failure_is_not_collapsed_to_noop(self) -> None:
        decision = classify_observations(
            [
                {
                    "id": 102,
                    "name": "QIKVRT CI",
                    "status": "completed",
                    "conclusion": "failure",
                    "jobs_total": 1,
                    "created_at": "2026-08-21T03:42:00Z",
                },
                {
                    "id": 103,
                    "name": "QIKVRT Collective Proposal Review",
                    "status": "completed",
                    "conclusion": "action_required",
                    "jobs_total": 0,
                    "created_at": "2026-08-21T03:42:01Z",
                },
            ]
        )
        self.assertEqual(decision.d0, 1)
        self.assertEqual(decision.state, "HOLD")
        self.assertEqual(decision.reason, "EXECUTED_FAILURE_PRESENT")

    def test_exact_head_status_prevents_retry_loops(self) -> None:
        self.assertIn("QIKVRT autonomous exact-head verification", self.text)
        self.assertIn("TRUSTED_EXACT_HEAD_VERIFIED", self.recovery_text)
        self.assertIn("TRUSTED_EXACT_HEAD_VERIFICATION_PENDING", self.recovery_text)
        self.assertIn("TRUSTED_EXACT_HEAD_VERIFICATION_FAILED", self.recovery_text)

    def test_dispatch_failure_cannot_leave_a_permanent_pending_status(self) -> None:
        self.assertIn("publish_dispatch_error", self.text)
        self.assertIn("trap publish_dispatch_error EXIT", self.text)
        self.assertIn("dispatch_status_published=true", self.text)
        self.assertIn("state=error", self.text)
        self.assertIn("Exact-head recovery dispatch failed", self.text)
        self.assertIn("trap - EXIT", self.text)

    def test_named_exact_head_gate_surface_is_restored(self) -> None:
        self.assertIn("qikvrt_ci.yml", self.text)
        self.assertIn("qikvrt_collective_review.yml", self.text)
        self.assertIn("qikvrt_global_completion.yml", self.text)
        self.assertIn('-f ref="$HEAD_REF"', self.text)

    def test_continuation_is_exact_head_bound_and_review_authority_stays_separate(self) -> None:
        self.assertIn('event_type:"qikvrt_autonomous_exact_head_verify"', self.text)
        self.assertIn("head_sha:$head", self.text)
        self.assertIn("base_sha:$base", self.text)
        self.assertIn("causal_state:\"REOBSERVE\"", self.text)
        self.assertIn("qikvrt_requested_review_executor.yml/dispatches", self.text)
        self.assertIn("REQUEST_AUTHORITY/D0=3", self.text)
        self.assertIn("is not fabricated", self.text)

    def test_exact_head_qce_verification_cannot_mutate_frozen_package_inventory(self) -> None:
        self.assertIn('qce_tmpdir="$(mktemp -d "${RUNNER_TEMP}/qikvrt-qce-exact-head.XXXXXX")"', self.exact_head_text)
        self.assertIn('--axiom-output "$qce_tmpdir/qce-autonomous-axiom-output.txt"', self.exact_head_text)
        self.assertIn('> "$qce_tmpdir/qce-autonomous-verification.json"', self.exact_head_text)
        self.assertIn("trap cleanup_qce_tmpdir EXIT HUP INT TERM", self.exact_head_text)
        self.assertNotIn("--axiom-output qce-autonomous-axiom-output.txt", self.exact_head_text)
        self.assertNotIn("> qce-autonomous-verification.json", self.exact_head_text)


if __name__ == "__main__":
    unittest.main()
