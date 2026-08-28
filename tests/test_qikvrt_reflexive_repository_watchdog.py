# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
NODE_POLICY = ROOT / "registry/NODE_DISCOVERY_POLICY.json"
WORKFLOW = ROOT / ".github/workflows/qikvrt_reflexive_repository_watchdog.yml"

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
) -> dict[str, object]:
    return {
        "id": run_id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "event": "workflow_dispatch",
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
        self.assertEqual(
            prevention["observation_cadence"],
            "EVENT_DRIVEN_NO_PERIODIC_POLLING",
        )
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
        self.assertEqual(
            node_acceptance["maximum_observation_interval"],
            "EVENT_DRIVEN_SOURCE_FRESHNESS_BOUND",
        )
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

    def test_workflow_is_event_driven_non_polling_and_read_only(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("cron:", workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("types: [requested, in_progress, completed]", workflow)
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
