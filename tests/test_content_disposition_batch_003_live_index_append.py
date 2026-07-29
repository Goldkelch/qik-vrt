#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
P = ROOT / "tools/qikvrt_content_disposition_batch_003_dispatch.py"
S = importlib.util.spec_from_file_location("batch003_dispatch_append", P)
m = importlib.util.module_from_spec(S)
assert S.loader is not None
S.loader.exec_module(m)


class T(unittest.TestCase):
    def setUp(self):
        self.index = json.loads(m.LIVE_INDEX.read_text(encoding="utf-8"))

    def test_current_appended_index_preserves_dispatch_projection(self):
        m.validate_live_index(self.index)
        m.validate_source_blobs()
        result = m.verify()
        self.assertEqual(
            result["state"],
            "BATCH_003_DISPATCH_STATUS_PROJECTION_CURRENT",
        )
        self.assertNotIn(m.LIVE_INDEX, m.EXPECTED_SOURCE_BLOBS)

    def test_post_acceptance_receipt_is_exactly_indexed(self):
        row = next(
            item
            for item in self.index["equality_receipts"]
            if item["receipt_id"]
            == "authority-mirror-equality-2026-07-30-post-acceptance-status-pr215-pr110"
        )
        self.assertEqual(
            row["file_sha256"],
            "59340767c0a8b3a6774e2110f32f6386681b340d91fc2a9d7da4d4e92ffaef80",
        )
        self.assertEqual(
            row["git_blob_sha1"],
            "89589ab48c2fe52d13f76f9588c702fe8bced2d3",
        )
        self.assertEqual(
            row["source_receipt_payload_sha256"],
            "359cc14f64ac0005a8b7ff48c00b0243aea4b14095df904640c6a3ceb8db99f9",
        )
        self.assertEqual(
            row["authority"]["main"],
            "191bee0e50cc0cbb1f71423289224c1de8cba7f2",
        )
        self.assertEqual(
            row["mirror"]["main"],
            "3c8a68165eb3fcb70a629b73732de5da31463e07",
        )

    def test_later_append_is_allowed(self):
        later = copy.deepcopy(self.index)
        row = copy.deepcopy(later["equality_receipts"][-1])
        row["receipt_id"] = "future-reciprocal-receipt"
        row["path"] = "evidence/receipts/future-reciprocal-receipt.json"
        later["equality_receipts"].append(row)
        m.validate_live_index(later)

    def test_duplicate_receipt_identity_blocks(self):
        bad = copy.deepcopy(self.index)
        bad["equality_receipts"].append(copy.deepcopy(bad["equality_receipts"][-1]))
        with self.assertRaises(m.E):
            m.validate_live_index(bad)

    def test_removing_pre_dispatch_receipt_blocks(self):
        bad = copy.deepcopy(self.index)
        bad["equality_receipts"] = [
            row
            for row in bad["equality_receipts"]
            if row["receipt_id"]
            != "authority-mirror-equality-2026-07-27-pr106-pr56"
        ]
        with self.assertRaises(m.E):
            m.validate_live_index(bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
