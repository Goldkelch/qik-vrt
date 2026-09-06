# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import math
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "physics" / "planck_tick_gap_law_v1.json"


class PlanckTickGapLawV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        constants = cls.contract["constants"]
        cls.hbar = float(constants["hbar_J_s"])
        cls.G = float(constants["G_m3_kg-1_s-2"])
        cls.c = float(constants["c_m_per_s"])
        cls.eV_J = float(constants["eV_J"])
        cls.tP = math.sqrt(cls.hbar * cls.G / cls.c**5)
        cls.EP_J = cls.hbar / cls.tP
        cls.EP_eV = cls.EP_J / cls.eV_J

    def test_epistemic_boundary_is_fail_closed(self):
        boundary = self.contract["epistemic_boundary"]
        self.assertTrue(boundary["formal_model"])
        self.assertTrue(boundary["differentiating_prediction_frozen"])
        self.assertFalse(boundary["empirically_confirmed"])
        self.assertFalse(boundary["independently_reproduced"])
        self.assertFalse(boundary["PASS"])
        self.assertFalse(boundary["FINAL_PASS"])
        self.assertFalse(boundary["EFFECT_ACK_DONE"])

    def test_planck_constants_are_self_consistent(self):
        constants = self.contract["constants"]
        self.assertAlmostEqual(
            self.tP,
            float(constants["derived_tP_s"]),
            delta=self.tP * 2e-15,
        )
        self.assertAlmostEqual(
            self.EP_eV,
            float(constants["derived_EP_eV"]),
            delta=self.EP_eV * 2e-15,
        )
        self.assertAlmostEqual(self.EP_J * self.tP, self.hbar, delta=self.hbar * 2e-15)

    def exact_shift(self, gap_eV: float) -> tuple[float, float, float]:
        x = gap_eV / self.EP_eV
        # Direct asin(x)-x loses all significant digits for the frozen low-energy
        # examples. The series is the numerically stable evaluation of the exact
        # low-energy branch at these x values.
        residual_dimensionless = x**3 / 6.0 + 3.0 * x**5 / 40.0
        delta_omega = residual_dimensionless / self.tP
        relative = x**2 / 6.0 + 3.0 * x**4 / 40.0
        return relative, delta_omega, 1.0 / delta_omega

    def test_frozen_examples_match_parameter_free_prediction(self):
        for example in self.contract["frozen_examples"]:
            relative, delta_omega, one_rad = self.exact_shift(float(example["DeltaE_eV"]))
            self.assertAlmostEqual(
                relative,
                float(example["relative_shift"]),
                delta=abs(relative) * 3e-15,
            )
            self.assertAlmostEqual(
                delta_omega,
                float(example["delta_omega_rad_per_s"]),
                delta=abs(delta_omega) * 3e-15,
            )
            self.assertAlmostEqual(
                one_rad,
                float(example["one_radian_accumulation_time_s"]),
                delta=abs(one_rad) * 3e-15,
            )

    def test_prediction_has_fixed_positive_sign_below_planck_gap(self):
        for fraction in (1e-12, 1e-9, 1e-6, 1e-3, 0.1, 0.5, 0.9):
            residual = fraction**3 / 6.0 + 3.0 * fraction**5 / 40.0
            self.assertGreater(residual, 0.0)

    def test_standard_quantum_mechanics_is_recovered_at_low_gap(self):
        for fraction in (1e-2, 1e-3, 1e-4):
            ratio = math.asin(fraction) / fraction
            leading = 1.0 + fraction**2 / 6.0
            self.assertLess(abs(ratio - leading), fraction**4)

    def test_v1_has_no_adjustable_deformation_coefficient(self):
        prediction = json.dumps(self.contract["derived_prediction"], sort_keys=True)
        for forbidden in ("alpha", "beta", "lambda", "fit_parameter", "free_parameter"):
            self.assertNotIn(forbidden, prediction.lower())


if __name__ == "__main__":
    unittest.main()
