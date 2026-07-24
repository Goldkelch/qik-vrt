#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

import hashlib
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_publish as publish

ROOT = pathlib.Path(__file__).resolve().parents[1]


class GenericZenodoPublicationContractTests(unittest.TestCase):
    def _fixture(self, root: pathlib.Path) -> pathlib.Path:
        artifact = root / "docs" / "sample.md"
        artifact.parent.mkdir(parents=True)
        data = b"# Sample\n\nRepository-bound publication fixture.\n"
        artifact.write_bytes(data)
        blob = hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()
        manifest = {
            "schema": publish.SCHEMA,
            "state": "publish",
            "confirm": "PUBLISH_TO_PRODUCTION_ZENODO",
            "repository": "owner/repository",
            "metadata": {
                "title": "Sample publication",
                "upload_type": "publication",
                "publication_type": "technicalnote",
                "description": "Test fixture",
                "creators": [{"name": "Example, Author"}],
                "version": "1.0.0",
                "access_right": "open",
                "license": "cc-by-4.0",
                "prereserve_doi": True
            },
            "files": [{
                "path": "docs/sample.md",
                "name": "sample.md",
                "git_blob_sha": blob
            }],
            "evidence_path": "release/sample/zenodo-publication.json"
        }
        path = root / "release" / "sample" / "publish-request.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(manifest, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def test_manifest_materializes_transport_hashes_from_git_blob(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            path = self._fixture(root)
            with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repository"}):
                manifest = publish.load_manifest(path, root)
            entry = manifest["files"][0]
            data = (root / entry["path"]).read_bytes()
            self.assertEqual(entry["git_blob_sha"], publish._git_blob_sha(data))
            self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(entry["size"], len(data))

    def test_git_blob_mismatch_blocks_before_remote_effect(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            path = self._fixture(root)
            value = json.loads(path.read_text(encoding="utf-8"))
            value["files"][0]["git_blob_sha"] = "0" * 40
            path.write_text(json.dumps(value) + "\n", encoding="utf-8")
            with mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repository"}):
                with self.assertRaisesRegex(zenodo.ZenodoError, "Git blob mismatch"):
                    publish.load_manifest(path, root)

    def test_generic_implementation_contains_no_specific_identity(self) -> None:
        source = (ROOT / "tools/qikvrt_zenodo_publish.py").read_text(encoding="utf-8")
        self.assertNotIn("Charta einer maschinenprüfbaren Wissenschaft", source)
        self.assertNotIn("21498774", source)
        self.assertNotIn("10.5281/zenodo", source)

    def test_capability_is_generic_and_workflow_independent(self) -> None:
        capability = json.loads(
            (ROOT / "runtime/capabilities/ZENODO_PUBLICATION_CAPABILITY.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(capability["implementation"], "tools/qikvrt_zenodo_publish.py")
        self.assertIn("tools/qikvrt_zenodo_publish.py --manifest", capability["invocation"])
        self.assertTrue(capability["workflow_binding"].startswith("none"))
        self.assertFalse(capability["genericity"]["document_specific_constants"])
        self.assertFalse(capability["genericity"]["release_specific_constants"])
        self.assertFalse(capability["genericity"]["record_or_doi_constants"])
        self.assertFalse(capability["genericity"]["workflow_specific_constants"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
