# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.

import copy
import hashlib
import json
import pathlib
import tempfile
import unittest

from tools import qikvrt_scientific_fact_growth as growth


def blank_claim(claim_id="SFG-TEST-001"):
    return {
        "schema": growth.SCHEMA,
        "claim_id": claim_id,
        "statement": "A bounded statement.",
        "classification": "OPEN",
        "status": "OPEN",
        "scope": "finite test scope",
        "boundary": "No external truth or effect is claimed.",
        "sources": [],
        "evidence": [],
        "proofs": [],
        "dependencies": [],
        "negates": [],
        "novelty": {
            "method": "CORPUS_RELATIVE_EXACT_CANONICAL_STATEMENT",
            "claimed": True,
        },
    }


def corpus(*claims):
    return {"schema": growth.CORPUS_SCHEMA, "corpus_id": "test", "claims": list(claims)}


class ScientificFactGrowthTests(unittest.TestCase):
    def test_open_claim_is_classified_without_truth_promotion(self):
        report = growth.evaluate(blank_claim(), corpus())
        self.assertEqual(report["decision"], "ADMIT_AS_CLASSIFIED")
        self.assertFalse(report["universal_truth_established"])
        self.assertFalse(report["global_scientific_novelty_established"])
        self.assertEqual(report["effect_ack"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(report["publication_authorized"])

    def test_formal_claim_requires_exact_kernel_receipt(self):
        claim = blank_claim()
        claim.update(classification="FORMAL_PROVED", status="PROVED")
        report = growth.evaluate(claim, corpus())
        self.assertEqual(report["decision"], "HOLD_OPEN")
        self.assertIn("formal_kernel_receipt", report["failed_checks"])

        claim["proofs"] = [{
            "kind": "LEAN_KERNEL_RECEIPT",
            "kernel_status": "VERIFIED",
            "compiler": "Lean 4.19.0",
            "theorem": "QIKVRT.V2.Knowledge.append_extends",
            "source_sha256": "1" * 64,
            "receipt_sha256": "2" * 64,
            "axioms": ["propext"],
        }]
        report = growth.evaluate(claim, corpus())
        self.assertEqual(report["decision"], "ADMIT_AS_CLASSIFIED")

    def test_nonformal_claim_cannot_borrow_formal_proof(self):
        claim = blank_claim()
        claim["proofs"] = [{"not": "a receipt"}]
        report = growth.evaluate(claim, corpus())
        self.assertEqual(report["decision"], "HOLD_OPEN")

    def test_empirical_claim_requires_observation_contract(self):
        claim = blank_claim()
        claim.update(classification="EMPIRICALLY_EVIDENCED", status="EVIDENCED")
        self.assertEqual(growth.evaluate(claim, corpus())["decision"], "HOLD_OPEN")
        claim["evidence"] = [{
            "kind": "OBSERVATION",
            "source_sha256": "3" * 64,
            "method": "predeclared finite measurement",
            "uncertainty": "bounded interval",
            "calibration": "traceable calibration record",
            "provenance": "content-addressed transformation chain",
        }]
        self.assertEqual(growth.evaluate(claim, corpus())["decision"], "ADMIT_AS_CLASSIFIED")

    def test_missing_dependency_holds_open(self):
        claim = blank_claim()
        claim["dependencies"] = ["SFG-MISSING-001"]
        report = growth.evaluate(claim, corpus())
        self.assertIn("dependency_closure", report["failed_checks"])

    def test_explicit_conflict_is_preserved(self):
        prior = blank_claim("SFG-PRIOR-001")
        prior["novelty"]["claimed"] = True
        claim = blank_claim("SFG-NEW-001")
        claim["negates"] = [prior["claim_id"]]
        report = growth.evaluate(claim, corpus(prior))
        self.assertEqual(report["decision"], "CONTESTED_PRESERVE_BOTH")
        self.assertEqual(report["explicit_conflicts"], [prior["claim_id"]])

    def test_novelty_is_corpus_relative_only(self):
        claim = blank_claim()
        first = growth.evaluate(claim, corpus())
        self.assertTrue(first["corpus_relative_syntactic_novel"])
        claim2 = copy.deepcopy(claim)
        claim2["claim_id"] = "SFG-TEST-002"
        claim2["novelty"]["claimed"] = False
        second = growth.evaluate(claim2, corpus(claim))
        self.assertFalse(second["corpus_relative_syntactic_novel"])
        self.assertFalse(second["global_scientific_novelty_established"])

    def test_merge_is_commutative_and_preserves_identifier_conflict(self):
        left_claim = blank_claim("SFG-SAME-001")
        right_claim = copy.deepcopy(left_claim)
        right_claim["statement"] = "A different bounded statement."
        left = growth.merge_corpora(corpus(left_claim), corpus(right_claim))
        right = growth.merge_corpora(corpus(right_claim), corpus(left_claim))
        self.assertEqual(growth.canonical_json(left), growth.canonical_json(right))
        self.assertEqual(left["claim_count"], 2)
        self.assertEqual(left["identifier_conflicts"][0]["claim_id"], "SFG-SAME-001")

    def test_unknown_claim_key_blocks(self):
        claim = blank_claim()
        claim["execute_me"] = True
        with self.assertRaises(growth.ValidationError):
            growth.evaluate(claim, corpus())

    def test_cli_output_is_deterministic(self):
        claim = blank_claim()
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            claim_path = root / "claim.json"
            corpus_path = root / "corpus.json"
            one = root / "one.json"
            two = root / "two.json"
            claim_path.write_text(json.dumps(claim), encoding="utf-8")
            corpus_path.write_text(json.dumps(corpus()), encoding="utf-8")
            self.assertEqual(growth.main(["evaluate", "--claim", str(claim_path),
                                          "--corpus", str(corpus_path), "--output", str(one)]), 0)
            self.assertEqual(growth.main(["evaluate", "--claim", str(claim_path),
                                          "--corpus", str(corpus_path), "--output", str(two)]), 0)
            self.assertEqual(hashlib.sha256(one.read_bytes()).digest(),
                             hashlib.sha256(two.read_bytes()).digest())


if __name__ == "__main__":
    unittest.main()
