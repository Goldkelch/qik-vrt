#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import pathlib
import unittest

from validate_qce_instance import ValidationError, parse_document


ROOT = pathlib.Path(__file__).resolve().parent
VALID = (ROOT / "QCE_REFERENCE_INSTANCE.vrt").read_text(encoding="utf-8")


class QCEValidatorTests(unittest.TestCase):
    def test_reference_is_valid(self) -> None:
        parsed = parse_document(VALID)
        self.assertEqual(parsed.fields["physical-closure"], ["OPEN_CANDIDATE"])
        self.assertEqual(parsed.fields["effect-state"], ["EFFECT_ACK_CONTINUE"])

    def test_missing_block_fails(self) -> None:
        with self.assertRaises(ValidationError):
            parse_document(VALID.replace("planck-element MODEL_CANDIDATE\n", ""))

    def test_duplicate_block_fails(self) -> None:
        with self.assertRaises(ValidationError):
            parse_document(VALID + "effect-state EFFECT_ACK_CONTINUE\n")

    def test_reordered_block_fails(self) -> None:
        lines = VALID.splitlines()
        lines[3], lines[4] = lines[4], lines[3]
        with self.assertRaises(ValidationError):
            parse_document("\n".join(lines) + "\n")

    def test_physical_promotion_fails(self) -> None:
        with self.assertRaises(ValidationError):
            parse_document(VALID.replace("OPEN_CANDIDATE", "PHYSICALLY_PROVED"))

    def test_done_promotion_fails(self) -> None:
        with self.assertRaises(ValidationError):
            parse_document(VALID.replace("EFFECT_ACK_CONTINUE", "EFFECT_ACK_DONE"))

    def test_wrong_two_step_fails(self) -> None:
        with self.assertRaises(ValidationError):
            parse_document(
                VALID.replace(
                    "FIRST_DIFFERENCE SECOND_PAIR_RELATION",
                    "SECOND_PAIR_RELATION FIRST_DIFFERENCE",
                )
            )

    def test_irreducible_uncertainty_must_be_preserved(self) -> None:
        with self.assertRaises(ValidationError):
            parse_document(VALID.replace("IRREDUCIBLE_PRESERVED", "IRREDUCIBLE_REMOVED"))

    def test_classical_cone_needs_all_three_witnesses(self) -> None:
        with self.assertRaises(ValidationError):
            parse_document(VALID.replace(" REQUIRES_STABLE_NULL_BOUNDARY", ""))

    def test_unknown_key_fails(self) -> None:
        with self.assertRaises(ValidationError):
            parse_document(VALID.replace("author Ingolf_Lohmann", "creator Ingolf_Lohmann"))


if __name__ == "__main__":
    unittest.main()
