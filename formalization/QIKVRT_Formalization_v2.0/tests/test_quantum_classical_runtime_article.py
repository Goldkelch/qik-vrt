#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import json
import pathlib
import re
import unittest

PROJECT = pathlib.Path(__file__).resolve().parents[1]
REPOSITORY = pathlib.Path(__file__).resolve().parents[3]
SOURCE = PROJECT / "QIKVRTEffectAck/QuantumClassicalRuntime.lean"
ENTRY = PROJECT / "QIKVRTEffectAck.lean"
CLAIMS = REPOSITORY / "docs/publications/2026-07-28-verantwortungsgebundener-erkenntnisprozess-quantenklassische-wirkungsmaschine/CLAIM_MATRIX.json"

THEOREMS = (
    "responsibleRelease_eq_true_iff",
    "responsibleRelease_requires_uncertainty",
    "responsibleRelease_requires_gate",
    "responsibleRelease_requires_effect_observation",
    "responsibility_does_not_force_deterministic_measurement",
    "measurement_alone_does_not_authorize_release",
    "backend_replacement_preserves_shape",
    "simulator_and_qpu_share_complete_shape",
    "selectState_effect_ack_iff",
)


class QuantumClassicalRuntimeArticleProofTests(unittest.TestCase):
    def test_source_is_imported_and_has_no_proof_escape(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        entry = ENTRY.read_text(encoding="utf-8")
        self.assertIn("import QIKVRTEffectAck.QuantumClassicalRuntime", entry)
        for prohibited in (r"\bsorry\b", r"\badmit\b", r"\baxiom\b", r"unsafe"):
            self.assertIsNone(re.search(prohibited, source))

    def test_all_named_theorems_are_present(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for theorem in THEOREMS:
            self.assertRegex(source, rf"\btheorem\s+{re.escape(theorem)}\b")

    def test_claim_matrix_binds_every_formal_reference(self) -> None:
        value = json.loads(CLAIMS.read_text(encoding="utf-8"))
        formal = [c for c in value["claims"] if c["classification"] == "FORMAL_KERNEL_PROVED"]
        self.assertEqual(len(formal), 8)
        refs = {ref.rsplit(".", 1)[-1] for claim in formal for ref in claim["proof_refs"]}
        self.assertEqual(refs, set(THEOREMS))
        self.assertTrue(all(c["status"] == "PROOF_SOURCE_PRESENT_AWAITING_KERNEL_RECEIPT" for c in formal))

    def test_real_qpu_integration_remains_open(self) -> None:
        value = json.loads(CLAIMS.read_text(encoding="utf-8"))
        claim = next(c for c in value["claims"] if c["claim_id"] == "QRT-018")
        self.assertEqual(claim["classification"], "IMPLEMENTATION_OPEN")
        self.assertEqual(claim["status"], "OPEN")


if __name__ == "__main__":
    unittest.main(verbosity=2)
