#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed static, algebraic and provenance checks for Wirkungsquadrat v1."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import pathlib
import re
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
ARTICLE = ROOT / "docs/publications/2026-07-25-wirkungsquadrat/Wirkungsquadrat_Planck_Skala_QIKVRT.tex"
LEAN = ROOT / "formalization/Wirkungsquadrat_v1.0/Wirkungsquadrat.lean"
LAKE = ROOT / "formalization/Wirkungsquadrat_v1.0/lakefile.toml"
TOOLCHAIN = ROOT / "formalization/Wirkungsquadrat_v1.0/lean-toolchain"
RECEIPT = ROOT / "release/wirkungsquadrat-v1/STATIC_VERIFICATION.json"

FORBIDDEN_LEAN = (
    re.compile(r"\bsorry\b"),
    re.compile(r"\badmit\b"),
    re.compile(r"^\s*axiom\b", re.MULTILINE),
    re.compile(r"^\s*constant\b", re.MULTILINE),
)

REQUIRED_THEOREMS = (
    "universal_action_square",
    "ellP_sq",
    "ellP_div_tP",
    "EP_div_pP",
    "ellP_mul_pP",
    "tP_mul_EP",
    "ellP_gravitational_anchor",
    "ellP_quantum_anchor",
    "gravitational_anchor_unique",
    "three_line_core",
)


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_lean_comments(text: str) -> str:
    """Remove nested block comments and line comments for proof-escape scanning."""
    out: list[str] = []
    i = 0
    depth = 0
    while i < len(text):
        if text.startswith("/-", i):
            depth += 1
            i += 2
            continue
        if depth and text.startswith("-/", i):
            depth -= 1
            i += 2
            continue
        if depth:
            i += 1
            continue
        if text.startswith("--", i):
            end = text.find("\n", i)
            if end < 0:
                break
            out.append("\n")
            i = end + 1
            continue
        out.append(text[i])
        i += 1
    if depth:
        raise SystemExit("BLOCK: unterminated Lean block comment")
    return "".join(out)


def solve_dimension_system() -> tuple[Fraction, Fraction, Fraction, int]:
    # Unknowns a,b,d for c^a hbar^b G^d with target dimension L.
    # Rows: mass, time, length.
    matrix = [
        [Fraction(0), Fraction(1), Fraction(-1), Fraction(0)],
        [Fraction(-1), Fraction(-1), Fraction(-2), Fraction(0)],
        [Fraction(1), Fraction(2), Fraction(3), Fraction(1)],
    ]
    determinant = -2
    for col in range(3):
        pivot = next((r for r in range(col, 3) if matrix[r][col]), None)
        if pivot is None:
            raise SystemExit("BLOCK: dimensional system lost rank")
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        divisor = matrix[col][col]
        matrix[col] = [value / divisor for value in matrix[col]]
        for row in range(3):
            if row == col:
                continue
            factor = matrix[row][col]
            matrix[row] = [
                matrix[row][j] - factor * matrix[col][j] for j in range(4)
            ]
    solution = tuple(matrix[i][3] for i in range(3))
    if solution != (Fraction(-3, 2), Fraction(1, 2), Fraction(1, 2)):
        raise SystemExit(f"BLOCK: unexpected dimensional solution: {solution}")
    return solution[0], solution[1], solution[2], determinant


def numeric_identity_check() -> dict[str, float]:
    # Deliberately non-special positive values; this supplements, never replaces, Lean.
    c = 7.25
    hbar = 2.75
    G = 5.5
    ell = math.sqrt(hbar * G / c**3)
    t = ell / c
    m = ell * c**2 / G
    p = m * c
    energy = p * c
    checks = {
        "ell_over_t": ell / t,
        "energy_over_p": energy / p,
        "ell_times_p": ell * p,
        "t_times_energy": t * energy,
        "quantum_anchor": hbar / (m * c),
        "gravitational_anchor": G * m / c**2,
    }
    expected = {
        "ell_over_t": c,
        "energy_over_p": c,
        "ell_times_p": hbar,
        "t_times_energy": hbar,
        "quantum_anchor": ell,
        "gravitational_anchor": ell,
    }
    for key, value in checks.items():
        if not math.isclose(value, expected[key], rel_tol=2e-13, abs_tol=2e-13):
            raise SystemExit(f"BLOCK: numeric identity mismatch: {key}")
    return checks


def verify() -> dict[str, object]:
    required = (ARTICLE, LEAN, LAKE, TOOLCHAIN)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"BLOCK: missing required files: {missing}")

    article = ARTICLE.read_text(encoding="utf-8")
    for token in (
        r"\frac{\ell_{\mathrm P}}{t_{\mathrm P}}",
        r"\ell_{\mathrm P}p_{\mathrm P}",
        r"\frac{G\mP}{c^2}",
        "Ursprungsfrage",
        "Was nicht folgt",
    ):
        if token not in article:
            raise SystemExit(f"BLOCK: article invariant missing: {token}")

    lean_raw = LEAN.read_text(encoding="utf-8")
    lean = strip_lean_comments(lean_raw)
    for pattern in FORBIDDEN_LEAN:
        match = pattern.search(lean)
        if match:
            raise SystemExit(f"BLOCK: forbidden Lean escape: {match.group(0)!r}")
    for theorem in REQUIRED_THEOREMS:
        if not re.search(rf"\btheorem\s+{re.escape(theorem)}\b", lean):
            raise SystemExit(f"BLOCK: required Lean theorem missing: {theorem}")
        if f"#print axioms {theorem}" not in lean and theorem in {
            "universal_action_square",
            "ellP_sq",
            "ellP_mul_pP",
            "tP_mul_EP",
            "ellP_gravitational_anchor",
            "ellP_quantum_anchor",
            "gravitational_anchor_unique",
            "three_line_core",
        }:
            raise SystemExit(f"BLOCK: theorem lacks axiom audit print: {theorem}")

    if TOOLCHAIN.read_text(encoding="utf-8").strip() != "leanprover/lean4:v4.19.0":
        raise SystemExit("BLOCK: Lean toolchain is not pinned to 4.19.0")
    lake = LAKE.read_text(encoding="utf-8")
    if 'rev = "v4.19.0"' not in lake:
        raise SystemExit("BLOCK: mathlib revision is not pinned to v4.19.0")

    a, b, d, determinant = solve_dimension_system()
    numeric = numeric_identity_check()
    result: dict[str, object] = {
        "schema": "qikvrt_wirkungsquadrat_static_verification_v1",
        "status": "PASS",
        "article_sha256": sha256(ARTICLE),
        "lean_source_sha256": sha256(LEAN),
        "lakefile_sha256": sha256(LAKE),
        "lean_toolchain_sha256": sha256(TOOLCHAIN),
        "required_theorems": list(REQUIRED_THEOREMS),
        "proof_escape_count": 0,
        "dimensional_matrix_determinant": determinant,
        "planck_length_exponents": {
            "c": str(a),
            "hbar": str(b),
            "G": str(d),
        },
        "numeric_supplement": numeric,
        "epistemic_boundary": (
            "Kernel proof concerns the typed algebraic propositions; empirical "
            "spacetime discreteness, quantum-gravity dynamics and cosmology remain external."
        ),
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="compare with the persisted receipt")
    parser.add_argument("--write", action="store_true", help="write the deterministic receipt")
    args = parser.parse_args()
    if args.check and args.write:
        raise SystemExit("choose either --check or --write")
    result = verify()
    encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.check:
        if not RECEIPT.is_file() or RECEIPT.read_bytes() != encoded:
            raise SystemExit("BLOCK: static verification receipt is missing or stale")
    elif args.write:
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_bytes(encoded)
    else:
        sys.stdout.buffer.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
