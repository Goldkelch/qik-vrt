# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
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
        )

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
        self.assertEqual(
            prevention["observer_run_policy"],
            "CANCEL_SUPERSEDED_OBSERVER_ONLY",
        )
        node_policy = json.loads(NODE_POLICY.read_text(encoding="utf-8"))
        node_acceptance = node_policy["reflexive_watchdog_acceptance"]
        self.assertTrue(node_acceptance["required_for_authority_mirror_and_future_nodes"])
        self.assertEqual(node_acceptance["maximum_observation_interval"], "PT5M")

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
            "observed_at": "2026-08-10T17:44:00Z",
            "progress_fingerprint": first["progress_fingerprint"],
        }
        value = self.analyze(runs, jobs(4), now="2026-08-10T18:00:00Z", baseline=baseline)
        self.assertEqual(value["state"], "PREEMPTIVE_HOLD_NO_PROGRESS_TRANSITION")
        self.assertEqual(
            value["first_blocker"],
            "ACTIVE_TOPOLOGY_UNCHANGED_BEYOND_PROGRESS_LEASE",
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

    def test_workflow_is_five_minute_reflexive_and_read_only(self) -> None:
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('cron: "*/5 * * * *"', workflow)
        self.assertIn("workflow_run:", workflow)
        self.assertIn("types: [requested, in_progress, completed]", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("qikvrt_reflexive_repository_watchdog.py", workflow)
        self.assertIn("qikvrt-reflexive-repository-watchdog-", workflow)
        self.assertNotIn("/dispatches", workflow)
        self.assertNotIn("gh pr merge", workflow)
        self.assertNotIn("issues/comments", workflow)


if __name__ == "__main__":
    unittest.main()
