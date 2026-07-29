#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from tools import qikvrt_integrity as integrity


class IntegrityGenerationTests(unittest.TestCase):
    CAPSULE = (
        REPOSITORY_ROOT
        / "release/zenodo-corpus-proof-2026-07-28/canonical-union"
        / "content-disposition-batch-002/status-projection-source-capsule"
        / "SOURCE_CAPSULE.json"
    )

    def _repository(self, root: pathlib.Path) -> None:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        (root / ".gitignore").write_text(
            "__pycache__/\n*.pyc\nlogs/\nunit_state/\ne2e_state/\n.qikvrt/runtime/\n",
            encoding="utf-8",
        )
        (root / "tools").mkdir()
        (root / "tools/qikvrt_integrity.py").write_text("# generator\n", encoding="utf-8")
        (root / "LEGACY_INTEGRITY_INVENTORIES.md").write_text("legacy map\n", encoding="utf-8")
        (root / "source.txt").write_text("tracked\n", encoding="utf-8")
        (root / "nested").mkdir()
        (root / "nested/tracked.txt").write_text("nested tracked\n", encoding="utf-8")
        (root / "new_source.py").write_text("print('untracked source')\n", encoding="utf-8")
        (root / "state").mkdir()
        (root / "state/launcher_acceptance_record.json").write_text(
            '{"accepted": true}\n', encoding="utf-8"
        )
        (root / "logs").mkdir()
        (root / "logs/runtime.jsonl").write_text("volatile\n", encoding="utf-8")
        (root / "__pycache__").mkdir()
        (root / "__pycache__/cache.pyc").write_bytes(b"cache")
        subprocess.run(
            [
                "git", "-C", str(root), "add", ".gitignore", "source.txt",
                "nested/tracked.txt",
                "state/launcher_acceptance_record.json",
            ],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"],
            check=True,
        )

    def test_generation_is_reproducible_and_detects_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self._repository(root)
            first = integrity.generate(root)
            self.assertTrue(first.ok)
            self.assertTrue(integrity.verify(root).ok)
            outputs_before = {
                name: (root / name).read_bytes()
                for name in (integrity.MANIFEST_NAME, integrity.INDEX_NAME, integrity.DETACHED_NAME)
            }
            subprocess.run(
                [
                    "git", "-C", str(root), "-c", "user.name=Test",
                    "-c", "user.email=test@example.invalid", "commit",
                    "--allow-empty", "-qm", "history-only change",
                ],
                check=True,
            )
            self.assertTrue(integrity.verify(root).ok)
            second = integrity.generate(root)
            self.assertTrue(second.ok)
            self.assertEqual(
                outputs_before,
                {
                    name: (root / name).read_bytes()
                    for name in (integrity.MANIFEST_NAME, integrity.INDEX_NAME, integrity.DETACHED_NAME)
                },
            )
            manifest = json.loads((root / integrity.MANIFEST_NAME).read_text(encoding="utf-8"))
            entries = {entry["path"]: entry for entry in manifest["files"]}
            self.assertNotIn("git_head", manifest)
            self.assertNotIn("source_head_before_generation", manifest)
            self.assertEqual(
                manifest["repository_content_tree_sha256"],
                integrity._content_tree_sha256(manifest["files"]),
            )
            manifest_bytes = (root / integrity.MANIFEST_NAME).read_bytes()
            with tempfile.TemporaryDirectory() as outside_metadata_directory:
                outside_manifest = pathlib.Path(outside_metadata_directory) / "manifest.json"
                outside_manifest.write_bytes(manifest_bytes)
                (root / integrity.MANIFEST_NAME).unlink()
                os.symlink(outside_manifest, root / integrity.MANIFEST_NAME)
                unsafe_metadata = integrity.verify(root)
                self.assertFalse(unsafe_metadata.ok)
                self.assertIn("must not be a symlink", unsafe_metadata.message)
                (root / integrity.MANIFEST_NAME).unlink()
                (root / integrity.MANIFEST_NAME).write_bytes(manifest_bytes)
            self.assertIn("new_source.py", entries)
            self.assertNotIn("logs/runtime.jsonl", entries)
            self.assertNotIn("__pycache__/cache.pyc", entries)
            self.assertFalse(entries["state/launcher_acceptance_record.json"]["immutable"])
            self.assertEqual(entries[integrity.MANIFEST_NAME]["exclusion_reason"], "cycle_prevention")
            self.assertEqual(
                manifest["integrity_authority"]["legacy_global_inventories"],
                list(integrity.LEGACY_GLOBAL_INVENTORIES),
            )
            (root / "source.txt").write_text("changed\n", encoding="utf-8")
            verification = integrity.verify(root)
            self.assertFalse(verification.ok)
            self.assertIn("differs from deterministic regeneration", verification.message)

            # A deliberate working-tree deletion is part of the prospective
            # content tree and must not make generation crash or preserve a
            # file that no longer exists.
            (root / "source.txt").unlink()
            self.assertTrue(integrity.generate(root).ok)
            self.assertTrue(integrity.verify(root).ok)
            regenerated = json.loads(
                (root / integrity.MANIFEST_NAME).read_text(encoding="utf-8")
            )
            self.assertNotIn(
                "source.txt", {entry["path"] for entry in regenerated["files"]}
            )

            with tempfile.TemporaryDirectory() as outside_directory:
                outside = pathlib.Path(outside_directory) / "mutable.py"
                outside.write_text("print('mutable external source')\n", encoding="utf-8")
                link = root / "external_source.py"
                os.symlink(outside, link)
                with self.assertRaisesRegex(RuntimeError, "must not be a symlink"):
                    integrity.generate(root)
                link.unlink()

            with tempfile.TemporaryDirectory() as outside_parent_directory:
                outside_parent = pathlib.Path(outside_parent_directory)
                (outside_parent / "tracked.txt").write_text(
                    "nested tracked\n", encoding="utf-8"
                )
                (root / "nested/tracked.txt").unlink()
                (root / "nested").rmdir()
                os.symlink(outside_parent, root / "nested")
                with self.assertRaisesRegex(RuntimeError, "must not be a symlink"):
                    integrity.generate(root)

    def test_portable_git_source_capsule_proves_exact_selected_closure(self) -> None:
        relative = self.CAPSULE.relative_to(REPOSITORY_ROOT).as_posix()
        capsule = integrity.load_portable_git_source_capsule(
            REPOSITORY_ROOT,
            relative,
        )
        self.assertEqual(
            capsule.commit_sha1,
            "4fd73232cc8d2189e14c950b376bb72ffcaf744e",
        )
        self.assertEqual(
            capsule.root_tree_sha1,
            "93551633d0c2ee8c02ae232e23914acd06b7d858",
        )
        self.assertEqual(len(capsule.objects), 13)
        self.assertEqual(len(capsule.files), 6)
        self.assertEqual(sum(len(value) for value in capsule.files.values()), 62594)
        self.assertEqual(
            capsule.capsule_sha256,
            "414ae95e9182db4fbd3d0658baea6b7aa10ea9d4d3f4b2190c11341095d0710f",
        )
        source_commit_is_local = subprocess.run(
            [
                "git",
                "-C",
                str(REPOSITORY_ROOT),
                "cat-file",
                "-e",
                f"{capsule.commit_sha1}^{{commit}}",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode == 0
        self.assertEqual(
            integrity.cross_check_portable_git_source_capsule(
                REPOSITORY_ROOT,
                capsule,
            ),
            source_commit_is_local,
        )
        evidence = integrity.portable_git_source_evidence(capsule)
        self.assertEqual(
            evidence["verification_mode"],
            "portable-git-object-closure",
        )
        self.assertEqual(evidence["blobs"], capsule.blobs)

    def test_portable_git_source_capsule_rejects_tampering(self) -> None:
        original = json.loads(self.CAPSULE.read_text(encoding="utf-8"))

        def changed_payload(value: dict[str, object]) -> None:
            objects = value["objects"]
            assert isinstance(objects, list)
            entry = next(
                row
                for row in objects
                if isinstance(row, dict) and row.get("type") == "blob"
            )
            payload = bytearray(base64.b64decode(entry["payload_base64"]))
            payload[0] ^= 1
            entry["payload_base64"] = base64.b64encode(payload).decode("ascii")

        def malformed_base64(value: dict[str, object]) -> None:
            objects = value["objects"]
            assert isinstance(objects, list) and isinstance(objects[0], dict)
            objects[0]["payload_base64"] = "not+base64!"

        def missing_tree(value: dict[str, object]) -> None:
            source = value["authority_source"]
            objects = value["objects"]
            assert isinstance(source, dict) and isinstance(objects, list)
            root_tree = source["root_tree_sha1"]
            for index, row in enumerate(objects):
                if (
                    isinstance(row, dict)
                    and row.get("type") == "tree"
                    and row.get("sha1") != root_tree
                ):
                    del objects[index]
                    break

        def unsafe_path(value: dict[str, object]) -> None:
            selection = value["selection"]
            assert isinstance(selection, dict)
            paths = selection["paths"]
            assert isinstance(paths, list) and isinstance(paths[0], dict)
            paths[0]["path"] = "../AI_PROGRESS.json"

        def changed_mode(value: dict[str, object]) -> None:
            selection = value["selection"]
            assert isinstance(selection, dict)
            paths = selection["paths"]
            assert isinstance(paths, list) and isinstance(paths[0], dict)
            paths[0]["mode"] = "100755"

        def changed_root(value: dict[str, object]) -> None:
            source = value["authority_source"]
            assert isinstance(source, dict)
            source["root_tree_sha1"] = "0" * 40

        def surplus_object(value: dict[str, object]) -> None:
            payload = b"surplus"
            header = f"blob {len(payload)}\0".encode("ascii")
            object_id = hashlib.sha1(
                header + payload,
                usedforsecurity=False,
            ).hexdigest()
            objects = value["objects"]
            assert isinstance(objects, list)
            objects.append(
                {
                    "type": "blob",
                    "sha1": object_id,
                    "bytes": len(payload),
                    "payload_sha256": hashlib.sha256(payload).hexdigest(),
                    "payload_base64": base64.b64encode(payload).decode("ascii"),
                }
            )

        cases = {
            "payload": changed_payload,
            "base64": malformed_base64,
            "missing_tree": missing_tree,
            "unsafe_path": unsafe_path,
            "mode": changed_mode,
            "root": changed_root,
            "surplus": surplus_object,
        }
        for name, mutate in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = pathlib.Path(directory)
                value = copy.deepcopy(original)
                mutate(value)
                (root / "capsule.json").write_text(
                    json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
                    + "\n",
                    encoding="utf-8",
                )
                with self.assertRaises(ValueError):
                    integrity.load_portable_git_source_capsule(
                        root,
                        "capsule.json",
                    )

    def test_portable_git_source_capsule_binding_and_symlink_fail_closed(self) -> None:
        relative = self.CAPSULE.relative_to(REPOSITORY_ROOT).as_posix()
        with self.assertRaisesRegex(ValueError, "binding drift"):
            integrity.load_portable_git_source_capsule(
                REPOSITORY_ROOT,
                relative,
                expected_binding={
                    "path": relative,
                    "bytes": self.CAPSULE.stat().st_size,
                    "sha256": "0" * 64,
                    "git_blob_sha1": "0" * 40,
                },
            )
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            os.symlink(self.CAPSULE, root / "capsule.json")
            with self.assertRaisesRegex(RuntimeError, "must not be a symlink"):
                integrity.load_portable_git_source_capsule(
                    root,
                    "capsule.json",
                )

    def test_portable_git_source_capsule_rejects_duplicate_json_and_git_drift(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            raw = self.CAPSULE.read_text(encoding="utf-8")
            duplicated = raw.replace(
                '  "schema": "qikvrt_portable_git_source_capsule_v1",\n',
                (
                    '  "schema": "qikvrt_portable_git_source_capsule_v1",\n'
                    '  "schema": "qikvrt_portable_git_source_capsule_v1",\n'
                ),
                1,
            )
            (root / "capsule.json").write_text(duplicated, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                integrity.load_portable_git_source_capsule(root, "capsule.json")

        relative = self.CAPSULE.relative_to(REPOSITORY_ROOT).as_posix()
        capsule = integrity.load_portable_git_source_capsule(
            REPOSITORY_ROOT,
            relative,
        )
        locally_available = mock.Mock(
            timed_out=False,
            output_limit_exceeded=False,
            returncode=0,
            stderr="",
            stdout="",
        )
        with (
            mock.patch.object(
                integrity,
                "run_bounded",
                return_value=locally_available,
            ),
            mock.patch.object(integrity, "_git", return_value=b"drift"),
        ):
            with self.assertRaisesRegex(ValueError, "disagrees"):
                integrity.cross_check_portable_git_source_capsule(
                    REPOSITORY_ROOT,
                    capsule,
                )


if __name__ == "__main__":
    unittest.main()
