#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import pathlib
import unittest

from tools import qikvrt_zenodo_corpus_proof_v2 as corpus_v2

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "release/zenodo-corpus-proof-2026-07-28/ZENODO_CORPUS_INVENTORY_FAILURE_RECEIPT.json"
REPORT = ROOT / "release/zenodo-corpus-proof-2026-07-28/ZENODO_CORPUS_INVENTORY_DIAGNOSTIC_DE.md"


class ZenodoCorpusInventoryFailureReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = json.loads(RECEIPT.read_text(encoding="utf-8"))

    def test_exact_failed_run_and_reproduced_record_are_bound(self) -> None:
        self.assertEqual(
            self.value["schema"],
            "qikvrt_zenodo_corpus_inventory_failure_receipt_v1",
        )
        self.assertEqual(self.value["state"], "DIAGNOSED_AND_REPAIR_PROMOTED")
        source = self.value["source_failure"]
        self.assertEqual(source["authority_commit"], "5fd40bcc12304d92ae4066df3c06cf9acfb7eb98")
        self.assertEqual(source["run_id"], 30347678298)
        self.assertEqual(source["job_id"], 90237623969)
        self.assertFalse(source["zenodo_mutation_executed"])
        reproduction = self.value["reproduction"]
        self.assertEqual(reproduction["record_id"], 21267021)
        self.assertEqual(
            reproduction["observed_failure_line"],
            "BLOCK: record 21267021 contains an unsafe public file name",
        )

    def test_failure_class_is_precise_and_truth_bounded(self) -> None:
        classification = self.value["classification"]
        self.assertEqual(classification["parent_failure_class"], "PUBLIC_FILESET_MISMATCH")
        self.assertEqual(
            classification["primary_failure_class"],
            "SAFE_RELATIVE_ZENODO_PUBLIC_FILE_KEY_REJECTED",
        )
        self.assertEqual(classification["failure_mode"], "FALSE_POSITIVE_PUBLIC_KEY_VALIDATION")
        self.assertEqual(classification["confidence"], "HIGH")
        self.assertNotIn("CONTENT_PROOF_FAILURE", classification["primary_failure_class"])

    def test_promoted_repair_and_exact_head_gates_are_bound(self) -> None:
        repair = self.value["promoted_repair"]
        self.assertEqual(repair["candidate_commit"], "1b546eb022e416c89193f94192c86371b78f8010")
        self.assertEqual(repair["authority_commit"], "65a173cbc666b5555e6251f97cba32b05ac983d9")
        self.assertEqual(repair["git_blob_sha"], "1106ebde33b45e0285f9ee312571681985c7434a")
        self.assertEqual(
            repair["sha256"],
            "3cf09d2e14336756a80a192a6546bdd9289bfe78b3edb9d44561d843f6c86f07",
        )
        conclusions = {item["name"]: item["conclusion"] for item in self.value["exact_head_gates"]}
        self.assertEqual(conclusions["QIKVRT CI"], "success")
        self.assertEqual(conclusions["QIKVRT repository evidence materialization"], "success")
        self.assertEqual(conclusions["QIKVRT Collective Proposal Review"], "success")
        self.assertEqual(conclusions["QIK-VRT global claim completion"], "success")
        self.assertEqual(conclusions["QIKVRT live status watch"], "success")
        self.assertEqual(conclusions["QIKVRT PR18 integrity repair"], "skipped")

    def test_safe_relative_key_is_accepted_and_unsafe_keys_remain_blocked(self) -> None:
        self.assertEqual(
            corpus_v2.safe_public_key("source/article/paper.pdf", 21267021),
            "source/article/paper.pdf",
        )
        for key in ("../paper.pdf", "/paper.pdf", "nested\\paper.pdf", "nested/../paper.pdf"):
            with self.subTest(key=key):
                with self.assertRaises(corpus_v2.PublicKeyError):
                    corpus_v2.safe_public_key(key, 21267021)

    def test_no_false_completion_claim_is_present(self) -> None:
        completion = self.value["completion_claims"]
        self.assertTrue(completion["diagnostic_complete"])
        self.assertTrue(completion["repair_complete"])
        self.assertFalse(completion["corpus_inventory_complete"])
        self.assertFalse(completion["corpus_proof_publication_complete"])
        self.assertFalse(completion["pass"])
        self.assertFalse(completion["final_pass"])
        self.assertFalse(completion["effect_ack_done"])
        effect = self.value["effect"]
        self.assertEqual(
            effect["next_deterministic_effect"],
            "RETRY_AUTHENTICATED_READ_ONLY_CORPUS_INVENTORY_USING_PROMOTED_SAFE_KEY_PARSER",
        )

    def test_report_and_receipt_contain_no_embedded_secret(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8") + REPORT.read_text(encoding="utf-8")
        self.assertNotRegex(text, r"(?i)access_token=[A-Za-z0-9_-]{20,}")
        self.assertNotIn("Authorization: Bearer", text)
        self.assertIn("SAFE_RELATIVE_ZENODO_PUBLIC_FILE_KEY_REJECTED", text)
        self.assertIn("Kein `PASS`. Kein `FINAL_PASS`. Kein `EFFECT_ACK_DONE`.", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
