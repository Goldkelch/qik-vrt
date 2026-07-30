#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_content_disposition_batch_003_subject_2581811b342e505d as m


class Batch003FirstSubjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.receipt_bytes = m.PUBLIC_RECEIPT.read_bytes()
        cls.index_bytes = m.PUBLIC_INDEX.read_bytes()
        cls.receipt = m.parse_exact_json(m.PUBLIC_RECEIPT_NAME, cls.receipt_bytes)
        cls.index = m.parse_exact_json(m.PUBLIC_INDEX_NAME, cls.index_bytes)
        cls.claims = m.build_claims(cls.receipt, cls.index)

    def test_exact_public_bytes_and_claim_extraction(self) -> None:
        m.verify_exact_bytes(m.PUBLIC_RECEIPT_NAME, self.receipt_bytes)
        m.verify_exact_bytes(m.PUBLIC_INDEX_NAME, self.index_bytes)
        self.assertEqual(len(self.receipt_bytes), 5189)
        self.assertEqual(len(self.index_bytes), 1487)
        self.assertEqual(hashlib.md5(self.receipt_bytes, usedforsecurity=False).hexdigest(), "8792385e000502fae63fa1b4e48e4723")
        self.assertEqual(hashlib.md5(self.index_bytes, usedforsecurity=False).hexdigest(), "aa033aeacb744efd8cb89ac8fcd66733")
        self.assertEqual(len(self.claims), 39)
        self.assertFalse(any(row["terminal_disposition"] == "OPEN" for row in self.claims))

    def test_read_only_zenodo_record_reobservation(self) -> None:
        record = {
            "id": m.RECORD_ID,
            "doi": m.DOI,
            "files": [
                {
                    "key": m.PUBLIC_RECEIPT_NAME,
                    "size": 5189,
                    "checksum": "md5:8792385e000502fae63fa1b4e48e4723",
                    "links": {"content": "https://zenodo.org/api/files/receipt"},
                },
                {
                    "key": m.PUBLIC_INDEX_NAME,
                    "size": 1487,
                    "checksum": "md5:aa033aeacb744efd8cb89ac8fcd66733",
                    "links": {"content": "https://zenodo.org/api/files/index"},
                },
            ],
        }

        def request(url: str, **_: object) -> bytes:
            if url.endswith(f"/api/records/{m.RECORD_ID}"):
                return json.dumps(record).encode("utf-8")
            if url.endswith("/receipt"):
                return self.receipt_bytes
            if url.endswith("/index"):
                return self.index_bytes
            raise AssertionError(url)

        observed = m.fetch_public_record(request=request)
        self.assertEqual(observed[m.PUBLIC_RECEIPT_NAME], self.receipt_bytes)
        self.assertEqual(observed[m.PUBLIC_INDEX_NAME], self.index_bytes)

    def test_mutated_public_byte_blocks_before_parsing(self) -> None:
        bad = bytearray(self.index_bytes)
        bad[-2] ^= 1
        with self.assertRaises(m.SubjectDispositionError):
            m.parse_exact_json(m.PUBLIC_INDEX_NAME, bytes(bad))

    def test_live_index_cannot_substitute_for_public_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            receipt = root / m.PUBLIC_RECEIPT_NAME
            index = root / m.PUBLIC_INDEX_NAME
            live = root / "index.json"
            receipt.write_bytes(self.receipt_bytes)
            index.write_bytes(self.index_bytes)
            live.write_bytes(self.index_bytes)
            with (
                mock.patch.object(m, "PUBLIC_RECEIPT", receipt),
                mock.patch.object(m, "PUBLIC_INDEX", index),
                mock.patch.object(m, "LIVE_INDEX", live),
                self.assertRaises(m.SubjectDispositionError),
            ):
                m.load_committed_public_freeze()

    def test_total_traceability_and_assertion_coverage(self) -> None:
        traceability = m.build_traceability(self.claims)
        coverage = m.build_assertion_coverage(self.receipt, self.index, self.claims)
        self.assertEqual(traceability["claim_count"], 39)
        self.assertEqual(traceability["untraced_claim_count"], 0)
        self.assertEqual(len(traceability["entries"]), 39)
        self.assertEqual(coverage["unclassified_leaf_count"], 0)
        self.assertGreater(coverage["covered_leaf_count"], 100)

    def test_false_completion_values_remain_negative_boundaries(self) -> None:
        by_pointer = {tuple(row["source_pointers"]): row for row in self.claims}
        for key in ("pass", "final_pass", "effect_ack_done", "fully_kernel_verified_overall_completion"):
            row = by_pointer[(f"/claims/{key}",)]
            self.assertEqual(row["status"], "NOT_ESTABLISHED")
            self.assertEqual(row["terminal_disposition"], "NEGATIVE_BOUNDARY")
            self.assertIs(row["source_value"], False)

    def test_content_change_and_completion_boundary(self) -> None:
        decision = m.build_content_decision(self.claims)
        self.assertEqual(decision["decision"]["state"], "NO_CONTENT_CHANGE_REQUIRED")
        self.assertFalse(decision["decision"]["required"])
        self.assertFalse(decision["decision"]["zenodo_mutation_authorized"])
        with self.assertRaises(m.SubjectDispositionError):
            m.build_subject_receipt(self.claims, remote_verified=False)
        receipt = m.build_subject_receipt(self.claims, remote_verified=True)
        completion = receipt["completion_claims"]
        self.assertTrue(completion["subject_terminally_dispositioned"])
        self.assertTrue(completion["first_subject_claim_extraction_complete"])
        for key in ("all_content_claims_dispositioned", "batch_003_terminal", "pass", "final_pass", "effect_ack_done", "zenodo_mutation_authorized"):
            self.assertIs(completion[key], False)

    def test_adversarial_claim_set_drift_blocks(self) -> None:
        bad = copy.deepcopy(self.receipt)
        del bad["claims"]["pass"]
        with self.assertRaises(m.SubjectDispositionError):
            m.build_claims(bad, self.index)

    def test_public_record_file_set_drift_blocks(self) -> None:
        record = {"id": m.RECORD_ID, "doi": m.DOI, "files": []}

        def request(url: str, **_: object) -> bytes:
            return json.dumps(record).encode("utf-8")

        with self.assertRaises(m.SubjectDispositionError):
            m.fetch_public_record(request=request)


if __name__ == "__main__":
    unittest.main(verbosity=2)
