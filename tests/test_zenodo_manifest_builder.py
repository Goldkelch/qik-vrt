#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Offline tests for the deterministic EFFECT_ACK Zenodo source export."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools/qikvrt_build_zenodo_manifest.py"
SENTINEL_NAME = "DO_NOT_UPLOAD__GENERATED_SOFTWARE_ARCHIVE_REQUIRED.txt"


def hashes(path: Path) -> tuple[int, str, str]:
    payload = path.read_bytes()
    return len(payload), hashlib.md5(payload).hexdigest(), hashlib.sha256(payload).hexdigest()  # noqa: S324


def entry(root: Path, relative: str, name: str) -> dict[str, object]:
    size, md5, sha256 = hashes(root / relative)
    return {
        "path": relative,
        "name": name,
        "size": size,
        "md5": md5,
        "sha256": sha256,
    }


class ZenodoManifestBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="qikvrt-zenodo-builder-")
        self.root = Path(self.temporary.name)
        (self.root / "release").mkdir()
        (self.root / "paper.txt").write_text("paper DOI 10.5281/zenodo.900001\n", encoding="utf-8")
        sentinel = self.root / "release" / SENTINEL_NAME
        sentinel.write_text("reserve only\n", encoding="utf-8")
        template = {
            "schema_version": 1,
            "release_id": "2026-07-22-effect-ack-universality-1.0.0",
            "authorization": {
                "repositories": ["Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt"],
                "tag": "v2026.07.22-effect-ack-universality-1.0.0",
            },
            "paper": {
                "metadata": {
                    "title": "EFFECT_ACK paper",
                    "version": "1.0.0",
                    "creators": [{"name": "Lohmann, Ingolf"}],
                    "upload_type": "publication",
                    "publication_type": "workingpaper",
                    "prereserve_doi": True,
                    "description": "Software DOI 10.5281/zenodo.900002",
                },
                "files": [entry(self.root, "paper.txt", "paper.txt")],
            },
            "software": {
                "source_record_id": 21488116,
                "concept_record_id": 21488115,
                "metadata": {
                    "title": "QIK-VRT EFFECT_ACK software",
                    "version": "2026.07.22-effect-ack-universality-1.0.0",
                    "creators": [{"name": "Lohmann, Ingolf"}],
                    "upload_type": "software",
                    "description": "Paper DOI 10.5281/zenodo.900001",
                },
                "files": [
                    entry(self.root, f"release/{SENTINEL_NAME}", SENTINEL_NAME)
                ],
            },
            "reserved_dois": {
                "paper": "10.5281/zenodo.900001",
                "software": "10.5281/zenodo.900002",
            },
        }
        (self.root / "release/manifest.json").write_text(
            json.dumps(template, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "QIK-VRT Test"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)
        self.commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.root, text=True
        ).strip()
        self.tree = subprocess.check_output(
            ["git", "show", "-s", "--format=%T", "HEAD"], cwd=self.root, text=True
        ).strip()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def invoke(self, output: str, tree: str | None = None) -> subprocess.CompletedProcess[str]:
        output_dir = f".qikvrt/{output}"
        return subprocess.run(
            [
                "python3",
                "-B",
                str(BUILDER),
                "--repository-root",
                str(self.root),
                "--template",
                "release/manifest.json",
                "--source-commit",
                self.commit,
                "--source-tree",
                tree or self.tree,
                "--output-directory",
                output_dir,
                "--result",
                f"{output_dir}/final.json",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_repeated_derivation_has_identical_archive_and_exact_tree_files(self) -> None:
        first = self.invoke("first")
        second = self.invoke("second")
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        name = "qik-vrt-v2026.07.22-effect-ack-universality-1.0.0-source.tar.gz"
        first_archive = self.root / ".qikvrt/first" / name
        second_archive = self.root / ".qikvrt/second" / name
        self.assertEqual(first_archive.read_bytes(), second_archive.read_bytes())
        tracked = subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", "HEAD"],
            cwd=self.root,
            text=True,
        ).splitlines()
        with tarfile.open(first_archive, "r:gz") as archive:
            self.assertEqual(archive.getnames(), tracked)
            self.assertEqual(archive.extractfile("paper.txt").read(), (self.root / "paper.txt").read_bytes())
        final = json.loads((self.root / ".qikvrt/first/final.json").read_text())
        names = [item["name"] for item in final["software"]["files"]]
        self.assertNotIn(SENTINEL_NAME, names)
        self.assertEqual(len(names), 3)
        checksum = (self.root / ".qikvrt/first" / (name + ".sha256")).read_text()
        self.assertEqual(checksum, f"{hashlib.sha256(first_archive.read_bytes()).hexdigest()}  {name}\n")

    def test_source_tree_mismatch_blocks_before_output(self) -> None:
        result = self.invoke("bad-tree", "0" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("source commit does not carry the authorized source tree", result.stderr)
        self.assertFalse((self.root / ".qikvrt/bad-tree/final.json").exists())


if __name__ == "__main__":
    unittest.main()
