# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
NODE_POLICY = ROOT / "registry/NODE_DISCOVERY_POLICY.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_reflexive_repository_watchdog.yml"
LIVE_STATUS_WORKFLOW = ROOT / ".github/workflows/qikvrt_live_status_watch.yml"

SPEC = importlib.util.spec_from_file_location(
    "qikvrt_reflexive_repository_watchdog",
    ROOT / "tools/qikvrt_reflexive_repository_watchdog.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)

HEAD = "a" * 40
TREE = "b" * 40
WRITER_A = "QIK-VRT autonomous bounded self-heal"
WRITER_B = "QIK-VRT autonomous draft-PR continuation"


def run(
    run_id: int,
    name: str,
    status: str,
    created_at: str,
    updated_at: str,
    conclusion: str | None = None,
    event: str = "workflow_dispatch",
) -> dict[str, object]:
    return {
        "id": run_id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "event": event,
        "head_sha": HEAD,
        "created_at": created_at,
        "updated_at": updated_at,
    }


def jobs(*run_ids: int) -> dict[str, object]:
    return {
        "jobs_by_run": {
            str(run_id): [
                {
                    "id": run_id * 10,
                    "name": "job",
                    "status": "in_progress",
                    "conclusion": None,
                }
            ]
            for run_id in run_ids
        }
    }


class ReflexiveRepositoryWatchdogTests(unittest.TestCase):
    def analyze(
        self,
        runs: list[dict[str, object]],
        job_value: dict[str, object],
        *,
        now: str = "2026-08-10T18:00:00Z",
        baseline: dict[str, object] | None = None,
        scope: str = "MAIN",
        liveness_dir: pathlib.Path | None = None,
        authority_head: str | None = HEAD,
    ) -> dict[str, object]:
        return MODULE.analyze(
            {"workflow_runs": runs},
            job_value,
            expected_head=HEAD,
            expected_tree=TREE,
            repository="example/qik-vrt",
            now=datetime.fromisoformat(now.replace("Z", "+00:00")).astimezone(timezone.utc),
            baseline=baseline,
            root=ROOT,
            observation_scope=scope,
            node_liveness_dir=liveness_dir,
            authority_head=authority_head,
        )

    @staticmethod
    def write_liveness(
        directory: pathlib.Path,
        *,
        acceptance_head: str = HEAD,
        renewal_due: str = "2026-08-11T18:00:00Z",
        health_expiry: str = "2026-08-11T18:00:00Z",
    ) -> None:
        directory.mkdir(parents=True)
        records = {
            "SEED_ACCEPTANCE_STATUS.json": {"observed_authority_commit": acceptance_head},
            "NODE_REGISTRATION_RENEWAL.json": {"next_renewal_due_utc": renewal_due},
            "NODE_HEALTH.json": {"expires_utc": health_expiry},
        }
        for name, value in records.items():
            (directory / name).write_text(json.dumps(value), encoding="utf-8")

    def test_contract_binds_every_repository_instance_and_preemptive_admission(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        prevention = contract["reflexive_deadlock_prevention"]
        self.assertTrue(prevention["enabled"])
        self.assertEqual(
            prevention["applies_to"],
            ["AUTHORITY", "MIRROR", "EVERY_FUTURE_MESH_NODE"],
        )
        self.assertEqual(prevention["observation_cadence"], "PT5M")
        self.assertEqual(
            prevention["admission_policy"],
            "PREEMPTIVE_HOLD_BEFORE_SECOND_WRITER",
        )
        gatewatch = prevention["gatewatch"]
        self.assertTrue(gatewatch["enabled"])
        self.assertEqual(gatewatch["observation_freshness_seconds"], 900)
        self.assertEqual(
            gatewatch["required_workflow_names_by_scope"]["PULL_REQUEST_MAIN"],
            ["QIKVRT CI", "QIKVRT repository evidence materialization"],
        )
        self.assertEqual(
            gatewatch["required_workflow_names_by_scope"]["PULL_REQUEST_STACKED"],
            ["QIKVRT CI"],
        )
        self.assertTrue(gatewatch["node_liveness"]["artifact_only_materialization"])
        self.assertEqual(
            prevention["observer_run_policy"],
            "CANCEL_SUPERSEDED_OBSERVER_ONLY",
        )
        node_policy = json.loads(NODE_POLICY.read_text(encoding="utf-8"))
        node_acceptance = node_policy["reflexive_watchdog_acceptance"]
        self.assertTrue(node_acceptance["required_for_authority_mirror_and_future_nodes"])
        self.assertEqual(node_acceptance["maximum_observation_interval"], "PT5M")
        self.assertEqual(node_acceptance["gatewatch_receipt_path"], "gatewatch-receipt.json")
        self.assertEqual(node_acceptance["trusted_gate_matrix"], "EXACT_HEAD_ARTIFACT_ONLY")

    def test_recent_single_writer_is_observed_without_overclaim(self) -> None:
        value = self.analyze(
            [run(1, WRITER_A, "in_progress", "2026-08-10T17:57:00Z", "2026-08-10T17:59:00Z")],
            jobs(1),
        )
        self.assertEqual(value["state"], "SAFE_PROGRESS")
        self.assertEqual(value["disposition"], "OBSERVE")
        self.assertFalse(value["completion_claims"]["DEADLOCK_FREEDOM_PROVED"])

    def test_second_active_writer_is_held_before_a_cycle_exists(self) -> None:
        value = self.analyze(
            [
                run(1, WRITER_A, "in_progress", "2026-08-10T17:58:00Z", "2026-08-10T17:59:00Z"),
                run(2, WRITER_B, "queued", "2026-08-10T17:59:00Z", "2026-08-10T17:59:00Z"),
            ],
            jobs(1, 2),
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_COMPETING_WRITERS")
        self.assertEqual(value["first_blocker"], "MORE_THAN_ONE_ACTIVE_REPOSITORY_WRITER")
        self.assertFalse(value["resource_graph"]["cycle_detected"])
        self.assertTrue(value["resource_graph"]["pre_cycle_conflict_detected"])

    def test_truncated_exact_head_run_page_is_a_fail_closed_hold(self) -> None:
        value = MODULE.analyze(
            {
                "total_count": 2,
                "workflow_runs": [
                    run(
                        91,
                        "QIKVRT CI",
                        "completed",
                        "2026-08-10T17:58:00Z",
                        "2026-08-10T17:59:00Z",
                        "success",
                    )
                ],
            },
            jobs(91),
            expected_head=HEAD,
            expected_tree=TREE,
            repository="example/qik-vrt",
            now=datetime(2026, 8, 10, 18, 0, tzinfo=timezone.utc),
            root=ROOT,
            authority_head=HEAD,
        )
        self.assertEqual(value["state"], "OBSERVATION_INCOMPLETE")
        self.assertEqual(value["disposition"], "HOLD")
        self.assertEqual(value["first_blocker"], "EXACT_HEAD_WORKFLOW_OBSERVATION_INCOMPLETE")
        self.assertFalse(value["observations"]["coverage"]["complete"])
        self.assertEqual(value["observations"]["coverage"]["total_run_count"], 2)

    def test_active_workflow_run_feedback_pair_is_not_quiescent(self) -> None:
        watchdog = "QIKVRT reflexive repository watchdog"
        live_status = "QIKVRT live status watch"
        runs = [
            run(
                101,
                watchdog,
                "queued",
                "2026-08-10T17:58:00Z",
                "2026-08-10T17:59:00Z",
                event="workflow_run",
            ),
            run(
                102,
                live_status,
                "queued",
                "2026-08-10T17:58:01Z",
                "2026-08-10T17:59:00Z",
                event="workflow_run",
            ),
        ]
        value = self.analyze(runs, {"jobs_by_run": {}})
        self.assertEqual(value["state"], "OBSERVATION_INCOMPLETE")
        self.assertEqual(value["first_blocker"], "OBSERVER_TRIGGER_TOPOLOGY_UNVERIFIED")
        self.assertFalse(value["resource_graph"]["cycle_detected"])

    def feedback_fixture(self, *, reciprocal=False, self_loop=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = pathlib.Path(directory.name)
        for source in (CONTRACT, NODE_POLICY, WORKFLOW, LIVE_STATUS_WORKFLOW):
            target = root / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        target = root / WORKFLOW.relative_to(ROOT)
        if reciprocal or self_loop:
            source_name = "QIKVRT reflexive repository watchdog" if self_loop else "QIKVRT live status watch"
            target.write_text(target.read_text().replace(
                "    workflows:\n", '    workflows:\n      - "' + source_name + '"\n', 1
            ))
        def git(*args):
            return subprocess.check_output(["git", "-C", str(root), *args], stderr=subprocess.DEVNULL).decode().strip()
        git("init", "-q")
        git("add", ".")
        git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "observer topology fixture")
        head, tree = git("rev-parse", "HEAD"), git("rev-parse", "HEAD^{tree}")
        runs = []
        for index, path in enumerate(MODULE.FEEDBACK_OBSERVER_PATHS):
            item = run(index + 1, ["QIKVRT reflexive repository watchdog", "QIKVRT live status watch"][index],
                       "in_progress", "2026-08-10T17:59:00Z", "2026-08-10T17:59:00Z", event="workflow_run")
            item.update(head_sha=head, path=path, workflow_id=100 + index)
            runs.append(item)
        return root, head, tree, runs

    def feedback_analyze(self, root, head, tree, runs):
        return MODULE.analyze(
            {"total_count": len(runs), "workflow_runs": runs}, jobs(1, 2),
            root=root, expected_head=head, expected_tree=tree, repository="example/qik-vrt",
            now=datetime(2026, 8, 10, 18, tzinfo=timezone.utc),
        )

    def test_common_ci_source_does_not_form_a_feedback_cycle(self):
        value = self.feedback_analyze(*self.feedback_fixture())
        graph = value["resource_graph"]["observer_trigger_graph"]
        self.assertEqual(graph["state"], "BOUND")
        self.assertEqual(len(graph["edges"]), 1)
        self.assertFalse(value["resource_graph"]["cycle_detected"])
        self.assertEqual(value["state"], "OBSERVER_ACTIVITY_OBSERVED")
        self.assertFalse(graph["executed_cycle_proven"])

    def test_reciprocal_committed_edges_hold_without_claiming_execution(self):
        value = self.feedback_analyze(*self.feedback_fixture(reciprocal=True))
        graph = value["resource_graph"]["observer_trigger_graph"]
        self.assertEqual(len(graph["edges"]), 2)
        self.assertTrue(graph["cycle_detected"])
        self.assertFalse(graph["executed_cycle_proven"])
        self.assertEqual(value["first_blocker"], "CONFIGURED_WORKFLOW_RUN_OBSERVER_FEEDBACK_CYCLE")

    def test_observer_display_name_does_not_create_productive_work(self):
        root, head, tree, runs = self.feedback_fixture()
        for item in runs:
            item["name"] = "projection for subject " + head
        value = self.feedback_analyze(root, head, tree, runs)
        self.assertEqual(value["resource_graph"]["observer_trigger_graph"]["state"], "BOUND")
        self.assertEqual(value["observations"]["active_productive_runs"], [])
        self.assertEqual(value["observations"]["active_observer_runs"], ["1", "2"])
        self.assertEqual(value["state"], "OBSERVER_ACTIVITY_OBSERVED")

    def test_self_trigger_is_a_configured_cycle(self):
        value = self.feedback_analyze(*self.feedback_fixture(self_loop=True))
        self.assertTrue(value["resource_graph"]["cycle_detected"])

    def test_dirty_worktree_cannot_replace_committed_topology(self):
        root, head, tree, runs = self.feedback_fixture()
        (root / MODULE.FEEDBACK_OBSERVER_PATHS[0]).write_text("invalid: [")
        value = self.feedback_analyze(root, head, tree, runs)
        self.assertEqual(value["resource_graph"]["observer_trigger_graph"]["state"], "BOUND")
        self.assertFalse(value["resource_graph"]["cycle_detected"])

    def test_missing_or_aliased_stable_id_holds_without_cycle_claim(self):
        for defect in ("missing", "alias", "path"):
            with self.subTest(defect=defect):
                root, head, tree, runs = self.feedback_fixture()
                if defect == "missing":
                    runs[0].pop("workflow_id")
                elif defect == "alias":
                    runs[0]["workflow_id"] = runs[1]["workflow_id"]
                else:
                    runs[0]["path"] = ".github/workflows/other.yml"
                value = self.feedback_analyze(root, head, tree, runs)
                self.assertEqual(value["first_blocker"], "OBSERVER_TRIGGER_TOPOLOGY_UNVERIFIED")
                self.assertFalse(value["resource_graph"]["cycle_detected"])

    def test_tree_drift_holds_without_cycle_claim(self):
        root, head, tree, runs = self.feedback_fixture()
        value = self.feedback_analyze(root, head, "f" * 40, runs)
        self.assertEqual(value["first_blocker"], "OBSERVER_TRIGGER_TOPOLOGY_UNVERIFIED")
        self.assertFalse(value["resource_graph"]["cycle_detected"])

    def test_stale_writer_lease_is_blocked_before_a_replacement_writer(self) -> None:
        value = self.analyze(
            [run(3, WRITER_A, "in_progress", "2026-08-10T17:20:00Z", "2026-08-10T17:30:00Z")],
            jobs(3),
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_STALE_WRITER_LEASE")
        self.assertEqual(value["productive_edge"], "REOBSERVE_STALE_WRITER_JOBS_STEPS_AND_RECEIPT")

    def test_unchanged_active_topology_crosses_the_progress_lease(self) -> None:
        runs = [run(4, "QIKVRT CI", "in_progress", "2026-08-10T17:43:00Z", "2026-08-10T17:44:00Z")]
        first = self.analyze(runs, jobs(4), now="2026-08-10T17:44:00Z")
        baseline = {
            "head_sha": HEAD,
            "tree_sha": TREE,
            "observed_at": "2026-08-10T17:44:00Z",
            "progress_fingerprint": first["progress_fingerprint"],
        }
        value = self.analyze(runs, jobs(4), now="2026-08-10T18:00:00Z", baseline=baseline)
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_NO_PROGRESS_TRANSITION")
        self.assertEqual(
            value["first_blocker"],
            "ACTIVE_TOPOLOGY_UNCHANGED_BEYOND_PROGRESS_LEASE",
        )

    def test_post_pr326_cancelled_observer_burst_requires_a_fresh_successor_receipt(self) -> None:
        observer = "QIKVRT reflexive repository watchdog"
        runs = [
            run(701, observer, "completed", "2026-08-11T13:39:35Z", "2026-08-11T13:39:38Z", "cancelled"),
            run(702, observer, "completed", "2026-08-11T13:39:38Z", "2026-08-11T13:39:55Z", "cancelled"),
            run(703, observer, "completed", "2026-08-11T13:39:55Z", "2026-08-11T13:40:39Z", "success"),
        ]
        job_value = {
            "jobs_by_run": {
                "701": [],
                "702": [],
                "703": [
                    {
                        "id": 7030,
                        "name": "exact-head-watchdog",
                        "status": "completed",
                        "conclusion": "success",
                    }
                ],
            }
        }
        fingerprint = MODULE.sha256_bytes(MODULE.canonical_json_bytes([]))
        coalesced = self.analyze(
            runs,
            job_value,
            now="2026-08-11T13:40:39Z",
            baseline={
                "head_sha": HEAD,
                "tree_sha": TREE,
                "observed_at": "2026-08-11T13:39:55Z",
                "progress_fingerprint": fingerprint,
            },
        )
        self.assertEqual(coalesced["state"], "QUIESCENT_OBSERVATION")
        self.assertEqual(coalesced["disposition"], "OBSERVE")
        self.assertIsNone(coalesced["first_blocker"])
        self.assertEqual(coalesced["observations"]["active_productive_runs"], [])
        self.assertEqual(coalesced["observations"]["waiting_productive_runs"], [])
        self.assertEqual(coalesced["observations"]["untrusted_terminal_runs"], [])

        starved = self.analyze(
            runs,
            job_value,
            now="2026-08-11T13:40:39Z",
            baseline={
                "head_sha": HEAD,
                "tree_sha": TREE,
                "observed_at": "2026-08-11T13:25:00Z",
                "progress_fingerprint": fingerprint,
            },
        )
        self.assertEqual(starved["state"], "PREEMPTIVE_HOLD_OBSERVATION_CADENCE_BREACH")
        self.assertEqual(
            starved["first_blocker"],
            "EXACT_HEAD_GATEWATCH_RECEIPT_EXCEEDED_FRESHNESS_BOUND",
        )

    def test_action_required_and_zero_job_terminal_runs_are_untrusted(self) -> None:
        value = self.analyze(
            [
                run(
                    5,
                    "QIKVRT CI",
                    "completed",
                    "2026-08-10T17:58:00Z",
                    "2026-08-10T17:59:00Z",
                    "action_required",
                )
            ],
            {"jobs_by_run": {"5": []}},
        )
        self.assertEqual(value["state"], "UNTRUSTED_EXECUTION_GAP")
        self.assertFalse(value["boundaries"]["action_required_is_trusted_execution"])
        self.assertFalse(value["boundaries"]["zero_job_is_trusted_execution"])

    def test_terminal_exact_head_gate_failure_is_held_with_job_evidence(self) -> None:
        value = self.analyze(
            [
                run(
                    6,
                    "QIKVRT CI",
                    "completed",
                    "2026-08-10T17:58:00Z",
                    "2026-08-10T17:59:00Z",
                    "failure",
                )
            ],
            {
                "jobs_by_run": {
                    "6": [
                        {
                            "id": 60,
                            "name": "failing job",
                            "status": "completed",
                            "conclusion": "failure",
                        }
                    ]
                }
            },
            scope="PULL_REQUEST_MAIN",
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_EXECUTED_GATE_FAILURE")
        self.assertEqual(value["first_blocker"], "TRUSTED_GATE_EXECUTED_FAILURE")
        gates = {gate["name"]: gate for gate in value["gatewatch"]["gates"]}
        self.assertEqual(gates["QIKVRT CI"]["state"], "FAILED")

    def test_missing_required_pull_request_gate_is_held_without_overclaiming_success(self) -> None:
        value = self.analyze(
            [
                run(
                    7,
                    "QIKVRT CI",
                    "completed",
                    "2026-08-10T17:58:00Z",
                    "2026-08-10T17:59:00Z",
                    "success",
                )
            ],
            {
                "jobs_by_run": {
                    "7": [
                        {
                            "id": 70,
                            "name": "verified job",
                            "status": "completed",
                            "conclusion": "success",
                        }
                    ]
                }
            },
            scope="PULL_REQUEST_MAIN",
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_REQUIRED_GATE_EVIDENCE")
        self.assertEqual(
            value["first_blocker"],
            "REQUIRED_TRUSTED_GATE_EVIDENCE_MISSING_OR_UNTRUSTED",
        )

    def test_stacked_pull_request_requires_only_gates_its_base_can_trigger(self) -> None:
        value = self.analyze(
            [
                run(
                    71,
                    "QIKVRT CI",
                    "completed",
                    "2026-08-10T17:58:00Z",
                    "2026-08-10T17:59:00Z",
                    "success",
                )
            ],
            {
                "jobs_by_run": {
                    "71": [
                        {
                            "id": 710,
                            "name": "verified job",
                            "status": "completed",
                            "conclusion": "success",
                        }
                    ]
                }
            },
            scope="PULL_REQUEST_STACKED",
        )
        gates = {gate["name"]: gate for gate in value["gatewatch"]["gates"]}
        self.assertEqual(value["gatewatch"]["required_workflow_names"], ["QIKVRT CI"])
        self.assertEqual(gates["QIKVRT CI"]["state"], "SUCCESS")
        self.assertEqual(gates["QIKVRT repository evidence materialization"]["state"], "NOT_OBSERVED")
        self.assertFalse(value["gatewatch"]["required_evidence_gaps"])

    def test_overdue_renewal_is_a_read_only_liveness_hold(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary) / "onboarding"
            self.write_liveness(directory, renewal_due="2026-08-10T17:59:00Z")
            value = self.analyze([], {"jobs_by_run": {}}, liveness_dir=directory)
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_NODE_LIVENESS")
        self.assertEqual(value["first_blocker"], "NODE_REGISTRATION_RENEWAL_OVERDUE")
        self.assertFalse(value["boundaries"]["liveness_record_observation_mutates_repository"])

    def test_expired_health_and_stale_seed_acceptance_are_reported_from_exact_records(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = pathlib.Path(temporary) / "onboarding"
            self.write_liveness(
                directory,
                acceptance_head="c" * 40,
                health_expiry="2026-08-10T17:59:00Z",
            )
            value = self.analyze([], {"jobs_by_run": {}}, liveness_dir=directory)
        liveness = value["gatewatch"]["node_liveness"]
        self.assertEqual(liveness["records"]["seed_acceptance"]["state"], "STALE")
        self.assertEqual(liveness["records"]["health"]["state"], "EXPIRED")
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_NODE_LIVENESS")

    def test_absent_node_liveness_records_are_not_misreported_on_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = self.analyze(
                [],
                {"jobs_by_run": {}},
                liveness_dir=pathlib.Path(temporary) / "absent-onboarding",
            )
        self.assertEqual(value["gatewatch"]["node_liveness"]["state"], "NOT_APPLICABLE")
        self.assertEqual(value["state"], "QUIESCENT_OBSERVATION")

    def test_old_same_head_receipt_detects_a_missed_gatewatch_tick(self) -> None:
        value = self.analyze(
            [],
            {"jobs_by_run": {}},
            baseline={
                "head_sha": HEAD,
                "tree_sha": TREE,
                "observed_at": "2026-08-10T17:40:00Z",
                "progress_fingerprint": MODULE.sha256_bytes(MODULE.canonical_json_bytes([])),
            },
        )
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_OBSERVATION_CADENCE_BREACH")
        self.assertEqual(
            value["first_blocker"], "EXACT_HEAD_GATEWATCH_RECEIPT_EXCEEDED_FRESHNESS_BOUND"
        )

    def test_stale_baseline_from_a_different_head_is_discarded(self) -> None:
        value = self.analyze(
            [],
            {"jobs_by_run": {}},
            baseline={
                "head_sha": "c" * 40,
                "tree_sha": TREE,
                "observed_at": "2026-08-10T17:40:00Z",
                "progress_fingerprint": MODULE.sha256_bytes(MODULE.canonical_json_bytes([])),
            },
        )
        self.assertFalse(value["baseline"]["same_head_and_tree"])
        self.assertEqual(value["state"], "QUIESCENT_OBSERVATION")

    def test_workflow_is_five_minute_reflexive_and_read_only(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        live_status_workflow = LIVE_STATUS_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cron: "*/5 * * * *"', workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("types: [completed]", workflow)
        self.assertNotIn('"QIKVRT live status watch"', workflow)
        self.assertIn("MAX_RUNS_PER_OBSERVATION: \"20\"", workflow)
        self.assertIn("EXACT_HEAD_WORKFLOW_OBSERVATION_INCOMPLETE", workflow)
        self.assertIn("observation-failure.json", workflow)
        self.assertIn("types: [completed]", live_status_workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("qikvrt_reflexive_repository_watchdog.py", workflow)
        self.assertIn("qikvrt-reflexive-repository-watchdog-", workflow)
        self.assertIn("QIKVRT CI", workflow)
        self.assertIn("QIKVRT repository evidence materialization", workflow)
        self.assertIn("observed-authority-main-head.txt", workflow)
        self.assertIn("gatewatch-receipt.json", workflow)
        self.assertIn("jq -r '.workflow_runs[].id'", workflow)
        self.assertIn("select(.id != $current and .conclusion == \"success\")", workflow)
        self.assertNotIn("select(.id != $current)][0]", workflow)
        self.assertNotIn(".workflow_runs[0:20]", workflow)
        self.assertNotIn("/dispatches", workflow)
        self.assertNotIn("gh pr merge", workflow)
        self.assertNotIn("issues/comments", workflow)


if __name__ == "__main__":
    unittest.main()
