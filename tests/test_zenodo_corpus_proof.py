#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

from tools import qikvrt_zenodo_corpus_proof as corpus
from tools import qikvrt_zenodo_corpus_proof_v2 as corpus_v2

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ZenodoCorpusProofTests(unittest.TestCase):
    def test_creator_attribution_accepts_both_name_orders(self) -> None:
        self.assertTrue(corpus.attributed_to_ingolf({"creators": [{"name": "Lohmann, Ingolf"}]}))
        self.assertTrue(corpus.attributed_to_ingolf({"creators": [{"name": "Ingolf Lohmann"}]}))
        self.assertFalse(corpus.attributed_to_ingolf({"creators": [{"name": "Other, Author"}]}))

    def test_public_file_shapes_are_normalized_without_network(self) -> None:
        listed = corpus_v2.public_files(
            {
                "files": [
                    {
                        "key": "paper.pdf",
                        "size": 12,
                        "checksum": "md5:" + "0" * 32,
                        "links": {"content": "https://zenodo.org/api/records/123/files/paper.pdf/content"},
                    }
                ]
            },
            123,
        )
        self.assertEqual(listed[0]["name"], "paper.pdf")
        mapped = corpus_v2.public_files(
            {
                "files": {
                    "entries": {
                        "evidence.json": {
                            "size": 34,
                            "checksum": "md5:" + "1" * 32,
                            "links": {"content": "https://zenodo.org/api/records/123/files/evidence.json/content"},
                        }
                    }
                }
            },
            123,
        )
        self.assertEqual(mapped[0]["name"], "evidence.json")

    def test_safe_nested_public_file_key_is_preserved_exactly(self) -> None:
        files = corpus_v2.public_files(
            {
                "files": [
                    {
                        "key": "source/article/paper.pdf",
                        "size": 12,
                        "checksum": "md5:" + "0" * 32,
                    }
                ]
            },
            21267021,
        )
        self.assertEqual(files[0]["name"], "source/article/paper.pdf")
        self.assertEqual(
            files[0]["download_url"],
            "https://zenodo.org/api/records/21267021/files/source%2Farticle%2Fpaper.pdf/content",
        )

    def test_unsafe_public_file_keys_are_rejected(self) -> None:
        for key in (
            "../paper.pdf",
            "/paper.pdf",
            "nested\\paper.pdf",
            "nested/./paper.pdf",
            "nested/../paper.pdf",
            "paper\x00.pdf",
            "paper\n.pdf",
        ):
            with self.subTest(key=repr(key)):
                with self.assertRaises(corpus_v2.PublicKeyError):
                    corpus_v2.safe_public_key(key, 123)

    def test_public_record_state_is_explicitly_verified(self) -> None:
        self.assertTrue(corpus_v2.public_record_is_published({"is_published": True}))
        self.assertTrue(corpus_v2.public_record_is_published({"status": "published"}))
        self.assertTrue(corpus_v2.public_record_is_published({"state": "done"}))
        self.assertFalse(corpus_v2.public_record_is_published({"status": "draft"}))

    def test_repository_reference_classification_is_truth_bounded(self) -> None:
        self.assertEqual(corpus.classify_repository_ref("proof/CLAIM_MATRIX.json"), "CLAIM_DISPOSITION")
        self.assertEqual(corpus.classify_repository_ref("proof/KERNEL_RECEIPT.json"), "FORMAL_PROOF")
        self.assertEqual(corpus.classify_repository_ref("release/zenodo-publication.json"), "EVIDENCE")
        self.assertEqual(corpus.classify_repository_ref("release/publish-request.json"), "OTHER")
        self.assertEqual(corpus.classify_repository_ref("docs/ARTICLE_DE.md"), "SOURCE_OR_CONTENT")

    def test_report_never_claims_all_natural_language_is_formally_proved(self) -> None:
        index = {
            "observed_at": "2026-07-28T09:30:00Z",
            "record_count": 1,
            "public_byte_verified_count": 1,
            "records": [
                {
                    "record_id": 123,
                    "doi": "10.5281/zenodo.123",
                    "title": "Fixture",
                    "claim_coverage": "RETROSPECTIVE_RECORD_LEVEL_ENVELOPE_ONLY",
                    "required_action": "CONTENT_CLAIM_EXTRACTION_REVIEW_AND_POSSIBLE_VERSIONED_CORRECTION",
                }
            ],
        }
        report = corpus.build_report(index)
        self.assertIn("keine natürliche Sprache pauschal", report)
        self.assertIn("NO_MACHINE_PROOF_NO_ZENODO_UPLOAD", report)
        self.assertNotIn("alle natürlichen Aussagen sind formal bewiesen", report.lower())

    def test_minimum_historical_guard_is_unique_and_contains_last_verified_article(self) -> None:
        path = ROOT / "release/zenodo-corpus-proof-2026-07-28/KNOWN_PUBLISHED_RECORDS_MINIMUM.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        record_ids = value["record_ids"]
        self.assertEqual(record_ids, sorted(record_ids))
        self.assertEqual(len(record_ids), len(set(record_ids)))
        self.assertIn(20712301, record_ids)
        self.assertIn(21482023, record_ids)
        self.assertIn(21640173, record_ids)

    def test_source_contains_no_embedded_token_or_account_secret(self) -> None:
        source = (ROOT / "tools/qikvrt_zenodo_corpus_proof.py").read_text(encoding="utf-8")
        hardened = (ROOT / "tools/qikvrt_zenodo_corpus_proof_v2.py").read_text(encoding="utf-8")
        self.assertNotRegex(source + hardened, r"(?i)access_token=[A-Za-z0-9_-]{20,}")
        self.assertNotIn("Bearer ey", source + hardened)

    def test_write_json_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = pathlib.Path(temporary) / "value.json"
            corpus.write_json(path, {"z": 1, "a": 2})
            first = path.read_bytes()
            corpus.write_json(path, {"a": 2, "z": 1})
            self.assertEqual(first, path.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
