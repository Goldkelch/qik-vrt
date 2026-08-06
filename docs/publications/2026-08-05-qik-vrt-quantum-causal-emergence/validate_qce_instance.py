#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed parser and static validator for the finite QCE reference syntax."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass


REQUIRED_ORDER = [
    "qce-version",
    "publication-id",
    "author",
    "planck-element",
    "two-step",
    "uncertainty",
    "primitive-causality",
    "classical-cone",
    "relation-network",
    "physical-closure",
    "kernel-boundary",
    "effect-state",
]

EXPECTED_VALUES = {
    "qce-version": ["1"],
    "planck-element": ["MODEL_CANDIDATE"],
    "two-step": ["FIRST_DIFFERENCE", "SECOND_PAIR_RELATION"],
    "uncertainty": ["REDUCIBLE_ACCOUNTED", "IRREDUCIBLE_PRESERVED"],
    "primitive-causality": ["UNRESOLVED", "UNCERTAINTY_PRESENT"],
    "classical-cone": [
        "REQUIRES_UNCERTAINTY_ACCOUNTED",
        "REQUIRES_CLASSICAL_GEOMETRY",
        "REQUIRES_STABLE_NULL_BOUNDARY",
    ],
    "relation-network": ["SEED_EVENTS_2", "SEED_RELATIONS_1", "GLOBALLY_BOUND"],
    "physical-closure": ["OPEN_CANDIDATE"],
    "kernel-boundary": ["FORMAL_MODEL_NOT_PHYSICAL_DISCOVERY"],
    "effect-state": ["EFFECT_ACK_CONTINUE"],
}

IDENTIFIER = re.compile(r"^[A-Za-z0-9_.-]+$")


class ValidationError(ValueError):
    """The document violates the finite QCE contract."""


@dataclass(frozen=True)
class ParsedDocument:
    fields: dict[str, list[str]]

    def as_dict(self) -> dict[str, object]:
        return {
            "schema": "qikvrt-qce-reference/1.0",
            "fields": self.fields,
            "physical_closure": "OPEN_CANDIDATE",
            "effect_state": "EFFECT_ACK_CONTINUE",
        }


def parse_document(text: str) -> ParsedDocument:
    fields: dict[str, list[str]] = {}
    observed_order: list[str] = []

    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        key, values = parts[0], parts[1:]
        if key not in REQUIRED_ORDER:
            raise ValidationError(f"line {line_number}: unknown key {key!r}")
        if key in fields:
            raise ValidationError(f"line {line_number}: duplicate key {key!r}")
        if not values:
            raise ValidationError(f"line {line_number}: key {key!r} has no value")
        fields[key] = values
        observed_order.append(key)

    if observed_order != REQUIRED_ORDER:
        raise ValidationError(
            "keys must occur exactly once in canonical order: "
            + ", ".join(REQUIRED_ORDER)
        )

    for key, expected in EXPECTED_VALUES.items():
        if fields[key] != expected:
            raise ValidationError(
                f"{key}: expected {' '.join(expected)!r}, got {' '.join(fields[key])!r}"
            )

    for key in ("publication-id", "author"):
        if len(fields[key]) != 1 or not IDENTIFIER.fullmatch(fields[key][0]):
            raise ValidationError(f"{key}: invalid identifier")

    forbidden_tokens = {
        "PASS",
        "FINAL_PASS",
        "EFFECT_ACK_DONE",
        "PHYSICALLY_PROVED",
        "SINGULARITY_IDENTIFIED",
    }
    all_tokens = {token for values in fields.values() for token in values}
    overlap = forbidden_tokens.intersection(all_tokens)
    if overlap:
        raise ValidationError("forbidden promotion token(s): " + ", ".join(sorted(overlap)))

    return ParsedDocument(fields)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=pathlib.Path)
    arguments = parser.parse_args()
    document = parse_document(arguments.path.read_text(encoding="utf-8"))
    print(json.dumps(document.as_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as error:
        print(f"BLOCK: {error}", file=sys.stderr)
        raise SystemExit(1) from error
