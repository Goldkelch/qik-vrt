#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "docs/publications/2026-08-01-scientific-fact-growth-mesh"
IETF_BASE = ROOT / "external/ietf/draft-lohmann-qikvrt-scientific-claim-assurance-00"


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ScientificFactGrowthPublicationTests(unittest.TestCase):
    def test_complete_claim_inventory_and_boundaries(self) -> None:
        matrix = load_json(PUBLICATION / "CLAIM_MATRIX.json")
        self.assertEqual(matrix["publication_id"], "qikvrt-scientific-fact-growth-mesh-v1")
        self.assertEqual(matrix["claim_count"], len(matrix["claims"]))
        self.assertEqual(matrix["claim_count"], 30)
        claims = {claim["claim_id"]: claim for claim in matrix["claims"]}
        self.assertEqual(len(claims), 30)
        self.assertEqual(
            sum(1 for claim in claims.values() if claim["classification"] == "FORMAL_PROVED"),
            21,
        )
        self.assertEqual(
            sum(1 for claim in claims.values() if claim["classification"] == "OPEN"),
            4,
        )
        for claim in claims.values():
            self.assertTrue(claim["statement"].strip())
            self.assertTrue(claim["boundary"].strip())
            self.assertIsInstance(claim["proof_refs"], list)
            self.assertIsInstance(claim["sources"], list)
            if claim["classification"] == "FORMAL_PROVED":
                self.assertEqual(claim["proof_refs"], [claim["proof"]])
            else:
                self.assertEqual(claim["proof_refs"], [])
        self.assertEqual(claims["SFG-024"]["sources"], ["audio_source"])
        self.assertFalse(matrix["aggregate"]["global_scientific_novelty_established"])
        self.assertFalse(matrix["aggregate"]["universal_truth_established"])
        self.assertEqual(matrix["aggregate"]["effect_ack"], "EFFECT_ACK_CONTINUE")

    def test_lean_snapshot_and_receipt_are_exact(self) -> None:
        receipt = load_json(PUBLICATION / "LEAN_KERNEL_RECEIPT.json")
        repository_source = (
            ROOT
            / "formalization/QIKVRT_Formalization_v2.0/"
            "QIKVRTFormalization/Knowledge/ScientificFactGrowth.lean"
        )
        snapshot = PUBLICATION / "FORMAL_ScientificFactGrowth.lean"
        self.assertEqual(repository_source.read_bytes(), snapshot.read_bytes())
        self.assertEqual(receipt["formal_source"]["sha256"], sha256(snapshot))
        self.assertEqual(receipt["compiler"]["version"], "4.19.0")
        self.assertEqual(receipt["kernel_status"], "VERIFIED")
        self.assertEqual(receipt["theorem_count"], 21)
        self.assertFalse(receipt["sorry_ax_observed"])
        self.assertFalse(receipt["project_specific_axiom_observed"])
        source_text = snapshot.read_text(encoding="utf-8")
        self.assertNotIn("sorry", source_text)

    def test_policy_schema_tool_and_tests_are_discoverable(self) -> None:
        protocol = load_json(ROOT / "policy/SCIENTIFIC_FACT_GROWTH_PROTOCOL.json")
        schema = load_json(ROOT / "schemas/scientific_claim_envelope.schema.json")
        self.assertEqual(protocol["mode"], "FINITE_CORPUS_RELATIVE_CLASSIFY_PROPOSE_ONLY")
        self.assertFalse(protocol["effect_boundary"]["publication_authorized"])
        self.assertEqual(schema["properties"]["schema"]["const"], "qikvrt_scientific_claim_envelope_v1")
        self.assertTrue((ROOT / "tools/qikvrt_scientific_fact_growth.py").is_file())
        self.assertTrue((ROOT / "tests/test_scientific_fact_growth.py").is_file())

    def test_pdf_validation_binds_exact_bytes(self) -> None:
        validation = load_json(PUBLICATION / "PDF_RENDER_VALIDATION.json")
        self.assertEqual(len(validation["documents"]), 2)
        self.assertEqual({item["page_count"] for item in validation["documents"]}, {2, 10})
        for item in validation["documents"]:
            source = PUBLICATION / item["source"]
            pdf = PUBLICATION / item["pdf"]
            self.assertEqual(item["source_sha256"], sha256(source))
            self.assertEqual(item["pdf_sha256"], sha256(pdf))
            self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))
            self.assertEqual(item["second_pass_warnings"], 0)
            self.assertEqual(item["second_pass_overfull_boxes"], 0)
            self.assertEqual(item["visual_inspection"], "PASS")

    def test_multilingual_read_aloud_set_is_complete(self) -> None:
        languages = ("DE", "EN", "FR", "IT", "ES", "PT", "EL", "PL", "DA", "NB", "SV")
        for language in languages:
            path = PUBLICATION / f"ARTICLE_WHATSAPP_{language}.md"
            text = path.read_text(encoding="utf-8")
            self.assertGreater(len(text), 5000, language)
            self.assertGreaterEqual(len(re.findall(r"(?m)^\*[0-9]+\.", text)), 12, language)
            self.assertIn("QIK-VRT", text)

    def test_source_audio_is_bound_but_not_published_as_evidence(self) -> None:
        source = load_json(PUBLICATION / "SOURCE_MEDIA_RECEIPT.json")
        self.assertEqual(source["source_count"], 1)
        item = source["sources"][0]
        self.assertEqual(item["sha256"], "8cb4693d2e0d1732986974d38733e0fdecf275889e379398790600c3b14d0a9e")
        self.assertFalse(item["repository_inclusion"])
        self.assertFalse(item["network_upload_performed"])
        self.assertFalse(source["evidence_boundary"]["spoken_claims_proved_true"])

    def test_ietf_candidate_is_deterministically_bound_and_not_submitted(self) -> None:
        candidate = load_json(IETF_BASE.with_suffix(".CANDIDATE.json"))
        validation = load_json(PUBLICATION / "IETF_RENDER_VALIDATION.json")
        self.assertEqual(candidate["state"], "CANDIDATE_NOT_SUBMITTED")
        self.assertFalse(candidate["datatracker_submission_performed"])
        self.assertFalse(candidate["protocol_scope"]["normative_wire_change"])
        for extension in ("xml", "txt", "html"):
            path = IETF_BASE.with_suffix(f".{extension}")
            self.assertEqual(candidate["artifacts"][extension]["sha256"], sha256(path))
        self.assertTrue(validation["reproducibility"]["text_byte_identical_between_runs"])
        self.assertTrue(validation["reproducibility"]["html_byte_identical_between_runs"])
        self.assertTrue(validation["reproducibility"]["final_runs_warning_and_error_free"])
        self.assertEqual(validation["truth_boundaries"]["effect_ack"], "EFFECT_ACK_CONTINUE")

    def test_public_text_preserves_nonclaims(self) -> None:
        monograph = (PUBLICATION / "FACHARTIKEL_DE.md").read_text(encoding="utf-8")
        boundary = (PUBLICATION / "EVIDENCE_BOUNDARY.md").read_text(encoding="utf-8")
        for marker in (
            "universelle Wahrheit",
            "globale wissenschaftliche Neuheit",
            "physikalische Brücke",
            "jede erdenkliche Frage",
        ):
            self.assertIn(marker, boundary)
        self.assertIn("kein orakel", monograph.lower())
        self.assertIn("nicht bewiesen", monograph.lower())


if __name__ == "__main__":
    unittest.main()
