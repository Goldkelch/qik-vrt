# SPDX-License-Identifier: CC-BY-NC-ND-4.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/publications/2026-08-06-delayed-choice-hardware-witness"
THEOREM = PACKAGE / "WHATSAPP_DECISION_SUFFICIENCY_DE.md"
README = PACKAGE / "README.md"
IMPERATIVE = ROOT / "docs/articles/a015_evidence_sufficiency_imperative.md"
WORK_UNIT = ROOT / "state/work_units/MINIMAL_RECOVERY_THEOREM_ORIENTATION_AND_UNIVERSALIZATION_V1.json"


class MinimalRecoveryTheoremOrientationAndUniversalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.theorem = THEOREM.read_text(encoding="utf-8")
        cls.readme = README.read_text(encoding="utf-8")
        cls.imperative = IMPERATIVE.read_text(encoding="utf-8")

    def test_orientation_retains_the_exact_scope_and_finite_model_boundary(self) -> None:
        self.assertIn("ker(Obs')", self.theorem)
        self.assertIn("FAIL_CLOSED", self.theorem)
        self.assertIn("DELAYED CHOICE", self.theorem)
        self.assertIn("FINITE_MODEL_EXHAUSTIVE_CHECK_PASSED", self.theorem)
        self.assertIn("945 Fälle", self.theorem)
        self.assertIn("Kollisionsfreiheit von SHA-256", self.theorem)

    def test_imperative_requires_admissibility_action_authority_and_safe_baseline(self) -> None:
        self.assertIn("SPDX-License-Identifier: CC-BY-NC-ND-4.0", self.imperative)
        self.assertIn("NORMATIVE_TRANSLATION_NOT_EMPIRICAL_OR_LEGAL_PROOF", self.imperative)
        self.assertIn("ker(Obs_D) subseteq ker(C_D)", self.imperative)
        self.assertIn("FAIL_CLOSED_OR_DOMAIN_SAFE_BASELINE", self.imperative)
        for field in (
            "H_ADM",
            "CORRECT_ACTION_CONTRACT",
            "FIBER_CONSTANCY_ARGUMENT",
            "WITNESS_REFINEMENT",
            "SAFE_BASELINE",
            "AUTHORITY_AND_RIGHTS_BOUNDARY",
            "EFFECT_BOUNDARY",
        ):
            self.assertIn(field, self.imperative)
        self.assertIn("keine freie KI-Definition", self.imperative)

    def test_bundle_links_the_normative_translation_without_inflating_claims(self) -> None:
        self.assertIn("a015_evidence_sufficiency_imperative.md", self.readme)
        self.assertIn("does not itself define a domain's correct action", self.readme)
        self.assertIn("does not itself", self.readme)
        self.assertIn("keine empirische, physikalische, kryptographische", self.imperative)

    def test_provenance_work_unit_separates_human_and_ai_contributions(self) -> None:
        work_unit = json.loads(WORK_UNIT.read_text(encoding="utf-8"))
        self.assertEqual(
            work_unit["work_unit_id"],
            "MINIMAL_RECOVERY_THEOREM_ORIENTATION_AND_UNIVERSALIZATION_V1",
        )
        self.assertEqual(work_unit["human_actor"]["actor_class"], "HUMAN")
        self.assertEqual(
            work_unit["artificial_cognitive_actor"]["actor_class"],
            "ARTIFICIAL_COGNITIVE_SYSTEM",
        )
        self.assertFalse(work_unit["release_claims"]["PASS"])
        self.assertFalse(work_unit["release_claims"]["FINAL_PASS"])
        self.assertFalse(work_unit["release_claims"]["EFFECT_ACK_DONE"])


if __name__ == "__main__":
    unittest.main()
