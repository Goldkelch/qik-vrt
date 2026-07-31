#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLICATION = ROOT / "docs/publications/2026-07-31-survival-anschlussfaehigsten"
PROJECT = ROOT / "formalization/QIKVRT_Formalization_v2.0"


def load_json(name: str) -> dict:
    return json.loads((PUBLICATION / name).read_text(encoding="utf-8"))


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(  # noqa: S324 -- canonical Git object identity
        f"blob {len(data)}\0".encode("ascii") + data
    ).hexdigest()


class SurvivalConnectabilityPublicationTests(unittest.TestCase):
    def test_canonical_interpretation_and_truth_boundary_are_both_present(self) -> None:
        canonical = (PUBLICATION / "CANONICAL_STATEMENT.md").read_text(encoding="utf-8")
        boundary = (PUBLICATION / "EVIDENCE_BOUNDARY.md").read_text(encoding="utf-8")
        self.assertIn(
            "Survival of the fittest = Survival of the Anschlussfähigsten.",
            canonical,
        )
        for component in (
            "Unterscheidungsfähigkeit",
            "Anpassungsfähigkeit",
            "Wirkungserhaltung",
            "Anschlussfähigkeit",
        ):
            self.assertIn(component, canonical)
        self.assertIn("keine neue Definition biologischer Fitness", boundary)
        self.assertIn("keine empirische Überlebensprognose", boundary)
        self.assertIn("kein Zenodo-Upload wird behauptet", boundary)

    def test_claim_matrix_is_fail_closed_before_kernel_receipt(self) -> None:
        matrix = load_json("CLAIM_MATRIX.json")
        self.assertEqual(matrix["claim_count"], len(matrix["claims"]))
        self.assertEqual(
            matrix["proof_state"], "AWAITING_EXACT_HEAD_KERNEL_RECEIPT"
        )
        self.assertEqual(
            matrix["completion_claims"],
            {
                "effect_ack_done": False,
                "final_pass": False,
                "pass": False,
                "system_wide_completion": "UNCLAIMED",
            },
        )
        claims = {item["claim_id"]: item for item in matrix["claims"]}
        self.assertEqual(len(claims), matrix["claim_count"])
        for claim_id in ("FIT-001", "FIT-002", "FIT-003"):
            self.assertEqual(claims[claim_id]["classification"], "FORMAL_PENDING_KERNEL")
            self.assertEqual(
                claims[claim_id]["status"],
                "PROOF_SOURCE_PRESENT_AWAITING_EXACT_HEAD_KERNEL_RECEIPT",
            )
        self.assertEqual(claims["EMP-001"]["status"], "OPEN_EMPIRICAL")
        self.assertEqual(claims["LIM-001"]["status"], "NOT_CLAIMED_OUT_OF_SCOPE")
        self.assertEqual(claims["NOR-001"]["status"], "DOES_NOT_FOLLOW")

    def test_kernel_plan_binds_all_formal_claims_and_source_bytes(self) -> None:
        matrix = load_json("CLAIM_MATRIX.json")
        plan = load_json("KERNEL_PROOF_PLAN.json")
        formal_refs = {
            ref
            for claim in matrix["claims"]
            if claim["classification"] == "FORMAL_PENDING_KERNEL"
            for ref in claim["proof_refs"]
        }
        self.assertEqual(formal_refs, set(plan["theorems"]))
        self.assertEqual(
            set(plan["axiom_audit"]["expected_axioms_by_theorem"]), formal_refs
        )
        for source in plan["sources"]:
            path = PROJECT / source["path"]
            self.assertTrue(path.is_file())
            self.assertEqual(path.stat().st_size, source["bytes"])
            self.assertEqual(sha256(path), source["sha256"])
            self.assertEqual(git_blob(path), source["git_blob_sha1"])

    def test_pdf_receipt_binds_exact_candidate_and_remains_prepublication(self) -> None:
        receipt = load_json("PDF_RENDER_VALIDATION.json")
        self.assertEqual(receipt["state"], "PDF_VISUALLY_VERIFIED")
        self.assertEqual(receipt["build"]["state"], "PASS")
        self.assertEqual(receipt["visual_qa"]["state"], "PASS")
        self.assertEqual(receipt["visual_qa"]["inspected_pages"], list(range(1, 15)))
        self.assertEqual(
            receipt["completion_claims"],
            {"repository_promotion_complete": False, "zenodo_published": False},
        )
        for key in ("markdown_source", "source", "pdf"):
            item = receipt[key]
            path = ROOT / item["path"]
            self.assertEqual(path.stat().st_size, item["bytes"])
            self.assertEqual(sha256(path), item["sha256"])
            self.assertEqual(git_blob(path), item["git_blob_sha1"])

    def test_claims_sources_and_archived_formal_snapshots_are_complete(self) -> None:
        matrix = load_json("CLAIM_MATRIX.json")
        bindings = load_json("SOURCE_EVIDENCE_BINDINGS.json")
        snapshots = load_json("FORMAL_SOURCE_SNAPSHOT.json")
        claim_ids = {item["claim_id"] for item in matrix["claims"]}
        self.assertEqual(set(bindings["claim_bindings"]), claim_ids)
        source_ids = [item["id"] for item in bindings["sources"]]
        self.assertEqual(len(source_ids), len(set(source_ids)))
        source_id_set = set(source_ids)
        for references in bindings["claim_bindings"].values():
            self.assertTrue(set(references) <= source_id_set)
        self.assertIn("DARWIN-VARIATION-1868", bindings["claim_bindings"]["HIS-001"])
        fileset = (PUBLICATION / "ZENODO_FILESET.md").read_text(encoding="utf-8")
        self.assertEqual(
            snapshots["state"], "BYTE_IDENTICAL_TO_KERNEL_PLAN_SOURCES"
        )
        for item in snapshots["snapshots"]:
            repository_path = ROOT / item["repository_path"]
            snapshot_path = ROOT / item["snapshot_path"]
            self.assertEqual(repository_path.read_bytes(), snapshot_path.read_bytes())
            self.assertEqual(snapshot_path.stat().st_size, item["bytes"])
            self.assertEqual(sha256(snapshot_path), item["sha256"])
            self.assertEqual(git_blob(snapshot_path), item["git_blob_sha1"])
            self.assertIn(snapshot_path.name, fileset)
        self.assertIn("ORIGINAL_THESIS_TRANSCRIPT.md", fileset)

    def test_article_claim_table_matches_machine_claim_ids(self) -> None:
        matrix = load_json("CLAIM_MATRIX.json")
        article = (PUBLICATION / "ARTICLE_DE.md").read_text(encoding="utf-8")
        table_ids = set(re.findall(r"(?m)^\| ([A-Z][A-Z0-9]*-[0-9]{3}) \|", article))
        self.assertEqual(table_ids, {item["claim_id"] for item in matrix["claims"]})

    def test_article_states_history_biology_model_and_empirical_limits(self) -> None:
        article = (PUBLICATION / "ARTICLE_DE.md").read_text(encoding="utf-8")
        required = (
            "Herbert Spencer",
            "Alfred Russel Wallace",
            "reproduktiven Beitrag",
            "FORMAL_CANDIDATE_AWAITING_KERNEL_CHECK",
            "FIT-001",
            "FIT-002",
            "FIT-003",
            "empirisch zu prüfen",
            "tatsächliche Überlebenswahrscheinlichkeit",
            "International Journal of Plant Sciences",
            "The Variation of Animals and Plants under Domestication",
        )
        for phrase in required:
            self.assertIn(phrase, article)
        self.assertNotRegex(article, re.compile(r"ZENODO_(?:PUBLISHED|MUTATION)\s*=\s*true"))

    def test_no_receipt_or_doi_is_fabricated_in_candidate(self) -> None:
        self.assertFalse((PUBLICATION / "KERNEL_RECEIPT.json").exists())
        self.assertFalse((PUBLICATION / "MACHINE_PROOF_BUNDLE.json").exists())
        self.assertFalse((PUBLICATION / "PREPUBLICATION_RETURN_RECEIPT.json").exists())
        citation = (PUBLICATION / "CITATION.cff").read_text(encoding="utf-8")
        self.assertNotRegex(citation, re.compile(r"(?m)^doi\s*:"))
        self.assertNotRegex(citation, re.compile(r"(?m)^date-released\s*:"))


if __name__ == "__main__":
    unittest.main()
