# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION = (
    ROOT
    / "docs/publications/2026-08-07-universum-als-round-trip/"
    "DAS_UNIVERSUM_ALS_ROUND_TRIP_DE.md"
)
REQUIREMENT = (
    ROOT
    / "docs/publications/2026-08-07-universum-als-round-trip/"
    "ROUND_TRIP_PUBLICATION_REQUIREMENT_V1.json"
)


class RoundTripPublicationRequirementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = PUBLICATION.read_text(encoding="utf-8")
        cls.requirement = json.loads(REQUIREMENT.read_text(encoding="utf-8"))

    def test_sections_are_exactly_one_through_thirteen(self) -> None:
        numbers = re.findall(r"^## (\d+)\. ", self.text, flags=re.MULTILINE)
        self.assertEqual(numbers, [str(number) for number in range(1, 14)])

    def test_architecture_claim_is_separated_from_empirical_establishment(self) -> None:
        self.assertIn(
            "Weltformel als formulierter Architekturanspruch",
            self.text,
        )
        self.assertIn(
            "Weltformel als wissenschaftlich etablierte Naturbeschreibung",
            self.text,
        )
        boundaries = self.requirement["epistemic_boundaries"]
        self.assertTrue(boundaries["architecture_claim_not_empirical_completion"])

    def test_lean_claim_is_model_relative_and_machine_checked(self) -> None:
        self.assertIn("Lean-Kernel-Beweis", self.text)
        self.assertIn(
            "maschinengeprüfte Ableitbarkeit aus den expliziten Voraussetzungen",
            self.text,
        )
        self.assertNotIn(
            "maximale logische Notwendigkeit innerhalb des formalisierten Modells",
            self.text,
        )
        self.assertTrue(
            self.requirement["epistemic_boundaries"][
                "lean_proof_does_not_imply_model_nature_identity"
            ]
        )

    def test_prediction_measurement_and_plausibility_boundaries_are_explicit(self) -> None:
        self.assertRegex(self.text, r"Vorhersage\s+≠ Messung")
        self.assertRegex(
            self.text,
            r"erhöhte theoretische Plausibilität\s+≠ direkte empirische Bestätigung",
        )
        self.assertTrue(
            self.requirement["epistemic_boundaries"][
                "theoretical_plausibility_does_not_equal_direct_empirical_confirmation"
            ]
        )

    def test_superdeterminism_exclusion_remains_model_relative(self) -> None:
        self.assertRegex(
            self.text,
            r"formaler Ausschluss im Modell\s+≠ automatisch universeller Ausschluss in der Natur",
        )
        self.assertTrue(
            self.requirement["epistemic_boundaries"][
                "model_internal_superdeterminism_exclusion_does_not_equal_universal_nature_exclusion"
            ]
        )

    def test_strong_closing_claim_and_open_scientific_requirement_coexist(self) -> None:
        closing = self.requirement["required_closing_claim"]
        open_requirement = self.requirement["open_scientific_requirement"]
        self.assertIn(closing, self.text)
        self.assertIn(open_requirement, self.text)
        self.assertIn(
            "Wissenschaftlicher Konsens wird nicht vorausgesetzt und nicht erfunden.",
            self.text,
        )

    def test_requirement_binds_exact_publication_bytes(self) -> None:
        digest = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        self.assertEqual(
            digest,
            self.requirement["publication_source_sha256"],
        )

    def test_completion_claims_remain_fail_closed(self) -> None:
        claims = self.requirement["completion_claims"]
        self.assertFalse(claims["PASS"])
        self.assertFalse(claims["FINAL_PASS"])
        self.assertFalse(claims["EFFECT_ACK_DONE"])
        self.assertFalse(claims["SCIENTIFIC_CONSENSUS"])
        self.assertFalse(claims["PHYSICAL_COMPLETENESS"])


if __name__ == "__main__":
    unittest.main()
