#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import qikvrt_anticipation as anticipation
from tools.qikvrt_seed_common import write_json
from src.qikvrt_effect_ack import (
    ConnectionDecision,
    EffectAckEngine,
    EffectAckRequest,
    EffectState,
    RiskLevel,
)


class GlobalSystemClosureContractTests(unittest.TestCase):
    def test_repository_contract_is_bounded_and_valid(self) -> None:
        receipt = anticipation.check()
        self.assertEqual(receipt["state"], "CONTINUE")
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertEqual(
            receipt["completion_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )
        self.assertEqual(receipt["verified_projection_count"], 9)

    def test_monotonic_improvement_is_measured_and_non_regressing(self) -> None:
        self.assertEqual(
            anticipation.classify_monotonic_transition(
                {"tests": 6, "receipts": 1}, {"tests": 7, "receipts": 1}
            ),
            "NON_REGRESSING_GATE_IMPROVEMENT",
        )
        self.assertEqual(
            anticipation.classify_monotonic_transition(
                {"tests": 6, "receipts": 1}, {"tests": 6, "receipts": 1}
            ),
            "BYTE_STABLE_NO_OP",
        )
        self.assertEqual(
            anticipation.classify_monotonic_transition(
                {"tests": 6, "receipts": 1}, {"tests": 7, "receipts": 0}
            ),
            "REJECTED_REGRESSION",
        )

    def test_metric_shape_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(anticipation.ClosureError, "metric sets"):
            anticipation.classify_monotonic_transition(
                {"tests": 6}, {"tests": 6, "receipts": 1}
            )

    def test_checkpoint_hash_binds_predecessor(self) -> None:
        checkpoint = {"checkpoint_id": "gsc-0001", "state": "CONTRACT_BOUND"}
        first = anticipation.checkpoint_hash(
            checkpoint, previous_checkpoint_sha256=anticipation.ZERO_SHA256
        )
        second = anticipation.checkpoint_hash(
            checkpoint, previous_checkpoint_sha256="1" * 64
        )
        self.assertNotEqual(first, second)
        self.assertEqual(
            first,
            anticipation.checkpoint_hash(
                checkpoint, previous_checkpoint_sha256=anticipation.ZERO_SHA256
            ),
        )

    def test_false_completion_claim_in_policy_is_blocked(self) -> None:
        policy, evidence = anticipation.load_contract()
        policy = copy.deepcopy(policy)
        policy["completion_claims"]["PASS"] = True
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / anticipation.POLICY_PATH, policy)
            write_json(root / anticipation.EVIDENCE_PATH, evidence)
            with self.assertRaisesRegex(anticipation.ClosureError, "false completion"):
                anticipation.check(root)

    def test_functionality_evidence_cannot_claim_merge(self) -> None:
        policy, evidence = anticipation.load_contract()
        evidence = copy.deepcopy(evidence)
        evidence["authority_evidence"]["merged"] = True
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_json(root / anticipation.POLICY_PATH, policy)
            write_json(root / anticipation.EVIDENCE_PATH, evidence)
            with self.assertRaisesRegex(anticipation.ClosureError, "PR boundary"):
                anticipation.validate_functionality_evidence(evidence)


class AnticipationProjectionTests(unittest.TestCase):
    def test_repository_projections_are_byte_current(self) -> None:
        expected = anticipation.expected_projections()
        self.assertEqual(set(expected), set(anticipation.PROJECTION_PATHS))
        for relative, raw in expected.items():
            self.assertEqual((anticipation.ROOT / relative).read_bytes(), raw)

    def test_repeated_derivation_is_byte_identical(self) -> None:
        policy, evidence = anticipation.load_contract()
        input_value = anticipation.load_anticipation_input()
        first = anticipation.build_projections(policy, evidence, input_value)
        second = anticipation.build_projections(policy, evidence, input_value)
        self.assertEqual(first, second)

    def test_equivalent_planner_is_replaceable(self) -> None:
        policy, evidence = anticipation.load_contract()
        input_value = anticipation.load_anticipation_input()

        def replacement(value: dict[str, object]) -> dict[str, object]:
            return copy.deepcopy(value["next_effect"])

        canonical = anticipation.build_projections(policy, evidence, input_value)
        replaced = anticipation.build_projections(
            policy, evidence, input_value, planner=replacement
        )
        self.assertEqual(canonical, replaced)

    def test_competing_planner_fails_closed(self) -> None:
        policy, evidence = anticipation.load_contract()
        input_value = anticipation.load_anticipation_input()

        def competing(value: dict[str, object]) -> dict[str, object]:
            result = copy.deepcopy(value["next_effect"])
            result["effect_id"] = "DIFFERENT_EFFECT"
            return result

        with self.assertRaisesRegex(
            anticipation.ClosureError, "TREND_DERIVATION_NONDETERMINISTIC"
        ):
            anticipation.build_projections(
                policy, evidence, input_value, planner=competing
            )

    def test_insufficient_observations_fail_closed(self) -> None:
        input_value = anticipation.load_anticipation_input()
        input_value["observations"] = input_value["observations"][:1]
        with self.assertRaisesRegex(
            anticipation.ClosureError, "INSUFFICIENT_VERIFIED_OBSERVATIONS"
        ):
            anticipation.validate_input(input_value)

    def test_activity_without_gate_change_is_not_progress(self) -> None:
        observations = [
            {"metrics": {"gates": 2, "receipts": 1}},
            {"metrics": {"gates": 2, "receipts": 1}},
        ]
        trend = anticipation.derive_trend(observations)
        self.assertEqual(trend["direction"], "STABLE")
        self.assertFalse(trend["productive_progress"])

    def test_checkpoint_chain_is_contiguous_and_false_pass_free(self) -> None:
        first = anticipation.read_json(
            anticipation.ROOT / anticipation.CHECKPOINT_1_PATH
        )
        second = anticipation.read_json(
            anticipation.ROOT / anticipation.CHECKPOINT_2_PATH
        )
        third = anticipation.read_json(
            anticipation.ROOT / anticipation.CHECKPOINT_3_PATH
        )
        self.assertEqual(
            second["previous_checkpoint_sha256"], first["checkpoint_sha256"]
        )
        self.assertEqual(
            first["checkpoint_sha256"],
            anticipation.checkpoint_hash(
                first, previous_checkpoint_sha256=anticipation.ZERO_SHA256
            ),
        )
        self.assertEqual(
            second["checkpoint_sha256"],
            anticipation.checkpoint_hash(
                second,
                previous_checkpoint_sha256=first["checkpoint_sha256"],
            ),
        )
        self.assertEqual(
            third["previous_checkpoint_sha256"], second["checkpoint_sha256"]
        )
        self.assertEqual(
            third["checkpoint_sha256"],
            anticipation.checkpoint_hash(
                third,
                previous_checkpoint_sha256=second["checkpoint_sha256"],
            ),
        )
        for checkpoint in (first, second, third):
            self.assertFalse(any(checkpoint["completion_claims"].values()))
        self.assertEqual(first["external_effect"], "NONE")
        self.assertEqual(second["external_effect"], "NONE")
        self.assertEqual(third["external_effect"], "NONE_INTENTS_ONLY")

    def test_materialization_has_no_external_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            required = (
                anticipation.POLICY_PATH,
                anticipation.EVIDENCE_PATH,
                anticipation.INPUT_PATH,
                anticipation.TARGETED_ENVELOPE_PATH,
                anticipation.ZENODO_QUEUE_PATH,
                anticipation.CHECKPOINT_2_PATH,
                Path("schemas/qikvrt-targeted-effect-envelope.schema.json"),
                Path(
                    "anticipation/effects/payloads/"
                    "system-closure-stage3.json"
                ),
                Path("registry/NODEMESH_INDEX.json"),
                Path("registry/NODEMESH_STATUS.json"),
                Path(
                    "registry/nodes/"
                    "a84f157a-cef2-4c47-bca9-8f407085bdbe.json"
                ),
                Path("formalization/QIKVRT_Formalization_v2.0/lean-toolchain"),
                Path("formalization/QIKVRT_Formalization_v2.0/lakefile.toml"),
            )
            for relative in required:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(anticipation.ROOT / relative, target)
            receipt = anticipation.materialize(root)
            self.assertEqual(receipt["external_effect"], "NONE")
            self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
            self.assertEqual(receipt["output_count"], 9)


class TargetedEffectAndZenodoQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.envelope = anticipation.load_targeted_envelope()

    def test_repository_targeted_intent_is_stale_and_not_dispatched(self) -> None:
        evaluation = anticipation.evaluate_targeted_envelope(self.envelope)
        self.assertEqual(evaluation["state"], "BLOCK")
        self.assertIn("TARGET_NODE_NOT_FRESH", evaluation["failure_classes"])
        self.assertFalse(evaluation["dispatch_eligible"])
        self.assertFalse(evaluation["dispatch_attempted"])
        self.assertFalse(evaluation["transport_ack_is_effect_ack"])

    def test_payload_hash_tamper_blocks(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        envelope["payload"]["sha256"] = "0" * 64
        evaluation = anticipation.evaluate_targeted_envelope(envelope)
        self.assertEqual(evaluation["state"], "BLOCK")
        self.assertIn(
            "PAYLOAD_HASH_OR_SIZE_MISMATCH", evaluation["failure_classes"]
        )

    def test_unknown_target_blocks(self) -> None:
        envelope = copy.deepcopy(self.envelope)
        envelope["target"]["node_guid"] = "00000000-0000-4000-8000-000000000000"
        evaluation = anticipation.evaluate_targeted_envelope(envelope)
        self.assertEqual(evaluation["state"], "BLOCK")
        self.assertIn("TARGET_NODE_NOT_UNIQUE", evaluation["failure_classes"])

    def fresh_fixture(
        self,
        root: Path,
        *,
        evaluated_at: str,
        not_before: str,
        expires: str,
        done: bool,
    ) -> dict[str, object]:
        envelope = copy.deepcopy(self.envelope)
        paths = (
            Path(envelope["payload"]["path"]),
            Path(envelope["target"]["registry_path"]),
            Path(envelope["target"]["registry_index_path"]),
            Path(envelope["target"]["registry_status_path"]),
            anticipation.CHECKPOINT_2_PATH,
        )
        for relative in paths:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(anticipation.ROOT / relative, target)
        status_path = root / envelope["target"]["registry_status_path"]
        status = anticipation.read_json(status_path)
        status["nodes"][0]["heartbeat_status"] = "FRESH"
        status["nodes"][0]["expires_utc"] = "2026-08-02T00:00:00Z"
        write_json(status_path, status)
        for path_key, hash_key in (
            ("registry_path", "registry_entry_sha256"),
            ("registry_index_path", "registry_index_sha256"),
            ("registry_status_path", "registry_status_sha256"),
        ):
            raw = (root / envelope["target"][path_key]).read_bytes()
            envelope["target"][hash_key] = hashlib.sha256(raw).hexdigest()
        envelope["timing"] = {
            "evaluated_at_utc": evaluated_at,
            "not_before_utc": not_before,
            "expires_utc": expires,
        }
        if done:
            subject = anticipation.targeted_effect_subject(envelope)
            evidence_ref = "sha256:" + hashlib.sha256(
                b"targeted-effect-fixture"
            ).hexdigest()
            result = EffectAckEngine().evaluate(
                EffectAckRequest(
                    protocol_root_id="qikvrt:test:targeted-effect",
                    input_id=envelope["envelope_id"],
                    payload=subject,
                    declared_input_hash=(
                        "sha256:" + hashlib.sha256(subject).hexdigest()
                    ),
                    transport_ack=True,
                    origin_checked=True,
                    context_checked=True,
                    semantics_reconstructed=True,
                    effect_anticipated=True,
                    risk_classified=True,
                    risk_level=RiskLevel.LOW,
                    responsibility_assigned=True,
                    responsibility_owner="Ingolf Lohmann",
                    connection_decision=ConnectionDecision.RELEASE,
                    policy_allows_release=True,
                    reasons=("effect-specific fixture evaluation",),
                    evidence_refs=(evidence_ref,),
                    required_evidence_refs=(evidence_ref,),
                    open_questions=(),
                    next_required_checks=(),
                ),
                created_utc=evaluated_at,
            )
            self.assertIs(result.state, EffectState.EFFECT_ACK_DONE)
            protocol_path = Path(
                "receipts/effect-ack/targeted-effect-fixture.json"
            )
            write_json(root / protocol_path, result.protocol.to_dict())
            envelope["authorization"] = {
                "responsible_human": "Ingolf Lohmann",
                "origin_authenticated": True,
                "effect_ack_state": "EFFECT_ACK_DONE",
                "effect_ack_protocol_path": protocol_path.as_posix(),
                "effect_ack_protocol_hash": result.protocol.protocol_hash,
                "effect_ack_evaluated_at_utc": evaluated_at,
            }
        return envelope

    def test_fresh_target_before_time_remains_continue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.fresh_fixture(
                root,
                evaluated_at="2026-08-01T11:59:00Z",
                not_before="2026-08-01T12:00:00Z",
                expires="2026-08-01T12:15:00Z",
                done=True,
            )
            evaluation = anticipation.evaluate_targeted_envelope(envelope, root)
        self.assertEqual(evaluation["state"], "CONTINUE_NOT_YET_DUE")
        self.assertFalse(evaluation["dispatch_eligible"])

    def test_due_target_without_fresh_ack_remains_continue(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.fresh_fixture(
                root,
                evaluated_at="2026-08-01T12:01:00Z",
                not_before="2026-08-01T12:00:00Z",
                expires="2026-08-01T12:15:00Z",
                done=False,
            )
            evaluation = anticipation.evaluate_targeted_envelope(envelope, root)
        self.assertEqual(evaluation["state"], "CONTINUE_AWAITING_FRESH_EFFECT_ACK")
        self.assertFalse(evaluation["dispatch_eligible"])

    def test_claimed_done_without_bound_protocol_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.fresh_fixture(
                root,
                evaluated_at="2026-08-01T12:01:00Z",
                not_before="2026-08-01T12:00:00Z",
                expires="2026-08-01T12:15:00Z",
                done=False,
            )
            envelope["authorization"]["effect_ack_state"] = "EFFECT_ACK_DONE"
            evaluation = anticipation.evaluate_targeted_envelope(envelope, root)
        self.assertEqual(evaluation["state"], "BLOCK")
        self.assertIn("FALSE_EFFECT_ACK_DONE", evaluation["failure_classes"])

    def test_due_target_with_fresh_done_is_only_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.fresh_fixture(
                root,
                evaluated_at="2026-08-01T12:01:00Z",
                not_before="2026-08-01T12:00:00Z",
                expires="2026-08-01T12:15:00Z",
                done=True,
            )
            evaluation = anticipation.evaluate_targeted_envelope(envelope, root)
        self.assertEqual(
            evaluation["state"], "ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_DISPATCH"
        )
        self.assertTrue(evaluation["dispatch_eligible"])
        self.assertFalse(evaluation["dispatch_attempted"])

    def test_expired_window_blocks_even_with_done(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            envelope = self.fresh_fixture(
                root,
                evaluated_at="2026-08-01T12:16:00Z",
                not_before="2026-08-01T12:00:00Z",
                expires="2026-08-01T12:15:00Z",
                done=True,
            )
            evaluation = anticipation.evaluate_targeted_envelope(envelope, root)
        self.assertEqual(evaluation["state"], "BLOCK")
        self.assertIn("DELIVERY_WINDOW_EXPIRED", evaluation["failure_classes"])

    def test_zenodo_queue_is_inert_until_machine_proof(self) -> None:
        queue = anticipation.load_zenodo_queue()
        evaluation = anticipation.evaluate_zenodo_queue(queue)
        self.assertEqual(evaluation["state"], "BLOCKED_AWAITING_MACHINE_PROOF")
        self.assertFalse(evaluation["network_mutation_allowed"])
        self.assertFalse(evaluation["network_mutation_attempted"])
        self.assertIn(
            "formal_claims_have_fresh_lean_lake_receipts",
            evaluation["missing_gates"],
        )

    def test_zenodo_queue_cannot_predeclare_a_gate(self) -> None:
        queue = anticipation.load_zenodo_queue()
        queue["gates"]["exact_candidate_frozen"] = True
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in (
                anticipation.ZENODO_QUEUE_PATH,
                Path("formalization/QIKVRT_Formalization_v2.0/lean-toolchain"),
                Path("formalization/QIKVRT_Formalization_v2.0/lakefile.toml"),
            ):
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                if relative == anticipation.ZENODO_QUEUE_PATH:
                    write_json(target, queue)
                else:
                    shutil.copyfile(anticipation.ROOT / relative, target)
            with self.assertRaisesRegex(
                anticipation.ClosureError, "premature satisfied gate"
            ):
                anticipation.load_zenodo_queue(root)


if __name__ == "__main__":
    unittest.main()
