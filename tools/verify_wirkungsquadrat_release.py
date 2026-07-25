#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
"""Canonical fail-closed verifier for the repository-native Wirkungsquadrat release."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import sys
from fractions import Fraction

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUB = ROOT / "docs/publications/2026-07-25-wirkungsquadrat"
FORMAL = ROOT / "formalization/Wirkungsquadrat_v1.0"
ARTICLE = PUB / "Wirkungsquadrat_Planck_Skala_QIKVRT.tex"
README = PUB / "README.md"
CITATION = PUB / "CITATION.cff"
METADATA = PUB / "zenodo-metadata.json"
LICENSE_NOTICE = PUB / "LICENSE_NOTICE.md"
LEAN = FORMAL / "WirkungsquadratKernel.lean"
LAKE = FORMAL / "lakefile.toml"
TOOLCHAIN = FORMAL / "lean-toolchain"
RECEIPT = ROOT / "release/wirkungsquadrat-v1/STATIC_VERIFICATION.json"

EXPECTED_PRECURSOR_SHA256 = "48a1f4edf1918080dd140529159ce8f98c3b5c10e04112867cf1fe9f3eed9a60"
EXPECTED_PRECURSOR_PDF_SHA256 = "d495a44921d25625c58dff812a65e99e2800a864b2876ab5abe13f2eca8d2975"
DOI_SENTINEL = "DOI_PENDING_PUBLICATION"
REQUIRED_THEOREMS = (
    "universal_action_square",
    "ellP_sq",
    "ellP_div_tP",
    "EP_div_pP",
    "ellP_mul_pP",
    "tP_mul_EP",
    "ellP_quantum_anchor",
    "ellP_gravitational_anchor",
    "gravitational_anchor_unique",
    "three_line_core",
)


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strip_lean_comments(text: str) -> str:
    result: list[str] = []
    depth = 0
    index = 0
    while index < len(text):
        if text.startswith("/-", index):
            depth += 1
            index += 2
            continue
        if depth and text.startswith("-/", index):
            depth -= 1
            index += 2
            continue
        if depth:
            index += 1
            continue
        if text.startswith("--", index):
            end = text.find("\n", index)
            if end < 0:
                break
            result.append("\n")
            index = end + 1
            continue
        result.append(text[index])
        index += 1
    if depth:
        raise SystemExit("BLOCK: unterminated Lean block comment")
    return "".join(result)


def dimensional_solution() -> tuple[Fraction, Fraction, Fraction, int]:
    rows = [
        [Fraction(0), Fraction(1), Fraction(-1), Fraction(0)],
        [Fraction(-1), Fraction(-1), Fraction(-2), Fraction(0)],
        [Fraction(1), Fraction(2), Fraction(3), Fraction(1)],
    ]
    determinant = -2
    for column in range(3):
        pivot = next((row for row in range(column, 3) if rows[row][column]), None)
        if pivot is None:
            raise SystemExit("BLOCK: dimensional matrix is singular")
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        rows[column] = [value / divisor for value in rows[column]]
        for row in range(3):
            if row == column:
                continue
            factor = rows[row][column]
            rows[row] = [rows[row][i] - factor * rows[column][i] for i in range(4)]
    solution = tuple(rows[i][3] for i in range(3))
    expected = (Fraction(-3, 2), Fraction(1, 2), Fraction(1, 2))
    if solution != expected:
        raise SystemExit(f"BLOCK: dimensional solution differs: {solution}")
    return solution[0], solution[1], solution[2], determinant


def supplemental_numeric_check() -> dict[str, float]:
    c, hbar, gravity = 7.25, 2.75, 5.5
    ell = math.sqrt(hbar * gravity / c**3)
    time = ell / c
    momentum = hbar / ell
    energy = c * momentum
    mass = momentum / c
    values = {
        "ell_over_time": ell / time,
        "energy_over_momentum": energy / momentum,
        "ell_times_momentum": ell * momentum,
        "time_times_energy": time * energy,
        "quantum_anchor": hbar / (mass * c),
        "gravitational_anchor": gravity * mass / c**2,
    }
    expected = {
        "ell_over_time": c,
        "energy_over_momentum": c,
        "ell_times_momentum": hbar,
        "time_times_energy": hbar,
        "quantum_anchor": ell,
        "gravitational_anchor": ell,
    }
    for name, value in values.items():
        if not math.isclose(value, expected[name], rel_tol=2e-13, abs_tol=2e-13):
            raise SystemExit(f"BLOCK: supplemental numeric check differs: {name}")
    return values


def verify() -> dict[str, object]:
    required = (README, ARTICLE, CITATION, METADATA, LICENSE_NOTICE, LEAN, LAKE, TOOLCHAIN)
    missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"BLOCK: missing release inputs: {missing}")

    readme = README.read_text(encoding="utf-8")
    if EXPECTED_PRECURSOR_SHA256 not in readme or EXPECTED_PRECURSOR_PDF_SHA256 not in readme:
        raise SystemExit("BLOCK: local precursor hashes are not bound in README")
    if "nicht als byteidentisch" not in readme:
        raise SystemExit("BLOCK: repository canonicalization boundary is missing")

    article = ARTICLE.read_text(encoding="utf-8")
    for token in (
        r"\frac{\lP}{\tP}",
        r"\lP\pP",
        r"\frac{G\mP}{c^2}",
        "Was nicht folgt",
        "Die weiterhin offene Ursprungsfrage",
    ):
        if token not in article:
            raise SystemExit(f"BLOCK: article invariant missing: {token}")

    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    required_keys = {
        "schema", "doi", "publication_date", "title", "creators", "description",
        "access_right", "license", "upload_type", "publication_type", "language",
        "version", "keywords", "related_identifiers", "notes",
    }
    if set(metadata) != required_keys:
        raise SystemExit("BLOCK: Zenodo metadata schema differs")
    if metadata["doi"] != DOI_SENTINEL:
        raise SystemExit("BLOCK: draft metadata must retain the DOI sentinel")
    if metadata["license"] != "cc-by-nc-nd-4.0":
        raise SystemExit("BLOCK: publication license differs")
    notes = metadata["notes"]
    if EXPECTED_PRECURSOR_SHA256 not in notes or EXPECTED_PRECURSOR_PDF_SHA256 not in notes:
        raise SystemExit("BLOCK: precursor provenance is missing from metadata")
    if "nicht als byteidentisch" not in notes:
        raise SystemExit("BLOCK: canonicalization boundary is missing from metadata")
    related = {entry.get("identifier") for entry in metadata["related_identifiers"]}
    required_related = {
        "10.5281/zenodo.21482023",
        "10.5281/zenodo.21488116",
        "10.5281/zenodo.21529081",
    }
    if not required_related.issubset(related):
        raise SystemExit("BLOCK: related Zenodo provenance is incomplete")

    citation = CITATION.read_text(encoding="utf-8")
    if DOI_SENTINEL not in citation or "CC-BY-NC-ND-4.0" not in citation:
        raise SystemExit("BLOCK: citation sentinel or license is missing")

    lean_source = strip_lean_comments(LEAN.read_text(encoding="utf-8"))
    forbidden = (
        re.compile(r"\bsorry\b"),
        re.compile(r"\badmit\b"),
        re.compile(r"^\s*axiom\b", re.MULTILINE),
        re.compile(r"^\s*constant\b", re.MULTILINE),
    )
    for pattern in forbidden:
        match = pattern.search(lean_source)
        if match:
            raise SystemExit(f"BLOCK: forbidden Lean escape: {match.group(0)!r}")
    for theorem in REQUIRED_THEOREMS:
        if not re.search(rf"\btheorem\s+{re.escape(theorem)}\b", lean_source):
            raise SystemExit(f"BLOCK: required theorem missing: {theorem}")
        if f"#print axioms {theorem}" not in lean_source:
            raise SystemExit(f"BLOCK: axiom print missing: {theorem}")

    if TOOLCHAIN.read_text(encoding="utf-8").strip() != "leanprover/lean4:v4.19.0":
        raise SystemExit("BLOCK: Lean toolchain differs")
    if 'rev = "v4.19.0"' not in LAKE.read_text(encoding="utf-8"):
        raise SystemExit("BLOCK: mathlib revision differs")

    a, b, d, determinant = dimensional_solution()
    numeric = supplemental_numeric_check()
    return {
        "schema": "qikvrt_wirkungsquadrat_static_verification_v2",
        "status": "PASS",
        "precursor_zip_sha256": EXPECTED_PRECURSOR_SHA256,
        "precursor_pdf_sha256": EXPECTED_PRECURSOR_PDF_SHA256,
        "repository_canonicalization_byte_identical_claim": False,
        "article_sha256": digest(ARTICLE),
        "lean_source_sha256": digest(LEAN),
        "lakefile_sha256": digest(LAKE),
        "lean_toolchain_sha256": digest(TOOLCHAIN),
        "metadata_sha256": digest(METADATA),
        "citation_sha256": digest(CITATION),
        "required_theorems": list(REQUIRED_THEOREMS),
        "proof_escape_count": 0,
        "doi_state": DOI_SENTINEL,
        "dimensional_matrix_determinant": determinant,
        "planck_length_exponents": {"c": str(a), "hbar": str(b), "G": str(d)},
        "numeric_supplement": numeric,
        "epistemic_boundary": (
            "The formal proof establishes the typed algebraic propositions from explicit "
            "definitions and positivity premises; empirical spacetime discreteness, "
            "quantum-gravity dynamics and cosmology remain external."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = verify()
    encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if args.write:
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_bytes(encoded)
    elif args.check:
        if not RECEIPT.is_file() or RECEIPT.read_bytes() != encoded:
            raise SystemExit("BLOCK: static verification receipt is missing or stale")
    else:
        sys.stdout.buffer.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
