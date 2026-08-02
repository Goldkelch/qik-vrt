#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0

from __future__ import annotations

import pathlib
import unittest

from validate_h5_instance import ValidationError, parse_document


ROOT = pathlib.Path(__file__).resolve().parent
VALID = (ROOT / "H5_REFERENCE_INSTANCE.vrt").read_text(encoding="utf-8")


class H5ValidationTests(unittest.TestCase):
    def assert_blocked(self, text: str, needle: str) -> None:
        with self.assertRaisesRegex(ValidationError, needle):
            parse_document(text)

    def test_reference_instance_passes(self) -> None:
        result = parse_document(VALID)
        self.assertEqual(result["effect-state"], "EFFECT_ACK_CONTINUE")
        self.assertEqual(len(result["open"]), 3)

    def test_missing_mandatory_block_is_blocked(self) -> None:
        start = VALID.index("duality D1")
        end = VALID.index("empirical-anchors E1")
        self.assert_blocked(VALID[:start] + VALID[end:], "block mismatch")

    def test_duplicate_mandatory_block_is_blocked(self) -> None:
        block_start = VALID.index("duality D1")
        block_end = VALID.index("empirical-anchors E1")
        duplicate = VALID[block_start:block_end]
        self.assert_blocked(VALID[:block_end] + duplicate + VALID[block_end:], "duplicate")

    def test_schwarzschild_factor_is_not_silently_used(self) -> None:
        altered = VALID.replace("G*m_P/c^2=l_P", "2*G*m_P/c^2=l_P")
        self.assert_blocked(altered, "S02")

    def test_wave_record_identity_is_not_completeness(self) -> None:
        altered = VALID.replace("physical-completeness = open", "physical-completeness = conditional")
        self.assert_blocked(altered, "S04")

    def test_gravitational_wave_is_not_graviton_observation(self) -> None:
        altered = VALID.replace("graviton = not-observed", "graviton = observed")
        self.assert_blocked(altered, "S05")

    def test_standard_model_limit_cannot_be_promoted(self) -> None:
        altered = VALID.replace("standard-model = open", "standard-model = conditional")
        self.assert_blocked(altered, "S06")

    def test_false_witness_cannot_yield_true_closure(self) -> None:
        altered = VALID.replace("result = MASSIVE_CLOSURE_FALSE", "result = MASSIVE_CLOSURE_TRUE")
        self.assert_blocked(altered, "S11/S12")

    def test_kernel_acceptance_is_not_physical_discovery(self) -> None:
        altered = VALID.replace("physical-discovery = open", "physical-discovery = empirically-supported")
        self.assert_blocked(altered, "S16")

    def test_virtual_model_is_not_physical_cosmology(self) -> None:
        altered = VALID.replace(
            "physical-cosmology-identity = open",
            "physical-cosmology-identity = empirically-supported",
        )
        self.assert_blocked(altered, "S15")

    def test_effect_done_cannot_be_constructed(self) -> None:
        altered = VALID.replace(
            "effect-state = EFFECT_ACK_CONTINUE;\n};",
            "effect-state = EFFECT_ACK_DONE;\n};",
            1,
        )
        self.assert_blocked(altered, "S20")


if __name__ == "__main__":
    unittest.main()
