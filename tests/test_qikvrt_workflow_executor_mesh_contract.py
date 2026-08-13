# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
SELF_HEALING_CONTRACT = ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json"
NODE_POLICY = ROOT / "registry/NODE_DISCOVERY_POLICY.json"
EXECUTOR_WORKFLOW = ROOT / ".github/workflows/qikvrt_workflow_executor.yml"
WATCHDOG_WORKFLOW = ROOT / ".github/workflows/qikvrt_workflow_executor_watchdog.yml"
LIVE_WATCH = ROOT / ".github/workflows/qikvrt_live_status_watch.yml"

SPEC = importlib.util.spec_from_file_location(
    "qikvrt_workflow_executor",
    ROOT / "tools/qikvrt_workflow_executor.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class WorkflowExecutorMeshContractTests(unittest.TestCase):
    @staticmethod
    def work_item(
        work_id: str,
        path: str,
        *,
        lane: str = "AUTHORITY_CANDIDATE",
        state: str = "READY",
        dependencies: list[str] | None = None,
        epoch: int = 1,
    ) -> dict[str, object]:
        return {
            "id": work_id,
            "lane": lane,
            "state": state,
            "changed_paths": [path, "REPOSITORY_FILE_MANIFEST.json"],
            "dependencies": dependencies or [],
            "last_progress_epoch": epoch,
            "state_signature": hashlib.sha256(work_id.encode("utf-8")).hexdigest(),
        }

    def test_contract_is_authority_first_and_effect_bounded(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(contract["schema"], "qikvrt_workflow_executor_mesh_contract_v1")
        self.assertEqual(contract["authority"]["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(contract["authority"]["entrypoint"], "AI")
        self.assertEqual(
            contract["executor"]["single_writer_order"],
            ["AUTHORITY", "MIRROR", "MESH_NODE"],
        )
        self.assertEqual(
            contract["executor"]["orchestration_mode"],
            "ACYCLIC_LEASED_CONFLICT_COMPONENTS",
        )
        self.assertEqual(contract["executor"]["maximum_parallel_independent_candidates"], 4)
        orchestration = contract["orchestration"]
        self.assertEqual(orchestration["scope"], "EVERY_WORKFLOW_IN_EXACT_TREE")
        topology = orchestration["topology"]
        self.assertTrue(topology["every_workflow_requires_concurrency"])
        self.assertTrue(topology["every_job_requires_timeout_minutes"])
        self.assertTrue(topology["job_needs_graph_must_be_acyclic"])
        self.assertTrue(topology["workflow_run_graph_must_be_acyclic"])
        self.assertEqual(topology["undeclared_shared_concurrency_group"], "BLOCK")
        self.assertEqual(len(topology["shared_serial_lanes"]), 3)
        work_queue = orchestration["work_queue"]
        self.assertFalse(work_queue["blocked_candidate_stalls_independent_component"])
        self.assertFalse(work_queue["hold_lease_while_waiting"])
        self.assertEqual(
            work_queue["dependency_cycle_policy"],
            "REJECT_CYCLE_AND_CONTINUE_INDEPENDENT_COMPONENTS",
        )
        self.assertEqual(
            contract["dispatch_policy"]["authorized_workflows"],
            [
                {
                    "workflow_id": "qikvrt_workflow_executor_watchdog.yml",
                    "workflow_path": ".github/workflows/qikvrt_workflow_executor_watchdog.yml",
                    "workflow_name": "QIKVRT workflow executor watchdog",
                    "allowed_events": ["workflow_dispatch"],
                    "external_effect": "NONE",
                    "is_writer": False,
                    "required_artifact_prefix": "qikvrt-workflow-executor-watchdog-",
                }
            ],
        )
        boundaries = contract["boundaries"]
        self.assertEqual(boundaries["direct_repository_mutation"], "FORBIDDEN")
        self.assertFalse(boundaries["watchdog_terminality_is_gate_success"])
        self.assertFalse(boundaries["action_required_is_trusted_execution"])
        self.assertFalse(boundaries["zero_job_is_trusted_execution"])
        continuity = contract["mesh_node_split_acceptance"]
        self.assertEqual(continuity["applies_to"], "EVERY_FUTURE_NODE_ADDED_BY_QUEUE_ROW")
        self.assertEqual(
            continuity["required_acceptance_tests"],
            [
                "tests/test_qikvrt_workflow_executor_mesh_contract.py",
                "tests/test_seed_workflows.py",
            ],
        )
        self.assertEqual(
            continuity["connection_order"],
            [
                "AUTHORITY_CONTRACT_BOUND",
                "NODE_RECEIPT_DECLARED",
                "NODE_STRUCTURAL_ACCEPTANCE",
                "SEED_QUEUE_ACCEPTANCE",
                "WATCHDOG_OBSERVATION",
            ],
        )

    def test_self_healing_and_node_policy_point_to_the_same_continuity_contract(self) -> None:
        self_healing = json.loads(SELF_HEALING_CONTRACT.read_text(encoding="utf-8"))
        bridge = self_healing["workflow_executor_mesh_continuity"]
        self.assertEqual(bridge["contract_path"], CONTRACT.relative_to(ROOT).as_posix())
        self.assertEqual(bridge["controller_path"], "tools/qikvrt_workflow_executor.py")
        self.assertEqual(bridge["external_effect"], "FORBIDDEN")
        policy = json.loads(NODE_POLICY.read_text(encoding="utf-8"))
        future = policy["future_node_split_acceptance"]
        self.assertTrue(policy["future_nodes_added_by_queue_rows"])
        self.assertTrue(future["required_for_queue_rows"])
        self.assertEqual(future["contract_path"], CONTRACT.relative_to(ROOT).as_posix())
        self.assertEqual(
            future["acceptance_test_path"],
            "tests/test_qikvrt_workflow_executor_mesh_contract.py",
        )

    def test_snapshot_binds_every_workflow_to_the_exact_head_and_tree(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        head = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD^{commit}"],
            text=True,
        ).strip()
        tree = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD^{tree}"],
            text=True,
        ).strip()
        self.assertEqual(snapshot["head_sha"], head)
        self.assertEqual(snapshot["tree_sha"], tree)
        self.assertRegex(snapshot["workflow_inventory_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(snapshot["workflow_topology_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(snapshot["workflow_topology"]["state"], "ACYCLIC_BOUNDED")
        self.assertEqual(
            snapshot["workflow_topology"]["workflow_count"],
            len(snapshot["workflow_inventory"]),
        )
        self.assertGreaterEqual(
            snapshot["workflow_topology"]["job_count"],
            snapshot["workflow_topology"]["workflow_count"],
        )
        self.assertEqual(snapshot["workflow_topology"]["shared_serial_lane_count"], 3)
        paths = {entry["path"] for entry in snapshot["workflow_inventory"]}
        self.assertIn(".github/workflows/qikvrt_workflow_executor.yml", paths)
        self.assertIn(".github/workflows/qikvrt_workflow_executor_watchdog.yml", paths)
        self.assertEqual(snapshot["workflow_delta"]["state"], "BASELINE_UNAVAILABLE")
        baseline = {"workflow_inventory": [{"path": path, "blob_sha": "0" * 40} for path in paths]}
        delta = MODULE.workflow_delta(snapshot["workflow_inventory"], baseline)
        self.assertEqual(delta["state"], "COMPARED")
        self.assertEqual(delta["added"], [])
        self.assertEqual(delta["removed"], [])
        self.assertEqual(sorted(delta["changed"]), sorted(paths))

    def test_plan_is_exact_head_deduplicated_and_writer_serialized(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        empty_plan = MODULE.dispatch_plan(snapshot, {"workflow_runs": []}, "main")
        candidate = empty_plan["candidates"][0]
        self.assertEqual(empty_plan["state"], "DISPATCH_CANDIDATE_READY")
        self.assertEqual(candidate["disposition"], "DISPATCH")
        self.assertEqual(candidate["head_sha"], snapshot["head_sha"])
        self.assertEqual(candidate["tree_sha"], snapshot["tree_sha"])
        self.assertRegex(candidate["workflow_blob_sha"], r"^[0-9a-f]{40}$")

        terminal = MODULE.dispatch_plan(
            snapshot,
            {
                "workflow_runs": [
                    {
                        "id": 7,
                        "name": "QIKVRT workflow executor watchdog",
                        "head_sha": snapshot["head_sha"],
                        "status": "completed",
                        "conclusion": "action_required",
                    }
                ]
            },
            "main",
        )
        self.assertEqual(terminal["candidates"][0]["disposition"], "HOLD")
        self.assertEqual(
            terminal["candidates"][0]["first_blocker"],
            "EQUIVALENT_EXACT_HEAD_RUN_REQUIRES_JOB_EVIDENCE",
        )
        writer = MODULE.dispatch_plan(
            snapshot,
            {
                "workflow_runs": [
                    {
                        "id": 8,
                        "name": "QIK-VRT autonomous bounded self-heal",
                        "head_sha": snapshot["head_sha"],
                        "status": "in_progress",
                    }
                ]
            },
            "main",
        )
        self.assertEqual(writer["candidates"][0]["first_blocker"], "COMPETING_WRITER_ACTIVE")

    def test_topology_audit_rejects_each_deadlock_primitive(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        records = [
            MODULE._parse_workflow(path.relative_to(ROOT).as_posix(), path.read_bytes())
            for path in sorted((ROOT / ".github/workflows").glob("*.y*ml"))
        ]
        topology = MODULE._workflow_topology_from_records(records, contract)
        self.assertEqual(topology["state"], "ACYCLIC_BOUNDED")

        missing_concurrency = copy.deepcopy(records)
        missing_concurrency[0]["concurrency_group"] = None
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "no concurrency group"):
            MODULE._workflow_topology_from_records(missing_concurrency, contract)

        missing_timeout = copy.deepcopy(records)
        first_job = next(iter(missing_timeout[0]["jobs"]))
        missing_timeout[0]["jobs"][first_job]["timeout_minutes"] = None
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "no timeout-minutes"):
            MODULE._workflow_topology_from_records(missing_timeout, contract)

        job_cycle = copy.deepcopy(records)
        two_job_workflow = next(item for item in job_cycle if len(item["jobs"]) >= 2)
        left, right = list(two_job_workflow["jobs"])[:2]
        two_job_workflow["jobs"][left]["needs"] = [right]
        two_job_workflow["jobs"][right]["needs"] = [left]
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "job dependency cycle"):
            MODULE._workflow_topology_from_records(job_cycle, contract)

        run_cycle = copy.deepcopy(records)
        run_cycle[0]["workflow_run_upstreams"] = [run_cycle[1]["name"]]
        run_cycle[1]["workflow_run_upstreams"] = [run_cycle[0]["name"]]
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "workflow_run cycle"):
            MODULE._workflow_topology_from_records(run_cycle, contract)

        shared_group = copy.deepcopy(records)
        shared_group[0]["concurrency_group"] = "undeclared-shared-group"
        shared_group[1]["concurrency_group"] = "undeclared-shared-group"
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "undeclared shared concurrency group"):
            MODULE._workflow_topology_from_records(shared_group, contract)

    def test_work_queue_runs_path_disjoint_candidates_in_parallel(self) -> None:
        left = self.work_item("pr:10", "src/left.py", epoch=5)
        right = self.work_item("pr:11", "src/right.py", epoch=6)
        plan = MODULE.work_queue_plan({"work_items": [left, right], "leases": []}, 100, ROOT)
        self.assertEqual(plan["state"], "RUNNABLE_COMPONENTS_READY")
        self.assertEqual(plan["selected_ids"], ["pr:10", "pr:11"])
        self.assertEqual(len(plan["recommended_leases"]), 2)

    def test_work_queue_serializes_semantic_overlap_but_ignores_generated_overlap(self) -> None:
        first = self.work_item("pr:20", "src/shared.py", epoch=5)
        second = self.work_item("pr:21", "src/shared.py", epoch=6)
        plan = MODULE.work_queue_plan({"work_items": [second, first], "leases": []}, 100, ROOT)
        self.assertEqual(plan["selected_ids"], ["pr:20"])
        disposition = {item["id"]: item for item in plan["dispositions"]}
        self.assertEqual(disposition["pr:21"]["first_blocker"], "SELECTED_CONFLICT_COMPONENT")

    def test_dependency_cycle_does_not_stall_an_independent_component(self) -> None:
        left = self.work_item("cycle:a", "src/a.py", dependencies=["cycle:b"])
        right = self.work_item("cycle:b", "src/b.py", dependencies=["cycle:a"])
        independent = self.work_item("pr:free", "src/free.py")
        plan = MODULE.work_queue_plan(
            {"work_items": [left, right, independent], "leases": []},
            100,
            ROOT,
        )
        self.assertEqual(plan["cycle_nodes"], ["cycle:a", "cycle:b"])
        self.assertEqual(plan["selected_ids"], ["pr:free"])
        disposition = {item["id"]: item for item in plan["dispositions"]}
        self.assertEqual(disposition["cycle:a"]["first_blocker"], "DEPENDENCY_CYCLE")

    def test_finite_lease_blocks_only_its_conflict_component(self) -> None:
        owner = self.work_item("owner", "src/leased.py", state="RUNNING")
        blocked = self.work_item("blocked", "src/leased.py")
        independent = self.work_item("independent", "src/free.py")
        lease = {
            "id": "lease:owner",
            "owner_id": "owner",
            "conflict_paths": owner["changed_paths"],
            "acquired_epoch": 90,
            "expires_epoch": 110,
            "generation": 1,
            "state_signature": owner["state_signature"],
        }
        plan = MODULE.work_queue_plan(
            {"work_items": [owner, blocked, independent], "leases": [lease]},
            100,
            ROOT,
        )
        self.assertEqual(plan["selected_ids"], ["independent"])
        disposition = {item["id"]: item for item in plan["dispositions"]}
        self.assertEqual(disposition["blocked"]["first_blocker"], "ACTIVE_CONFLICT_LEASE")
        expired = copy.deepcopy(lease)
        expired.update({"acquired_epoch": 70, "expires_epoch": 80})
        expired_plan = MODULE.work_queue_plan(
            {"work_items": [owner, blocked], "leases": [expired]},
            100,
            ROOT,
        )
        self.assertEqual(expired_plan["expired_lease_ids"], ["lease:owner"])
        self.assertEqual(expired_plan["selected_ids"], ["blocked"])

    def test_unchanged_renewal_and_hold_while_waiting_are_quarantined(self) -> None:
        owner = self.work_item("owner", "src/leased.py", state="RUNNING")
        waiting = self.work_item("waiting", "src/waiting.py", state="WAITING")
        independent = self.work_item("independent", "src/free.py")
        lease = {
            "id": "lease:owner",
            "owner_id": "owner",
            "conflict_paths": owner["changed_paths"],
            "acquired_epoch": 90,
            "expires_epoch": 110,
            "generation": 2,
            "state_signature": owner["state_signature"],
            "renewed_from_state_signature": owner["state_signature"],
        }
        waiting_lease = {
            "id": "lease:waiting",
            "owner_id": "waiting",
            "conflict_paths": waiting["changed_paths"],
            "acquired_epoch": 90,
            "expires_epoch": 110,
            "generation": 1,
            "state_signature": waiting["state_signature"],
        }
        plan = MODULE.work_queue_plan(
            {
                "work_items": [owner, waiting, independent],
                "leases": [lease, waiting_lease],
            },
            100,
            ROOT,
        )
        self.assertEqual(plan["selected_ids"], ["independent"])
        disposition = {item["id"]: item for item in plan["dispositions"]}
        self.assertEqual(
            disposition["owner"]["first_blocker"],
            "LEASE_RENEWAL_WITHOUT_PROGRESS",
        )
        self.assertEqual(
            disposition["waiting"]["first_blocker"],
            "ACTIVE_LEASE_WITHOUT_RUNNING_OWNER",
        )

    def test_mirror_work_requires_a_completed_authority_dependency(self) -> None:
        authority = self.work_item(
            "authority",
            "src/authority.py",
            lane="AUTHORITY_PROMOTION",
            state="COMPLETED",
        )
        mirror = self.work_item(
            "mirror",
            "src/mirror.py",
            lane="MIRROR_PORT",
            dependencies=["authority"],
        )
        orphan = self.work_item("orphan", "src/orphan.py", lane="MIRROR_PORT")
        plan = MODULE.work_queue_plan(
            {"work_items": [authority, mirror, orphan], "leases": []},
            100,
            ROOT,
        )
        self.assertEqual(plan["selected_ids"], ["mirror"])
        disposition = {item["id"]: item for item in plan["dispositions"]}
        self.assertEqual(
            disposition["orphan"]["first_blocker"],
            "COMPLETED_AUTHORITY_DEPENDENCY_REQUIRED",
        )

    def test_node_receipt_requires_the_declared_acceptance_order(self) -> None:
        receipt = MODULE.build_node_receipt("example/node", "main", ROOT)
        validation = MODULE.validate_node_receipt(receipt, "example/node", "main", ROOT)
        self.assertEqual(validation["state"], "NODE_SPLIT_CONTINUITY_ACCEPTANCE_READY")
        declaration = {
            "workflow_executor_continuity": {
                "schema": "qikvrt_workflow_executor_mesh_continuity_declaration_v1",
                "receipt_path": "state/autonomy/WORKFLOW_EXECUTOR_MESH_NODE_RECEIPT_V1.json",
                "receipt_url": MODULE.expected_node_receipt_url("example/node", "main"),
                "acceptance_required": True,
            }
        }
        self.assertEqual(
            MODULE.validate_node_continuity_declaration(declaration, "example/node", "main"),
            declaration["workflow_executor_continuity"]["receipt_url"],
        )
        damaged = copy.deepcopy(receipt)
        damaged["acceptance"]["required_tests"] = []
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "acceptance tests"):
            MODULE.validate_node_receipt(damaged, "example/node", "main", ROOT)

    def test_executor_and_watchdogs_cannot_cross_the_effect_boundary(self) -> None:
        executor = EXECUTOR_WORKFLOW.read_text(encoding="utf-8")
        watchdog = WATCHDOG_WORKFLOW.read_text(encoding="utf-8")
        live_watch = LIVE_WATCH.read_text(encoding="utf-8")
        self.assertIn("actions: write", executor)
        self.assertIn("qikvrt_workflow_executor.py", executor)
        self.assertIn("/dispatches", executor)
        self.assertIn("test \"$refreshed_head\" = \"$head\"", executor)
        self.assertNotIn("gh pr merge", executor)
        self.assertNotIn("zenodo", executor.casefold())
        self.assertNotIn("ietf", executor.casefold())
        self.assertIn("contents: read", watchdog)
        self.assertIn("tests.test_qikvrt_workflow_executor_mesh_contract", watchdog)
        self.assertIn("qikvrt-workflow-executor-watchdog-", watchdog)
        self.assertNotIn("/dispatches", watchdog)
        self.assertIn("github.event_name == 'pull_request'", live_watch)

    def test_watchdog_binds_the_literal_pull_request_head(self) -> None:
        watchdog = WATCHDOG_WORKFLOW.read_text(encoding="utf-8")
        exact_event_head = "${{ github.event.pull_request.head.sha || github.sha }}"
        self.assertIn(f"ref: {exact_event_head}", watchdog)
        self.assertIn(f"EXPECTED_HEAD: {exact_event_head}", watchdog)
        self.assertIn('test "$head" = "$EXPECTED_HEAD"', watchdog)
        self.assertIn('snapshot --expect-head "$EXPECTED_HEAD"', watchdog)
        self.assertNotIn('snapshot --expect-head "$head"', watchdog)


if __name__ == "__main__":
    unittest.main()
