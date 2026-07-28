#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import unittest
from unittest import mock

from tools import qikvrt_zenodo_publish as zenodo_publish

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIR = ROOT / "docs/publications/2026-07-28-canonical-closing-statement-historical-context"
ARTICLE = DIR / "ARTICLE_DE.md"
MANIFEST = DIR / "STATUS_ARTICLE_MANIFEST.json"
REQUEST = ROOT / "release/canonical-closing-status-article-2026-07-28/publish-request.json"
EVIDENCE = ROOT / "release/canonical-closing-status-article-2026-07-28/zenodo-publication.json"
COMPLETION = ROOT / "GLOBAL_COMPLETION_RECEIPT.json"

EXPECTED_SCOPE = "qikvrt-global-claim-scope-v1"
EXPECTED_COMPLETION_BLOB = "97466066860a57af412e79220a4dff43a82e300e"
EXPECTED_COMPLETION_SHA256 = "bbae95a8b4f10ff9601a452411fbe8a43f3b717c127d5cadfa84b94232f427e8"
EXPECTED_ARTICLE_BLOB = "3c2cb383687f353031d59b0f914dc91cd04a7ce3"
EXPECTED_MANIFEST_BLOB = "f70ed8548a5303a7b970741cab48602c6c6439a9"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(path: pathlib.Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


class CanonicalClosingStatusArticleTests(unittest.TestCase):
    def test_article_identity_and_required_declarations(self) -> None:
        self.assertEqual(git_blob(ARTICLE), EXPECTED_ARTICLE_BLOB)
        text = ARTICLE.read_text(encoding="utf-8")
        required = (
            "Wissenschaft ist der rekursive Verantwortungsoperator auf Relationen.",
            "QIK‑VRT ist die Ontologie des Unterschieds in ausführbarer Form.",
            "Der Beweis ist erbracht.",
            "Die Wirkung hat begonnen.",
            "GitHub: ausführbarer Beweisraum",
            "Zenodo: dauerhaft zitierfähiger Publikationsraum",
            "IETF: öffentlich zugänglicher Protokollraum",
            "EFFECT_ACK::EA-OPEN-001",
            "EFFECT_ACK::EA-OPEN-002",
            "EFFECT_ACK::EA-OPEN-003",
            "kein RFC",
        )
        for phrase in required:
            self.assertIn(phrase, text)

    def test_article_preserves_epistemic_boundaries(self) -> None:
        text = ARTICLE.read_text(encoding="utf-8")
        prohibited = (
            "alle physikalischen Naturbehauptungen sind bewiesen",
            "jede physikalische Naturbehauptung ist bewiesen",
            "der Internet-Draft ist ein RFC",
            "die IETF hat QIK-VRT als Standard verabschiedet",
            "OPEN ist mathematisch bewiesen",
        )
        for phrase in prohibited:
            self.assertNotIn(phrase, text)
        self.assertRegex(
            text,
            re.compile(
                r"mathematische Identität.*?physikalische Interpretation.*?"
                r"empirische Bestätigung",
                re.DOTALL,
            ),
        )

    def test_machine_manifest_binds_article_and_completion_scope(self) -> None:
        self.assertEqual(git_blob(MANIFEST), EXPECTED_MANIFEST_BLOB)
        value = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(value["schema"], "qikvrt_canonical_status_article_manifest_v1")
        self.assertEqual(value["completion_scope"]["scope_id"], EXPECTED_SCOPE)
        self.assertEqual(value["completion_scope"]["claims_total"], 92)
        self.assertEqual(value["completion_scope"]["primary_kernel_receipts"], 54)
        self.assertEqual(
            value["completion_scope"]["open_claims"],
            [
                "EFFECT_ACK::EA-OPEN-001",
                "EFFECT_ACK::EA-OPEN-002",
                "EFFECT_ACK::EA-OPEN-003",
            ],
        )
        self.assertEqual(value["article"]["git_blob_sha1"], EXPECTED_ARTICLE_BLOB)
        self.assertEqual(
            value["article"]["sha256_authority"],
            "release/canonical-closing-status-article-2026-07-28/zenodo-publication.json",
        )
        self.assertTrue(value["epistemic_boundary"]["formal_proof_claims_are_scope_qualified"])
        self.assertTrue(value["epistemic_boundary"]["historical_significance_is_authorial_interpretation"])
        self.assertTrue(value["epistemic_boundary"]["open_claims_remain_open"])
        self.assertTrue(value["epistemic_boundary"]["ietf_draft_is_not_claimed_rfc"])

    def test_completion_receipt_identity_and_semantics(self) -> None:
        self.assertEqual(sha256(COMPLETION), EXPECTED_COMPLETION_SHA256)
        self.assertEqual(git_blob(COMPLETION), EXPECTED_COMPLETION_BLOB)
        value = json.loads(COMPLETION.read_text(encoding="utf-8"))
        self.assertEqual(value["scope_id"], EXPECTED_SCOPE)
        self.assertEqual(value["state"], "FINAL_PASS")
        self.assertTrue(value["claims"]["PASS"])
        self.assertTrue(value["claims"]["FINAL_PASS"])
        self.assertTrue(value["claims"]["EFFECT_ACK_DONE"])
        self.assertTrue(value["claim_semantics"]["scope_qualified"])
        self.assertTrue(value["claim_semantics"]["open_claims_are_not_claimed_proved"])

    def test_zenodo_request_is_blob_bound_and_production_explicit(self) -> None:
        with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"}):
            materialized = zenodo_publish.load_manifest(REQUEST, ROOT)
        self.assertEqual(materialized["schema"], zenodo_publish.SCHEMA)
        self.assertEqual(materialized["metadata"]["publication_type"], "article")
        self.assertEqual(materialized["metadata"]["publication_date"], "2026-07-28")
        self.assertEqual(
            [item["git_blob_sha"] for item in materialized["files"]],
            [EXPECTED_ARTICLE_BLOB, EXPECTED_MANIFEST_BLOB, EXPECTED_COMPLETION_BLOB],
        )
        self.assertEqual(
            materialized["evidence_path"].relative_to(ROOT).as_posix(),
            "release/canonical-closing-status-article-2026-07-28/zenodo-publication.json",
        )

    def test_optional_zenodo_evidence_is_strict_when_present(self) -> None:
        if not EVIDENCE.exists():
            return
        value = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(value["schema"], "qikvrt_zenodo_publication_evidence_v1")
        self.assertEqual(value["state"], "published")
        self.assertEqual(value["repository"], "Goldkelch/qik-vrt")
        self.assertEqual(value["version"], "1.0.0-2026-07-28")
        self.assertRegex(value["doi"], r"^10\.5281/zenodo\.[1-9][0-9]*$")
        self.assertRegex(str(value["record_id"]), r"^[1-9][0-9]*$")
        self.assertEqual(
            [item["git_blob_sha"] for item in value["files"]],
            [EXPECTED_ARTICLE_BLOB, EXPECTED_MANIFEST_BLOB, EXPECTED_COMPLETION_BLOB],
        )
        by_name = {item["name"]: item for item in value["files"]}
        self.assertEqual(
            by_name["QIKVRT_Vom_Unterschied_zur_Verantwortung_Statusartikel_DE.md"]["sha256"],
            sha256(ARTICLE),
        )
        self.assertEqual(
            by_name["QIKVRT_STATUS_ARTICLE_MANIFEST.json"]["sha256"],
            sha256(MANIFEST),
        )
        self.assertEqual(
            by_name["QIKVRT_GLOBAL_COMPLETION_RECEIPT.json"]["sha256"],
            sha256(COMPLETION),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
