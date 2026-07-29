#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from tools import qikvrt_anticipation as anticipation
from tools.qikvrt_seed_common import write_json


class GlobalSystemClosureContractTests(unittest.TestCase):
    def test_repository_contract_is_bounded_and_valid(self) -> None:
        receipt = anticipation.check()
        self.assertEqual(receipt["state"], "CONTINUE")
        self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertEqual(
            receipt["completion_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )
        self.assertEqual(receipt["verified_projection_count"], 7)

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
        for checkpoint in (first, second):
            self.assertEqual(checkpoint["external_effect"], "NONE")
            self.assertFalse(any(checkpoint["completion_claims"].values()))

    def test_materialization_has_no_external_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy, evidence = anticipation.load_contract()
            input_value = anticipation.load_anticipation_input()
            write_json(root / anticipation.POLICY_PATH, policy)
            write_json(root / anticipation.EVIDENCE_PATH, evidence)
            write_json(root / anticipation.INPUT_PATH, input_value)
            receipt = anticipation.materialize(root)
            self.assertEqual(receipt["external_effect"], "NONE")
            self.assertEqual(receipt["effect_state"], "EFFECT_ACK_CONTINUE")
            self.assertEqual(receipt["output_count"], 7)


if __name__ == "__main__":
    unittest.main()
