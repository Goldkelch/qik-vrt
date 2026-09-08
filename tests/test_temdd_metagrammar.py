#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
"""Structural regressions for the TEMDD conservative-metagrammar scope."""

from __future__ import annotations

import hashlib
import json
import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
FORMAL_ROOT = ROOT / "formalization/QIKVRT_Formalization_v2.0"
META = FORMAL_ROOT / "QIKVRTFormalization/TEMDD/MetaGrammar.lean"
AUDIT = FORMAL_ROOT / "QIKVRTFormalization/TEMDD/AxiomAudit.lean"
SCOPE = FORMAL_ROOT / "TEMDD_PROOF_SCOPE.json"
POLICY = ROOT / "policy/TEMDD_LANGUAGE_V1.json"
ARTICLE = ROOT / "docs/TEMDD_METAGRAMMAR.md"


def identity(path: pathlib.Path) -> dict[str, object]:
    raw = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "git_blob_sha1": hashlib.sha1(
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest(),
    }


class TEMDDMetaGrammarScopeTests(unittest.TestCase):
    def test_scope_binds_the_exact_formal_surface(self) -> None:
        scope = json.loads(SCOPE.read_text(encoding="utf-8"))
        self.assertEqual(scope["formal_system"], "leanprover/lean4:v4.19.0")
        self.assertEqual(
            scope["source_files"]["metagrammar"]["path"],
            META.relative_to(ROOT).as_posix(),
        )
        self.assertEqual(
            scope["source_files"]["axiom_audit"]["path"],
            AUDIT.relative_to(ROOT).as_posix(),
        )
        self.assertEqual(scope["claim_class"], "FORMAL_MODEL_THEOREM")
        self.assertFalse(scope["release_claims"]["PASS"])
        self.assertFalse(scope["release_claims"]["FINAL_PASS"])
        self.assertFalse(scope["release_claims"]["EFFECT_ACK_DONE"])
        for source_file in scope["source_files"].values():
            self.assertEqual(identity(ROOT / source_file["path"]), source_file)

    def test_theorem_inventory_is_audited_and_has_no_proof_escape(self) -> None:
        scope = json.loads(SCOPE.read_text(encoding="utf-8"))
        source = META.read_text(encoding="utf-8")
        audit = AUDIT.read_text(encoding="utf-8")
        for theorem in scope["theorems"]:
            name = theorem["name"]
            self.assertIn(f"theorem {name}", source)
            self.assertIn(name, audit)
        self.assertTrue(scope["proof_escape_policy"]["project_axioms_forbidden"])
        self.assertTrue(scope["proof_escape_policy"]["sorry_admit_forbidden"])

    def test_policy_and_public_article_keep_the_boundary_explicit(self) -> None:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        meta = policy["metagrammar"]
        self.assertEqual(meta["formal_kernel"], META.relative_to(ROOT).as_posix())
        self.assertIn("truth_extraction_from_arbitrary_data", meta["nonclaims"])
        article = ARTICLE.read_text(encoding="utf-8").lower()
        for required in (
            "konservative erweiterung",
            "nicht bewiesen",
            "keine wahrheitsorakel",
            "empirische",
        ):
            self.assertIn(required, article)


if __name__ == "__main__":
    unittest.main()
