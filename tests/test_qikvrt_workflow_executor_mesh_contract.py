# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
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
        dispatch = contract["dispatch_policy"]
        self.assertEqual(dispatch["maximum_dispatches_per_run"], 1)
        self.assertEqual(dispatch["dispatch_identity"], ["EXACT_HEAD", "WORKFLOW_PATH", "EVENT"])
        self.assertEqual(
            dispatch["run_observation"]["job_attempt_filter"],
            "EXPLICIT_ATTEMPT_ENDPOINT_PLUS_RUN_DETAIL_REOBSERVATION",
        )
        self.assertIn(
            "PRE_EFFECT_EQUIVALENT_RUN_AND_CROSS_HEAD_WRITER_REOBSERVED",
            dispatch["required_conditions"],
        )
        inventory = contract["workflow_inventory"]
        self.assertEqual(
            inventory["baseline"],
            "LATEST_EXACT_COMPATIBLE_EXECUTOR_SNAPSHOT_ARTIFACT_OR_FAIL_CLOSED",
        )
        self.assertEqual(inventory["compatible_baseline_unavailable_or_invalid"], "HOLD")
        authorized = dispatch["authorized_workflows"]
        self.assertEqual(
            [entry["capability_id"] for entry in authorized],
            ["firefox_proxy_delegation_bridge", "workflow_executor_watchdog"],
        )
        firefox = authorized[0]
        self.assertEqual(firefox["priority"], 10)
        self.assertEqual(firefox["purpose"], "CAPABILITY_EXACT_HEAD_GATE")
        self.assertEqual(firefox["allowed_events"], ["workflow_dispatch"])
        self.assertEqual(len(firefox["required_subjects"]), 7)
        self.assertFalse(
            firefox["historical_provenance"][
                "transferable_as_current_exact_head_gate_evidence"
            ]
        )
        self.assertEqual(authorized[1]["priority"], 100)
        self.assertEqual(
            authorized[1]["evidence_policy"],
            "TERMINAL_RUN_SUPPRESSES_DUPLICATE_ONLY",
        )
        self.assertTrue(
            all(value is False for value in dispatch["receipt_contract"]["completion_claims"].values())
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
        recovery = bridge["capability_gate_recovery"]
        self.assertEqual(
            recovery["classification"],
            "PRESENT_BYTES_CURRENT_EXACT_HEAD_GATE_UNOBSERVED",
        )
        self.assertEqual(
            recovery["action"],
            "DISPATCH_ONE_ALLOWLISTED_NO_EFFECT_WORKFLOW",
        )
        self.assertFalse(recovery["historical_gate_evidence_transferable"])
        self.assertFalse(recovery["transport_acknowledgement_is_execution_evidence"])
        self.assertTrue(all(value is False for value in recovery["completion_claims"].values()))
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
        self.assertRegex(snapshot["contract_blob_sha"], r"^[0-9a-f]{40}$")
        self.assertRegex(snapshot["workflow_inventory_sha256"], r"^[0-9a-f]{64}$")
        paths = {entry["path"] for entry in snapshot["workflow_inventory"]}
        self.assertIn(".github/workflows/qikvrt_workflow_executor.yml", paths)
        self.assertIn(".github/workflows/qikvrt_workflow_executor_watchdog.yml", paths)
        bindings = {
            entry["capability_id"]: entry for entry in snapshot["capability_bindings"]
        }
        firefox = bindings["firefox_proxy_delegation_bridge"]
        self.assertEqual(
            firefox["binding_state"],
            "PRESENT_BYTES_DECLARED_CURRENT_GATE_UNOBSERVED",
        )
        self.assertEqual(len(firefox["subject_bindings"]), 7)
        self.assertTrue(all(item["state"] == "EXACT" for item in firefox["subject_bindings"]))
        self.assertEqual(
            firefox["declaration"]["state"],
            "DECLARED_MACHINE_READABLE",
        )
        self.assertRegex(firefox["subject_manifest_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(snapshot["dispatch_ledger"], [])
        self.assertEqual(snapshot["workflow_delta"]["state"], "BASELINE_UNAVAILABLE")
        baseline = {"workflow_inventory": [{"path": path, "blob_sha": "0" * 40} for path in paths]}
        delta = MODULE.workflow_delta(snapshot["workflow_inventory"], baseline)
        self.assertEqual(delta["state"], "COMPARED")
        self.assertEqual(delta["added"], [])
        self.assertEqual(delta["removed"], [])
        self.assertEqual(sorted(delta["changed"]), sorted(paths))

    @staticmethod
    def run_observation(*runs):
        head = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", "HEAD^{commit}"],
            text=True,
        ).strip()
        return {
            "schema": "qikvrt_workflow_run_observation_v1",
            "repository": "Goldkelch/qik-vrt",
            "head_sha": head,
            "pagination_complete": True,
            "workflow_runs": list(runs),
        }

    @staticmethod
    def firefox_run(snapshot, *, status="completed", conclusion="success", jobs=None, path=None):
        return {
            "id": 701,
            "run_attempt": 1,
            "name": "QIKVRT Firefox proxy delegation bridge",
            "path": path or ".github/workflows/qikvrt_firefox_proxy_delegation.yml@refs/heads/main",
            "event": "workflow_dispatch",
            "head_sha": snapshot["head_sha"],
            "status": status,
            "conclusion": conclusion,
            "run_detail_reobserved": jobs is not None,
            "jobs": [] if jobs is None else jobs,
        }

    @staticmethod
    def successful_firefox_jobs(snapshot, run_attempt=1, run_id=701):
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        required = contract["dispatch_policy"]["authorized_workflows"][0][
            "required_job_evidence"
        ]["required_successful_steps"]
        return [
            {
                "id": 9001,
                "name": "verify",
                "run_id": run_id,
                "head_sha": snapshot["head_sha"],
                "run_attempt": run_attempt,
                "attempt_endpoint_bound": True,
                "status": "completed",
                "conclusion": "success",
                "steps": [
                    {"name": name, "status": "completed", "conclusion": "success"}
                    for name in required
                ],
            }
        ]

    def test_plan_is_exact_head_deduplicated_and_writer_serialized(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        empty_plan = MODULE.dispatch_plan(snapshot, self.run_observation(), "main")
        candidate = empty_plan["candidates"][0]
        self.assertEqual(empty_plan["state"], "DISPATCH_CANDIDATE_READY")
        self.assertEqual(candidate["disposition"], "DISPATCH")
        self.assertEqual(candidate["capability_id"], "firefox_proxy_delegation_bridge")
        self.assertEqual(candidate["head_sha"], snapshot["head_sha"])
        self.assertEqual(candidate["tree_sha"], snapshot["tree_sha"])
        self.assertRegex(candidate["workflow_blob_sha"], r"^[0-9a-f]{40}$")
        self.assertRegex(candidate["dispatch_key"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            empty_plan["candidates"][1]["first_blocker"],
            "HIGHER_PRIORITY_DISPATCH_SELECTED",
        )

        terminal = MODULE.dispatch_plan(
            snapshot,
            self.run_observation(self.firefox_run(snapshot, conclusion="action_required")),
            "main",
        )
        self.assertEqual(terminal["candidates"][0]["disposition"], "HOLD")
        self.assertEqual(
            terminal["candidates"][0]["first_blocker"],
            "EQUIVALENT_EXACT_HEAD_RUN_ACTION_REQUIRED",
        )
        writer = MODULE.dispatch_plan(
            snapshot,
            self.run_observation(
                {
                    "id": 8,
                    "run_attempt": 1,
                    "name": "QIK-VRT autonomous bounded self-heal",
                    "path": ".github/workflows/qikvrt_autonomous_self_heal.yml",
                    "event": "workflow_dispatch",
                    "head_sha": "0" * 40,
                    "status": "in_progress",
                    "conclusion": None,
                    "jobs": [],
                }
            ),
            "main",
        )
        self.assertEqual(writer["candidates"][0]["first_blocker"], "COMPETING_WRITER_ACTIVE")

    def test_positive_job_and_step_evidence_advances_to_the_next_priority_gate(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        plan = MODULE.dispatch_plan(
            snapshot,
            self.run_observation(
                self.firefox_run(snapshot, jobs=self.successful_firefox_jobs(snapshot))
            ),
            "main",
        )
        self.assertEqual(plan["candidates"][0]["disposition"], "OBSERVED")
        self.assertEqual(
            plan["candidates"][0]["evidence_state"],
            "CURRENT_EXACT_HEAD_GATE_OBSERVED",
        )
        self.assertEqual(plan["candidates"][1]["disposition"], "DISPATCH")

    def test_zero_job_failure_and_incomplete_steps_hold_without_retry(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        cases = [
            (
                self.firefox_run(snapshot),
                "EQUIVALENT_EXACT_HEAD_RUN_ZERO_JOB",
            ),
            (
                self.firefox_run(snapshot, conclusion="failure"),
                "EQUIVALENT_EXACT_HEAD_RUN_FAILED",
            ),
            (
                self.firefox_run(
                    snapshot,
                    jobs=[
                        {
                            "id": 9001,
                            "name": "verify",
                            "run_id": 701,
                            "head_sha": snapshot["head_sha"],
                            "run_attempt": 1,
                            "attempt_endpoint_bound": True,
                            "status": "completed",
                            "conclusion": "success",
                            "steps": [],
                        }
                    ],
                ),
                "EQUIVALENT_EXACT_HEAD_RUN_REQUIRES_JOB_EVIDENCE",
            ),
            (
                self.firefox_run(snapshot, status="in_progress", conclusion=None),
                "EQUIVALENT_EXACT_HEAD_RUN_ACTIVE",
            ),
        ]
        for run, blocker in cases:
            with self.subTest(blocker=blocker):
                plan = MODULE.dispatch_plan(snapshot, self.run_observation(run), "main")
                self.assertEqual(plan["candidates"][0]["disposition"], "HOLD")
                self.assertEqual(plan["candidates"][0]["first_blocker"], blocker)
                self.assertFalse(any(item["disposition"] == "DISPATCH" for item in plan["candidates"]))

        stale_attempt = {
            **self.firefox_run(
                snapshot,
                jobs=self.successful_firefox_jobs(snapshot, run_attempt=1),
            ),
            "run_attempt": 2,
        }
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "not bound to its run, head, and attempt"):
            MODULE.dispatch_plan(snapshot, self.run_observation(stale_attempt), "main")
        missing_reobservation = self.firefox_run(
            snapshot,
            jobs=self.successful_firefox_jobs(snapshot),
        )
        missing_reobservation["run_detail_reobserved"] = False
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "lacks post-job run reobservation"):
            MODULE.dispatch_plan(
                snapshot,
                self.run_observation(missing_reobservation),
                "main",
            )

    def test_malformed_or_authority_drifted_run_observations_block(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        cases = [
            {},
            {**self.run_observation(), "pagination_complete": False},
            {**self.run_observation(), "repository": "example/fork"},
            {**self.run_observation(), "head_sha": "0" * 40},
        ]
        for observation in cases:
            with self.subTest(observation=observation):
                with self.assertRaises(MODULE.ExecutorBlock):
                    MODULE.dispatch_plan(snapshot, observation, "main")
        duplicate = self.firefox_run(snapshot, status="in_progress", conclusion=None)
        newer_attempt = copy.deepcopy(duplicate)
        newer_attempt["run_attempt"] = 2
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "duplicates a run id"):
            MODULE.dispatch_plan(
                snapshot,
                self.run_observation(duplicate, newer_attempt),
                "main",
            )

    def test_path_event_identity_and_capability_bytes_fail_closed(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        wrong_path = self.firefox_run(
            snapshot,
            status="in_progress",
            conclusion=None,
            path=".github/workflows/not-the-firefox-gate.yml",
        )
        plan = MODULE.dispatch_plan(snapshot, self.run_observation(wrong_path), "main")
        self.assertEqual(plan["candidates"][0]["disposition"], "DISPATCH")

        drifted = copy.deepcopy(snapshot)
        firefox = drifted["capability_bindings"][0]
        firefox["subject_bindings"][0]["state"] = "BLOB_DRIFT"
        firefox["binding_state"] = "CAPABILITY_BYTES_OR_DECLARATION_DRIFT"
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "snapshot immutable evidence drift"):
            MODULE.dispatch_plan(drifted, self.run_observation(), "main")
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "not an object"):
            MODULE.dispatch_plan(snapshot, self.run_observation(42), "main")

    def test_disclosure_binding_drift_is_detected_not_just_the_capability_id(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        declaration = contract["dispatch_policy"]["authorized_workflows"][0]["declaration"]
        disclosure = json.loads(
            (ROOT / ".well-known/qik-vrt-self-disclosure.json").read_text(encoding="utf-8")
        )
        disclosure["bindings"]["firefox_proxy_delegation_bridge"][
            "historical_gate_evidence_transferable"
        ] = True
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            target = root / ".well-known/qik-vrt-self-disclosure.json"
            target.parent.mkdir(parents=True)
            target.write_text(json.dumps(disclosure), encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(
                [
                    "git", "-C", str(root),
                    "-c", "user.name=QIKVRT Test",
                    "-c", "user.email=qikvrt-test@example.invalid",
                    "commit", "-qm", "fixture",
                ],
                check=True,
            )
            binding = MODULE._declaration_binding(root, "HEAD", declaration)
        self.assertEqual(binding["state"], "CAPABILITY_BINDING_DRIFT")

    def test_transport_receipt_is_exactly_bound_and_suppresses_duplicate(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        plan = MODULE.dispatch_plan(snapshot, self.run_observation(), "main")
        receipt = MODULE.build_dispatch_receipt(
            plan,
            "qikvrt_firefox_proxy_delegation.yml",
            "DISPATCH_TRANSPORT_ACKNOWLEDGED_EXECUTION_UNOBSERVED",
            "2026-08-25T12:00:00Z",
        )
        self.assertEqual(receipt["dispatch_key"], plan["candidates"][0]["dispatch_key"])
        self.assertEqual(receipt["repository"], "Goldkelch/qik-vrt")
        self.assertFalse(receipt["transport_acknowledgement_is_gate_execution_evidence"])
        self.assertFalse(receipt["gate_execution_observed"])
        self.assertTrue(all(value is False for value in receipt["completion_claims"].values()))
        replay = copy.deepcopy(snapshot)
        replay["dispatch_ledger"] = [receipt]
        held = MODULE.dispatch_plan(replay, self.run_observation(), "main")
        self.assertEqual(
            held["candidates"][0]["first_blocker"],
            "EQUIVALENT_DISPATCH_REQUEST_ACKNOWLEDGED",
        )
        damaged = copy.deepcopy(receipt)
        damaged["tree_sha"] = "0" * 40
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "fingerprint drift"):
            MODULE._dispatch_ledger({"dispatch_ledger": [damaged]}, contract)
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "duplicate dispatch key"):
            MODULE._dispatch_ledger({"dispatch_ledger": [receipt, receipt]}, contract)
        overstated = copy.deepcopy(receipt)
        overstated["PASS"] = True
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "fields are not exact"):
            MODULE._dispatch_ledger({"dispatch_ledger": [overstated]}, contract)

        drifted_plan = copy.deepcopy(plan)
        drifted_plan["candidates"][0]["head_sha"] = "0" * 40
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "exact no-effect binding"):
            MODULE.build_dispatch_receipt(
                drifted_plan,
                "qikvrt_firefox_proxy_delegation.yml",
                "DISPATCH_TRANSPORT_ACKNOWLEDGED_EXECUTION_UNOBSERVED",
                "2026-08-25T12:00:00Z",
            )
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "canonical UTC timestamp"):
            MODULE.build_dispatch_receipt(
                plan,
                "qikvrt_firefox_proxy_delegation.yml",
                "DISPATCH_TRANSPORT_ACKNOWLEDGED_EXECUTION_UNOBSERVED",
                "not-a-time",
            )

        forged_plan = copy.deepcopy(plan)
        forged_plan["observed"]["capability_bindings"][0]["subject_manifest_sha256"] = "a" * 64
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "snapshot immutable evidence drift"):
            MODULE.build_dispatch_receipt(
                forged_plan,
                "qikvrt_firefox_proxy_delegation.yml",
                "DISPATCH_TRANSPORT_ACKNOWLEDGED_EXECUTION_UNOBSERVED",
                "2026-08-25T12:00:00Z",
            )

    def test_baseline_must_be_a_complete_snapshot_and_cli_rejects_arrays(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "dispatch ledger is missing"):
            MODULE._dispatch_ledger({"workflow_inventory": []}, contract)
        current = MODULE.snapshot(ROOT)
        incomplete = copy.deepcopy(current)
        incomplete.pop("dispatch_ledger")
        with self.assertRaisesRegex(MODULE.ExecutorBlock, "complete Authority executor snapshot"):
            MODULE.snapshot(ROOT, baseline=incomplete)
        with tempfile.TemporaryDirectory() as directory:
            baseline_path = pathlib.Path(directory) / "baseline.json"
            baseline_path.write_text("[]\n", encoding="utf-8")
            self.assertEqual(
                MODULE.main(["snapshot", "--baseline", str(baseline_path), "--json"]),
                2,
            )

    def test_transport_failure_is_persisted_as_hold_without_blind_retry(self) -> None:
        snapshot = MODULE.snapshot(ROOT)
        plan = MODULE.dispatch_plan(snapshot, self.run_observation(), "main")
        receipt = MODULE.build_dispatch_receipt(
            plan,
            "qikvrt_firefox_proxy_delegation.yml",
            "DISPATCH_TRANSPORT_FAILED",
            "2026-08-25T12:00:00Z",
        )
        replay = copy.deepcopy(snapshot)
        replay["dispatch_ledger"] = [receipt]
        held = MODULE.dispatch_plan(replay, self.run_observation(), "main")
        self.assertEqual(
            held["candidates"][0]["first_blocker"],
            "PRIOR_DISPATCH_TRANSPORT_FAILED",
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
        self.assertIn("workflow_run:", executor)
        self.assertIn("QIKVRT Firefox proxy delegation bridge", executor)
        self.assertIn("/attempts/${run_attempt}/jobs?per_page=100", executor)
        self.assertIn("attempt_endpoint_bound: true", executor)
        self.assertIn("run_detail_reobserved: true", executor)
        self.assertIn('actions/runs/${run_id}"', executor)
        self.assertNotIn("jobs?filter=all", executor)
        self.assertIn("--paginate --slurp", executor)
        self.assertIn(".total_count", executor)
        self.assertIn("head_sha=${live_head}", executor)
        self.assertIn("qikvrt_workflow_run_observation_v1", executor)
        self.assertNotIn("done < <(jq -c '.workflow_runs[]'", executor)
        self.assertIn('test "$GITHUB_REPOSITORY" = "$authority_repository"', executor)
        self.assertIn('previous_snapshot="${RUNNER_TEMP}/', executor)
        self.assertNotIn(".qikvrt/workflow-executor/previous-snapshot", executor)
        self.assertIn("baseline-state.txt", executor)
        self.assertIn("BLOCK compatible executor baseline exists", executor)
        self.assertIn("compatibility_paths=(", executor)
        self.assertIn("for run_status in queued in_progress waiting requested pending", executor)
        self.assertIn("qikvrt-workflow-executor-pre-dispatch-runs.json", executor)
        self.assertIn("workflow_blob_sha", executor)
        self.assertIn("dispatch-receipt", executor)
        self.assertIn("include-hidden-files: true", executor)
        self.assertIn("HEAD^{tree}", executor)
        self.assertNotIn("sleep 5", executor)
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
