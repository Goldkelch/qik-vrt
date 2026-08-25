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
from unittest import mock

from tools.qikvrt_mesh_heartbeat import (
    AUTHORITY_EFFECT_SCOPE,
    EXTERNAL_EFFECT,
    HEARTBEAT_HZ,
    HEARTBEAT_INTERVAL_NS,
    HEARTBEAT_ROLE,
    LEDGER_REF,
    LIFECYCLE,
    HeartbeatContractError,
    WorkRing,
    _strict_json_loads,
    build_heartbeat,
    build_work_event,
    canonical_sha256,
    evaluate_ledger_ref_control,
    flatten_ledger_rule_pages,
    ledger_ref_control_reobserve,
    main as heartbeat_main,
    observe_ledger_ref_control,
    run_demo,
    verify_audit,
    verify_ledger_ref_control_receipt,
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


class MeshHeartbeatLedgerRefControlTests(unittest.TestCase):
    @staticmethod
    def _rule(ruleset_id: int, rule_type: str) -> dict[str, object]:
        return {
            "type": rule_type,
            "ruleset_id": ruleset_id,
            "ruleset_source_type": "Repository",
            "ruleset_source": "Goldkelch/qik-vrt",
        }

    @staticmethod
    def _detail(
        ruleset_id: int,
        *,
        include: list[str] | None = None,
        bypass: object = (),
    ) -> dict[str, object]:
        value: dict[str, object] = {
            "id": ruleset_id,
            "target": "branch",
            "enforcement": "active",
            "source_type": "Repository",
            "source": "Goldkelch/qik-vrt",
            "conditions": {
                "ref_name": {
                    "include": [LEDGER_REF] if include is None else include,
                    "exclude": [],
                }
            },
            "rules": [
                {"type": "non_fast_forward"},
                {"type": "deletion"},
            ],
        }
        if bypass != ():
            value["bypass_actors"] = bypass
        return value

    def _evaluate(
        self,
        rules: list[dict[str, object]],
        details: dict[int, dict[str, object]],
        *,
        repository: str = "Goldkelch/qik-vrt",
        source_head: str = HEAD,
        source_run_id: int = 7,
        observer_run_id: int = 11,
        observer_run_attempt: int = 1,
        observation_phase: str = "INITIAL",
        ledger_transition: str = "NONE",
    ) -> dict[str, object]:
        return evaluate_ledger_ref_control(
            rules,
            details,
            repository=repository,
            source_head=source_head,
            source_run_id=source_run_id,
            observer_run_id=observer_run_id,
            observer_run_attempt=observer_run_attempt,
            observation_phase=observation_phase,
            ledger_transition=ledger_transition,
        )

    @staticmethod
    def _reseal(receipt: dict[str, object]) -> dict[str, object]:
        result = copy.deepcopy(receipt)
        result.pop("receipt_sha256", None)
        result["receipt_sha256"] = canonical_sha256(result)
        return result

    @staticmethod
    def _enforce_pair(
        baseline: dict[str, object],
        current: dict[str, object],
        *,
        repository: str = "Goldkelch/qik-vrt",
        source_head: str = HEAD,
        source_run_id: int = 7,
        observer_run_id: int = 11,
        observer_run_attempt: int = 1,
        observation_phase: str | None = None,
        ledger_transition: str | None = None,
    ) -> tuple[int, dict[str, object] | None]:
        current_phase = (
            observation_phase
            if observation_phase is not None
            else str(current["observation_phase"])
        )
        current_transition = (
            ledger_transition
            if ledger_transition is not None
            else str(current["ledger_transition_before_observation"])
        )
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            baseline_path = root / "baseline.json"
            current_path = root / "current.json"
            comparison_path = root / "comparison.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            current_path.write_text(json.dumps(current), encoding="utf-8")
            rc = heartbeat_main([
                "enforce-ledger-ref-control",
                "--receipt", str(current_path),
                "--expected-snapshot-receipt", str(baseline_path),
                "--comparison-output", str(comparison_path),
                "--repository", repository,
                "--source-head", source_head,
                "--source-run-id", str(source_run_id),
                "--observer-run-id", str(observer_run_id),
                "--observer-run-attempt", str(observer_run_attempt),
                "--observation-phase", current_phase,
                "--ledger-ref", LEDGER_REF,
                "--ledger-transition", current_transition,
            ])
            comparison = (
                json.loads(comparison_path.read_text(encoding="utf-8"))
                if comparison_path.exists()
                else None
            )
        return rc, comparison

    def test_same_ruleset_literal_include_and_empty_bypass_satisfy_guard(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        receipt = self._evaluate(rules, {42: self._detail(42, bypass=[])})
        self.assertEqual(receipt["state"], "CONTROL_OBSERVED")
        self.assertIsNone(receipt["d0"])
        self.assertTrue(receipt["ledger_write_guard_satisfied"])
        self.assertEqual(receipt["selected_ruleset_id"], 42)
        self.assertEqual(
            canonical_sha256(receipt["protection_snapshot"]),
            receipt["protection_snapshot_sha256"],
        )
        self.assertFalse(any(receipt["completion_claims"].values()))
        verify_ledger_ref_control_receipt(receipt)

    def test_split_rulesets_do_not_combine_into_authority(self) -> None:
        receipt = self._evaluate(
            [self._rule(41, "deletion"), self._rule(42, "non_fast_forward")],
            {},
        )
        self.assertEqual(receipt["state"], "REQUEST_AUTHORITY")
        self.assertEqual(receipt["d0"], 3)
        self.assertFalse(receipt["ledger_write_guard_satisfied"])
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "LEDGER_REF_CONTROL_REQUEST_AUTHORITY",
        ):
            verify_ledger_ref_control_receipt(receipt)

    def test_hidden_or_nonempty_bypass_and_nonliteral_include_request_authority(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        cases = (
            (self._detail(42), "LEDGER_RULESET_BYPASS_VISIBILITY_REQUIRED"),
            (
                self._detail(
                    42,
                    bypass=[
                        {
                            "actor_id": 5,
                            "actor_type": "Integration",
                            "bypass_mode": "always",
                        }
                    ],
                ),
                "LEDGER_RULESET_BYPASS_PRESENT",
            ),
            (
                self._detail(42, include=["refs/heads/main"], bypass=[]),
                "LEDGER_RULESET_LITERAL_INCLUDE_MISSING",
            ),
        )
        for detail, blocker in cases:
            with self.subTest(blocker=blocker):
                receipt = self._evaluate(rules, {42: detail})
                self.assertEqual(receipt["state"], "REQUEST_AUTHORITY")
                self.assertEqual(receipt["d0"], 3)
                self.assertEqual(receipt["first_blocker"], blocker)
                forged_blocker = copy.deepcopy(receipt)
                forged_blocker["first_blocker"] = "ARBITRARY_BLOCKER"
                forged_blocker = self._reseal(forged_blocker)
                with self.assertRaisesRegex(
                    HeartbeatContractError,
                    "authority state mismatch",
                ):
                    verify_ledger_ref_control_receipt(forged_blocker)

    def test_excludes_request_authority_and_source_mismatch_is_invalid(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        excluded = self._detail(42, bypass=[])
        excluded["conditions"]["ref_name"]["exclude"] = [LEDGER_REF]
        wrong_source = self._detail(42, bypass=[])
        wrong_source["source"] = "other/repository"
        receipt = self._evaluate(rules, {42: excluded})
        self.assertEqual(receipt["state"], "REQUEST_AUTHORITY")
        self.assertEqual(receipt["d0"], 3)
        self.assertEqual(receipt["first_blocker"], "LEDGER_RULESET_EXCLUDE_PRESENT")
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "SOURCE_REPOSITORY_MISMATCH",
        ):
            self._evaluate(rules, {42: wrong_source})

    def test_incomplete_observation_is_reobserve_without_completion(self) -> None:
        receipt = ledger_ref_control_reobserve(
            repository="Goldkelch/qik-vrt",
            source_head=HEAD,
            source_run_id=7,
            blocker="LEDGER_RULESET_API_FAILED",
        )
        self.assertEqual(receipt["state"], "REOBSERVE")
        self.assertEqual(receipt["d0"], 2)
        self.assertFalse(receipt["ledger_write_guard_satisfied"])
        self.assertFalse(any(receipt["completion_claims"].values()))

        with mock.patch(
            "tools.qikvrt_mesh_heartbeat._gh_json",
            side_effect=HeartbeatContractError("LEDGER_RULESET_API_FAILED"),
        ):
            observed = observe_ledger_ref_control(
                repository="Goldkelch/qik-vrt",
                source_head=HEAD,
                source_run_id=7,
            )
        self.assertEqual(observed["state"], "REOBSERVE")
        self.assertEqual(observed["d0"], 2)
        self.assertEqual(observed["first_blocker"], "LEDGER_RULESET_API_FAILED")

    def test_ruleset_snapshot_is_order_independent_and_sealed(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        first = self._evaluate(rules, {42: self._detail(42, bypass=[])})
        reversed_detail = self._detail(42, bypass=[])
        reversed_detail["rules"] = list(reversed(reversed_detail["rules"]))
        second = self._evaluate(
            list(reversed(rules)),
            {42: reversed_detail},
        )
        self.assertEqual(
            first["protection_snapshot_sha256"],
            second["protection_snapshot_sha256"],
        )
        tampered = copy.deepcopy(first)
        tampered["selected_ruleset_id"] = 99
        with self.assertRaisesRegex(HeartbeatContractError, "seal mismatch"):
            verify_ledger_ref_control_receipt(tampered)

        body_tampered = copy.deepcopy(first)
        body_tampered["protection_snapshot"]["ledger_ref"] = "refs/heads/other"
        body_tampered = self._reseal(body_tampered)
        with self.assertRaisesRegex(HeartbeatContractError, "snapshot digest mismatch"):
            verify_ledger_ref_control_receipt(body_tampered)

    def test_strict_verifier_rejects_skeleton_completion_and_source_forgery(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        receipt = self._evaluate(rules, {42: self._detail(42, bypass=[])})

        skeleton = self._reseal({
            "schema": receipt["schema"],
            "observation_complete": True,
        })
        with self.assertRaisesRegex(HeartbeatContractError, "fields are not exact"):
            verify_ledger_ref_control_receipt(skeleton)

        empty_completion = copy.deepcopy(receipt)
        empty_completion["completion_claims"] = {}
        empty_completion = self._reseal(empty_completion)
        with self.assertRaisesRegex(HeartbeatContractError, "common binding mismatch"):
            verify_ledger_ref_control_receipt(empty_completion)

        forged_source = copy.deepcopy(receipt)
        candidate = forged_source["protection_snapshot"]["candidate_rulesets"][0]
        candidate["effective_source"] = "other/repository"
        candidate["source"] = "other/repository"
        forged_source["protection_snapshot_sha256"] = canonical_sha256(
            forged_source["protection_snapshot"]
        )
        forged_source = self._reseal(forged_source)
        with self.assertRaisesRegex(HeartbeatContractError, "source binding mismatch"):
            verify_ledger_ref_control_receipt(forged_source)

    def test_strict_verifier_rejects_bool_int_receipt_aliases(self) -> None:
        rules = [self._rule(1, "deletion"), self._rule(1, "non_fast_forward")]
        receipt = self._evaluate(rules, {1: self._detail(1, bypass=[])})
        cases = []

        mutation_alias = copy.deepcopy(receipt)
        mutation_alias["repository_ruleset_mutation_performed"] = 0
        cases.append((mutation_alias, "manufactured ruleset mutation"))

        completion_alias = copy.deepcopy(receipt)
        completion_alias["completion_claims"]["PASS"] = 0
        cases.append((completion_alias, "completion claims are invalid"))

        identifier_alias = copy.deepcopy(receipt)
        identifier_alias["qualifying_ruleset_ids"] = [True]
        identifier_alias["selected_ruleset_id"] = True
        cases.append((identifier_alias, "qualifying IDs mismatch"))

        for value, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(HeartbeatContractError, message):
                    verify_ledger_ref_control_receipt(self._reseal(value))

    def test_cli_snapshot_drift_emits_bound_reobserve_receipt(self) -> None:
        rules_42 = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        rules_43 = [self._rule(43, "deletion"), self._rule(43, "non_fast_forward")]
        baseline = self._evaluate(rules_42, {42: self._detail(42, bypass=[])})
        current = self._evaluate(
            rules_43,
            {43: self._detail(43, bypass=[])},
            observation_phase="POST_READBACK",
            ledger_transition="FAST_FORWARD_PUSHED",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            baseline_path = root / "baseline.json"
            current_path = root / "current.json"
            comparison_path = root / "comparison.json"
            baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
            current_path.write_text(json.dumps(current), encoding="utf-8")
            rc = heartbeat_main([
                "enforce-ledger-ref-control",
                "--receipt", str(current_path),
                "--expected-snapshot-receipt", str(baseline_path),
                "--comparison-output", str(comparison_path),
                "--repository", "Goldkelch/qik-vrt",
                "--source-head", HEAD,
                "--source-run-id", "7",
                "--observer-run-id", "11",
                "--observer-run-attempt", "1",
                "--observation-phase", "POST_READBACK",
                "--ledger-ref", LEDGER_REF,
                "--ledger-transition", "FAST_FORWARD_PUSHED",
            ])
            self.assertEqual(rc, 2)
            comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        self.assertEqual(comparison["state"], "REOBSERVE")
        self.assertEqual(comparison["d0"], 2)
        self.assertEqual(
            comparison["first_blocker"],
            "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT",
        )
        self.assertTrue(comparison["comparison_performed"])
        self.assertEqual(
            comparison["expected_protection_snapshot_sha256"],
            baseline["protection_snapshot_sha256"],
        )
        self.assertEqual(
            comparison["observed_protection_snapshot_sha256"],
            current["protection_snapshot_sha256"],
        )
        self.assertEqual(
            comparison["ledger_transition_before_observation"],
            "FAST_FORWARD_PUSHED",
        )
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "LEDGER_REF_CONTROL_REOBSERVE",
        ):
            verify_ledger_ref_control_receipt(comparison)

    def test_cli_rejects_equal_snapshot_cross_event_receipts(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        baseline = self._evaluate(rules, {42: self._detail(42, bypass=[])})
        foreign = self._evaluate(
            rules,
            {42: self._detail(42, bypass=[])},
            source_head="3" * 40,
            source_run_id=99,
            observation_phase="PRE_PUSH",
        )
        rc, comparison = self._enforce_pair(baseline, foreign)
        self.assertEqual(rc, 2)
        self.assertIsNotNone(comparison)
        self.assertEqual(comparison["state"], "REOBSERVE")
        self.assertEqual(
            comparison["first_blocker"],
            "LEDGER_REF_CONTROL_EVIDENCE_INVALID",
        )
        self.assertFalse(comparison["comparison_performed"])

        wrong_transition_baseline = self._evaluate(
            rules,
            {42: self._detail(42, bypass=[])},
            observation_phase="POST_READBACK",
            ledger_transition="FAST_FORWARD_PUSHED",
        )
        current_pre_push = self._evaluate(
            rules,
            {42: self._detail(42, bypass=[])},
            observation_phase="PRE_PUSH",
        )
        rc, comparison = self._enforce_pair(
            wrong_transition_baseline,
            current_pre_push,
        )
        self.assertEqual(rc, 2)
        self.assertEqual(
            comparison["first_blocker"],
            "LEDGER_REF_CONTROL_EVIDENCE_INVALID",
        )

    def test_cli_context_binding_precedes_authority_or_drift_classification(self) -> None:
        control_rules = [
            self._rule(42, "deletion"),
            self._rule(42, "non_fast_forward"),
        ]
        baseline = self._evaluate(
            control_rules,
            {42: self._detail(42, bypass=[])},
        )
        foreign_authority = self._evaluate(
            control_rules,
            {42: self._detail(42)},
            source_head="3" * 40,
            source_run_id=99,
            observation_phase="PRE_PUSH",
        )
        rc, comparison = self._enforce_pair(baseline, foreign_authority)
        self.assertEqual(rc, 2)
        self.assertEqual(
            comparison["first_blocker"],
            "LEDGER_REF_CONTROL_EVIDENCE_INVALID",
        )

        foreign_baseline = self._evaluate(
            control_rules,
            {42: self._detail(42, bypass=[])},
            source_head="3" * 40,
            source_run_id=99,
        )
        current = self._evaluate(
            [self._rule(43, "deletion"), self._rule(43, "non_fast_forward")],
            {43: self._detail(43, bypass=[])},
            observation_phase="PRE_PUSH",
        )
        rc, comparison = self._enforce_pair(foreign_baseline, current)
        self.assertEqual(rc, 2)
        self.assertEqual(
            comparison["first_blocker"],
            "LEDGER_REF_CONTROL_EVIDENCE_INVALID",
        )
        self.assertFalse(comparison["comparison_performed"])

    def test_cli_matching_authority_receipt_uses_authority_exit(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        baseline = self._evaluate(rules, {42: self._detail(42, bypass=[])})
        current = self._evaluate(
            rules,
            {42: self._detail(42)},
            observation_phase="PRE_PUSH",
        )
        rc, comparison = self._enforce_pair(baseline, current)
        self.assertEqual(rc, 3)
        self.assertIsNone(comparison)

    def test_cli_rejects_initial_replay_and_cross_attempt_replay(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        initial = self._evaluate(rules, {42: self._detail(42, bypass=[])})
        rc, comparison = self._enforce_pair(initial, initial)
        self.assertEqual(rc, 2)
        self.assertEqual(
            comparison["first_blocker"],
            "LEDGER_REF_CONTROL_EVIDENCE_INVALID",
        )

        pre_push = self._evaluate(
            rules,
            {42: self._detail(42, bypass=[])},
            observer_run_attempt=2,
            observation_phase="PRE_PUSH",
        )
        self.assertEqual(
            initial["protection_snapshot_sha256"],
            pre_push["protection_snapshot_sha256"],
        )
        self.assertNotEqual(initial["receipt_sha256"], pre_push["receipt_sha256"])
        rc, comparison = self._enforce_pair(initial, pre_push)
        self.assertEqual(rc, 2)
        self.assertEqual(
            comparison["first_blocker"],
            "LEDGER_REF_CONTROL_EVIDENCE_INVALID",
        )

    def test_cli_initial_enforcement_binds_explicit_context(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        current = self._evaluate(rules, {42: self._detail(42, bypass=[])})
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            current_path = root / "current.json"
            comparison_path = root / "comparison.json"
            current_path.write_text(json.dumps(current), encoding="utf-8")
            rc = heartbeat_main([
                "enforce-ledger-ref-control",
                "--receipt", str(current_path),
                "--comparison-output", str(comparison_path),
                "--repository", "Goldkelch/qik-vrt",
                "--source-head", "3" * 40,
                "--source-run-id", "99",
                "--observer-run-id", "11",
                "--observer-run-attempt", "1",
                "--observation-phase", "INITIAL",
                "--ledger-ref", LEDGER_REF,
                "--ledger-transition", "NONE",
            ])
            self.assertEqual(rc, 2)
            comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        self.assertEqual(comparison["state"], "REOBSERVE")
        self.assertEqual(
            comparison["first_blocker"],
            "LEDGER_REF_CONTROL_EVIDENCE_INVALID",
        )

    def test_cli_corrupt_current_or_baseline_is_reobserve_not_authority(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        control = self._evaluate(rules, {42: self._detail(42, bypass=[])})
        request = self._evaluate(
            [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")],
            {42: self._detail(42)},
            observation_phase="PRE_PUSH",
        )
        corrupt_request = copy.deepcopy(request)
        corrupt_request["selected_ruleset_id"] = 99
        corrupt_baseline = copy.deepcopy(control)
        corrupt_baseline["receipt_sha256"] = "sha256:" + "0" * 64
        for baseline, current in (
            (control, corrupt_request),
            (corrupt_baseline, control),
        ):
            with self.subTest(baseline_corrupt=baseline is corrupt_baseline):
                with tempfile.TemporaryDirectory() as directory:
                    root = pathlib.Path(directory)
                    baseline_path = root / "baseline.json"
                    current_path = root / "current.json"
                    comparison_path = root / "comparison.json"
                    baseline_path.write_text(json.dumps(baseline), encoding="utf-8")
                    current_path.write_text(json.dumps(current), encoding="utf-8")
                    rc = heartbeat_main([
                        "enforce-ledger-ref-control",
                        "--receipt", str(current_path),
                        "--expected-snapshot-receipt", str(baseline_path),
                        "--comparison-output", str(comparison_path),
                        "--repository", "Goldkelch/qik-vrt",
                        "--source-head", HEAD,
                        "--source-run-id", "7",
                        "--observer-run-id", "11",
                        "--observer-run-attempt", "1",
                        "--observation-phase", "PRE_PUSH",
                        "--ledger-ref", LEDGER_REF,
                        "--ledger-transition", "NONE",
                    ])
                    self.assertEqual(rc, 2)
                    comparison = json.loads(
                        comparison_path.read_text(encoding="utf-8")
                    )
                self.assertEqual(comparison["state"], "REOBSERVE")
                self.assertEqual(
                    comparison["first_blocker"],
                    "LEDGER_REF_CONTROL_EVIDENCE_INVALID",
                )
                self.assertFalse(comparison["comparison_performed"])
                self.assertIsNone(
                    comparison["expected_protection_snapshot_sha256"]
                )
                self.assertIsNone(
                    comparison["observed_protection_snapshot_sha256"]
                )

    def test_malformed_pages_and_boolean_ruleset_ids_fail_closed(self) -> None:
        for malformed in (None, [], {}, [["not-an-object"]], [[]] * 101):
            with self.subTest(malformed=malformed):
                with self.assertRaises(HeartbeatContractError):
                    flatten_ledger_rule_pages(malformed)
        with self.assertRaisesRegex(HeartbeatContractError, "BINDING_INVALID"):
            self._evaluate(
                [self._rule(True, "deletion")],  # type: ignore[arg-type]
                {},
            )
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        float_id = self._detail(42, bypass=[])
        float_id["id"] = 42.0
        with self.assertRaisesRegex(HeartbeatContractError, "DETAIL_ID_MISMATCH"):
            self._evaluate(rules, {42: float_id})

        for field, malformed in (
            ("target", None),
            ("enforcement", True),
        ):
            detail = self._detail(42, bypass=[])
            detail[field] = malformed
            with self.subTest(field=field, malformed=malformed):
                with self.assertRaisesRegex(
                    HeartbeatContractError,
                    "DETAIL_STATE_INVALID",
                ):
                    self._evaluate(rules, {42: detail})

        malformed_lists = []
        empty_rule = self._detail(42, bypass=[])
        empty_rule["rules"].append({"type": ""})  # type: ignore[union-attr]
        malformed_lists.append(empty_rule)
        empty_include = self._detail(42, bypass=[])
        empty_include["conditions"]["ref_name"]["include"].append("")  # type: ignore[index,union-attr]
        malformed_lists.append(empty_include)
        empty_exclude = self._detail(42, bypass=[])
        empty_exclude["conditions"]["ref_name"]["exclude"].append("")  # type: ignore[index,union-attr]
        malformed_lists.append(empty_exclude)
        for detail in malformed_lists:
            with self.subTest(detail=detail):
                with self.assertRaises(HeartbeatContractError):
                    self._evaluate(rules, {42: detail})

        with self.assertRaisesRegex(HeartbeatContractError, "positive"):
            self._evaluate(rules, {42: self._detail(42, bypass=[])}, source_run_id=0)

    def test_ledger_json_decoder_rejects_duplicate_and_nonfinite_values(self) -> None:
        for malformed in (
            '{"ruleset_id":42,"ruleset_id":43}',
            '{"ruleset_id":NaN}',
            '{"ruleset_id":Infinity}',
            '{"ruleset_id":-Infinity}',
        ):
            with self.subTest(malformed=malformed):
                with self.assertRaisesRegex(
                    HeartbeatContractError,
                    "LEDGER_RULESET_API_INVALID_JSON",
                ):
                    _strict_json_loads(
                        malformed,
                        "LEDGER_RULESET_API_INVALID_JSON",
                    )

    def test_ruleset_sources_are_repository_bound_and_domain_strict(self) -> None:
        valid_rules = [
            self._rule(42, "deletion"),
            self._rule(42, "non_fast_forward"),
        ]
        for source_type, source in (
            ("Banana", "Goldkelch/qik-vrt"),
            ("Repository", "other/repository"),
        ):
            rules = copy.deepcopy(valid_rules)
            detail = self._detail(42, bypass=[])
            for rule in rules:
                rule["ruleset_source_type"] = source_type
                rule["ruleset_source"] = source
            detail["source_type"] = source_type
            detail["source"] = source
            with self.subTest(source_type=source_type, source=source):
                with self.assertRaisesRegex(
                    HeartbeatContractError,
                    "SOURCE_",
                ):
                    self._evaluate(rules, {42: detail})

        malformed_extra = self._rule(99, "pull_request")
        malformed_extra["ruleset_source_type"] = None
        with self.assertRaisesRegex(HeartbeatContractError, "SOURCE_DOMAIN_INVALID"):
            self._evaluate(
                [*valid_rules, malformed_extra],
                {42: self._detail(42, bypass=[])},
            )

        organization_rules = copy.deepcopy(valid_rules)
        organization_detail = self._detail(42, bypass=[])
        for rule in organization_rules:
            rule["ruleset_source_type"] = "Organization"
            rule["ruleset_source"] = "Goldkelch"
        organization_detail["source_type"] = "Organization"
        organization_detail["source"] = "Goldkelch"
        receipt = self._evaluate(
            organization_rules,
            {42: organization_detail},
        )
        self.assertTrue(receipt["ledger_write_guard_satisfied"])
        verify_ledger_ref_control_receipt(receipt)

        confusable_rules = copy.deepcopy(valid_rules)
        confusable_detail = self._detail(42, bypass=[])
        for rule in confusable_rules:
            rule["ruleset_source"] = "GoldKelch/qik-vrt"
        confusable_detail["source"] = "GoldKelch/qik-vrt"
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "SOURCE_DOMAIN_INVALID",
        ):
            self._evaluate(confusable_rules, {42: confusable_detail})

        variant_rules = copy.deepcopy(valid_rules)
        variant_detail = self._detail(42, bypass=[])
        for rule in variant_rules:
            rule["ruleset_source"] = "gOLDKELCH/QIK-VRT"
        variant_detail["source"] = "gOLDKELCH/QIK-VRT"
        canonical = self._evaluate(
            valid_rules,
            {42: self._detail(42, bypass=[])},
        )
        variant = self._evaluate(variant_rules, {42: variant_detail})
        self.assertEqual(
            canonical["protection_snapshot_sha256"],
            variant["protection_snapshot_sha256"],
        )
        self.assertEqual(
            variant["protection_snapshot"]["candidate_rulesets"][0]["source"],  # type: ignore[index]
            "Goldkelch/qik-vrt",
        )

        cross_domain = self._detail(42, bypass=[])
        cross_domain["source_type"] = "Organization"
        cross_domain["source"] = "Goldkelch"
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "SOURCE_BINDING_MISMATCH",
        ):
            self._evaluate(valid_rules, {42: cross_domain})

        contradictory_noncandidate = [
            *copy.deepcopy(valid_rules),
            self._rule(99, "pull_request"),
            self._rule(99, "update"),
        ]
        contradictory_noncandidate[-1]["ruleset_source_type"] = "Organization"
        contradictory_noncandidate[-1]["ruleset_source"] = "Goldkelch"
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "EFFECTIVE_SOURCE_CONTRADICTION",
        ):
            self._evaluate(
                contradictory_noncandidate,
                {42: self._detail(42, bypass=[])},
            )
        with mock.patch(
            "tools.qikvrt_mesh_heartbeat._gh_json",
            return_value=[[*contradictory_noncandidate]],
        ):
            observed = observe_ledger_ref_control(
                repository="Goldkelch/qik-vrt",
                source_head=HEAD,
                source_run_id=7,
            )
        self.assertEqual(observed["state"], "REOBSERVE")
        self.assertEqual(observed["d0"], 2)

    def test_effective_detail_contradictions_are_reobserve_evidence(self) -> None:
        rules = [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")]
        cases: list[dict[str, object]] = []
        wrong_target = self._detail(42, bypass=[])
        wrong_target["target"] = "tag"
        cases.append(wrong_target)
        inactive = self._detail(42, bypass=[])
        inactive["enforcement"] = "disabled"
        cases.append(inactive)
        missing_rule = self._detail(42, bypass=[])
        missing_rule["rules"] = [{"type": "deletion"}]
        cases.append(missing_rule)
        for detail in cases:
            with self.subTest(detail=detail):
                with self.assertRaisesRegex(
                    HeartbeatContractError,
                    "EFFECTIVE_DETAIL_CONTRADICTION",
                ):
                    self._evaluate(rules, {42: detail})
                with mock.patch(
                    "tools.qikvrt_mesh_heartbeat._gh_json",
                    side_effect=[[[*rules]], detail],
                ):
                    observed = observe_ledger_ref_control(
                        repository="Goldkelch/qik-vrt",
                        source_head=HEAD,
                        source_run_id=7,
                    )
                self.assertEqual(observed["state"], "REOBSERVE")
                self.assertEqual(observed["d0"], 2)

    def test_comparison_receipt_rederives_actual_snapshot_drift(self) -> None:
        expected = "sha256:" + "1" * 64
        observed = "sha256:" + "2" * 64
        valid = ledger_ref_control_reobserve(
            repository="Goldkelch/qik-vrt",
            source_head=HEAD,
            source_run_id=7,
            observation_phase="PRE_PUSH",
            blocker="LEDGER_REF_CONTROL_SNAPSHOT_DRIFT",
            expected_snapshot_sha256=expected,
            observed_snapshot_sha256=observed,
        )
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "LEDGER_REF_CONTROL_REOBSERVE",
        ):
            verify_ledger_ref_control_receipt(valid)

        equal_digest = copy.deepcopy(valid)
        equal_digest["observed_protection_snapshot_sha256"] = expected
        equal_digest = self._reseal(equal_digest)
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "comparison semantics are invalid",
        ):
            verify_ledger_ref_control_receipt(equal_digest)

        false_comparison = ledger_ref_control_reobserve(
            repository="Goldkelch/qik-vrt",
            source_head=HEAD,
            source_run_id=7,
            blocker="LEDGER_RULESET_API_FAILED",
        )
        false_comparison["first_blocker"] = "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT"
        false_comparison = self._reseal(false_comparison)
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "comparison mismatch",
        ):
            verify_ledger_ref_control_receipt(false_comparison)

    def test_initial_comparison_and_truthy_verifier_aliases_are_rejected(self) -> None:
        expected = "sha256:" + "1" * 64
        observed = "sha256:" + "2" * 64
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "comparison semantics are invalid",
        ):
            ledger_ref_control_reobserve(
                repository="Goldkelch/qik-vrt",
                source_head=HEAD,
                source_run_id=7,
                observation_phase="INITIAL",
                blocker="LEDGER_REF_CONTROL_SNAPSHOT_DRIFT",
                expected_snapshot_sha256=expected,
                observed_snapshot_sha256=observed,
            )

        valid = self._evaluate(
            [self._rule(42, "deletion"), self._rule(42, "non_fast_forward")],
            {42: self._detail(42, bypass=[])},
        )
        for alias in (1, 1.0, "yes"):
            with self.subTest(alias=alias):
                with self.assertRaisesRegex(
                    HeartbeatContractError,
                    "exact Boolean",
                ):
                    verify_ledger_ref_control_receipt(
                        valid,
                        allow_noncontrol_state=alias,  # type: ignore[arg-type]
                    )

        forged = ledger_ref_control_reobserve(
            repository="Goldkelch/qik-vrt",
            source_head=HEAD,
            source_run_id=7,
            observation_phase="PRE_PUSH",
            blocker="LEDGER_REF_CONTROL_SNAPSHOT_DRIFT",
            expected_snapshot_sha256=expected,
            observed_snapshot_sha256=observed,
        )
        forged["observation_phase"] = "INITIAL"
        forged = self._reseal(forged)
        with self.assertRaisesRegex(
            HeartbeatContractError,
            "comparison semantics are invalid",
        ):
            verify_ledger_ref_control_receipt(
                forged,
                allow_noncontrol_state=True,
            )


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
        self.assertIn(
            "tools/qikvrt_mesh_heartbeat.py ledger-ref-control",
            workflow,
        )
        self.assertIn(
            "tools/qikvrt_mesh_heartbeat.py enforce-ledger-ref-control",
            workflow,
        )
        self.assertNotIn("AUTHORIZED_TO_ATTEMPT_LEDGER_WRITE", workflow)
        observe_index = workflow.index(
            "Observe repository-enforced ledger ref administration"
        )
        preserve_index = workflow.index(
            "Preserve ledger ref administrative observation"
        )
        enforce_index = workflow.index("Enforce ledger ref administrative control")
        ledger_init_index = workflow.index('ledger="$RUNNER_TEMP/ledger"')
        prepush_index = workflow.index("ledger-ref-control-before-push.json")
        source_cas_index = workflow.index('source_remote_before_push="$(')
        ledger_cas_index = workflow.index('ledger_remote_before_push="$(')
        push_index = workflow.index('git -C "$ledger" push origin')
        terminal_control_index = workflow.index(
            "ledger-ref-control-after-readback.json"
        )
        self.assertLess(observe_index, preserve_index)
        self.assertLess(preserve_index, enforce_index)
        self.assertLess(enforce_index, ledger_init_index)
        self.assertLess(ledger_init_index, prepush_index)
        self.assertLess(prepush_index, source_cas_index)
        self.assertLess(source_cas_index, ledger_cas_index)
        self.assertLess(ledger_cas_index, push_index)
        self.assertLess(push_index, terminal_control_index)
        self.assertEqual(workflow.count("--expected-snapshot-receipt"), 2)
        self.assertEqual(workflow.count("--comparison-output"), 3)
        self.assertEqual(workflow.count("--observer-run-id"), 6)
        self.assertEqual(workflow.count("--observer-run-attempt"), 6)
        self.assertEqual(workflow.count("--observation-phase INITIAL"), 2)
        self.assertEqual(workflow.count("--observation-phase PRE_PUSH"), 2)
        self.assertEqual(workflow.count("--observation-phase POST_READBACK"), 2)
        self.assertIn(
            "ledger-ref-control-comparison-initial.json",
            workflow,
        )
        self.assertIn(
            "ledger-ref-control-comparison-before-push.json",
            workflow,
        )
        self.assertIn(
            "ledger-ref-control-comparison-after-readback.json",
            workflow,
        )
        self.assertIn(
            '--ledger-transition "$ledger_transition"',
            workflow,
        )
        self.assertIn("Preserve repeated ledger ref control observations", workflow)
        self.assertIn("if: always()", workflow)
        control_artifact_names = re.findall(
            r"name: (qikvrt-mesh-heartbeat-ledger[^\n]+)",
            workflow,
        )
        self.assertEqual(len(control_artifact_names), 3)
        for artifact_name in control_artifact_names:
            self.assertIn("${{ github.run_id }}", artifact_name)
            self.assertIn("${{ github.run_attempt }}", artifact_name)
        repeated_upload = workflow.split(
            "Preserve repeated ledger ref control observations",
            1,
        )[1]
        self.assertIn(
            "${{ runner.temp }}/ledger-ref-control.json",
            repeated_upload,
        )
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
        self.assertIn("ledger_ref_control_observation_phase", workflow)
        self.assertIn("ledger_ref_control_observer_run_id", workflow)
        self.assertIn("ledger_ref_control_observer_run_attempt", workflow)
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

    def test_policy_requires_external_ledger_ref_administration(self) -> None:
        policy = json.loads(
            (ROOT / "policy/QIKVRT_MESH_HEARTBEAT_V1.json").read_text(
                encoding="utf-8"
            )
        )["trusted_main_ledger_writer"]
        self.assertTrue(policy["repository_enforced_ref_protection_required"])
        self.assertEqual(
            policy["ruleset_observation_endpoint"],
            "GET_REPOSITORY_RULES_FOR_BRANCH_AND_RULESET_DETAIL",
        )
        self.assertEqual(
            policy["required_active_rules_on_one_ruleset"],
            ["deletion", "non_fast_forward"],
        )
        self.assertTrue(
            policy["ruleset_observation_must_complete_before_ledger_mutation"]
        )
        self.assertTrue(policy["literal_ledger_ref_include_required"])
        self.assertTrue(policy["empty_exclude_list_required"])
        self.assertTrue(policy["visible_empty_bypass_actor_list_required"])
        self.assertTrue(
            policy["bypass_actor_visibility_requires_ruleset_write_authority"]
        )
        self.assertTrue(policy["control_receipts_same_source_context_required"])
        self.assertTrue(
            policy["control_receipt_observer_run_and_attempt_required"]
        )
        self.assertEqual(
            policy["control_receipt_sha256_self_seal_scope"],
            "BYTE_INTEGRITY_ONLY",
        )
        self.assertFalse(
            policy["control_receipt_sha256_self_seal_is_keyed_authentication"]
        )
        self.assertEqual(
            policy["control_observation_phases"],
            ["INITIAL", "PRE_PUSH", "POST_READBACK"],
        )
        self.assertEqual(policy["baseline_transition_required"], "NONE")
        self.assertTrue(policy["current_transition_must_match_phase"])
        self.assertEqual(
            policy["supported_ruleset_source_types"],
            ["Organization", "Repository"],
        )
        self.assertTrue(
            policy["repository_ruleset_source_must_match_repository"]
        )
        self.assertTrue(
            policy["organization_ruleset_source_must_match_repository_owner"]
        )
        self.assertTrue(policy["ruleset_source_identifiers_ascii_only"])
        self.assertEqual(
            policy["effective_detail_contradiction_state"],
            "REOBSERVE",
        )
        self.assertTrue(
            policy["source_and_ledger_cas_after_prepush_observation"]
        )
        self.assertTrue(policy["identical_control_snapshot_required_before_push"])
        self.assertTrue(
            policy["identical_control_snapshot_required_after_readback"]
        )
        self.assertEqual(policy["missing_control_state"], "REQUEST_AUTHORITY")
        self.assertEqual(policy["incomplete_observation_state"], "REOBSERVE")
        self.assertFalse(policy["repository_ruleset_mutation_allowed"])
        self.assertFalse(policy["ruleset_push_atomicity_observed"])
        self.assertTrue(
            policy["post_readback_control_is_detection_not_prevention"]
        )

    def test_ledger_ref_control_uses_bounded_read_only_github_observation(self) -> None:
        source = (ROOT / "tools/qikvrt_mesh_heartbeat.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('quote(branch, safe=\'\')', source)
        self.assertIn('"--paginate", "--slurp"', source)
        self.assertIn("?includes_parents=true", source)
        self.assertIn("run_bounded(command, timeout=60", source)
        self.assertIn("max_output_bytes=4 * 1024 * 1024", source)
        self.assertIn("LEDGER_RULESET_BYPASS_VISIBILITY_REQUIRED", source)
        for mutation in ('"POST"', '"PATCH"', '"PUT"', '"DELETE"'):
            self.assertNotIn(mutation, source)


if __name__ == "__main__":
    unittest.main()
