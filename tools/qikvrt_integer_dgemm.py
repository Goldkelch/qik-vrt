#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic FP64 matrix multiplication using exact INT8 limbs.

The implementation is a reference path, not a vendor-tuned DGEMM.  Each finite
binary64 value is represented as signed base-128 INT8 limbs and an exponent.
Products are accumulated as bounded integer buckets and converted to FP64 only
for the final summation.  This makes the arithmetic contract explicit without
claiming native INT8 hardware execution.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
import time
from typing import Sequence


INT8_MIN = -128
INT8_MAX = 127
INT32_MIN = -(1 << 31)
INT32_MAX = (1 << 31) - 1
BASE = 1 << 7


def _mantissa_and_exponent(value: float) -> tuple[int, int]:
    if not math.isfinite(value):
        raise ValueError("only finite binary64 values are supported")
    numerator, denominator = value.as_integer_ratio()
    exponent = 0
    while denominator > 1:
        denominator >>= 1
        exponent -= 1
    return numerator, exponent


def _limbs(value: float) -> tuple[int, tuple[int, ...], int]:
    mantissa, exponent = _mantissa_and_exponent(value)
    sign = -1 if mantissa < 0 else 1
    mantissa = abs(mantissa)
    limbs: list[int] = []
    while mantissa:
        limbs.append(mantissa % BASE)
        mantissa //= BASE
    return sign, tuple(limbs or [0]), exponent


def _shape(matrix: Sequence[Sequence[float]]) -> tuple[int, int]:
    rows = len(matrix)
    columns = len(matrix[0]) if rows else 0
    if any(len(row) != columns for row in matrix):
        raise ValueError("matrix rows must have equal length")
    return rows, columns


def integer_dgemm(
    left: Sequence[Sequence[float]],
    right: Sequence[Sequence[float]],
) -> list[list[float]]:
    """Return ``left @ right`` through INT8 limbs and integer accumulation.

    The final conversion uses Python's correctly rounded binary64 conversion.
    Each exponent bucket is flushed in INT32-sized chunks; therefore the
    contract is explicit about the accumulator width even though this portable
    reference implementation uses Python integers for the bucket sum.
    """

    left_rows, inner = _shape(left)
    right_rows, columns = _shape(right)
    if inner != right_rows:
        raise ValueError("matrix dimensions are incompatible")
    left_parts = [[_limbs(float(value)) for value in row] for row in left]
    right_parts = [[_limbs(float(value)) for value in row] for row in right]
    result: list[list[float]] = []
    for i in range(left_rows):
        output_row: list[float] = []
        for j in range(columns):
            buckets: dict[int, int] = {}
            for k in range(inner):
                left_sign, left_limbs, left_exp = left_parts[i][k]
                right_sign, right_limbs, right_exp = right_parts[k][j]
                for left_index, left_limb in enumerate(left_limbs):
                    for right_index, right_limb in enumerate(right_limbs):
                        product = (
                            left_sign
                            * right_sign
                            * left_limb
                            * right_limb
                        )
                        if not -(INT8_MAX * INT8_MAX) <= product <= INT8_MAX * INT8_MAX:
                            raise AssertionError("INT8 limb product escaped contract")
                        exponent = left_exp + right_exp + 7 * (left_index + right_index)
                        buckets[exponent] = buckets.get(exponent, 0) + product
            value = 0.0
            for exponent in sorted(buckets):
                accumulated = buckets[exponent]
                if accumulated < INT32_MIN or accumulated > INT32_MAX:
                    raise OverflowError("INT32 accumulation bound exceeded")
                value += math.ldexp(float(accumulated), exponent)
            output_row.append(value)
        result.append(output_row)
    return result


def reference_dgemm(
    left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]
) -> list[list[float]]:
    left_rows, inner = _shape(left)
    right_rows, columns = _shape(right)
    if inner != right_rows:
        raise ValueError("matrix dimensions are incompatible")
    return [
        [sum(float(left[i][k]) * float(right[k][j]) for k in range(inner))
         for j in range(columns)]
        for i in range(left_rows)
    ]


def _max_abs_error(actual: Sequence[Sequence[float]], expected: Sequence[Sequence[float]]) -> float:
    return max(
        (abs(actual[i][j] - expected[i][j])
         for i in range(len(actual))
         for j in range(len(actual[0]))),
        default=0.0,
    )


def run_benchmark(size: int = 4, repetitions: int = 3) -> dict[str, object]:
    left = [[(i + 1) * 0.125 + (j - 1) * 0.03125 for j in range(size)]
            for i in range(size)]
    right = [[(i - 2) * 0.0625 - (j + 1) * 0.015625 for j in range(size)]
             for i in range(size)]
    expected = reference_dgemm(left, right)
    integer_durations = []
    reference_durations = []
    integer_result = []
    for _ in range(repetitions):
        start = time.perf_counter_ns()
        integer_result = integer_dgemm(left, right)
        integer_durations.append(time.perf_counter_ns() - start)
        start = time.perf_counter_ns()
        reference_dgemm(left, right)
        reference_durations.append(time.perf_counter_ns() - start)
    return {
        "schema": "qikvrt_integer_dgemm_benchmark_v1",
        "contract": {
            "input": "finite IEEE-754 binary64",
            "representation": "signed base-128 INT8 limbs with per-value binary exponent",
            "accumulator": "bounded INT32 exponent buckets",
            "final_sum": "binary64",
            "bit_identity_required": False,
            "status_flags": "not modeled by this reference path",
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "implementation": platform.python_implementation(),
        },
        "workload": {"rows": size, "inner": size, "columns": size, "repetitions": repetitions},
        "validation": {
            "max_abs_error": _max_abs_error(integer_result, expected),
            "exact_value_match": integer_result == expected,
        },
        "timing_ns": {
            "integer_path": integer_durations,
            "reference_path": reference_durations,
        },
        "claims": {
            "native_int8_hardware": False,
            "qikvrt_speedup": False,
            "energy_measurement": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--size", type=int, default=4)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.benchmark:
        print(json.dumps(run_benchmark(args.size, args.repetitions), indent=2, sort_keys=True))
    else:
        print("integer_dgemm reference path ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
