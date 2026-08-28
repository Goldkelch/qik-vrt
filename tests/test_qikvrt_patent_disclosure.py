# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
"""Static boundaries for the deterministic terminal/Mesh disclosure dossier."""
from __future__ import annotations

import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOSSIER = ROOT / "docs/patent/QIKVRT_DETERMINISTIC_MESH_DISCLOSURE_V1.md"
DISCLOSURE = ROOT / "state/patent/QIKVRT_DETERMINISTIC_MESH_DISCLOSURE_V1.json"
EVIDENCE = ROOT / "state/patent/QIKVRT_DETERMINISTIC_MESH_EVIDENCE_MATRIX_V1.json"
PRIOR_ART = ROOT / "state/patent/QIKVRT_DETERMINISTIC_MESH_PRIOR_ART_SEARCH_V1.json"


class PatentDisclosureTests(unittest.TestCase):
    def test_dossier_covers_the_bounded_technical_stack(self) -> None:
        text = DOSSIER.read_text(encoding="utf-8")
        for required in (
            "Sessionless HTTP and explicit retained state",
            "Frozen finite Mesh epoch and `N*N` topology",
            "Canonical finite wire frame",
            "Deterministic admission",
            "Prototype reproducibility and physical evidence plan",
            "Prior-art and filing preparation plan",
        ):
            self.assertIn(required, text)
        self.assertIn("stateless HTTP request != stateless daemon != stateless external system", text)
        self.assertIn("not a patent\napplication", text)
        self.assertIn("Firefox reference\nclient", text)
        self.assertIn("PHYSICAL_EXECUTION_OPEN", text)

    def test_evidence_is_bound_to_existing_artifacts_and_keeps_boundaries_open(self) -> None:
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["schema"], "qikvrt_deterministic_mesh_evidence_matrix_v1")
        self.assertEqual(evidence["status"], "TECHNICAL_EVIDENCE_INDEX_NOT_LEGAL_OR_PHYSICAL_PROOF")
        identifiers = [item["id"] for item in evidence["evidence"]]
        self.assertEqual(len(identifiers), len(set(identifiers)))
        for item in evidence["evidence"]:
            self.assertTrue(item["boundary"])
            for relative_path in item["artifacts"]:
                self.assertTrue((ROOT / relative_path).is_file(), relative_path)
        self.assertFalse(evidence["claims"]["novelty_established"])
        self.assertFalse(evidence["claims"]["physical_hardware_observed"])

    def test_disclosure_and_search_plan_do_not_preclaim_legal_result(self) -> None:
        disclosure = json.loads(DISCLOSURE.read_text(encoding="utf-8"))
        prior_art = json.loads(PRIOR_ART.read_text(encoding="utf-8"))
        self.assertEqual(disclosure["evidence_matrix"], "state/patent/QIKVRT_DETERMINISTIC_MESH_EVIDENCE_MATRIX_V1.json")
        self.assertTrue(disclosure["boundaries"]["http_is_sessionless_not_system_stateless"])
        self.assertFalse(disclosure["boundaries"]["firefox_v2_peer_runtime_observed"])
        self.assertFalse(disclosure["claims"]["patentability_determined"])
        self.assertFalse(disclosure["claims"]["application_filed"])
        self.assertEqual(prior_art["status"], "PRELIMINARY_SEARCH_NOT_A_NOVELTY_OPINION")
        self.assertIn("claim_element_by_element_chart", prior_art["search_plan"]["required_methods"])
        self.assertFalse(prior_art["claims"]["novelty_established"])


if __name__ == "__main__":
    unittest.main()
