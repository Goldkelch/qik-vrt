#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed contract tests for plan-only mesh replica orchestration."""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/MESH_REPLICA_ORCHESTRATION_CONTRACT_V1.json"
WORKFLOW_CONTRACT = ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
SOURCE = ROOT / "tools/qikvrt_mesh_replica_orchestrator.py"

SPEC = importlib.util.spec_from_file_location("qikvrt_mesh_replica_orchestrator", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def current_identity() -> tuple[str, str]:
    head = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD^{commit}"], text=True
    ).strip()
    tree = subprocess.check_output(
        ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD^{tree}"], text=True
    ).strip()
    return head, tree


class MeshReplicaOrchestrationTests(unittest.TestCase):
    def setUp(self) -> None:
        head, tree = current_identity()
        self.request = {
            "schema": "qikvrt_mesh_replica_request_v1",
            "request_id": "read-only-replica-plan-0001",
            "mode": "PLAN_VALIDATE_ONLY",
            "source": {
                "repository": "Goldkelch/qik-vrt",
                "ref": "main",
                "head_sha": head,
                "tree_sha": tree,
            },
            "target": {
                "kind": "LOCAL_ISOLATED_READ_ONLY",
                "identifier": "qikvrt-read-only-replica-0001",
            },
            "task": {
                "selector": "bounded-test-plan",
                "sha256": "a" * 64,
            },
            "resources": {
                "replica_count": 1,
                "ttl_seconds": 600,
                "disk_bytes": 1048576,
                "cpu_seconds": 60,
                "network_bytes": 0,
            },
            "synchronization": {
                "requested": False,
                "direction": "NONE",
                "path_allowlist": [],
            },
        }
        self.observation = {
            "schema": "qikvrt_mesh_replica_observation_v1",
            "authority": {
                "repository": "Goldkelch/qik-vrt",
                "head_sha": head,
                "tree_sha": tree,
            },
            "node_liveness": "FRESH_BOUND",
            "active_productive_writers": 0,
            "queued_productive_runs": 0,
            "planned_request_ids": [],
        }

    def plan(self, request: dict | None = None, observation: dict | None = None) -> dict:
        return MODULE.plan_replica(
            request if request is not None else self.request,
            observation if observation is not None else self.observation,
            ROOT,
        )

    def test_contract_is_plan_only_and_linked_from_existing_mesh_contract(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["schema"], "qikvrt_mesh_replica_orchestration_contract_v1")
        self.assertEqual(contract["mode"], "PLAN_VALIDATE_ONLY")
        self.assertEqual(contract["apply_mode"], "NOT_IMPLEMENTED")
        self.assertEqual(contract["execution_effect"], "NONE")
        self.assertTrue(contract["requires_exact_execution_authorization"])
        self.assertEqual(contract["resource_caps"]["max_parallel_read_only_replicas"], 4)
        self.assertIn("git_clone", contract["forbidden_operations"])
        workflow_contract = json.loads(WORKFLOW_CONTRACT.read_text(encoding="utf-8"))
        bridge = workflow_contract["replica_orchestration"]
        self.assertEqual(bridge["contract_path"], CONTRACT.relative_to(ROOT).as_posix())
        self.assertEqual(bridge["controller_path"], SOURCE.relative_to(ROOT).as_posix())
        self.assertEqual(bridge["mode"], "PLAN_VALIDATE_ONLY")

    def test_valid_request_remains_hold_until_a_separate_apply_contract_exists(self) -> None:
        result = self.plan()
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["first_blocker"], "APPLY_MODE_NOT_IMPLEMENTED")
        self.assertEqual(result["execution_effect"], "NONE")
        self.assertEqual(result["permitted_actions"], [])
        self.assertEqual(result["authority_snapshot"]["head_sha"], self.request["source"]["head_sha"])
        self.assertRegex(result["request_sha256"], r"^[0-9a-f]{64}$")

    def test_source_drift_active_writer_unfresh_liveness_and_duplicate_hold(self) -> None:
        stale = copy.deepcopy(self.request)
        stale["source"]["head_sha"] = "0" * 40
        self.assertEqual(self.plan(stale)["first_blocker"], "SOURCE_HEAD_TREE_DRIFT")

        active = copy.deepcopy(self.observation)
        active["active_productive_writers"] = 1
        self.assertEqual(self.plan(observation=active)["first_blocker"], "COMPETING_PRODUCTIVE_WRITER")

        stale_liveness = copy.deepcopy(self.observation)
        stale_liveness["node_liveness"] = "STALE"
        self.assertEqual(self.plan(observation=stale_liveness)["first_blocker"], "MESH_NODE_LIVENESS_UNVERIFIED")

        duplicate = copy.deepcopy(self.observation)
        duplicate["planned_request_ids"] = [self.request["request_id"]]
        result = self.plan(observation=duplicate)
        self.assertEqual(result["state"], "NOOP")
        self.assertEqual(result["first_blocker"], "DUPLICATE_EXACT_REQUEST")

    def test_remote_target_sync_request_and_quota_breach_never_become_execution(self) -> None:
        remote = copy.deepcopy(self.request)
        remote["target"]["kind"] = "REMOTE_REPOSITORY"
        self.assertEqual(self.plan(remote)["first_blocker"], "REMOTE_TARGET_NOT_AUTHORIZED")

        sync = copy.deepcopy(self.request)
        sync["synchronization"] = {
            "requested": True,
            "direction": "AUTHORITY_TO_MIRROR",
            "path_allowlist": ["docs/"],
        }
        self.assertEqual(self.plan(sync)["first_blocker"], "SYNCHRONIZATION_REQUIRES_SEPARATE_AUTHORIZATION")

        over_quota = copy.deepcopy(self.request)
        over_quota["resources"]["replica_count"] = 5
        self.assertEqual(self.plan(over_quota)["first_blocker"], "RESOURCE_CAP_EXCEEDED")

    def test_missing_required_binding_is_a_hold_not_an_execution(self) -> None:
        missing = copy.deepcopy(self.request)
        del missing["task"]["sha256"]
        result = self.plan(missing)
        self.assertEqual(result["state"], "HOLD")
        self.assertEqual(result["first_blocker"], "REQUEST_INVALID")
        self.assertIn("task.sha256", result["detail"])

    def test_cli_fails_closed_before_reading_inputs_when_expected_head_drifts(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SOURCE),
                "plan",
                "--request",
                "missing-request.json",
                "--observation",
                "missing-observation.json",
                "--expect-head",
                "0" * 40,
            ],
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertEqual(completed.stdout, "")
        self.assertIn("EXACT_HEAD_DRIFT", completed.stderr)

    def test_controller_has_no_clone_fork_push_or_network_execution_surface(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertEqual(source.count("subprocess.run("), 1)
        self.assertIn('["git", "-C", str(root), *arguments]', source)
        self.assertEqual(source.count('_git(root, "rev-parse"'), 2)
        for forbidden in (
            "git clone",
            "git push",
            "git fetch",
            "urllib.request",
            "requests.",
            "/forks",
            "create_repository",
            "create_branch",
            "subprocess.call",
            "subprocess.Popen",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
