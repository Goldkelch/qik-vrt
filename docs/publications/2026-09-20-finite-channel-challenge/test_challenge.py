# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Synthetic evaluator tests. These fixtures are NOT physical observations."""
import copy
import unittest
from fractions import Fraction

from challenge import ALPHA, LAG_NS, N, SCHEMA, commitment, score, tail_probability, threshold


def synthetic_record(correct=N // 2):
    predictions = [0] * N
    return {
        "schema": SCHEMA,
        "preregistration_sha256": "a" * 64,
        "predictions": predictions,
        "future_choices": [0] * correct + [1] * (N - correct),
        "prediction_sha256": commitment(predictions),
        "sealed_ns": 1,
        "choices_started_ns": 1 + LAG_NS,
    }


class ScorerTests(unittest.TestCase):
    def test_small_exact_probability(self):
        self.assertEqual(tail_probability(3, 2), Fraction(1, 2))
        self.assertEqual(tail_probability(3, 3), Fraction(1, 8))
        self.assertEqual(tail_probability(0, 0), 1)

    def test_threshold_is_minimal(self):
        k = threshold()
        self.assertLessEqual(tail_probability(N, k), ALPHA)
        self.assertGreater(tail_probability(N, k - 1), ALPHA)

    def test_chance_level_negative_control(self):
        self.assertFalse(score(synthetic_record(), "a" * 64)["statistical_threshold_met"])

    def test_injected_perfect_control_is_not_a_physics_claim(self):
        result = score(synthetic_record(N), "a" * 64)
        self.assertTrue(result["statistical_threshold_met"])
        self.assertFalse(result["future_to_past_channel_established"])

    def test_missing_trial_rejected(self):
        record = synthetic_record()
        record["future_choices"].pop()
        with self.assertRaises(ValueError):
            score(record, "a" * 64)

    def test_altered_prediction_rejected(self):
        record = synthetic_record()
        record["predictions"][0] = 1
        with self.assertRaises(ValueError):
            score(record, "a" * 64)

    def test_late_seal_rejected(self):
        record = synthetic_record()
        record["sealed_ns"] = record["choices_started_ns"]
        with self.assertRaises(ValueError):
            score(record, "a" * 64)

    def test_preregistration_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            score(synthetic_record(), "b" * 64)

    def test_nonbits_and_boolean_timestamps_rejected(self):
        for path, value in (("predictions", True), ("future_choices", 2)):
            record = synthetic_record()
            record[path][0] = value
            with self.assertRaises(ValueError):
                score(record, "a" * 64)
        record = synthetic_record()
        record["sealed_ns"] = True
        with self.assertRaises(ValueError):
            score(record, "a" * 64)

    def test_forged_chronology_is_explicitly_not_authenticated(self):
        # Valid-looking invented timestamps are not a trusted clock receipt.
        result = score(copy.deepcopy(synthetic_record(N)), "a" * 64)
        self.assertFalse(result["physical_chronology_authenticated"])
        self.assertFalse(result["independent_randomization_authenticated"])


if __name__ == "__main__":
    unittest.main()
