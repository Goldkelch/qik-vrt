#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import unittest

from tools import qikvrt_survival_connectability_kernel_evidence as evidence


class SurvivalConnectabilityKernelEvidenceTests(unittest.TestCase):
    def test_static_candidate_contract_binds_all_formal_modules(self) -> None:
        value = evidence.static_validation()
        imports = {item["plan"]["import"] for item in value["sources"]}
        self.assertEqual(
            imports,
            {
                "QIKVRTFormalization.Process.ConnectabilitySimulation",
                "QIKVRTFormalization.Process.OperationalContinuation",
                "QIKVRTFormalization.Process.WeightedConnectability",
            },
        )
        self.assertTrue(
            {
                "QIKVRT.V2.OperationalContinuation.FIT001_checked",
                "QIKVRT.V2.ConnectabilitySimulation.FIT002_checked",
                "QIKVRT.V2.ConnectabilitySimulation.FIT003_checked",
                "QIKVRT.V2.WeightedConnectability.MAT001_checked",
                "QIKVRT.V2.WeightedConnectability.MAT002_checked",
            }
            <= set(value["plan"]["theorems"])
        )
        self.assertEqual(
            value["plan"]["artifact_name"],
            "qikvrt-survival-connectability-kernel-evidence",
        )

    def test_axiom_parser_accepts_wrapped_reports(self) -> None:
        theorems = [
            "QIKVRT.V2.OperationalContinuation.FIT001_checked",
            "QIKVRT.V2.ConnectabilitySimulation.FIT002_checked",
        ]
        output = """
        'QIKVRT.V2.OperationalContinuation.FIT001_checked' does not depend on any axioms
        'FIT002_checked' depends on axioms:
          [propext, Quot.sound]
        """
        self.assertEqual(
            evidence.parse_axiom_reports(output, theorems),
            {
                theorems[0]: [],
                theorems[1]: ["Quot.sound", "propext"],
            },
        )

    def test_comment_stripping_does_not_treat_truth_boundary_as_escape(self) -> None:
        source = """
        /- This comment may discuss an axiom or sorry without declaring one. -/
        theorem checked : True := by
          trivial
        """
        stripped = evidence.strip_lean_comments_and_strings(source)
        self.assertNotRegex(stripped, r"\baxiom\b|\bsorry\b")
        self.assertRegex(stripped, r"\btheorem\s+checked\b")


if __name__ == "__main__":
    unittest.main()
