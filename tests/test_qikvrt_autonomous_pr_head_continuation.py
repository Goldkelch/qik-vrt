# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path

import yaml

from tools.qikvrt_pr_head_recovery import classify_observations

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_autonomous_pr_head_continuation.yml"
EXACT_HEAD_WORKFLOW = ROOT / ".github" / "workflows" / "qikvrt_autonomous_exact_head_verify.yml"
RECOVERY_TOOL = ROOT / "tools" / "qikvrt_pr_head_recovery.py"
EXACT_REVIEW_OUTBOX_TOOL = ROOT / "tools" / "qikvrt_exact_review_outbox.py"
ABI = ROOT / "state" / "autonomy" / "CAUSAL_D0_ABI_V1.json"


class AutonomousPrHeadContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.exact_head_text = EXACT_HEAD_WORKFLOW.read_text(encoding="utf-8")
        cls.binding_job_text = cls.exact_head_text[
            cls.exact_head_text.index("  bind-dispatch:") :
            cls.exact_head_text.index("  accept-exact-head-outbox-transport:")
        ]
        cls.candidate_job_text = cls.exact_head_text[
            cls.exact_head_text.index("  verify-candidate:") :
            cls.exact_head_text.index("  validate-candidate-observation:")
        ]
        cls.candidate_validator_job_text = cls.exact_head_text[
            cls.exact_head_text.index("  validate-candidate-observation:") :
            cls.exact_head_text.index("  validate-publisher-observation:")
        ]
        cls.publisher_validator_job_text = cls.exact_head_text[
            cls.exact_head_text.index("  validate-publisher-observation:") :
            cls.exact_head_text.index("  publish-status:")
        ]
        cls.status_publisher_job_text = cls.exact_head_text[
            cls.exact_head_text.index("  publish-status:") :
            cls.exact_head_text.index("  publish-observation:")
        ]
        cls.publisher_job_text = cls.exact_head_text[
            cls.exact_head_text.index("  publish-observation:") :
            cls.exact_head_text.index("  persist-exact-review-outbox:")
        ]
        cls.review_transport_text = cls.exact_head_text[
            cls.exact_head_text.index("  persist-exact-review-outbox:") :
            cls.exact_head_text.index("  persist-exact-head-outbox-result:")
        ]
        cls.business_result_job_text = cls.exact_head_text[
            cls.exact_head_text.index("  persist-exact-head-outbox-result:") :
        ]
        cls.recovery_text = RECOVERY_TOOL.read_text(encoding="utf-8")
        cls.exact_review_outbox_text = EXACT_REVIEW_OUTBOX_TOOL.read_text(
            encoding="utf-8"
        )
        cls.abi = json.loads(ABI.read_text(encoding="utf-8"))

    def test_schedule_is_recovery_only_and_never_an_eventless_pr_scan(self) -> None:
        self.assertIn("workflow_dispatch:", self.text)
        self.assertIn("pull_request_target:", self.text)
        self.assertIn("workflow_run:", self.text)
        self.assertIn("schedule:", self.text)
        self.assertEqual(self.text.count('cron: "17 * * * *"'), 1)
        schedule_branch = self.text[
            self.text.index('if [ "$TRIGGER_EVENT_NAME" = schedule ]; then') :
            self.text.index(
                "          else",
                self.text.index('if [ "$TRIGGER_EVENT_NAME" = schedule ]; then'),
            )
        ]
        self.assertIn("RECOVERY_ONLY", schedule_branch)
        self.assertNotIn("pulls?state=open", schedule_branch)
        self.assertIn("scope_limit=0", schedule_branch)
        self.assertIn("printf '[]", schedule_branch)
        recovery_job = self.text[
            self.text.index("  observe-exact-head-outbox-recovery:") :
            self.text.index("  dispatch-exact-head-outbox-recovery:")
        ]
        self.assertIn("next --lane exact-head-dispatch", recovery_job)
        observer = recovery_job.split("  select-exact-head-outbox-recovery:", 1)[0]
        writer = recovery_job.split("  select-exact-head-outbox-recovery:", 1)[1]
        self.assertNotIn("actions/workflows/", observer.split("next --lane exact-head-dispatch", 1)[0])
        self.assertIn("prepare-transport --lane exact-head-dispatch", writer)
        self.assertNotIn("recovery-subject-pointers.tsv", recovery_job)
        self.assertNotIn("pulls?state=open", recovery_job)
        # The historical artifact parser may recognize migration receipts but
        # is not invoked. Schedule recovery is exclusively the Core FIFO.
        self.assertEqual(self.text.count("trusted_orphan_exact_intent_state"), 1)
        self.assertNotIn("orphan_exact_transport_retry_once", self.text)
        self.assertNotIn("ORPHAN_EXACT_TRANSPORT_RETRY_ONCE", self.recovery_text)

    def test_continuation_and_exact_verifier_shell_blocks_parse(self) -> None:
        for workflow in (WORKFLOW, EXACT_HEAD_WORKFLOW):
            with self.subTest(workflow=workflow.name):
                lines = workflow.read_text(encoding="utf-8").splitlines()
                blocks: list[str] = []
                index = 0
                while index < len(lines):
                    if lines[index].startswith("        run: |"):
                        index += 1
                        block: list[str] = []
                        while index < len(lines):
                            line = lines[index]
                            if line and not line.startswith("          "):
                                break
                            block.append(
                                line[10:] if line.startswith("          ") else ""
                            )
                            index += 1
                        blocks.append("\n".join(block) + "\n")
                        continue
                    index += 1
                self.assertTrue(blocks)
                for number, block in enumerate(blocks, start=1):
                    parsed = subprocess.run(
                        ["bash", "-n"],
                        input=block,
                        text=True,
                        capture_output=True,
                        check=False,
                    )
                    self.assertEqual(
                        parsed.returncode,
                        0,
                        f"{workflow.name} run block {number}: {parsed.stderr}",
                    )

    def test_relevant_repository_edges_are_interrupt_sources(self) -> None:
        for workflow_name in (
            "QIKVRT repository evidence materialization",
            "QIKVRT adaptive stacked successor integrity materialization",
            "QIKVRT CI",
            "QIKVRT Collective Proposal Review",
            "QIK-VRT global claim completion",
            "QIKVRT required code-owner review",
            "QIK-VRT autonomous exact-head verification",
            "QIKVRT requested review contract",
            "QIKVRT requested review executor",
            "QIKVRT required review gate",
            "QIKVRT workflow executor watchdog",
        ):
            self.assertIn(workflow_name, self.text)
        self.assertNotIn('      - "QIKVRT code-owner review observer"', self.text)
        self.assertIn("types: [completed]", self.text)

    def test_ruleset_boundary_is_manual_secret_free_and_does_not_scan_candidates(self) -> None:
        bridge = self.text[
            self.text.index("  hold-ruleset-reconciliation-for-manual-authority:") :
        ]
        self.assertIn("actions: read", bridge)
        self.assertNotIn("actions: write", bridge)
        self.assertIn("contents: read", bridge)
        self.assertNotIn("contents: write", bridge)
        self.assertIn("AUTOMATIC_BRANCH_PROTECTION_CHANGE_NOT_AUTHORIZED", bridge)
        self.assertIn('workflow_path:".github/workflows/qikvrt_ruleset_reconcile.yml"', bridge)
        self.assertIn('environment:"qikvrt-ruleset-authority"', bridge)
        self.assertIn("automatic_ruleset_dispatch:false", bridge)
        self.assertIn("automatic_reconciler_rerun:false", bridge)
        self.assertIn("automatic_requested_review_resume:false", bridge)
        self.assertIn("productive_effect:false", bridge)
        self.assertIn("include-hidden-files: true", bridge)
        self.assertIn("if-no-files-found: error", bridge)
        self.assertNotIn("QIKVRT_RULESET_ADMIN_TOKEN", bridge)
        self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER", bridge)
        self.assertNotIn("pulls?state=open", bridge)
        self.assertNotIn("pull_request.head.sha", bridge)
        self.assertNotIn("git push", bridge)
        self.assertNotIn("gh api --method POST", bridge)
        self.assertNotIn("gh api --method PUT", bridge)
        self.assertIn(
            "github.event.workflow_run.path == '.github/workflows/qikvrt_required_review_gate.yml'",
            bridge,
        )

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

    def test_hold_contract_is_durable_and_nonterminal_without_a_fifth_state(self) -> None:
        contract = self.abi["continuation_contract"]
        self.assertEqual(contract["schema"], "qikvrt.causal-continuation.v1")
        self.assertFalse(contract["hold_is_terminal"])
        self.assertFalse(contract["reobserve_is_terminal"])
        self.assertTrue(contract["hold_requires_next_action_or_resume_event"])
        self.assertTrue(contract["client_return_requires_terminal_persistence_run"])
        self.assertEqual(set(self.abi["states"]), {"NOOP", "HOLD", "REOBSERVE", "REQUEST_AUTHORITY"})
        self.assertIn("A nonterminal persistence run does not permit client return", self.abi["invariants"])
        self.assertIn(
            "Client return at D0 == 0 requires trusted exact-head success and independently bound terminal review and ruleset gates",
            self.abi["invariants"],
        )

    def test_effect_gate_preserves_transport_effect_separation(self) -> None:
        gate = self.abi["productive_effect_gate"]
        self.assertEqual(gate["required_d0"], 0)
        self.assertEqual(gate["required_effect_ack"], "DONE")
        self.assertEqual(gate["expression"], "D0 == 0 && EFFECT_ACK == DONE")
        self.assertIn("TRANSPORT_ACK != EFFECT_ACK", self.abi["invariants"])
        self.assertIn("productive_effect:false", self.text)
        self.assertIn('effect_ack:"NOT_REQUIRED"', self.text)

    def test_authority_is_minimal_and_does_not_merge_or_review(self) -> None:
        self.assertIn("actions: read", self.text)
        self.assertIn("contents: write", self.text)
        self.assertIn("pull-requests: read", self.text)
        continuation_job = self.text[: self.text.index("  hold-ruleset-reconciliation-for-manual-authority:")]
        self.assertNotIn("statuses: write", continuation_job)
        self.assertNotIn("pull-requests: write", self.text)
        self.assertNotIn("/merges", self.text)
        self.assertNotIn("/reviews", self.text)
        self.assertIn("persist-credentials: false", self.text)

    def test_repository_dispatch_permission_is_explicit_and_bounded(self) -> None:
        self.assertIn('"repos/${GITHUB_REPOSITORY}/dispatches"', self.text)
        top = self.text[: self.text.index("jobs:")]
        self.assertIn("contents: read", top)
        self.assertNotIn("contents: write", top)
        dispatch_job = self.text[
            self.text.index("  dispatch-exact-head-transport:") :
            self.text.index("  hold-ruleset-reconciliation-for-manual-authority:")
        ]
        self.assertIn("contents: write", dispatch_job)
        self.assertNotIn("contents: write\n  pull-requests: write", self.text)
        self.assertNotIn("git push", self.text)
        self.assertNotIn("gh api --method PUT", self.text)
        self.assertNotIn("gh api --method PATCH", self.text)

    def test_branch_workflow_dispatch_cannot_execute_continuation_authority(self) -> None:
        job_header = self.text[
            self.text.index("  continue-one-stalled-internal-pr:") :
            self.text.index("    runs-on: ubuntu-24.04", self.text.index("  continue-one-stalled-internal-pr:"))
        ]
        self.assertIn(
            "(github.event_name != 'workflow_dispatch' || github.ref == 'refs/heads/main')",
            job_header,
        )
        trusted_main_events = (
            '((.event == "workflow_run" or .event == "schedule" or '
            '.event == "workflow_dispatch") and .head_branch == "main" and '
            '.head_sha == $workflow_sha)'
        )
        self.assertIn(trusted_main_events, " ".join(self.text.split()))
        self.assertIn(trusted_main_events, " ".join(self.exact_head_text.split()))

    def test_non_main_pull_request_target_cannot_supply_trusted_workflow_bytes(self) -> None:
        job_header = self.text[
            self.text.index("  continue-one-stalled-internal-pr:") :
            self.text.index(
                "    runs-on: ubuntu-24.04",
                self.text.index("  continue-one-stalled-internal-pr:"),
            )
        ]
        self.assertIn(
            "(github.event_name != 'pull_request_target' || github.ref == 'refs/heads/main')",
            job_header,
        )
        producer_guard = (
            '(.event == "pull_request_target" and $workflow_sha == $base and '
            '.head_sha == $base and .head_branch == $base_ref and '
            '([.pull_requests[]? | select( .number == ($pr|tonumber) and '
            '.head.repo.full_name == $repository and .head.ref == $ref and '
            '.head.sha == $head and .base.ref == $base_ref and '
            '.base.sha == $base )] | length) == 1)'
        )
        self.assertIn(producer_guard, " ".join(self.text.split()))
        self.assertIn(producer_guard, " ".join(self.exact_head_text.split()))
        # Recovery may classify a terminal pull_request_target transport actor,
        # but only the exact producer guards above can authorize its subject.
        self.assertIn("ref: ${{ github.workflow_sha }}", self.text)

    def test_every_causal_trigger_subject_preempts_the_newest_thirty_window(self) -> None:
        self.assertIn("trigger_subject_pointer=false", self.text)
        self.assertIn('TRIGGER_PR_NUMBER: ${{ github.event.pull_request.number }}', self.text)
        self.assertIn('[ "$TRIGGER_EVENT_NAME" = pull_request_target ]', self.text)
        self.assertIn(
            'actions/runs/${TRIGGER_WORKFLOW_RUN_ID}',
            self.text,
        )
        self.assertIn('.pull_requests[]? | select(', self.text)
        self.assertIn('^qikvrt-rr-v3\\ e=', self.text)
        self.assertIn('if [ "$trigger_subject_pointer" = true ]; then', self.text)
        self.assertIn(
            'gh_read "repos/${GITHUB_REPOSITORY}/pulls/${TRIGGER_POINTER_PR}"',
            self.text,
        )
        self.assertIn('> "$root/trigger-pointer-pr.json"', self.text)
        self.assertIn('.number == ($pr|tonumber) and .state == "open"', self.text)
        self.assertIn('.head.sha == $head', self.text)
        self.assertIn('.base.ref == "main"', self.text)
        self.assertIn(
            '([$pointer] + [.[0][] | select(.number != $pointer.number)])[:$limit]',
            self.text,
        )
        self.assertIn(
            '"$root/open-prs.json" "$root/trigger-pointer-pr.json"',
            self.text,
        )
        newest_thirty = [
            {"number": number, "head": {"sha": f"{number:040x}"}}
            for number in range(1, 31)
        ]
        pointer = {"number": 31, "head": {"sha": "f" * 40}}
        projected = subprocess.run(
            [
                "jq",
                "-cn",
                "--argjson",
                "window",
                json.dumps(newest_thirty),
                "--argjson",
                "pointer",
                json.dumps(pointer),
                "--argjson",
                "limit",
                "30",
                "([$pointer] + [$window[] | select(.number != $pointer.number)])[:$limit]",
            ],
            text=True,
            capture_output=True,
            check=True,
        )
        prioritized = json.loads(projected.stdout)
        self.assertEqual(len(prioritized), 30)
        self.assertEqual(prioritized[0], pointer)
        self.assertNotIn(30, {entry["number"] for entry in prioritized})

    def test_discovery_and_productive_edge_are_bounded(self) -> None:
        self.assertIn("scope_limit=30", self.text)
        self.assertIn("per_page=${scope_limit}", self.text)
        self.assertIn("Event-driven bounded discovery", self.text)
        self.assertIn("scope_limit=0", self.text)
        self.assertIn("RECOVERY_ONLY_DURABLE_OUTBOX_SCAN", self.text)
        self.assertIn('test "$live_ref" = "$selected_head"', self.text)
        self.assertIn('if [ "$live_ref" != "$head" ]; then', self.text)

    def test_workflow_delegates_classification_to_one_tested_module(self) -> None:
        self.assertIn("tools/qikvrt_pr_head_recovery.py classify", self.text)
        self.assertIn("--exact-head-status", self.text)
        self.assertIn("decision-${pr}.json", self.text)
        self.assertIn("classify_observations", self.recovery_text)
        self.assertNotIn('elif [ "$zero_job_action_required"', self.text)
        self.assertNotIn("useful_terminal=$((useful_terminal + 1))", self.text)

    def test_nonterminal_receipt_preserves_exact_subject_and_continuation(self) -> None:
        self.assertIn(
            "([.[] | select(.d0 == 3)][0] // [.[] | select(.d0 == 1 or .d0 == 2)][0]) + {event:$event,scope:$scope[0]}",
            self.text,
        )
        self.assertIn('"$root/decisions.jsonl"', self.text)
        self.assertNotIn("NO_REOBSERVE_EDGE_WITH_ACTIVE_OR_ADVERSE_WORK", self.text)
        self.assertIn("persistence_run_terminal:false", self.text)
        self.assertIn("client_return_allowed:false", self.text)

    def test_pure_stale_head_cannot_be_overwritten_by_terminal_noop(self) -> None:
        no_selection = self.text[
            self.text.index('if [ -z "$selected_pr" ]; then') :
            self.text.index("# Final exact reobservation immediately before exposing")
        ]
        self.assertIn(
            "if jq -e 'select(.d0 == 1 or .d0 == 2 or .d0 == 3)'",
            no_selection,
        )
        self.assertIn(
            "([.[] | select(.d0 == 3)][0] // [.[] | select(.d0 == 1 or .d0 == 2)][0]) + {event:$event,scope:$scope[0]}",
            no_selection,
        )
        self.assertIn("REPEATED_HEAD_REF_DRIFT", self.text)
        self.assertIn("persistence_run_terminal:false", self.text)

    def test_only_latest_run_per_workflow_drives_the_decision(self) -> None:
        self.assertIn("latest run per workflow", self.recovery_text)
        self.assertIn("workflow_id", self.recovery_text)
        self.assertIn("workflow_path", self.recovery_text)
        self.assertIn("--argjson workflow_id", self.text)
        self.assertIn("--arg workflow_path", self.text)
        self.assertIn("created_at", self.recovery_text)
        self.assertIn("run_id", self.recovery_text)
        self.assertIn('--arg event "$event"', self.text)
        self.assertIn("event:(.event // \"\")", self.text)

    def test_run_inventory_is_fully_paginated_and_count_bound(self) -> None:
        self.assertIn("gh_read --paginate --slurp", self.text)
        self.assertIn("run-pages-${pr}.json", self.text)
        self.assertIn("qikvrt_pr_head_recovery.py flatten-runs", self.text)
        self.assertIn("incomplete run pagination", self.recovery_text)

    def test_workflow_preserves_timestamp_when_conclusion_is_empty(self) -> None:
        self.assertIn("while IFS= read -r run", self.text)
        self.assertIn('created_at:(.created_at // "")', self.text)
        self.assertNotIn(
            '.workflow_runs[] | [.id,.name,.status,(.conclusion // ""),.created_at] | @tsv',
            self.text,
        )

    def test_exact_installation_rate_limit_uses_the_bounded_observer_backoff(self) -> None:
        self.assertIn("gh_read()", self.text)
        self.assertIn("for delay in 0 15 45", self.text)
        self.assertIn("API rate limit exceeded for installation.", self.text)
        self.assertIn("QIKVRT_GITHUB_INSTALLATION_RATE_LIMIT_BACKOFF_SECONDS", self.text)
        self.assertIn('if ! grep -Fq "API rate limit exceeded for installation." "$error"', self.text)
        self.assertNotIn("until gh api", self.text)

    def test_false_noop_regression_runs_in_canonical_suite(self) -> None:
        decision = classify_observations(
            [
                {
                    "id": 100,
                    "workflow_id": 2001,
                    "workflow_path": ".github/workflows/qikvrt_ci.yml",
                    "event": "pull_request",
                    "name": "QIKVRT CI",
                    "status": "completed",
                    "conclusion": "success",
                    "jobs_total": 1,
                    "created_at": "2026-08-21T03:30:00Z",
                },
                {
                    "id": 101,
                    "workflow_id": 2001,
                    "workflow_path": ".github/workflows/qikvrt_ci.yml",
                    "event": "pull_request",
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
                    "workflow_id": 2001,
                    "workflow_path": ".github/workflows/qikvrt_ci.yml",
                    "event": "pull_request",
                    "name": "QIKVRT CI",
                    "status": "completed",
                    "conclusion": "failure",
                    "jobs_total": 1,
                    "created_at": "2026-08-21T03:42:00Z",
                },
                {
                    "id": 103,
                    "workflow_id": 2002,
                    "workflow_path": ".github/workflows/qikvrt_collective_review.yml",
                    "event": "pull_request",
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
        self.assertEqual(decision.reason, "ADVERSE_TERMINAL_RESULT_PRESENT")

    def test_exact_head_status_prevents_retry_loops(self) -> None:
        self.assertIn("QIKVRT autonomous candidate self-check", self.text)
        self.assertIn("trusted_self_check_status()", self.text)
        self.assertIn("qikvrt-exact-head-publisher-${run_id}-${run_attempt}", self.text)
        self.assertIn("--trusted-exact-head-source", self.text)
        self.assertIn("self_check_success", self.text)
        self.assertIn("CANDIDATE_SELF_CHECK_SCOPE_COMPLETE", self.recovery_text)
        self.assertNotIn("commits/${head}/status\"", self.text)
        self.assertIn("TRUSTED_EXACT_HEAD_VERIFIED", self.recovery_text)
        self.assertIn("TRUSTED_EXACT_HEAD_VERIFICATION_PENDING", self.recovery_text)
        self.assertIn("TRUSTED_EXACT_HEAD_VERIFICATION_FAILED", self.recovery_text)

    def test_main_headed_verifier_is_bound_by_subject_artifact_before_classification(self) -> None:
        self.assertIn("trusted_verifier_run_status()", self.text)
        self.assertIn("qikvrt-exact-head-binding-${pr}-${head}", self.text)
        self.assertIn("qikvrt.autonomous-exact-head-dispatch-binding.v1", self.text)
        self.assertIn("Bind exact trusted dispatch subject", self.text)
        self.assertIn("verifier-run-pages-${pr}.json", self.text)
        self.assertIn("actions/workflows/${workflow_id}/runs?event=repository_dispatch", self.text)
        self.assertIn("verifier-artifact-pages-${pr}-${run_id}.json", self.text)
        self.assertNotIn("all-repository-artifact-pages", self.text)
        self.assertIn("producer-request.json", self.text)
        self.assertIn("producer.sealed_transport", self.text)
        self.assertIn("trusted_verifier_source", self.text)
        self.assertIn('[ "$verifier_status" = failure ]', self.text)
        self.assertIn("printf '%s\\t%s\\t%s\\t%s\\t%s\\n' pending true", self.text)
        self.assertIn("display_title == $title", self.text)
        self.assertIn("dynamic title is only an index", self.text)
        self.assertIn("trusted_unbound_trigger_disposition", self.text)
        self.assertIn("unbound_verifier_completion", self.text)
        self.assertIn("UNBOUND_VERIFIER_COMPLETION_AWAITS_EXTERNAL_EDGE", self.recovery_text)

    def test_cancel_before_binding_never_authorizes_legacy_transport_replay(self) -> None:
        self.assertIn("trusted_unbound_trigger_disposition()", self.text)
        self.assertIn("TRIGGER_WORKFLOW_RUN_ID", self.text)
        self.assertIn("TRIGGER_WORKFLOW_RUN_ATTEMPT", self.text)
        self.assertIn("TRIGGER_WORKFLOW_DISPLAY_TITLE", self.text)
        self.assertIn("TRIGGER_POINTER_PRODUCER_RUN_ID", self.text)
        self.assertIn("unbound-trigger-producer-artifact-pages-${pr}.json", self.text)
        self.assertNotIn("actions/artifacts?per_page=100", self.text)
        self.assertIn('[ "$pr" = "$TRIGGER_POINTER_PR" ]', self.text)
        self.assertIn('[ "$head" = "$TRIGGER_POINTER_HEAD" ]', self.text)
        self.assertIn(
            'actions/artifacts?name=${artifact_name}&per_page=100',
            self.text,
        )
        self.assertIn('1:attempt1) printf \'%s\\n\' authority', self.text)
        self.assertIn(
            '1:attempt1_attempt2|2:attempt1_attempt2) printf \'%s\\n\' authority',
            self.text,
        )
        self.assertNotIn("unbound_verifier_retry_once", self.text)
        self.assertIn("repeated_unbound_verifier_completion", self.text)
        self.assertNotIn("UNBOUND_VERIFIER_RETRY_ONCE", self.recovery_text)
        self.assertIn("REPEATED_UNBOUND_VERIFIER_COMPLETION", self.recovery_text)
        self.assertIn("REQUEST_AUTHORITY", self.recovery_text)
        self.assertIn("CAUSAL_ATTEMPT", self.text)
        self.assertIn("attempt:($attempt|tonumber)", self.text)

    def test_dispatch_ordinals_have_one_subject_bound_durable_witness(self) -> None:
        self.assertIn("trusted_dispatch_witness_state()", self.text)
        self.assertIn(
            "qikvrt-autonomous-exact-head-dispatch-${pr}-${head}-attempt-${attempt}",
            self.text,
        )
        self.assertIn(
            "actions/artifacts?name=${artifact_name}&per_page=100",
            self.text,
        )
        self.assertIn("([.[] | .artifacts[]] | length) == .[0].total_count", self.text)
        self.assertIn('[ "$total" -ne 1 ]', self.text)
        self.assertIn('.workflow_run.id == $run_id', self.text)
        self.assertIn('.workflow_run.head_sha == $workflow_sha', self.text)
        self.assertIn('false:true) printf \'%s\\n\' attempt2_only', self.text)
        self.assertIn('true:true) printf \'%s\\n\' attempt1_attempt2', self.text)
        self.assertIn('attempt2_only|invalid)', self.text)
        self.assertIn('--exact-head-status pending', self.text)
        self.assertIn('--exact-head-status failure', self.text)
        self.assertIn("Preserve exact subject dispatch ordinal witness", self.text)
        self.assertIn(
            "qikvrt-autonomous-exact-head-dispatch-${{ needs.continue-one-stalled-internal-pr.outputs.pr }}-"
            "${{ needs.continue-one-stalled-internal-pr.outputs.head }}-attempt-${{ needs.continue-one-stalled-internal-pr.outputs.attempt }}",
            self.text,
        )
        self.assertIn("retention-days: 90", self.text)

    def test_duplicate_attempt_one_witnesses_never_authorize_attempt_two(self) -> None:
        recovery = self.text[
            self.text.index("  observe-exact-head-outbox-recovery:") :
            self.text.index("  dispatch-exact-head-outbox-recovery:")
        ]
        self.assertIn("next --lane exact-head-dispatch", recovery)
        self.assertIn("prepare-transport --lane exact-head-dispatch", recovery)
        self.assertIn("request_for_transport_attempt", recovery)
        # New-run transport is one-shot.  A complete zero-successor cursor is
        # an Authority terminal, never authority for another POST.
        self.assertIn("record-retry-scan-cursor --lane exact-head-dispatch", recovery)
        self.assertIn("materialize_retry_scan_cursor", recovery)
        self.assertIn("COMPLETE_ZERO_SUCCESSOR", recovery)
        self.assertIn("AMBIGUITY_SET_EXCEEDED_AUTHORITY", recovery)
        self.assertIn("materialize_retry_cursor_authority_observation", recovery)
        self.assertIn('seal_authority_observation "$blocker"', recovery)
        self.assertIn('window_end="$observation_started_at"', recovery)
        self.assertNotIn('window_end="$actor_updated_at"', recovery)
        self.assertIn(".cas.appended", recovery)
        self.assertNotIn('mode:"ATTEMPTS_EXHAUSTED"', recovery)
        self.assertNotIn('ATTEMPT_1_TERMINAL_ADVERSE', recovery)
        self.assertNotIn("qikvrt_ruleset_outbox_retry_evidence_v1", recovery)
        self.assertNotIn("materialize_transport_retry_evidence", recovery)
        self.assertNotIn("request_for_transport_attempt(item['intent'],2)", recovery)
        self.assertIn("record-observation --lane exact-head-dispatch", recovery)
        self.assertIn("EXACT_HEAD_COMPLETION_EVIDENCE_MISSING", recovery)
        self.assertIn("REPEATED_EXACT_HEAD_RESULT_NOT_PERSISTED", recovery)
        self.assertIn("observed_child_sha256", recovery)
        self.assertIn("artifact_set_sha256", recovery)
        self.assertNotIn("SAME_RUN_EXACT_RESULT_INCOMPLETE", recovery)
        self.assertNotIn(
            "ACCEPTED_EXACT_CHILD_RESULT_ADVERSE_OR_INCOMPLETE", recovery
        )
        self.assertIn("qikvrt-outbox-retry-scan-cursor-exact-head-dispatch-", recovery)
        self.assertNotIn("qikvrt-outbox-retry-observation-exact-head-dispatch-", recovery)

    def test_all_exact_transport_posts_require_a_new_prepare_cas(self) -> None:
        initial_head = self.text[
            self.text.index("  persist-exact-head-transport-outbox:") :
            self.text.index("  observe-exact-review-outbox:")
        ]
        recovered_head = self.text[
            self.text.index("  select-exact-head-outbox-recovery:") :
            self.text.index("  prepare-exact-head-transport-intent:")
        ]
        initial_review = self.exact_head_text[
            self.exact_head_text.index("  persist-exact-review-outbox:") :
            self.exact_head_text.index("  accept-exact-review-transport:")
        ]
        recovered_review = self.text[
            self.text.index("  mutate-exact-review-outbox:") :
            self.text.index("  accept-exact-review-outbox-recovery:")
        ]

        for name, region in (
            ("initial exact head", initial_head),
            ("recovered exact head", recovered_head),
            ("initial exact review", initial_review),
            ("recovered exact review", recovered_review),
        ):
            with self.subTest(name=name):
                self.assertIn(".cas.appended", region)
                self.assertIn("prepare-transport", region)

        self.assertIn(
            "needs.persist-exact-head-transport-outbox.outputs.new_transport == 'true'",
            initial_head,
        )
        self.assertIn(
            "needs.persist-exact-review-outbox.outputs.new_transport == 'true'",
            initial_review,
        )
        self.assertIn("echo \"action=POST\"", recovered_head)
        self.assertIn("echo \"action=POST\"", recovered_review)
        for region in (recovered_head, recovered_review):
            self.assertLess(
                region.index(".cas.appended"), region.index('echo "action=POST"')
            )
            self.assertIn('echo "action=NONE"', region)

    def test_exact_effects_reject_failed_job_or_whole_run_replays(self) -> None:
        initial_head = self.text[
            self.text.index("  dispatch-exact-head-transport:") :
            self.text.index("  observe-exact-review-outbox:")
        ]
        recovered_head = self.text[
            self.text.index("  dispatch-exact-head-outbox-recovery:") :
            self.text.index("  prepare-exact-head-transport-intent:")
        ]
        initial_review = self.exact_head_text[
            self.exact_head_text.index("  dispatch-exact-review-transport:") :
            self.exact_head_text.index("  accept-exact-review-transport:")
        ]
        recovered_review = self.text[
            self.text.index("  dispatch-exact-review-outbox-recovery:") :
            self.text.index("  accept-exact-review-outbox-recovery:")
        ]

        for name, region in (
            ("initial exact head", initial_head),
            ("exact head", recovered_head),
            ("initial exact review", initial_review),
            ("exact review", recovered_review),
        ):
            with self.subTest(name=name):
                # A failed-job rerun keeps the workflow run ID but increments
                # GITHUB_RUN_ATTEMPT.  Both the immutable artifact name and
                # the Core prepare receipt therefore stop before POST.
                self.assertIn("-run-${GITHUB_RUN_ID}-attempt-${GITHUB_RUN_ATTEMPT}", region)
                self.assertIn(".actor_run_id == $actor", region)
                self.assertIn(".actor_run_attempt == $actor_attempt", region)
                self.assertIn(".cas.persisted == true and .cas.appended == true", region)
                self.assertIn("request_sha256", region)
                self.assertIn("digest(request)", region)
                self.assertLess(
                    region.index(".cas.persisted == true and .cas.appended == true"),
                    region.index("gh api --method POST"),
                )

    def test_candidate_owned_review_observer_is_not_a_privileged_resume_source(self) -> None:
        self.assertNotIn("pull_request_review:", self.text)
        self.assertNotIn('      - "QIKVRT code-owner review observer"', self.text)
        self.assertIn("QIKVRT requested review executor", self.text)

    def test_dispatch_never_publishes_an_orphanable_pending_status(self) -> None:
        dispatch = self.text[
            self.text.index("  dispatch-exact-head-transport:") :
            self.text.index("  observe-exact-review-outbox:")
        ]
        self.assertNotIn("state=pending", dispatch)
        self.assertNotIn("statuses/", dispatch)
        self.assertIn("TRANSPORT_ACCEPTED_AWAITING_EXACT_RUN_ID", dispatch)
        self.assertIn("workflow_run.completed", dispatch)

    def test_candidate_branch_workflow_dispatch_and_materializer_are_absent(self) -> None:
        dispatch = self.text[
            self.text.index("  dispatch-exact-head-transport:") :
            self.text.index("  observe-exact-review-outbox:")
        ]
        for unsafe_workflow in (
            "qikvrt_batch04_integrity.yml",
            "qikvrt_ci.yml",
            "qikvrt_collective_review.yml",
            "qikvrt_global_completion.yml",
            "qikvrt_requested_review_contract.yml",
        ):
            self.assertNotIn(unsafe_workflow, dispatch)
        self.assertNotIn('ref="$HEAD_REF"', dispatch)
        # The App-authorized FIFO writer seals the attempt-specific request in
        # the preceding job.  The repository_dispatch effect job may only
        # consume those exact pre-effect bytes; it must not reconstruct or
        # mutate the request while holding contents:write.
        persist = self.text[
            self.text.index("  persist-exact-head-transport-outbox:") :
            self.text.index("  dispatch-exact-head-transport:")
        ]
        self.assertIn("request_for_transport_attempt", persist)
        self.assertNotIn("request_for_transport_attempt", dispatch)
        self.assertNotIn("qikvrt_ruleset_outbox.py", dispatch)
        self.assertIn("qikvrt-exact-head-pre-effect-", dispatch)
        self.assertIn('"repos/${GITHUB_REPOSITORY}/dispatches"', dispatch)

    def test_exact_review_recovery_has_no_legacy_parallel_transport(self) -> None:
        generic = self.text[: self.text.index("  hold-ruleset-reconciliation-for-manual-authority:")]
        self.assertIn('event_type:"qikvrt_autonomous_exact_head_verify"', generic)
        self.assertIn("head_sha:$head", generic)
        self.assertIn("base_sha:$base", generic)
        self.assertIn("head_tree_sha:$tree", generic)
        self.assertIn("base_ref:$base_ref", generic)
        self.assertIn("producer_workflow_id", generic)
        self.assertIn('causal:{attempt:($attempt|tonumber),d0:2,state:"REOBSERVE",productive_effect:false}', generic)
        self.assertIn(
            'test "$(jq \'.client_payload | keys | length\' "$root/dispatch-request.json")" -le 10',
            generic,
        )
        self.assertIn("github.event.client_payload.subject.head_sha", self.exact_head_text)
        self.assertIn("github.event.client_payload.producer.run_id", self.exact_head_text)
        self.assertNotIn("retry-requested-review-transport", generic)
        self.assertNotIn("requested_review_retry", generic)
        self.assertNotIn("REQUESTED_REVIEW_TRANSPORT_RETRY_ONCE", self.recovery_text)
        self.assertIn('lane:"exact-review-dispatch"', self.exact_head_text)
        self.assertIn("accept --lane exact-review-dispatch", self.exact_head_text)
        exact_review = self.text[
            self.text.index("  observe-exact-review-outbox:") :
            self.text.index("  hold-ruleset-reconciliation-for-manual-authority:")
        ]
        self.assertIn("next --lane exact-review-dispatch", exact_review)
        self.assertIn("complete --lane exact-review-dispatch", exact_review)
        self.assertIn("terminalize --lane exact-review-dispatch", exact_review)
        self.assertIn("record-observation --lane exact-review-dispatch", exact_review)
        self.assertLess(
            exact_review.index("record-observation --lane exact-review-dispatch"),
            exact_review.index(
                "terminalize --lane exact-review-dispatch",
                exact_review.index("record-observation --lane exact-review-dispatch"),
            ),
        )
        self.assertIn("materialize_authority_terminal", exact_review)
        self.assertNotIn("'observation':observation", exact_review)
        self.assertNotIn("qikvrt_ruleset_outbox_retry_evidence_v1", exact_review)
        self.assertNotIn("materialize_transport_retry_evidence", exact_review)
        self.assertNotIn("request_for_transport_attempt(item['intent'],2)", exact_review)
        self.assertIn(
            "qikvrt-outbox-retry-scan-cursor-exact-review-dispatch-",
            exact_review,
        )
        self.assertIn("record-retry-scan-cursor --lane exact-review-dispatch", exact_review)
        self.assertIn("materialize_retry_scan_cursor", exact_review)
        self.assertIn("COMPLETE_ZERO_SUCCESSOR", exact_review)
        self.assertIn("AMBIGUITY_SET_EXCEEDED_AUTHORITY", exact_review)
        self.assertIn("materialize_retry_cursor_authority_observation", exact_review)
        self.assertIn('seal_authority_observation "$blocker"', exact_review)
        self.assertIn('window_end="$observation_started_at"', exact_review)
        self.assertNotIn('window_end="$actor_updated_at"', exact_review)
        self.assertIn("EXACT_REVIEW_COMPLETION_EVIDENCE_MISSING", exact_review)
        self.assertIn("observed_child_sha256", exact_review)
        self.assertIn('if [ "$sealed_main" != "$live_main" ]; then', exact_review)
        self.assertNotIn(
            ".intent.payload.main_head_sha == $ENV.GITHUB_WORKFLOW_SHA",
            exact_review,
        )
        self.assertIn("qikvrt_exact_review_outbox.py", exact_review)
        self.assertIn(
            "publish-run-completion-envelope", self.exact_review_outbox_text
        )
        self.assertNotIn("retry-requested-review-transport", exact_review)
        self.assertNotIn("qikvrt-outbox-retry-observation-exact-review-dispatch-", exact_review)
        self.assertNotIn("for page in $(seq", exact_review)
        self.assertIn(".cas.appended", exact_review)

    def test_exact_retry_scans_preserve_the_declared_run_inventory(self) -> None:
        self.assertEqual(
            self.text.count("jq -c '{total_count,workflow_runs}'"),
            2,
        )
        self.assertEqual(self.text.count("page_response=page"), 2)
        self.assertGreaterEqual(
            self.text.count("(.total_count | floor) == .total_count"),
            2,
        )
        self.assertNotIn(
            "jq -c '.workflow_runs' <<<\"$page_json\" > \"$root/retry-scan-page.json\"",
            self.text,
        )

    def test_exact_head_success_routes_one_exact_review_subject(self) -> None:
        self.assertIn("permissions: {}", self.exact_head_text)
        self.assertIn("contents: read", self.candidate_job_text)
        self.assertIn("pull-requests: read", self.candidate_job_text)
        self.assertNotIn("actions: write", self.candidate_job_text)
        self.assertNotIn("pull-requests: write", self.candidate_job_text)
        self.assertNotIn("statuses: write", self.candidate_job_text)
        self.assertNotIn("actions: write", self.publisher_job_text)
        self.assertIn("pull-requests: read", self.publisher_job_text)
        self.assertNotIn("pull-requests: write", self.publisher_job_text)
        self.assertNotIn("statuses: write", self.publisher_job_text)
        self.assertNotIn("actions/checkout@", self.publisher_job_text)
        self.assertIn("statuses: write", self.status_publisher_job_text)
        self.assertNotIn("actions: write", self.status_publisher_job_text)
        self.assertNotIn("actions: read", self.status_publisher_job_text)
        self.assertNotIn("actions/download-artifact@", self.status_publisher_job_text)
        self.assertIn(
            "Reobserve exact subject and publish only the validated status",
            self.status_publisher_job_text,
        )
        self.assertIn("actions: write", self.review_transport_text)
        self.assertNotIn("statuses: write", self.review_transport_text)
        self.assertIn(
            "Dispatch exact requested-review transport only",
            self.exact_head_text,
        )
        self.assertIn(
            "qikvrt_requested_review_executor.yml/dispatches",
            self.exact_head_text,
        )
        self.assertIn('.head.ref == $ref and .head.sha == $head', self.publisher_job_text)
        self.assertIn('.base.ref == $base_ref and .base.sha == $base', self.publisher_job_text)
        self.assertIn("TARGET_TREE_SHA", self.publisher_job_text)
        self.assertIn('ref:"main",return_run_details:true', self.review_transport_text)
        self.assertIn('inputs:{pr:$pr,head:$head,fingerprint:("0"*64)', self.review_transport_text)
        self.assertIn("request_for_transport_attempt", self.review_transport_text)

    def test_candidate_result_is_self_check_not_terminal_trusted_evidence(self) -> None:
        self.assertIn('classification:"CANDIDATE_SELF_CHECK_ONLY"', self.exact_head_text)
        self.assertIn("trusted_terminal_verification:false", self.exact_head_text)
        self.assertIn("Candidate self-check (read-only)", self.exact_head_text)
        self.assertIn("Read-only trusted-main publisher validation", self.exact_head_text)
        self.assertIn("Publish exact candidate status only", self.exact_head_text)
        self.assertIn("Seal trusted-main publisher receipt", self.exact_head_text)
        self.assertNotIn("TRUSTED_EXACT_HEAD_VERIFIED", self.exact_head_text)

    def test_publisher_binds_run_artifact_and_untrusted_payload_fail_closed(self) -> None:
        for binding in (
            "workflow_id == $workflow_id",
            '(.path | split("@")[0]) == $path',
            '.event == "repository_dispatch"',
            ".head_tree_sha == $tree",
            ".producer.workflow_id == ($producer_workflow_id|tonumber)",
            ".workflow_run.id == $run_id",
            ".digest == $digest",
        ):
            self.assertIn(binding, self.exact_head_text)
        self.assertIn(
            "Parse candidate receipt strictly as untrusted data",
            self.candidate_validator_job_text,
        )
        self.assertNotIn("statuses: write", self.candidate_validator_job_text)
        self.assertNotIn("actions: write", self.candidate_validator_job_text)
        self.assertNotIn("python3 -B tools/", self.status_publisher_job_text)
        self.assertNotIn("make test", self.publisher_job_text)

    def test_publisher_binds_exact_producer_dispatch_artifact_before_write(self) -> None:
        for evidence in (
            "Preserve exact-head transport intent before dispatch",
            "binding-dispatch-request.json",
            "binding-dispatch-intent.json",
            "producer-request.json",
            "producer-intent.json",
        ):
            self.assertIn(evidence, self.binding_job_text)
        self.assertIn("--paginate --slurp", self.binding_job_text)
        self.assertIn("producer_artifact_digest", self.binding_job_text)
        self.assertIn("(.client_payload | keys)", self.binding_job_text)
        self.assertIn("$DISPATCH_SCHEMA", self.binding_job_text)
        self.assertIn(
            'schema:"qikvrt.autonomous-exact-head-dispatch-binding.v1"',
            self.binding_job_text,
        )
        self.assertIn(
            "needs: [bind-dispatch, verify-candidate, validate-candidate-observation]",
            self.publisher_validator_job_text,
        )
        self.assertIn(
            "steps.binding_receipt.outcome == 'success'",
            self.publisher_validator_job_text,
        )
        self.assertIn('qikvrt.autonomous-candidate-self-check-publisher.v2', self.publisher_job_text)
        self.assertIn("continuation_artifact", self.publisher_job_text)
        self.assertIn("sealed_transport", self.publisher_validator_job_text)
        self.assertIn("BINDING_RUN_ATTEMPT", self.publisher_validator_job_text)

    def test_publisher_revalidates_immutable_original_producer_attempt_before_each_effect(self) -> None:
        pre_status_start = self.publisher_validator_job_text.index(
            "      - name: Revalidate producer attempt and binding before status effect"
        )
        status_plan_start = self.publisher_validator_job_text.index(
            "      - name: Seal fail-closed candidate self-check status plan"
        )
        pre_review_start = self.publisher_validator_job_text.index(
            "      - name: Revalidate producer attempt and binding before review effect"
        )
        review_intent_start = self.publisher_validator_job_text.index(
            "      - name: Materialize requested-review transport intent attempt 1"
        )
        self.assertLess(pre_status_start, status_plan_start)
        self.assertLess(status_plan_start, pre_review_start)
        self.assertLess(pre_review_start, review_intent_start)

        for block in (
            self.publisher_validator_job_text[pre_status_start:status_plan_start],
            self.publisher_validator_job_text[pre_review_start:review_intent_start],
        ):
            self.assertIn(
                'actions/runs/${PRODUCER_RUN_ID}/attempts/${PRODUCER_RUN_ATTEMPT}")',
                block,
            )
            self.assertIn('--argjson attempt "$PRODUCER_RUN_ATTEMPT"', block)
            self.assertIn('.id == $run_id and .run_attempt == $attempt', block)
            self.assertIn(".workflow_id == $workflow_id", block)
            self.assertIn('(.path | split("@")[0]) == $path', block)
            self.assertIn("jobs?filter=all&per_page=100", block)
            self.assertIn("Preserve exact-head transport intent before dispatch", block)
            self.assertIn("qikvrt.autonomous-exact-head-dispatch-binding.v1", block)
            self.assertIn(".producer == {run_id:", block)
            self.assertIn("sealed_transport", block)
            self.assertNotIn("actions/artifacts/${BOUND_PRODUCER_ARTIFACT_ID}/zip", block)

        review_intent_condition = self.publisher_validator_job_text[
            review_intent_start : self.publisher_validator_job_text.index(
                "        env:", review_intent_start
            )
        ]
        self.assertIn(
            "steps.pre_status_binding.outcome == 'success'",
            self.publisher_validator_job_text,
        )
        self.assertIn(
            "steps.pre_review_binding.outcome == 'success'",
            review_intent_condition,
        )

        self.assertIn(".run_attempt <= ($run_attempt|tonumber)", self.publisher_validator_job_text)
        self.assertIn(
            "qikvrt-exact-head-binding-${TARGET_PR}-${TARGET_SHA}-run-${GITHUB_RUN_ID}-attempt-${BINDING_RUN_ATTEMPT}",
            self.publisher_validator_job_text,
        )
        self.assertNotIn("statuses: write", self.publisher_validator_job_text)
        self.assertIn("statuses: write", self.status_publisher_job_text)
        self.assertIn(
            "Fence trusted evaluator/main immediately before the sole write",
            self.status_publisher_job_text,
        )
        self.assertNotIn("actions/artifacts/", self.status_publisher_job_text)

    def test_duplicate_exact_subject_uses_trusted_receipt_not_bare_status(self) -> None:
        dedupe = self.publisher_validator_job_text[
            self.publisher_validator_job_text.index("      - name: Detect an already published exact subject") :
            self.publisher_validator_job_text.index("      - name: Seal fail-closed candidate self-check status plan")
        ]
        self.assertIn("qikvrt-exact-head-publisher-${prior_run_id}-${prior_attempt}", dedupe)
        self.assertIn("dedupe-publisher.zip", dedupe)
        self.assertIn("Read-only trusted-main publisher validation", dedupe)
        self.assertIn("Publish exact candidate status only", dedupe)
        self.assertIn("Seal trusted-main publisher receipt", dedupe)
        self.assertNotIn("Trusted-main observer and publisher", dedupe)
        self.assertIn(".status_id == ($prior_status_id|tonumber)", dedupe)
        self.assertIn('duplicate=true', dedupe)
        self.assertIn("continuation_artifact", dedupe)
        self.assertIn("steps.dedupe.outputs.duplicate != 'true'", self.publisher_validator_job_text)
        self.assertIn('[ "$CANDIDATE_VALIDATION_STATE" = success ] || not_duplicate', dedupe)
        self.assertIn("sort_by(.id,.created_at) | last", dedupe)
        self.assertIn("= success ] || not_duplicate", dedupe)
        self.assertNotIn("gh pr comment", self.exact_head_text)

    def test_candidate_validator_never_self_references_or_holds_write_authority(self) -> None:
        self.assertNotIn(
            "needs.validate-candidate-observation.outputs",
            self.candidate_validator_job_text.split("    steps:", 1)[0],
        )
        self.assertIn(
            "ARTIFACT_ID: ${{ needs.verify-candidate.outputs.artifact_id }}",
            self.candidate_validator_job_text,
        )
        self.assertIn(
            "CANDIDATE_VALIDATION_STATE: ${{ needs.validate-candidate-observation.outputs.state }}",
            self.publisher_validator_job_text,
        )
        for job in (
            self.binding_job_text,
            self.candidate_job_text,
            self.candidate_validator_job_text,
            self.publisher_validator_job_text,
            self.status_publisher_job_text,
            self.publisher_job_text,
            self.review_transport_text,
            self.business_result_job_text,
        ):
            self.assertFalse(
                "actions: write" in job and "statuses: write" in job,
                "one job must not hold both Actions and Status write authority",
            )

    def test_outbox_authority_credentials_are_cli_scoped_not_job_scoped(self) -> None:
        exact_jobs = (
            "bind-dispatch",
            "accept-exact-head-outbox-transport",
            "persist-exact-review-outbox",
            "accept-exact-review-transport",
        )
        continuation_jobs = (
            "observe-exact-head-outbox-completion",
            "terminalize-exact-head-outbox-completion",
            "observe-exact-head-outbox-recovery",
            "select-exact-head-outbox-recovery",
            "persist-exact-head-transport-outbox",
        )
        for text, names in (
            (self.exact_head_text, exact_jobs),
            (self.text, continuation_jobs),
        ):
            for name in names:
                with self.subTest(job=name):
                    start = text.index(f"  {name}:")
                    match = re.search(r"(?m)^  [a-z0-9][a-z0-9-]*:\s*$", text[start + 3 :])
                    next_job = start + 3 + match.start() if match else len(text)
                    block = text[start:next_job]
                    header = block.split("    steps:", 1)[0]
                    self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN:", header)
                    self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN:", header)
                    self.assertNotIn("QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID:", header)
                    self.assertIn("environment: qikvrt-outbox-ledger-authority", header)
                    self.assertIn("unset LEDGER_", block)
                    has_auditor = "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN" in block
                    has_writer = "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN" in block
                    self.assertFalse(
                        has_auditor and has_writer,
                        "Auditor and Writer credentials must never share one job",
                    )
                    if has_auditor:
                        self.assertIn("QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID", block)
                        self.assertIn('QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID="$writer_actor"', block)
        for effect_job in (
            "dispatch-exact-head-transport",
            "dispatch-exact-head-outbox-recovery",
        ):
            start = self.text.index(f"  {effect_job}:")
            match = re.search(
                r"(?m)^  [a-z0-9][a-z0-9-]*:\s*$", self.text[start + 3 :]
            )
            next_job = start + 3 + match.start() if match else len(self.text)
            block = self.text[start:next_job]
            self.assertNotIn("OUTBOX_LEDGER_WRITER_TOKEN", block)
            self.assertNotIn("OUTBOX_LEDGER_AUDITOR_TOKEN", block)
            self.assertNotIn("qikvrt_ruleset_outbox.py", block)

        def job(text: str, name: str) -> str:
            start = text.index(f"  {name}:")
            match = re.search(r"(?m)^  [a-z0-9][a-z0-9-]*:\s*$", text[start + 3 :])
            end = start + 3 + match.start() if match else len(text)
            return text[start:end]

        readers = (
            job(self.exact_head_text, "bind-dispatch"),
            job(self.text, "observe-exact-head-outbox-completion"),
            job(self.text, "observe-exact-head-outbox-recovery"),
        )
        for block in readers:
            self.assertIn("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", block)
            self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", block)
            self.assertIn("QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID", block)
        writers = (
            job(self.exact_head_text, "accept-exact-head-outbox-transport"),
            job(self.exact_head_text, "persist-exact-review-outbox"),
            job(self.exact_head_text, "accept-exact-review-transport"),
            job(self.text, "terminalize-exact-head-outbox-completion"),
            job(self.text, "select-exact-head-outbox-recovery"),
            job(self.text, "persist-exact-head-transport-outbox"),
        )
        for block in writers:
            self.assertIn("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", block)
            self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", block)
            self.assertIn("QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID", block)

        for path, names in (
            (EXACT_HEAD_WORKFLOW, exact_jobs),
            (WORKFLOW, continuation_jobs),
        ):
            jobs = yaml.safe_load(path.read_text(encoding="utf-8"))["jobs"]
            for name in names:
                for step in jobs[name].get("steps", []):
                    values = " ".join(str(value) for value in (step.get("env") or {}).values())
                    if "QIKVRT_ENV_OUTBOX_LEDGER_" not in values:
                        continue
                    with self.subTest(workflow=path.name, job=name, step=step.get("name")):
                        self.assertNotIn("uses", step)
                        run = step.get("run", "")
                        self.assertNotIn("gh api", run)
                        self.assertIn("tools/qikvrt_ruleset_outbox.py", run)
                        self.assertIn("QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID", run)

    def test_legacy_exact_run_locator_parses_the_complete_transport_title(self) -> None:
        locator = self.text[
            self.text.index("trusted_exact_run_for_intent_state()") :
            self.text.index("trusted_orphan_exact_intent_state()")
        ]
        self.assertIn('"[0-9a-f]{64}-seq=[1-9][0-9]*-transport-attempt="', locator)
        self.assertIn('select(\n                (.display_title // "") |', locator)
        self.assertNotIn("select(.display_title == $title)", locator)

    def test_exact_result_is_sealed_before_external_completion_terminalizes_fifo(self) -> None:
        self.assertIn(
            "qikvrt-exact-head-business-result-${{ github.run_id }}-${{ github.run_attempt }}",
            self.business_result_job_text,
        )
        self.assertIn(
            'state:"RESULT_BYTES_SEALED_AWAITING_WORKFLOW_COMPLETION"',
            self.business_result_job_text,
        )
        self.assertNotIn("terminalize --lane exact-head-dispatch", self.business_result_job_text)
        completion = self.text[
            self.text.index("  observe-exact-head-outbox-completion:") :
            self.text.index("  observe-exact-head-outbox-recovery:")
        ]
        self.assertNotIn("transport-attempt=([12])", completion)
        self.assertNotIn('[[ "$transport_attempt" =~ ^[12]$ ]]', completion)
        self.assertIn('test "$transport_attempt" = 1', completion)
        self.assertIn("lookup --lane exact-head-dispatch", completion)
        self.assertIn("complete --lane exact-head-dispatch", completion)
        self.assertIn("observe-same-run-result --lane exact-head-dispatch", completion)
        self.assertIn("qikvrt-exact-head-completion-observation-", completion)
        observer, writer = completion.split("  terminalize-exact-head-outbox-completion:", 1)
        self.assertIn("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", observer)
        self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", observer)
        self.assertIn("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", writer)
        self.assertNotIn("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", writer)
        self.assertIn("qikvrt_ruleset_outbox_completion_evidence_v1", completion)
        self.assertIn("from tools.qikvrt_ruleset_outbox import digest", completion)
        self.assertIn("locator_child_sha256", completion)
        self.assertIn("completion_evidence_sha256", completion)
        self.assertIn("same_run_result:$same_run", completion)
        recovery_header = self.text[
            self.text.index("  observe-exact-head-outbox-recovery:") :
            self.text.index(
                "    steps:",
                self.text.index("  observe-exact-head-outbox-recovery:"),
            )
        ]
        self.assertIn("needs: terminalize-exact-head-outbox-completion", recovery_header)
        self.assertIn("always() && github.event_name == 'schedule'", recovery_header)

    def test_exact_transport_locator_is_attempt_specific_and_below_title_limit(self) -> None:
        self.assertIn("intent=${{ github.event.client_payload.transport.intent_sha256 }}", self.exact_head_text)
        self.assertIn("seq=${{ github.event.client_payload.transport.sequence }}", self.exact_head_text)
        self.assertIn("transport-attempt=${{ github.event.client_payload.transport.attempt }}", self.exact_head_text)
        self.assertIn("request_for_transport_attempt", self.binding_job_text)
        self.assertIn("lookup --lane exact-head-dispatch", self.binding_job_text)
        title = (
            "qikvrt-exact-head-pr-9999999999-sha-" + "f" * 40
            + "-producer-99999999999999999999-99999999999999999999-attempt-1-intent="
            + "f" * 64
            + "-seq=99999999999999999999-transport-attempt=1"
        )
        self.assertLess(len(title), 255)

    def test_every_non_success_candidate_result_resolves_fail_closed(self) -> None:
        self.assertIn(
            "needs: [bind-dispatch, verify-candidate, validate-candidate-observation]",
            self.publisher_validator_job_text,
        )
        self.assertIn("if: always()", self.publisher_validator_job_text)
        self.assertIn("state=error", self.publisher_validator_job_text)
        self.assertIn(
            '[ "$CANDIDATE_VALIDATION_STATE" = success ]',
            self.publisher_validator_job_text,
        )
        self.assertIn('[[ "$PLANNED_STATE" =~ ^(success|error)$ ]]', self.status_publisher_job_text)
        self.assertIn('-f state="$PLANNED_STATE"', self.status_publisher_job_text)
        self.assertIn("steps.artifact_identity.outcome", self.candidate_validator_job_text)
        self.assertIn("steps.receipt.outcome", self.candidate_validator_job_text)

    def test_exact_verifier_run_blocks_do_not_interpolate_dispatch_payload(self) -> None:
        lines = self.exact_head_text.splitlines()
        index = 0
        while index < len(lines):
            if lines[index].startswith("        run: |"):
                index += 1
                block: list[str] = []
                while index < len(lines):
                    line = lines[index]
                    if line and not line.startswith("          "):
                        break
                    block.append(line)
                    index += 1
                self.assertNotIn("github.event.client_payload", "\n".join(block))
                continue
            index += 1

    def test_scan_scope_never_promotes_bounded_or_fork_observation_to_global_terminal(self) -> None:
        self.assertIn('scope_limit=30', self.text)
        self.assertIn('AUTONOMOUS_INTERNAL_PR_HEAD_SCAN', self.text)
        self.assertIn('RECOVERY_ONLY_DURABLE_OUTBOX_SCAN', self.text)
        self.assertIn('global_terminal:false', self.text)
        self.assertIn("scope-subjects.jsonl", self.text)
        self.assertIn("eligible_internal_main", self.text)
        self.assertIn("BOUNDED_SCAN_HAS_NO_GLOBAL_TERMINAL_CLAIM", self.text)
        self.assertNotIn('reason:"NO_REOBSERVE_EDGE"', self.text)

    def test_continuation_evidence_artifact_includes_hidden_files_and_fails_closed(self) -> None:
        evidence = self.text[
            self.text.index("      - name: Preserve causal continuation evidence") :
            self.text.index("  hold-ruleset-reconciliation-for-manual-authority:")
        ]
        self.assertIn("if-no-files-found: error", evidence)
        self.assertIn("include-hidden-files: true", evidence)

    def test_ingest_and_recovery_groups_survive_the_manual_ruleset_boundary(self) -> None:
        self.assertNotIn('- "QIKVRT main ruleset reconciler"', self.text)
        self.assertIn("hold-ruleset-reconciliation-for-manual-authority:", self.text)
        self.assertIn(
            "github.event_name == 'schedule' && 'recovery'",
            self.text,
        )
        self.assertIn("github.event_name == 'workflow_dispatch' && 'manual'", self.text)
        self.assertIn("|| 'ingest'", self.text)
        self.assertIn("queue: max", self.text)

    def test_recovery_admission_cannot_be_evicted_by_ingest_overflow(self) -> None:
        group = next(
            line.strip()
            for line in self.text.splitlines()
            if line.strip().startswith("group: qikvrt-autonomous-pr-head-continuation-")
        )
        self.assertIn("github.event_name == 'schedule' && 'recovery'", group)
        self.assertIn("|| 'ingest'", group)
        self.assertNotEqual(group.rsplit("-", 1)[-1], "${{ github.run_id }}")
        self.assertIn("cancel-in-progress: false", self.text[: self.text.index("jobs:")])

    def test_exact_head_qce_verification_cannot_mutate_frozen_package_inventory(self) -> None:
        self.assertIn('qce_tmpdir="$(mktemp -d "${RUNNER_TEMP}/qikvrt-qce-exact-head.XXXXXX")"', self.exact_head_text)
        self.assertIn('--axiom-output "$qce_tmpdir/qce-autonomous-axiom-output.txt"', self.exact_head_text)
        self.assertIn('> "$qce_tmpdir/qce-autonomous-verification.json"', self.exact_head_text)
        self.assertIn("trap cleanup_qce_tmpdir EXIT HUP INT TERM", self.exact_head_text)
        self.assertNotIn("--axiom-output qce-autonomous-axiom-output.txt", self.exact_head_text)
        self.assertNotIn("> qce-autonomous-verification.json", self.exact_head_text)


if __name__ == "__main__":
    unittest.main()
