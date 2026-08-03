from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import qikvrt_retrospective_proof_corpus_zenodo_candidate as candidate
from tools import qikvrt_retrospective_proof_corpus_zenodo_publication_controls as controls
from tools import qikvrt_zenodo_publish as publish


ROOT = pathlib.Path(__file__).resolve().parents[1]


def event_value(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema": controls.EVENT_SCHEMA,
        "authorization_id": controls.AUTHORIZATION_ID,
        "publication_id": controls.PUBLICATION_ID,
        "decision": "AUTHORIZE_EXACT_UPLOAD",
        "exact_statement": controls.exact_statement(),
        "return_sha256": controls.RETURN_SHA256,
        "metadata_sha256": controls.METADATA_SHA256,
        "machine_proof_sha256": controls.MACHINE_PROOF_SHA256,
        "authorized_at": "2026-08-03T10:00:00Z",
        "repository_recorded_conversation_assertion": True,
        "independent_external_proof": False,
        "nonce": "1234567890abcdef" * 4,
    }
    value.update(changes)
    return value


def event_text(**changes: object) -> str:
    return json.dumps(event_value(**changes), ensure_ascii=False, separators=(",", ":"))


class RetrospectiveProofCorpusZenodoPublicationControlTests(unittest.TestCase):
    def temporary_control(self) -> tuple[tempfile.TemporaryDirectory[str], pathlib.PurePosixPath]:
        temporary = tempfile.TemporaryDirectory(
            prefix="corpus-controls-test-",
            dir=ROOT / "release",
        )
        relative = pathlib.Path(temporary.name).relative_to(ROOT).as_posix()
        return temporary, pathlib.PurePosixPath(relative)

    def test_exact_frozen_candidate_and_authorization_statement(self) -> None:
        self.assertEqual(
            controls.SOURCE_HEAD,
            "035642a660583113ec739d90577193ccb5a08889",
        )
        self.assertEqual(
            controls.RETURN_SHA256,
            "46c57378a6708df379768f943a99905cde3da4c4a11220f9a177e9bc968d3968",
        )
        self.assertEqual(
            controls.METADATA_SHA256,
            "4bb6abea1f226f3950337ee3585abd1ba5d52f731a93f25fabfc2722f5b170de",
        )
        self.assertEqual(
            controls.MACHINE_PROOF_SHA256,
            "cfe9ae60e3da81a6427c96399bd70299c74f12999dc4371809b879f5a5630be1",
        )
        self.assertEqual(
            controls.UPLOAD_CONTRACT_SHA256,
            "3965b4167094ff47de60fc32023ac74ea1598148ab381885be8da3db4c427609",
        )
        self.assertEqual(
            controls.exact_statement(),
            "AUTHORIZE_EXACT_UPLOAD "
            "authorization_id=qikvrt-retrospective-proof-corpus-v3-rebuild-20260803t094446z "
            "publication_id=qikvrt-retrospective-proof-corpus-2026-07-28-v3 "
            "return_sha256=46c57378a6708df379768f943a99905cde3da4c4a11220f9a177e9bc968d3968 "
            "metadata_sha256=4bb6abea1f226f3950337ee3585abd1ba5d52f731a93f25fabfc2722f5b170de "
            "machine_proof_sha256=cfe9ae60e3da81a6427c96399bd70299c74f12999dc4371809b879f5a5630be1",
        )

    def test_absent_event_blocks_without_writing_controls(self) -> None:
        temporary, control_rel = self.temporary_control()
        with temporary:
            with self.assertRaisesRegex(
                controls.CorpusPublicationControlError,
                "explicit strict JSON OWNER_AUTHORIZATION_EVENT is required",
            ):
                controls.materialize(
                    check=False,
                    event_raw=None,
                    control_rel=control_rel,
                )
            self.assertFalse((ROOT / control_rel / controls.AUTHORIZATION_BASENAME).exists())
            self.assertFalse((ROOT / control_rel / controls.MANIFEST_BASENAME).exists())

    def test_cli_absent_event_is_fail_closed(self) -> None:
        control = ROOT / controls.CONTROL_REL
        before = (
            sorted(
                (path.name, path.read_bytes())
                for path in control.iterdir()
                if path.is_file() and not path.is_symlink()
            )
            if control.is_dir() and not control.is_symlink()
            else None
        )
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(SystemExit, "BLOCK explicit strict JSON"):
                controls.main([])
        after = (
            sorted(
                (path.name, path.read_bytes())
                for path in control.iterdir()
                if path.is_file() and not path.is_symlink()
            )
            if control.is_dir() and not control.is_symlink()
            else None
        )
        self.assertEqual(after, before)
        isolated_environment = {
            key: value
            for key, value in os.environ.items()
            if key != controls.OWNER_AUTHORIZATION_EVENT_ENV
        }
        isolated = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-B",
                str(
                    ROOT
                    / "tools/qikvrt_retrospective_proof_corpus_zenodo_publication_controls.py"
                ),
                "--check",
            ],
            cwd=ROOT,
            env=isolated_environment,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(isolated.returncode, 0)
        self.assertIn("BLOCK explicit strict JSON", isolated.stderr)
        self.assertNotIn("Traceback", isolated.stderr)

    def test_old_exact_authorization_is_not_reused(self) -> None:
        old_authorization_id = "qikvrt-retrospective-proof-corpus-v3-20260802t223957z"
        old_return = "6a8a3fe211d086f34ae306d084a23304410f6ba9876cf1f0feb1be54fbd0fcad"
        old_metadata = "0d55ce8ffd5023f5666ad6a4ee656766613e879f9f726834692198c5b304b8c5"
        old_machine = "cbeb6d818e38e91369b8730a0621b48059fdf60fe8d2fccfef0d79b79f20542c"
        old_statement = publish._canonical_authorization_statement(
            old_authorization_id,
            controls.PUBLICATION_ID,
            old_return,
            old_metadata,
            old_machine,
        )
        temporary, control_rel = self.temporary_control()
        with temporary:
            with self.assertRaisesRegex(
                controls.CorpusPublicationControlError,
                "authorization_id differs from the frozen candidate",
            ):
                controls.materialize(
                    check=False,
                    event_raw=event_text(
                        authorization_id=old_authorization_id,
                        exact_statement=old_statement,
                        return_sha256=old_return,
                        metadata_sha256=old_metadata,
                        machine_proof_sha256=old_machine,
                    ),
                    control_rel=control_rel,
                )
            self.assertEqual(list((ROOT / control_rel).iterdir()), [])

    def test_event_json_is_strict_exact_and_repository_recorded(self) -> None:
        duplicate = event_text()[:-1] + ',"nonce":"' + ("a" * 64) + '"}'
        invalid_events = (
            duplicate,
            event_text(extra="forbidden"),
            event_text(repository_recorded_conversation_assertion=False),
            event_text(independent_external_proof=True),
            event_text(authorized_at="2026-08-03T09:44:45Z"),
            event_text(nonce="0" * 64),
            event_text(nonce="A" * 64),
            event_text()[:-1] + ',"extra":NaN}',
        )
        for raw in invalid_events:
            with self.subTest(raw=raw[-80:]):
                with self.assertRaises(controls.CorpusPublicationControlError):
                    controls.parse_authorization_event(raw)

    def test_valid_event_materializes_deterministic_generic_v2_controls(self) -> None:
        temporary, control_rel = self.temporary_control()
        with temporary:
            report = controls.materialize(
                check=False,
                event_raw=event_text(),
                control_rel=control_rel,
            )
            authorization_path = ROOT / report["authorization_path"]
            manifest_path = ROOT / report["manifest_path"]
            first_authorization = authorization_path.read_bytes()
            first_manifest = manifest_path.read_bytes()

            checked = controls.materialize(
                check=True,
                event_raw=event_text(),
                control_rel=control_rel,
            )
            self.assertEqual(checked, report)
            self.assertEqual(authorization_path.read_bytes(), first_authorization)
            self.assertEqual(manifest_path.read_bytes(), first_manifest)

            normalized = publish.load_manifest(manifest_path, ROOT)
            self.assertEqual(normalized["schema"], publish.SCHEMA_V2)
            self.assertEqual(normalized["source_head"], controls.SOURCE_HEAD)
            self.assertEqual(len(normalized["files"]), controls.EXPECTED_UPLOADS)
            self.assertEqual(
                normalized["owner_authorization"]["authorization_id"],
                controls.AUTHORIZATION_ID,
            )
            self.assertFalse((ROOT / control_rel / controls.EVIDENCE_BASENAME).exists())

    def test_manifest_uses_all_65_ordered_matrix_mappings_without_basename_inference(self) -> None:
        event = controls.parse_authorization_event(event_text())
        temporary, control_rel = self.temporary_control()
        with temporary:
            _auth_path, _manifest_path, _auth_raw, manifest_raw, files = controls.build_controls(
                event,
                control_rel,
            )
            manifest = json.loads(manifest_raw.decode("utf-8"))
            matrix = candidate.load_json(candidate.CLAIM_MATRIX_PATH, "claim matrix")
            entries = matrix["upload_contract"]["ordered_entries"]
            expected = [
                {"path": item["path"], "name": item["name"]}
                for item in entries
            ]
            observed = [
                {"path": item["path"], "name": item["name"]}
                for item in manifest["files"]
            ]
            self.assertEqual(observed, expected)
            self.assertEqual(
                candidate.canonical_json_sha256(entries),
                controls.UPLOAD_CONTRACT_SHA256,
            )
            self.assertEqual(len(files), 65)
            self.assertEqual(len({item["path"] for item in files}), 65)
            self.assertEqual(len({item["name"] for item in files}), 65)
            self.assertEqual(
                files[-4:],
                [
                    {
                        "path": "release/zenodo-corpus-proof-2026-07-28/CORPUS_CLAIM_MATRIX.json",
                        "name": "CORPUS_CLAIM_MATRIX.json",
                        "git_blob_sha": files[-4]["git_blob_sha"],
                    },
                    {
                        "path": "release/zenodo-corpus-proof-2026-07-28/PREPUBLICATION_RETURN_RECEIPT.json",
                        "name": "PREPUBLICATION_RETURN_RECEIPT.json",
                        "git_blob_sha": files[-3]["git_blob_sha"],
                    },
                    {
                        "path": "release/zenodo-corpus-proof-2026-07-28/ZENODO_METADATA.json",
                        "name": "ZENODO_METADATA.json",
                        "git_blob_sha": files[-2]["git_blob_sha"],
                    },
                    {
                        "path": "release/zenodo-corpus-proof-2026-07-28/MACHINE_PROOF_BUNDLE.json",
                        "name": "MACHINE_PROOF_BUNDLE.json",
                        "git_blob_sha": files[-1]["git_blob_sha"],
                    },
                ],
            )

            upload_paths = {item["path"] for item in files}
            self.assertNotIn(
                (control_rel / controls.AUTHORIZATION_BASENAME).as_posix(),
                upload_paths,
            )
            self.assertNotIn(
                (control_rel / controls.MANIFEST_BASENAME).as_posix(),
                upload_paths,
            )

    def test_changed_existing_control_is_never_overwritten(self) -> None:
        event = controls.parse_authorization_event(event_text())
        temporary, control_rel = self.temporary_control()
        with temporary:
            authorization_path, _manifest_path, auth_raw, manifest_raw, _files = (
                controls.build_controls(event, control_rel)
            )
            authorization_path.write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(
                controls.CorpusPublicationControlError,
                "refusing to overwrite changed publication control",
            ):
                controls.emit_controls(
                    control_rel,
                    auth_raw,
                    manifest_raw,
                    check=False,
                )
            self.assertEqual(authorization_path.read_text(encoding="utf-8"), "changed\n")


if __name__ == "__main__":
    unittest.main()
