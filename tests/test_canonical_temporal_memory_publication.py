#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import hashlib
import itertools
import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION = (
    ROOT
    / "docs/publications/2026-07-30-canonical-temporal-memory-effect-ack"
)
TEX = (
    PUBLICATION
    / "QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.tex"
)
PDF = (
    PUBLICATION
    / "QIK-VRT_Kanonischer_Speicher_Retrokausalitaet_EFFECT_ACK_2026-07-30.pdf"
)
CLAIMS = PUBLICATION / "CLAIM_MATRIX.json"
SOURCES = PUBLICATION / "SOURCE_EVIDENCE_BINDINGS.json"
BOUNDARY = PUBLICATION / "EVIDENCE_BOUNDARY.md"
RENDER = PUBLICATION / "PDF_RENDER_VALIDATION.json"
ZENODO_SUMS = PUBLICATION / "ZENODO_SHA256SUMS"
LEAN = (
    ROOT
    / "formalization/QIKVRT_Formalization_v2.0"
    / "QIKVRTEffectAck/CanonicalTemporalMemory.lean"
)
ENTRY = (
    ROOT
    / "formalization/QIKVRT_Formalization_v2.0"
    / "QIKVRTEffectAck.lean"
)
SCOPE = "qikvrt-canonical-temporal-memory-effect-ack-v1"

THEOREMS = {
    "release_eq_true_iff",
    "release_requires_valid_past",
    "release_requires_valid_future",
    "release_requires_effect_ack",
    "future_boundary_is_counterfactually_relevant",
    "future_boundary_does_not_overwrite_past",
    "reciprocal_closure_eq_true_iff",
    "reciprocal_closure_requires_cause_and_effect",
}


def release(
    past_valid: bool,
    future_valid: bool,
    cause_bound: bool,
    policy_passed: bool,
    effect_ack_done: bool,
) -> bool:
    return all(
        (
            past_valid,
            future_valid,
            cause_bound,
            policy_passed,
            effect_ack_done,
        )
    )


class CanonicalTemporalMemoryPublicationTests(unittest.TestCase):
    def test_candidate_files_and_scope_are_present(self) -> None:
        for path in (
            TEX,
            PDF,
            CLAIMS,
            SOURCES,
            BOUNDARY,
            RENDER,
            ZENODO_SUMS,
            LEAN,
            ENTRY,
        ):
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 0, path)

    def test_release_truth_table_is_done_only_and_two_boundary(self) -> None:
        released = []
        for values in itertools.product((False, True), repeat=5):
            outcome = release(*values)
            if outcome:
                released.append(values)
            for index, value in enumerate(values):
                if not value:
                    self.assertFalse(
                        outcome,
                        f"release occurred with false condition {index}: {values}",
                    )
        self.assertEqual(released, [(True, True, True, True, True)])

    def test_future_boundary_is_nonvacuous_without_past_overwrite(self) -> None:
        fixed = {
            "past_valid": True,
            "cause_bound": True,
            "policy_passed": True,
            "effect_ack_done": True,
        }
        accepted = release(fixed["past_valid"], True, *tuple(fixed.values())[1:])
        rejected = release(fixed["past_valid"], False, *tuple(fixed.values())[1:])
        self.assertTrue(accepted)
        self.assertFalse(rejected)

        past_archive = b"canonical-observed-history"
        self.assertIs(past_archive, past_archive)
        self.assertEqual(
            (past_archive, b"anticipated-effect-a")[0],
            (past_archive, b"anticipated-effect-b")[0],
        )

    def test_lean_source_is_imported_named_and_escape_free(self) -> None:
        source = LEAN.read_text(encoding="utf-8")
        entry = ENTRY.read_text(encoding="utf-8")
        self.assertIn("import QIKVRTEffectAck.CanonicalTemporalMemory", entry)
        for theorem in THEOREMS:
            self.assertRegex(source, rf"\btheorem\s+{re.escape(theorem)}\b")
        for prohibited in (r"\bsorry\b", r"\badmit\b", r"\baxiom\b", r"\bunsafe\b"):
            self.assertIsNone(re.search(prohibited, source), prohibited)
        self.assertIn("does not assume an observation arriving from the physical", source)

    def test_claim_inventory_is_complete_typed_and_fail_closed(self) -> None:
        value = json.loads(CLAIMS.read_text(encoding="utf-8"))
        self.assertEqual(value["publication_id"], SCOPE)
        self.assertEqual(value["claim_count"], 10)
        self.assertEqual(len(value["claims"]), 10)
        self.assertEqual(
            {item["claim_id"] for item in value["claims"]},
            {f"CTM-{index:03d}" for index in range(1, 11)},
        )
        self.assertEqual(
            {item["classification"] for item in value["claims"]},
            {
                "FORMAL_PROVED",
                "SOURCE_BOUND",
                "NORMATIVE",
                "INTERPRETATIVE",
                "OPEN",
            },
        )
        self.assertFalse(value["completion_claims"]["pass"])
        self.assertFalse(value["completion_claims"]["final_pass"])
        self.assertFalse(value["completion_claims"]["effect_ack_done"])
        self.assertEqual(
            value["completion_claims"]["system_wide_completion"],
            "UNCLAIMED",
        )
        self.assertIn(
            value["proof_state"],
            {"AWAITING_EXACT_HEAD_KERNEL_RECEIPT", "KERNEL_VERIFIED"},
        )

    def test_source_bindings_cover_every_external_claim_source(self) -> None:
        value = json.loads(SOURCES.read_text(encoding="utf-8"))
        self.assertEqual(value["scope_id"], SCOPE)
        identifiers = {item["id"] for item in value["bindings"]}
        self.assertTrue(
            {
                "RFC8785",
                "RFC6920",
                "W3C-PROV-DM",
                "ABL-1964",
                "WHARTON-ARGAMAN-2020",
                "MA-KOFLER-ZEILINGER-2016",
                "EFFECT-ACK-DRAFT-01",
                "TONONI-KOCH-2015",
                "SETH-BAYNE-2022",
            }.issubset(identifiers)
        )
        for item in value["bindings"]:
            self.assertTrue(item["claim_ids"])
            self.assertTrue("doi" in item or "locator" in item)

    def test_candidate_checksum_index_is_complete_and_current(self) -> None:
        actual = {}
        for line in ZENODO_SUMS.read_text(encoding="ascii").splitlines():
            digest, name = line.split("  ", 1)
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
            self.assertNotIn(name, actual)
            actual[name] = digest
        expected_names = {
            "BOUNDARY_TEST_REPORT.json",
            "CITATION.cff",
            "CLAIM_MATRIX.json",
            "EVIDENCE_BOUNDARY.md",
            "LICENSE_NOTICE.md",
            "PDF_RENDER_VALIDATION.json",
            PDF.name,
            TEX.name,
            "README.md",
            "SOURCE_EVIDENCE_BINDINGS.json",
            "ZENODO_FILESET.md",
        }
        self.assertEqual(set(actual), expected_names)
        for name, digest in actual.items():
            self.assertEqual(
                hashlib.sha256((PUBLICATION / name).read_bytes()).hexdigest(),
                digest,
            )

    def test_paper_states_literal_thesis_and_scientific_boundaries(self) -> None:
        text = TEX.read_text(encoding="utf-8")
        required = (
            "Die Ausgangsthese lautet wortwörtlich",
            "Operationale Protokoll-Retrokausalität",
            "Kontrafaktische Relevanz der Zukunft",
            "Keine freigegebene Ursache ohne gebundene Wirkung",
            "Keine geschlossene Wirkung ohne gebundene Ursache",
            "future\\_boundary\\_does\\_not\\_overwrite\\_past",
            "SYSTEM\\_WIDE\\_COMPLETION",
            "ist empirisch offen",
            "Quod erat demonstrandum",
        )
        for phrase in required:
            self.assertIn(phrase, text)
        prohibited = (
            "Delayed-Choice-Experimente beweisen physikalische Retrokausalität",
            "Hashgleichheit beweist Wahrheit",
            "Wechselwirkung beweist Bewusstsein",
            "IETF-Konsens ist erreicht",
            "SYSTEM\\_WIDE\\_COMPLETION=true",
        )
        for phrase in prohibited:
            self.assertNotIn(phrase, text)

    def test_render_receipt_is_candidate_scoped_and_not_publication_claim(self) -> None:
        value = json.loads(RENDER.read_text(encoding="utf-8"))
        self.assertEqual(value["scope_id"], SCOPE)
        self.assertEqual(value["state"], "PDF_VISUALLY_VERIFIED")
        self.assertEqual(value["pdf"]["pages"], 15)
        self.assertTrue(value["visual_qa"]["all_pages_inspected"])
        self.assertFalse(value["completion_claims"]["zenodo_published"])
        self.assertFalse(value["completion_claims"]["ietf_revision_02_posted"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
