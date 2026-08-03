#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Verify the bounded virtual-past reception research note."""

from __future__ import annotations

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "docs/publications/2026-08-03-virtual-past-reception"
MATRIX = BUNDLE / "CLAIM_MATRIX.json"
WORK_UNIT = ROOT / "work-units/QIKVRT_VIRTUAL_PAST_RECEPTION_INTEGRATION_V1.json"


class VirtualPastReceptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
        cls.work_unit = json.loads(WORK_UNIT.read_text(encoding="utf-8"))

    def test_bundle_files_exist(self) -> None:
        for name in (
            "README.md",
            "NOTE_DE.md",
            "CLAIM_MATRIX.json",
            "EVIDENCE_BOUNDARY.md",
            "CORRECTION_NOTICE.md",
        ):
            self.assertTrue((BUNDLE / name).is_file(), name)

    def test_claims_are_typed_and_separated(self) -> None:
        self.assertEqual(self.matrix["claim_count"], 3)
        claims = {entry["claim_id"]: entry for entry in self.matrix["claims"]}
        self.assertEqual(set(claims), {"VPR-001", "VPR-002", "VPR-003"})
        self.assertEqual(claims["VPR-001"]["classification"], "INTERPRETATIVE")
        self.assertEqual(claims["VPR-001"]["status"], "DECLARED")
        self.assertEqual(claims["VPR-002"]["classification"], "SOURCE_BOUND")
        self.assertEqual(claims["VPR-002"]["status"], "BOUND")
        self.assertEqual(claims["VPR-003"]["classification"], "OPEN")
        self.assertEqual(claims["VPR-003"]["status"], "OPEN")

    def test_no_claim_class_manufactures_effect_ack(self) -> None:
        mapping = self.matrix["effect_ack_mapping"]
        self.assertIs(mapping["claim_class_selects_effect_ack_state"], False)
        completion = self.matrix["completion_claims"]
        self.assertIs(completion["pass"], False)
        self.assertIs(completion["final_pass"], False)
        self.assertIs(completion["effect_ack_done"], False)

    def test_work_unit_does_not_manufacture_effect_ack_state(self) -> None:
        self.assertIs(self.work_unit["effect_ack_state_claimed"], False)
        self.assertEqual(
            self.work_unit["effect_ack_status"],
            "NOT_DERIVED_NO_COMPLETE_BOUND_DECISION_RECORD",
        )
        self.assertNotIn("effect_state", self.work_unit)

    def test_no_new_zenodo_or_ietf_effect_is_authorized(self) -> None:
        self.assertEqual(
            self.work_unit["zenodo_disposition"]["action"],
            "NO_NEW_RECORD_OR_VERSION_FOR_THIS_NOTE",
        )
        self.assertEqual(
            self.work_unit["ietf_disposition"]["action"],
            "NO_NEW_REVISION_OR_SUBMISSION_FOR_THIS_NOTE",
        )
        boundary = self.work_unit["authorization_boundary"]
        self.assertIs(boundary["zenodo_mutation_authorized"], False)
        self.assertIs(boundary["ietf_datatracker_mutation_authorized"], False)
        self.assertIs(boundary["merge_authorized_by_this_work_unit"], False)

    def test_active_h3_effect_writer_is_excluded(self) -> None:
        exclusion = self.work_unit["writer_exclusion"]
        self.assertEqual(
            exclusion["protected_branch"],
            "recovery-execution/vrtcore-relational-h3-e1-v1",
        )
        self.assertRegex(exclusion["observed_head"], r"^[0-9a-f]{40}$")

    def test_effect_ack_boundary_does_not_exclude_compensation(self) -> None:
        consequence = self.work_unit["effect_ack_consequence"]
        self.assertIs(
            consequence["later_record_retroactively_unexecutes_past_effect"],
            False,
        )
        self.assertIs(
            consequence["compensation_or_real_world_reversal_excluded"],
            False,
        )

    def test_makefile_is_repository_adapted_not_byte_portable(self) -> None:
        self.assertNotIn("Makefile", self.work_unit["portable_paths"])
        adapted = {
            entry["path"] for entry in self.work_unit["repository_adapted_paths"]
        }
        self.assertEqual(adapted, {"Makefile"})

    def test_note_preserves_scientific_boundary(self) -> None:
        note = (BUNDLE / "NOTE_DE.md").read_text(encoding="utf-8")
        evidence = (BUNDLE / "EVIDENCE_BOUNDARY.md").read_text(encoding="utf-8")
        self.assertIn("gewöhnliche Vorwärtskausalität", note)
        self.assertIn("keinen behaupteten Pfeil von heute", note)
        self.assertIn("keine physikalische oder ontische Retrokausalität", evidence)
        self.assertIn("keine neue empirisch unterscheidbare Vorhersage", evidence)


if __name__ == "__main__":
    unittest.main()
