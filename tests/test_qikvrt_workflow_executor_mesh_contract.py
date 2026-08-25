# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
REVIEW_POLICY = ROOT / "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
REVIEW_DOC = ROOT / "docs/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE.md"
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

    def test_mesh_self_review_feedback_plane_is_exact_role_local_and_single_writer(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        plane = contract["review_feedback_plane"]
        self.assertTrue(plane["enabled"])
        self.assertEqual(plane["mode"], "ROLE_LOCAL_REPOSITORY_NATIVE_MESH_SELF_REVIEW")

        executor = plane["executor"]
        self.assertEqual(executor["workflow_name"], "QIKVRT requested review executor")
        self.assertFalse(executor["human_review_request_prerequisite"])
        self.assertEqual(executor["platform_review_event"], "COMMENT")
        self.assertEqual(executor["bot_approve_or_request_changes_event"], "FORBIDDEN")

        binding = plane["exact_subject_binding"]
        self.assertEqual(
            binding["required_fields"],
            [
                "REPOSITORY_ROLE",
                "PULL_REQUEST_NUMBER",
                "TRUSTED_EVALUATOR_AND_WORKFLOW_BLOB_SHA",
                "OPEN_INTERNAL_MAIN_BASED_ELIGIBILITY_AND_DRAFT_STATE",
                "PULL_REQUEST_TITLE_AND_BODY_SHA256",
                "BASE_SHA",
                "BASE_TREE_SHA",
                "HEAD_SHA",
                "HEAD_TREE_SHA",
                "SORTED_REVIEWED_SCOPE",
                "SCOPE_SHA256",
                "DIFF_SHA256",
                "DISCUSSION_ITEM_IDS_TIMESTAMPS_AND_BODY_SHA256",
                "REQUIRED_GATE_WORKFLOW_ID_PATH_EVENT_AND_POSITIVE_JOB_COUNT",
                "ACTIVE_WRITER_QUEUE_STATE",
            ],
        )
        self.assertEqual(binding["review_fingerprint_algorithm"], "SHA256")
        self.assertEqual(
            binding["review_fingerprint_input"],
            "CANONICAL_JSON_OF_EXACT_SUBJECT_AND_CAUSAL_EVIDENCE_BINDING",
        )
        self.assertEqual(binding["subject_drift_disposition"], "HOLD_UNVERIFIED")
        self.assertEqual(binding["predecessor_evidence_transfer"], "FORBIDDEN")
        self.assertEqual(
            binding["same_fingerprint_requires"],
            "BYTE_IDENTICAL_RECEIPT_AND_DIFF",
        )

        ledger = plane["ledger"]
        self.assertTrue(ledger["role_local"])
        self.assertTrue(ledger["append_only"])
        self.assertEqual(
            ledger["initialization"],
            "ORPHAN_ROOT_COMMIT_WITH_FIRST_EXACT_RECEIPT",
        )
        self.assertEqual(ledger["ref"], "refs/heads/qikvrt/mesh-review-ledger-v1")
        self.assertEqual(
            ledger["receipt_path_template"],
            "state/mesh/reviews/pr-<N>/<head>/<fingerprint>.json",
        )
        self.assertEqual(
            ledger["diff_path_template"],
            "state/mesh/reviews/pr-<N>/<head>/<fingerprint>.diff",
        )
        transport = ledger["diff_transport"]
        self.assertEqual(
            transport["current_format"],
            "qikvrt_mesh_review_diff_manifest_v1",
        )
        self.assertTrue(transport["legacy_raw_diff_requires_absent_format_marker"])
        self.assertEqual(transport["chunk_bytes"], 1_048_576)
        self.assertEqual(transport["max_chunks"], 64)
        self.assertEqual(transport["max_diff_bytes"], 67_108_864)
        self.assertTrue(transport["manifest_validation_before_chunk_fetch"])
        self.assertTrue(transport["canonical_json_and_exact_integer_fields"])
        self.assertTrue(transport["per_chunk_and_full_diff_sha256"])
        self.assertEqual(ledger["write_protocol"], "FAST_FORWARD_COMPARE_AND_SWAP_ONLY")
        self.assertEqual(ledger["candidate_branch_write"], "FORBIDDEN")
        self.assertEqual(ledger["main_branch_write"], "FORBIDDEN")
        self.assertEqual(ledger["single_writer_workflow_name"], executor["workflow_name"])
        self.assertFalse(ledger["ledger_push_triggers_candidate_ci"])
        self.assertEqual(
            contract["dispatch_policy"]["writer_workflow_names"].count(
                ledger["single_writer_workflow_name"]
            ),
            1,
        )

    def test_mesh_self_review_projects_one_fail_closed_d0_action_without_authority_transfer(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        plane = contract["review_feedback_plane"]
        projections = plane["projections"]
        self.assertEqual(
            projections["canonical_source"],
            "ROLE_LOCAL_LEDGER_RECEIPT_AND_REVIEW_DIFF",
        )
        self.assertEqual(projections["actions_artifact"], "EXACT_RECEIPT_AND_DIFF_PROJECTION")
        self.assertTrue(projections["actions_artifact_includes_hidden_evidence_root"])
        self.assertEqual(projections["status_context"], "QIKVRT requested review execution")
        self.assertEqual(projections["status_deduplication"], "LATEST_CONTEXT_STATUS_ONLY")
        self.assertEqual(projections["pull_request_review_event"], "COMMENT")
        self.assertEqual(projections["platform_review_state"], "COMMENTED")
        self.assertFalse(projections["candidate_mutation"])
        self.assertFalse(projections["independent_code_owner_authority"])

        downstream = plane["downstream_feedback"]
        self.assertTrue(downstream["persist_before_signal"])
        self.assertTrue(downstream["exactly_one_derived_next_action"])
        self.assertEqual(downstream["new_parallel_action_router"], "FORBIDDEN")
        self.assertFalse(downstream["status_alone_authorizes_continuation"])
        self.assertTrue(downstream["promotion_reobserves_ledger_receipt_and_diff"])
        self.assertEqual(
            downstream["signals"],
            ["WORKFLOW_RUN_COMPLETED", "EXACT_HEAD_STATUS_TRANSITION"],
        )
        self.assertEqual(
            downstream["consumer_workflows"],
            [
                ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml",
                ".github/workflows/qikvrt_expected_head_promotion.yml",
            ],
        )

        self.assertEqual(
            {key: value["state"] for key, value in plane["d0_mapping"].items()},
            {"0": "NOOP", "1": "HOLD", "2": "REOBSERVE", "3": "REQUEST_AUTHORITY"},
        )
        self.assertFalse(
            plane["authority_boundary"][
                "automated_mesh_review_is_independent_code_owner_review"
            ]
        )
        self.assertEqual(
            plane["authority_boundary"]["independent_code_owner_gate"],
            "SEPARATE_EXACT_HEAD_PREREQUISITE",
        )
        self.assertTrue(all(value is False for value in plane["completion_claims"].values()))

    def test_review_policy_and_human_contract_match_the_mesh_feedback_contract(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        policy = json.loads(REVIEW_POLICY.read_text(encoding="utf-8"))
        plane = contract["review_feedback_plane"]
        policy_plane = policy["mesh_self_review_feedback_plane"]

        self.assertFalse(policy["review_lifecycle"]["human_review_request_prerequisite"])
        self.assertFalse(policy["review_executor"]["human_review_request_required"])
        self.assertEqual(
            policy["mesh_self_review_owner_delegation"],
            "state/authorization/delegations/OWNER_MESH_REPOSITORY_SELF_REVIEW_FEEDBACK_V1.json",
        )
        self.assertEqual(policy_plane["receipt_ledger"]["ref"], plane["ledger"]["ref"])
        self.assertEqual(
            policy_plane["receipt_ledger"]["receipt_path_template"],
            plane["ledger"]["receipt_path_template"],
        )
        self.assertEqual(
            policy_plane["receipt_ledger"]["diff_path_template"],
            plane["ledger"]["diff_path_template"],
        )
        self.assertEqual(
            policy_plane["receipt_ledger"]["diff_transport"],
            plane["ledger"]["diff_transport"],
        )
        self.assertEqual(
            {key: value["state"] for key, value in policy_plane["d0_mapping"].items()},
            {key: value["state"] for key, value in plane["d0_mapping"].items()},
        )
        self.assertTrue(all(value is False for value in policy_plane["completion_claims"].values()))

        documentation = REVIEW_DOC.read_text(encoding="utf-8")
        self.assertIn("refs/heads/qikvrt/mesh-review-ledger-v1", documentation)
        self.assertIn("state/mesh/reviews/pr-<N>/<head>/<fingerprint>.json", documentation)
        self.assertIn(
            "state/mesh/reviews/pr-<N>/<head>/<fingerprint>.diff",
            documentation,
        )
        self.assertIn("D0=3 REQUEST_AUTHORITY", documentation)
        self.assertIn("may submit only a\n`COMMENT` review event", documentation)

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
