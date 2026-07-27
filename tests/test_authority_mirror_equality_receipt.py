#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import hashlib
import json
import os
import pathlib
import unittest
from unittest import mock

from tools import qikvrt_integrity as integrity
from tools import qikvrt_zenodo_publish as zenodo_publish

ROOT = pathlib.Path(__file__).resolve().parents[1]
RECEIPT_PATH = ROOT / "evidence" / "receipts" / "authority-mirror-equality-2026-07-27-pr106-pr56.json"
INDEX_PATH = ROOT / "evidence" / "receipts" / "index.json"
PUBLISH_REQUEST_PATH = (
    ROOT / "release" / "authority-mirror-equality-2026-07-27" / "publish-request.json"
)

EXPECTED_RECEIPT_SHA256 = "2372fae39499febbb005d771cb2ce62bde7967a79cdd5e3b159a3591fc80ac98"
EXPECTED_RECEIPT_GIT_BLOB = "83c80c53d330eb929defb3739ecc9184e6754639"
EXPECTED_INDEX_SHA256 = "47c5d7107098c0527c80aa0d65deeeb6a15ce1496588fda3fda087d4d18d5ff4"
EXPECTED_INDEX_GIT_BLOB = "24ed0bf0736b444d51e6773c66b57301cb6b9727"
EXPECTED_SOURCE_RECEIPT_PAYLOAD_SHA256 = (
    "ef3550482c22c2858669b086137922a2220b6e65863f3f4d2d8239392afd7fb1"
)


def git_blob_sha(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()  # noqa: S324 - Git object identity


class AuthorityMirrorEqualityReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.receipt_raw = RECEIPT_PATH.read_bytes()
        self.receipt = json.loads(self.receipt_raw.decode("utf-8"))
        self.index_raw = INDEX_PATH.read_bytes()
        self.index = json.loads(self.index_raw.decode("utf-8"))
        self.publish_request = json.loads(PUBLISH_REQUEST_PATH.read_text(encoding="utf-8"))

    def test_receipt_is_content_addressed_and_scope_bound(self) -> None:
        self.assertEqual(hashlib.sha256(self.receipt_raw).hexdigest(), EXPECTED_RECEIPT_SHA256)
        self.assertEqual(git_blob_sha(self.receipt_raw), EXPECTED_RECEIPT_GIT_BLOB)
        self.assertEqual(
            self.receipt["receipt_id"],
            "authority-mirror-equality-2026-07-27-pr106-pr56",
        )
        self.assertEqual(
            self.receipt["scope"],
            "promotion_2026-07-27_pr106_pr56",
        )
        self.assertNotEqual(self.receipt["scope"], "promotion_2026-07-25")
        self.assertEqual(
            self.receipt["reciprocal_github_receipts"]["receipt_payload_sha256"],
            EXPECTED_SOURCE_RECEIPT_PAYLOAD_SHA256,
        )

    def test_receipt_binds_exact_authority_mirror_and_non_claims(self) -> None:
        self.assertEqual(
            self.receipt["authority"]["main"],
            "5c0a60dac2dab9d00449da1fce6943dabee36b83",
        )
        self.assertEqual(
            self.receipt["authority"]["exact_green_head"],
            "bd76ce60a053f6ec9fd103230728741c1621f3cb",
        )
        self.assertEqual(
            self.receipt["mirror"]["main"],
            "50b2471a4f670a40d54cd9a9eace1d60a7f194f9",
        )
        self.assertEqual(
            self.receipt["mirror"]["exact_green_head"],
            "8b951ef0ab3293e5c134a0f0ef2c39ad2cc288c0",
        )
        self.assertEqual(
            self.receipt["equality"]["repository_content_tree_sha256"],
            "18adedec4c76ce38b93c0d8ebd5e14df09a422ee14a4d9bb159f183315f1a918",
        )
        self.assertEqual(
            self.receipt["equality"]["repository_manifest_sha256"],
            "141e436a413f7b766983f3a5939f81dfe7227db7f9e98dfd9aa37aa0edd9b7d5",
        )
        self.assertTrue(self.receipt["claims"]["authority_mirror_equality_verified"])
        self.assertTrue(self.receipt["claims"]["scoped_promotion_chain_complete"])
        for key in (
            "pass",
            "final_pass",
            "effect_ack_done",
            "fully_kernel_verified_overall_completion",
        ):
            self.assertFalse(self.receipt["claims"][key])

    def test_index_is_appendable_and_exactly_binds_receipt(self) -> None:
        self.assertEqual(hashlib.sha256(self.index_raw).hexdigest(), EXPECTED_INDEX_SHA256)
        self.assertEqual(git_blob_sha(self.index_raw), EXPECTED_INDEX_GIT_BLOB)
        self.assertEqual(self.index["schema"], "qikvrt_equality_receipt_index_v1")
        self.assertEqual(len(self.index["equality_receipts"]), 1)
        entry = self.index["equality_receipts"][0]
        self.assertEqual(entry["path"], RECEIPT_PATH.relative_to(ROOT).as_posix())
        self.assertEqual(entry["file_sha256"], EXPECTED_RECEIPT_SHA256)
        self.assertEqual(entry["git_blob_sha1"], EXPECTED_RECEIPT_GIT_BLOB)
        self.assertEqual(
            entry["source_receipt_payload_sha256"],
            EXPECTED_SOURCE_RECEIPT_PAYLOAD_SHA256,
        )
        self.assertFalse(
            self.index["manifest_integration"]["direct_generated_manifest_mutation"]
        )
        classification, immutable, reason = integrity.classification(
            INDEX_PATH.relative_to(ROOT).as_posix()
        )
        self.assertEqual(classification, "historical_evidence")
        self.assertTrue(immutable)
        self.assertEqual(reason, "")

    def test_generic_zenodo_request_is_valid_and_git_blob_bound(self) -> None:
        self.assertEqual(
            self.publish_request["schema"],
            zenodo_publish.SCHEMA,
        )
        self.assertEqual(
            self.publish_request["evidence_path"],
            "release/authority-mirror-equality-2026-07-27/zenodo-publication.json",
        )
        self.assertEqual(
            [entry["git_blob_sha"] for entry in self.publish_request["files"]],
            [EXPECTED_RECEIPT_GIT_BLOB, EXPECTED_INDEX_GIT_BLOB],
        )
        with mock.patch.dict(
            os.environ,
            {"GITHUB_REPOSITORY": "Goldkelch/qik-vrt"},
            clear=False,
        ):
            materialized = zenodo_publish.load_manifest(PUBLISH_REQUEST_PATH, ROOT)
        self.assertEqual(
            [entry["sha256"] for entry in materialized["files"]],
            [EXPECTED_RECEIPT_SHA256, EXPECTED_INDEX_SHA256],
        )
        self.assertEqual(
            materialized["metadata"]["version"],
            "1.0.0-2026-07-27",
        )

    def test_publication_request_has_no_prebound_remote_record_identity(self) -> None:
        serialized = json.dumps(self.publish_request, sort_keys=True)
        self.assertNotIn('"record_id"', serialized)
        self.assertNotIn('"doi"', serialized)
        self.assertNotIn('"conceptdoi"', serialized)
        self.assertTrue(self.publish_request["metadata"]["prereserve_doi"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
