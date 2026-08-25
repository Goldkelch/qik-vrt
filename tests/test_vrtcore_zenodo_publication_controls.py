from __future__ import annotations

import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_vrtcore_zenodo_publication_controls as controls
from tools import qikvrt_zenodo_actions as zenodo
from tools import qikvrt_zenodo_publish as publish


ROOT = pathlib.Path(__file__).resolve().parents[1]


class VRTCoreZenodoPublicationControlTests(unittest.TestCase):
    def load_authority_manifest(self, path: pathlib.Path) -> dict[str, object]:
        with mock.patch.dict(
            os.environ,
            {"GITHUB_REPOSITORY": "ingolf-lohmann/qik-vrt"},
        ):
            with self.assertRaisesRegex(
                zenodo.ZenodoError,
                "manifest repository differs from the executing repository",
            ):
                publish.load_manifest(path, ROOT)
        with mock.patch.dict(
            os.environ,
            {"GITHUB_REPOSITORY": publish.PRODUCTION_REPOSITORY},
        ):
            return publish.load_manifest(path, ROOT)

    def test_three_exact_unique_owner_decisions(self) -> None:
        self.assertEqual(set(controls.PROFILES), {"h3", "h5", "h6"})
        ids = {str(value["authorization_id"]) for value in controls.PROFILES.values()}
        self.assertEqual(len(ids), 3)
        for profile in controls.PROFILES.values():
            statement = controls.exact_statement(profile)
            self.assertTrue(statement.startswith("AUTHORIZE_EXACT_UPLOAD "))
            self.assertIn("authorization_id=" + str(profile["authorization_id"]), statement)
            self.assertIn("publication_id=" + str(profile["publication_id"]), statement)

    def test_controls_pass_active_v2_manifest_gate(self) -> None:
        for profile in controls.PROFILES.values():
            control = ROOT / str(profile["control"])
            manifest = self.load_authority_manifest(control / "publish-request.json")
            self.assertEqual(manifest["source_head"], controls.SOURCE_HEAD)
            self.assertEqual(len(manifest["files"]), profile["upload_count"])
            self.assertEqual(
                manifest["owner_authorization"]["authorization_id"],
                profile["authorization_id"],
            )
            self.assertFalse((control / "zenodo-publication.json").exists())

    def test_single_use_nonces_are_distinct_without_exposing_values(self) -> None:
        digests = set()
        for profile in controls.PROFILES.values():
            control = ROOT / str(profile["control"])
            value = json.loads(
                (control / "OWNER_ZENODO_AUTHORIZATION.json").read_text(encoding="utf-8")
            )
            nonce = value["nonce"]
            self.assertEqual(len(nonce), 64)
            self.assertNotEqual(nonce, "0" * 64)
            normalized = self.load_authority_manifest(control / "publish-request.json")
            digests.add(normalized["owner_authorization"]["nonce_digest"]["value"])
        self.assertEqual(len(digests), 3)

    def test_missing_control_refuses_replacement_single_use_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = pathlib.Path(directory) / "OWNER_ZENODO_AUTHORIZATION.json"
            with self.assertRaisesRegex(
                SystemExit,
                "replacement nonce generation is forbidden",
            ):
                controls.read_preserved_event(missing)


if __name__ == "__main__":
    unittest.main()
