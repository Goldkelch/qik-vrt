#!/usr/bin/env python3
"""Regression tests for the executable world-formula relation kernel."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPOSITORY_ROOT / "formalization" / "QIKVRT_Formalization_v2.0"
SOURCE = (
    PACKAGE_ROOT
    / "QIKVRTFormalization"
    / "WorldFormula"
    / "Relations.lean"
)
AUDIT = (
    PACKAGE_ROOT
    / "QIKVRTFormalization"
    / "WorldFormula"
    / "AxiomAudit.lean"
)
TOP_LEVEL = PACKAGE_ROOT / "QIKVRTFormalization.lean"
TOOLCHAIN = PACKAGE_ROOT / "lean-toolchain"
WORK_UNIT = (
    REPOSITORY_ROOT
    / "state"
    / "work_units"
    / "WORLD_FORMULA_RELATION_KERNEL_V1.json"
)


class WorldFormulaRelationKernelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.work_unit = json.loads(WORK_UNIT.read_text(encoding="utf-8"))

    def test_toolchain_and_source_bindings(self) -> None:
        lean = self.work_unit["lean"]
        self.assertEqual(lean["toolchain"], TOOLCHAIN.read_text(encoding="utf-8").strip())
        expected_paths = {
            SOURCE.relative_to(REPOSITORY_ROOT).as_posix(),
            AUDIT.relative_to(REPOSITORY_ROOT).as_posix(),
        }
        self.assertEqual(set(lean["source_modules"]), expected_paths)
        for path in expected_paths:
            self.assertTrue((REPOSITORY_ROOT / path).is_file(), path)

    def test_relation_inventory_is_complete_and_unique(self) -> None:
        relations = self.work_unit["relations"]
        expected_ids = {f"WF-R{index:02d}" for index in range(1, 13)}
        observed_ids = {relation["id"] for relation in relations}
        self.assertEqual(observed_ids, expected_ids)
        self.assertEqual(len(relations), len(observed_ids))
        self.assertTrue(
            all(relation["status"] == "CANDIDATE_IMPLEMENTED" for relation in relations)
        )

    def test_axiom_audit_matches_theorem_inventory_exactly(self) -> None:
        expected = {
            f"#print axioms {name}" for name in self.work_unit["key_theorems"]
        }
        observed = {
            line.strip()
            for line in AUDIT.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("#print axioms ")
        }
        self.assertEqual(observed, expected)

    def test_top_level_imports_relation_kernel(self) -> None:
        import_line = "import QIKVRTFormalization.WorldFormula.Relations"
        lines = TOP_LEVEL.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines.count(import_line), 1)

    def test_source_contains_no_admitted_or_project_axiom_declaration(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        forbidden = re.compile(r"(?m)^\s*(?:sorry|admit|axiom)\b")
        self.assertIsNone(forbidden.search(source))
        self.assertFalse(self.work_unit["lean"]["admitted_gaps_permitted"])

    def test_epistemic_boundary_remains_fail_closed(self) -> None:
        boundary = self.work_unit["claim_boundary"]
        self.assertEqual(boundary["physical_correspondence"], "NOT_INFERRED")
        self.assertEqual(boundary["empirical_confirmation"], "NOT_CLAIMED")
        self.assertEqual(boundary["scientific_establishment"], "NOT_CLAIMED")
        self.assertEqual(boundary["scientific_consensus"], "NOT_CLAIMED")
        self.assertEqual(
            self.work_unit["candidate_state"],
            "MATERIALIZED_PENDING_LEAN_BUILD_AXIOM_AUDIT_INTEGRITY_AND_EXACT_HEAD_RECEIPT",
        )
        self.assertEqual(
            self.work_unit["release_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )


if __name__ == "__main__":
    unittest.main()
