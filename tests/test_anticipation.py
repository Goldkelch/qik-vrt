# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools import qikvrt_anticipation as anticipation


ROOT = Path(__file__).resolve().parents[1]


class GlobalSystemClosureContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = anticipation.load_policy(ROOT)
        self.input_value = anticipation.load_anticipation_input(ROOT)

    def test_repository_contract_is_bounded_and_valid(self) -> None:
        anticipation.validate_policy(self.policy)
        anticipation.validate_input(self.input_value, ROOT)
        self.assertEqual(
            self.policy["completion_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )
        self.assertFalse(
            self.policy["status_projection"]["external_effects_may_be_dispatched"]
        )

    def test_monotonic_improvement_is_measured_and_non_regressing(self) -> None:
        previous = {"a": 2, "b": 4}
        self.assertEqual(
            anticipation.classify_monotonic_transition(previous, {"a": 3, "b": 4}),
            "NON_REGRESSING_GATE_IMPROVEMENT",
        )
        self.assertEqual(
            anticipation.classify_monotonic_transition(previous, previous),
            "BYTE_STABLE_NO_OP",
        )
        self.assertEqual(
            anticipation.classify_monotonic_transition(previous, {"a": 1, "b": 5}),
            "REJECTED_REGRESSION",
        )

    def test_metric_shape_drift_fails_closed(self) -> None:
        with self.assertRaisesRegex(anticipation.ClosureError, "metric sets"):
            anticipation.classify_monotonic_transition({"a": 1}, {"b": 1})

    def test_checkpoint_hash_binds_predecessor(self) -> None:
        checkpoint = {"checkpoint_id": "test", "value": 1}
        zero_hash = "0" * 64
        first = anticipation.checkpoint_hash(
            checkpoint, previous_checkpoint_sha256=zero_hash
        )
        second = anticipation.checkpoint_hash(
            checkpoint, previous_checkpoint_sha256="1" * 64
        )
        self.assertNotEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_false_completion_claim_in_policy_is_blocked(self) -> None:
        policy = copy.deepcopy(self.policy)
        policy["completion_claims"]["PASS"] = True
        with self.assertRaisesRegex(anticipation.ClosureError, "false completion"):
            anticipation.validate_policy(policy)

    def test_bound_current_status_tamper_is_blocked(self) -> None:
        input_value = copy.deepcopy(self.input_value)
        input_value["source_bindings"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(anticipation.ClosureError, "digest drift"):
            anticipation.validate_input(input_value, ROOT)


class AnticipationProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = anticipation.load_policy(ROOT)
        self.input_value = anticipation.load_anticipation_input(ROOT)

    def test_repository_projections_are_byte_current(self) -> None:
        verified = anticipation.verify_projections(ROOT)
        self.assertEqual(set(verified), {path.as_posix() for path in anticipation.PROJECTION_PATHS})

    def test_repeated_derivation_is_byte_identical(self) -> None:
        first = anticipation.build_projections(self.policy, self.input_value)
        second = anticipation.build_projections(self.policy, self.input_value)
        self.assertEqual(first, second)

    def test_equivalent_planner_is_replaceable(self) -> None:
        expected = anticipation.build_projections(self.policy, self.input_value)

        def replacement(value: dict[str, object]) -> dict[str, object]:
            return dict(value["next_effect"])  # type: ignore[arg-type]

        observed = anticipation.build_projections(
            self.policy, self.input_value, planner=replacement
        )
        self.assertEqual(expected, observed)

    def test_competing_planner_fails_closed(self) -> None:
        def competing(value: dict[str, object]) -> dict[str, object]:
            result = dict(value["next_effect"])  # type: ignore[arg-type]
            result["effect_id"] = "COMPETING_EFFECT"
            return result

        with self.assertRaisesRegex(
            anticipation.ClosureError, "TREND_DERIVATION_NONDETERMINISTIC"
        ):
            anticipation.build_projections(
                self.policy, self.input_value, planner=competing
            )

    def test_insufficient_observations_fail_closed(self) -> None:
        input_value = copy.deepcopy(self.input_value)
        input_value["observations"] = input_value["observations"][:1]
        with self.assertRaisesRegex(
            anticipation.ClosureError, "INSUFFICIENT_VERIFIED_OBSERVATIONS"
        ):
            anticipation.validate_input(input_value)

    def test_activity_without_metric_change_is_not_progress(self) -> None:
        observations = copy.deepcopy(self.input_value["observations"])
        observations[1]["metrics"] = copy.deepcopy(observations[0]["metrics"])
        trend = anticipation.derive_trend(observations)
        self.assertEqual(trend["direction"], "STABLE")
        self.assertFalse(trend["productive_progress"])
        self.assertEqual(trend["basis"], ["BYTE_STABLE_NO_OP"])

    def test_checkpoint_chain_is_contiguous_and_false_pass_free(self) -> None:
        outputs = anticipation.build_projections(self.policy, self.input_value)
        first = json.loads(outputs[anticipation.CHECKPOINT_1_PATH])
        second = json.loads(outputs[anticipation.CHECKPOINT_2_PATH])
        self.assertEqual(
            second["previous_checkpoint_sha256"], first["checkpoint_sha256"]
        )
        for checkpoint in (first, second):
            self.assertEqual(
                checkpoint["completion_claims"],
                {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
            )
            self.assertEqual(checkpoint["external_effect"], "NONE")

    def test_current_projection_matches_declared_schema_shape(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/qikvrt-anticipation-state.schema.json").read_text(
                encoding="utf-8"
            )
        )
        current = json.loads(
            anticipation.build_projections(self.policy, self.input_value)[
                anticipation.CURRENT_PATH
            ]
        )
        self.assertTrue(set(schema["required"]).issubset(current))
        self.assertEqual(
            current["schema_version"],
            schema["properties"]["schema_version"]["const"],
        )
        self.assertFalse(current["execution"]["automatically_dispatched"])
        self.assertEqual(
            current["current_state"]["effect_state"], "EFFECT_ACK_CONTINUE"
        )

    def test_materialization_has_no_external_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            copied_paths = [
                anticipation.POLICY_PATH,
                anticipation.INPUT_PATH,
                *(
                    Path(binding["path"])
                    for binding in self.input_value["source_bindings"]
                ),
            ]
            for relative in copied_paths:
                destination = root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / relative, destination)
            result = anticipation.materialize(root)
            self.assertEqual(result["external_effect"], "NONE")
            self.assertEqual(result["effect_state"], "EFFECT_ACK_CONTINUE")
            self.assertEqual(
                sorted(
                    path.relative_to(root).as_posix()
                    for path in root.rglob("*")
                    if path.is_file() and path.relative_to(root) not in copied_paths
                ),
                sorted(path.as_posix() for path in anticipation.PROJECTION_PATHS),
            )


if __name__ == "__main__":
    unittest.main()
