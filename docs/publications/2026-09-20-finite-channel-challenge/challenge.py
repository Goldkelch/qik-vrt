#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Offline score only. This program cannot authenticate physical chronology."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path

N = 10_000
LAG_NS = 60_000_000_000
ALPHA = Fraction(1, 1_000_000)
SCHEMA = "qikvrt_future_message_session_v1"


def commitment(bits: list[int]) -> str:
    return hashlib.sha256(bytes(bits)).hexdigest()


def tail_probability(n: int, correct: int) -> Fraction:
    """Exact one-sided fair-coin binomial tail; no float decision."""
    if type(n) is not int or type(correct) is not int or not 0 <= correct <= n:
        raise ValueError("invalid binomial counts")
    term = math.comb(n, correct)
    total = term
    for j in range(correct, n):
        term = term * (n - j) // (j + 1)
        total += term
    return Fraction(total, 1 << n)


def threshold() -> int:
    lo, hi = 0, N
    while lo < hi:
        mid = (lo + hi) // 2
        if tail_probability(N, mid) <= ALPHA:
            hi = mid
        else:
            lo = mid + 1
    return lo


def score(record: dict, preregistration_sha256: str) -> dict:
    """Validate declared fields, then score; signatures/anchors need an auditor."""
    if len(preregistration_sha256) != 64 or any(
        c not in "0123456789abcdef" for c in preregistration_sha256
    ):
        raise ValueError("expected an exact preregistration SHA-256")
    if record.get("schema") != SCHEMA:
        raise ValueError("schema mismatch")
    if record.get("preregistration_sha256") != preregistration_sha256:
        raise ValueError("preregistration binding mismatch")
    for name in ("predictions", "future_choices"):
        bits = record.get(name)
        if not isinstance(bits, list) or len(bits) != N:
            raise ValueError(f"{name} must contain exactly {N} bits; no omissions")
        if any(type(bit) is not int or bit not in (0, 1) for bit in bits):
            raise ValueError(f"{name} has a non-bit value")
    for name in ("sealed_ns", "choices_started_ns"):
        if type(record.get(name)) is not int or record[name] < 0:
            raise ValueError(f"{name} must be a nonnegative integer")
    if record["choices_started_ns"] - record["sealed_ns"] < LAG_NS:
        raise ValueError("declared future choices precede the required delay")
    if record.get("prediction_sha256") != commitment(record["predictions"]):
        raise ValueError("prediction commitment mismatch")
    correct = sum(a == b for a, b in zip(record["predictions"], record["future_choices"]))
    p = tail_probability(N, correct)
    return {
        "schema": "qikvrt_future_message_score_v1",
        "trials": N,
        "correct": correct,
        "p_numerator": str(p.numerator),
        "p_denominator": str(p.denominator),
        "alpha_numerator": 1,
        "alpha_denominator": 1_000_000,
        "statistical_threshold_met": p <= ALPHA,
        "physical_chronology_authenticated": False,
        "independent_randomization_authenticated": False,
        "independent_replication_authenticated": False,
        "future_to_past_channel_established": False,
        "scope": "Arithmetic conditional on supplied data and fair independent future choices.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--preregistration-sha256", required=True)
    args = parser.parse_args()
    print(json.dumps(score(json.loads(args.record.read_text()), args.preregistration_sha256),
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
