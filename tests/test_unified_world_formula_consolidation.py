#!/usr/bin/env python3
"""Regression coverage for the consolidated 32-theorem kernel."""
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "formalization/QIKVRT_Formalization_v2.0"
ONTOLOGY = PACKAGE / "universal_ontology/CLAIM_MATRIX.json"
WORLD = PACKAGE / "universal_ontology/WORLD_FORMULA_CLAIM_MATRIX.json"
AUDIT = PACKAGE / "QIKVRTUniversalOntology/AxiomAudit.lean"
RELATIONS = PACKAGE / "QIKVRTFormalization/WorldFormula/Relations.lean"
SOURCE_PR_WORK = ROOT / "state/work_units/WORLD_FORMULA_RELATION_KERNEL_V1.json"


class UnifiedWorldFormulaConsolidationTests(unittest.TestCase):
    def load(self, path: pathlib.Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def test_union_contains_exactly_32_unique_theorem_constants(self):
        matrices = [self.load(ONTOLOGY), self.load(WORLD)]
        constants = [
            claim["proof_constant"]
            for matrix in matrices
            for claim in matrix["claims"]
            if claim["kind"] == "FORMAL_THEOREM"
        ]
        self.assertEqual(len(constants), 32)
        self.assertEqual(len(constants), len(set(constants)))
        audited = {
            line.strip().removeprefix("#print axioms ")
            for line in AUDIT.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("#print axioms ")
        }
        self.assertEqual(set(constants), audited)

    def test_world_formula_source_and_boundary_are_preserved(self):
        matrix = self.load(WORLD)
        self.assertEqual(matrix["source_pr"], 451)
        self.assertEqual(matrix["source_head"], "3a9a28fa0b6560754f77aef350e6229b42093d0f")
        self.assertEqual(matrix["physical_correspondence"], "NOT_INFERRED")
        self.assertTrue(RELATIONS.is_file())
        work = self.load(SOURCE_PR_WORK)
        self.assertEqual(work["claim_boundary"]["physical_correspondence"], "NOT_INFERRED")
        self.assertEqual(
            work["release_claims"],
            {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        )


if __name__ == "__main__":
    unittest.main()
