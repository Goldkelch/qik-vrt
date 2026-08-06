# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_autonomous_pre_effect_controller",
    ROOT / "tools/qikvrt_autonomous_pre_effect_controller.py",
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AutonomousPreEffectControllerTests(unittest.TestCase):
    def test_policy_is_active_and_fail_closed(self) -> None:
        policy = MODULE.load_policy()
        self.assertEqual(policy["mission"], "AUTONOMOUS_UNTIL_FIRST_IRREVERSIBLE_EXTERNAL_EFFECT")
        self.assertEqual(policy["preconditions"], MODULE.EXPECTED_PRECONDITIONS)
        self.assertEqual(policy["fail_closed"]["state"], "HOLD")
        self.assertTrue(policy["fail_closed"]["repair_forbidden"])

    def test_all_preconditions_allow_repository_internal_execution(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        self.assertEqual(MODULE.classify(preconditions, None), "AUTONOMOUS_EXECUTION_ALLOWED")

    def test_missing_precondition_holds_instead_of_repairs(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        preconditions["NO_COMPETING_WRITER"] = False
        self.assertEqual(MODULE.classify(preconditions, None), "HOLD")

    def test_irreversible_effect_requires_exact_owner_authorization(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        for effect in MODULE.IRREVERSIBLE_EFFECTS:
            self.assertEqual(MODULE.classify(preconditions, effect), "REQUIRE_EXACT_PRODUCT_OWNER_AUTHORIZATION")

    def test_unknown_effect_fails_closed(self) -> None:
        preconditions = {name: True for name in MODULE.EXPECTED_PRECONDITIONS}
        with self.assertRaises(MODULE.PreEffectBlock):
            MODULE.classify(preconditions, "UNBOUND_EXTERNAL_EFFECT")

    def test_completion_and_epistemic_claims_remain_prohibited(self) -> None:
        policy = MODULE.load_policy()
        prohibited = set(policy["prohibited_autonomous_effects"])
        self.assertTrue(MODULE.PROHIBITED_CLAIMS.issubset(prohibited))
        self.assertFalse(policy["epistemic_boundaries"]["scientific_confirmation_inferable"])
        self.assertFalse(policy["epistemic_boundaries"]["physical_correspondence_inferable"])
        self.assertFalse(policy["epistemic_boundaries"]["independent_review_fabricable"])
        self.assertFalse(policy["epistemic_boundaries"]["measurement_fabricable"])


if __name__ == "__main__":
    unittest.main()
