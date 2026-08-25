# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import asyncio
import copy
import json
import pathlib
import re
import tempfile
import textwrap
import unittest

from tools.qikvrt_mesh_heartbeat import (
    AUTHORITY_EFFECT_SCOPE,
    EXTERNAL_EFFECT,
    HEARTBEAT_HZ,
    HEARTBEAT_INTERVAL_NS,
    HEARTBEAT_ROLE,
    LIFECYCLE,
    HeartbeatContractError,
    WorkRing,
    build_heartbeat,
    build_work_event,
    canonical_sha256,
    run_demo,
    verify_audit,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIVE_STATUS = ROOT / ".github/workflows/qikvrt_live_status_watch.yml"
HEAD = "1" * 40
TREE = "2" * 40


class MeshHeartbeatPureContractTests(unittest.TestCase):
    def test_heartbeat_is_liveness_only_and_keeps_quiescence(self) -> None:
        heartbeat = build_heartbeat(
            node_id="authority-a",
            pair_id="pair-a",
            role="AUTHORITY",
            sequence=0,
            scheduled_monotonic_ns=1_000_000_000,
            sent_monotonic_ns=1_000_001_000,
            previous_heartbeat_sha256="GENESIS",
            source_head=HEAD,
            source_tree=TREE,
        )
        self.assertEqual(heartbeat["heartbeat_hz"], HEARTBEAT_HZ)
        self.assertEqual(heartbeat["heartbeat_role"], HEARTBEAT_ROLE)
        self.assertFalse(heartbeat["semantic_work_triggered"])
        self.assertFalse(heartbeat["polling"])
        self.assertFalse(heartbeat["blind_retry"])
        ring = WorkRing()
        ring.observe_heartbeat(heartbeat)
        self.assertEqual(ring.state, "0")
        self.assertEqual(ring.heartbeat_semantic_work_count, 0)

    def test_work_ring_executes_exact_lifecycle_once(self) -> None:
        ring = WorkRing()
        event = build_work_event(source_head=HEAD, source_tree=TREE)
        self.assertEqual(event["construction_scope"], "LOCAL_SYSTEM_TEST")
        self.assertFalse(event["external_ingress_authentication_observed"])
        first = ring.execute(event)
        second = ring.execute(event)
        self.assertEqual(first, second)
        self.assertEqual(first["lifecycle"], LIFECYCLE)
        self.assertEqual(first["authority_effect_scope"], AUTHORITY_EFFECT_SCOPE)
        self.assertTrue(first["local_authority_effect_reobserved"])
        self.assertFalse(first["repository_authority_effect_observed"])
        self.assertEqual(first["external_effect"], EXTERNAL_EFFECT)
        self.assertEqual(ring.state, "0")
        self.assertEqual(len(ring.authority_ledger), 1)

    def test_event_id_payload_rebinding_fails_closed(self) -> None:
        ring = WorkRing()
        event = build_work_event(source_head=HEAD, source_tree=TREE)
        ring.execute(event)
        changed = copy.deepcopy(event)
        changed["payload"]["nonce"] = "different"
        changed["payload_sha256"] = canonical_sha256(changed["payload"])
        with self.assertRaisesRegex(HeartbeatContractError, "event_id reuse"):
            ring.execute(changed)

    def test_false_heartbeat_semantic_work_claim_is_rejected(self) -> None:
        heartbeat = build_heartbeat(
            node_id="authority-a",
            pair_id="pair-a",
            role="AUTHORITY",
            sequence=0,
            scheduled_monotonic_ns=1_000_000_000,
            sent_monotonic_ns=1_000_001_000,
            previous_heartbeat_sha256="GENESIS",
            source_head=HEAD,
            source_tree=TREE,
        )
        heartbeat["semantic_work_triggered"] = True
        with self.assertRaisesRegex(HeartbeatContractError, "may not trigger"):
            WorkRing().observe_heartbeat(heartbeat)


class MeshHeartbeatSystemTests(unittest.TestCase):
    def test_four_process_two_pair_one_hertz_system_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = pathlib.Path(directory)
            receipt = asyncio.run(
                run_demo(
                    source_head=HEAD,
                    source_tree=TREE,
                    output_dir=output,
                    heartbeat_count=4,
                    event_name="local",
                    run_id=0,
                )
            )
            verify_audit(receipt, source_head=HEAD, source_tree=TREE)
            self.assertEqual(receipt["heartbeat_hz"], 1)
            self.assertEqual(receipt["scheduled_interval_ns"], HEARTBEAT_INTERVAL_NS)
            self.assertEqual(receipt["node_process_count"], 4)
            self.assertEqual(receipt["pair_count"], 2)
            self.assertEqual(receipt["heartbeats_per_node"], 4)
            self.assertEqual(receipt["total_heartbeats"], 16)
            self.assertEqual(receipt["heartbeat_semantic_work_count"], 0)
            self.assertEqual(receipt["polling_count"], 0)
            self.assertEqual(receipt["blind_retry_count"], 0)
            self.assertEqual(
                receipt["locally_constructed_content_bound_work_event_count"],
                1,
            )
            self.assertFalse(
                receipt["external_ingress_authentication_observed"]
            )
            self.assertTrue(receipt["duplicate_event_replay_byte_identical"])
            self.assertTrue(receipt["event_id_payload_rebinding_blocked"])
            self.assertTrue(receipt["local_authority_effect_reobserved"])
            self.assertFalse(receipt["repository_authority_effect_observed"])
            self.assertFalse(receipt["general_effect_ack_done"])
            for path in (
                "execution-receipt.json",
                "heartbeats.jsonl",
                "work-receipt.json",
                "authority-ledger.json",
            ):
                self.assertTrue((output / path).is_file(), path)

    def test_audit_rejects_manufactured_repository_authority_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = asyncio.run(
                run_demo(
                    source_head=HEAD,
                    source_tree=TREE,
                    output_dir=pathlib.Path(directory),
                    heartbeat_count=4,
                    event_name="local",
                    run_id=0,
                )
            )
        receipt["repository_authority_effect_observed"] = True
        with self.assertRaisesRegex(HeartbeatContractError, "manufacture"):
            verify_audit(receipt, source_head=HEAD, source_tree=TREE)

    def test_audit_rejects_manufactured_external_ingress_authentication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt = asyncio.run(
                run_demo(
                    source_head=HEAD,
                    source_tree=TREE,
                    output_dir=pathlib.Path(directory),
                    heartbeat_count=4,
                    event_name="local",
                    run_id=0,
                )
            )
        receipt["external_ingress_authentication_observed"] = True
        with self.assertRaisesRegex(HeartbeatContractError, "authentication"):
            verify_audit(receipt, source_head=HEAD, source_tree=TREE)


class MeshHeartbeatRepositoryContractTests(unittest.TestCase):
    def test_policy_binds_one_hertz_liveness_without_semantic_polling(self) -> None:
        policy = json.loads(
            (ROOT / "policy/QIKVRT_MESH_HEARTBEAT_V1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(policy["heartbeat_hz"], 1)
        self.assertEqual(policy["heartbeat_role"], HEARTBEAT_ROLE)
        self.assertFalse(policy["heartbeat_may_trigger_semantic_work"])
        self.assertFalse(policy["domain_polling_allowed"])
        self.assertFalse(policy["blind_retry_allowed"])
        self.assertEqual(policy["work_lifecycle"], LIFECYCLE)
        self.assertEqual(
            policy["semantic_work_trigger"],
            "LOCALLY_CONSTRUCTED_CONTENT_BOUND_EVENT_ONLY",
        )
        self.assertFalse(policy["external_ingress_authentication_observed"])
        self.assertEqual(
            policy["system_test"]["work_event_construction_scope"],
            "LOCAL_SYSTEM_TEST",
        )
        projection = policy["live_status_projection"]
        self.assertEqual(projection["trigger"], "REPOSITORY_EVENT_ONLY")
        self.assertFalse(projection["repository_api_polling"])
        self.assertFalse(projection["sleep_loop"])
        self.assertTrue(projection["artifact_required"])

    def test_candidate_workflow_is_event_driven_read_only_and_audited(self) -> None:
        workflow = (ROOT / ".github/workflows/qikvrt_mesh_heartbeat.yml").read_text(
            encoding="utf-8"
        )
        job_prefix = workflow.split("\n    steps:", 1)[0]
        self.assertNotIn("schedule:", workflow)
        self.assertNotIn("runner.temp", job_prefix)
        self.assertIn(
            'evidence_dir="$RUNNER_TEMP/qikvrt-mesh-heartbeat"',
            workflow,
        )
        self.assertIn("contents: read", workflow)
        self.assertIn("github.event.pull_request.head.sha || github.sha", workflow)
        self.assertIn("--heartbeat-count 4", workflow)
        self.assertIn("qikvrt-mesh-heartbeat-${{ env.QIKVRT_EXACT_HEAD }}", workflow)
        self.assertIn("Verify repository-native integrity", workflow)

    def test_live_status_projection_is_event_driven_and_api_poll_free(self) -> None:
        workflow = LIVE_STATUS.read_text(encoding="utf-8")
        job_prefix = workflow.split("\n    steps:", 1)[0]
        self.assertNotIn("runner.temp", job_prefix)
        self.assertIn(
            'evidence_dir="$RUNNER_TEMP/qikvrt-live-status-event"',
            workflow,
        )
        self.assertIn("workflow_run:", workflow)
        self.assertIn("types: [requested, in_progress, completed]", workflow)
        self.assertIn("GITHUB_STEP_SUMMARY", workflow)
        self.assertIn("REPOSITORY_EVENT_ONLY", workflow)
        self.assertIn("polling: false", workflow)
        self.assertIn("blind_retry: false", workflow)
        self.assertIn("Upload exact event-bound status evidence", workflow)
        self.assertIn("actions: read", workflow)
        self.assertIn("pull-requests: read", workflow)
        for forbidden in (
            "schedule:",
            "while :",
            "sleep 5",
            "MAX_CYCLES",
            "gh api",
            "actions/runs?branch=",
            "issues: write",
            "pull-requests: write",
        ):
            self.assertNotIn(forbidden, workflow)

    def test_trusted_writer_is_main_only_serialized_and_cas_bound(self) -> None:
        workflow = (
            ROOT / ".github/workflows/qikvrt_mesh_heartbeat_main_ledger.yml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("schedule:", workflow)
        self.assertIn("workflow_run", workflow)
        self.assertIn("github.event.workflow_run.event == 'push'", workflow)
        self.assertIn("github.event.workflow_run.head_branch == 'main'", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("AUTHORITY_MAIN_ADVANCED_BEFORE_LEDGER_WRITE", workflow)
        self.assertIn("AUTHORITY_MAIN_ADVANCED_BEFORE_LEDGER_PUSH", workflow)
        self.assertIn("LEDGER_REF_ADVANCED_BEFORE_PUSH", workflow)
        self.assertIn(
            "value['locally_constructed_content_bound_work_event_count'] == 1",
            workflow,
        )
        self.assertIn(
            "value['external_ingress_authentication_observed'] is False",
            workflow,
        )
        self.assertNotIn(
            "authenticated_content_bound_work_event_count",
            workflow,
        )
        self.assertIn("git -C \"$ledger\" push origin \"HEAD:$LEDGER_REF\"", workflow)
        self.assertIn(
            "LEDGER_REF_POST_PUSH_REOBSERVATION_MISMATCH",
            workflow,
        )
        self.assertIn("LEDGER_REF_ADVANCED_DURING_READBACK", workflow)
        self.assertIn("LEDGER_REF_ADVANCED_DURING_INITIAL_FETCH", workflow)
        self.assertIn(
            'git -C "$ledger" rev-parse --verify FETCH_HEAD^{commit}',
            workflow,
        )
        self.assertIn(
            'git -C "$readback" fetch --no-tags --depth=1 origin "$LEDGER_REF"',
            workflow,
        )
        self.assertIn('show "FETCH_HEAD:$target"', workflow)
        self.assertIn("show 'FETCH_HEAD:latest.json'", workflow)
        self.assertIn('cmp "$source" "$RUNNER_TEMP/readback-target.json"', workflow)
        self.assertIn('cmp "$source" "$RUNNER_TEMP/readback-latest.json"', workflow)
        self.assertIn(
            "qikvrt_mesh_heartbeat_ledger_reobservation_v1",
            workflow,
        )
        self.assertIn("ledger_transition='NOOP_ALREADY_CURRENT'", workflow)
        self.assertIn("ledger_transition='FAST_FORWARD_PUSHED'", workflow)
        self.assertIn(
            "'reobserved_remote_ledger_head': os.environ['REOBSERVED_LEDGER_HEAD']",
            workflow,
        )
        self.assertIn(
            "Preserve terminal ledger reobservation receipt",
            workflow,
        )
        self.assertNotIn("MESH_HEARTBEAT_LEDGER_ALREADY_CURRENT'\n            exit 0", workflow)

    def test_trusted_writer_embedded_python_is_syntactically_valid(self) -> None:
        workflow = (
            ROOT / ".github/workflows/qikvrt_mesh_heartbeat_main_ledger.yml"
        ).read_text(encoding="utf-8")
        blocks = re.findall(
            r"^[ \t]+python3 -B - <<'PY'[^\n]*\n(.*?)^[ \t]+PY$",
            workflow,
            re.MULTILINE | re.DOTALL,
        )
        self.assertEqual(len(blocks), 2)
        for index, block in enumerate(blocks):
            compile(textwrap.dedent(block), f"<heartbeat-ledger-{index}>", "exec")


if __name__ == "__main__":
    unittest.main()
