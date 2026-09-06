#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
import importlib.util
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_integer_dgemm", ROOT / "tools/qikvrt_integer_dgemm.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class IntegerDgemmTests(unittest.TestCase):
    def test_exact_binary_values_match_reference(self):
        left = [[1.0, -2.0], [0.5, 4.0]]
        right = [[3.0, 0.25], [-1.0, 2.0]]
        self.assertEqual(MODULE.integer_dgemm(left, right), MODULE.reference_dgemm(left, right))

    def test_fractional_values_have_small_error(self):
        left = [[0.1, -1.25], [3.5, 2.0 ** -20]]
        right = [[-2.0, 0.75], [4.0, 2.0 ** -10]]
        actual = MODULE.integer_dgemm(left, right)
        expected = MODULE.reference_dgemm(left, right)
        self.assertLessEqual(MODULE._max_abs_error(actual, expected), 1e-15)

    def test_contract_rejects_non_finite_values(self):
        with self.assertRaises(ValueError):
            MODULE.integer_dgemm([[float("nan")]], [[1.0]])

    def test_contract_rejects_bad_dimensions(self):
        with self.assertRaises(ValueError):
            MODULE.integer_dgemm([[1.0, 2.0]], [[1.0]])

    def test_benchmark_is_explicitly_non_release(self):
        result = MODULE.run_benchmark(size=2, repetitions=1)
        self.assertFalse(result["claims"]["native_int8_hardware"])
        self.assertFalse(result["claims"]["qikvrt_speedup"])
        self.assertFalse(result["claims"]["energy_measurement"])


if __name__ == "__main__":
    unittest.main()
