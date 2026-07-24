# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
from __future__ import annotations

import json
import pathlib
import subprocess
import tempfile
import unittest

from tools import qikvrt_ci_post_test as sanitizer


class CiPostTestSanitationTests(unittest.TestCase):
    def _git(self, root: pathlib.Path, *arguments: str) -> None:
        subprocess.run(["git", "-C", str(root), *arguments], check=True)

    def _fixture(self, root: pathlib.Path) -> None:
        self._git(root, "init", "-q")
        (root / ".gitignore").write_text(".qikvrt/\n", encoding="utf-8")
        (root / "source.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "state").mkdir()
        (root / "state" / "launcher_acceptance_record.json").write_text(
            '{"accepted": false}\n', encoding="utf-8"
        )
        self._git(
            root,
            "add",
            ".gitignore",
            "source.py",
            "state/launcher_acceptance_record.json",
        )
        self._git(
            root,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        )

    def test_preserves_untracked_and_restores_mutable_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self._fixture(root)
            mutable = root / "state" / "launcher_acceptance_record.json"
            mutable.write_text('{"accepted": true}\n', encoding="utf-8")
            audit = root / "audit" / "runtime.json"
            audit.parent.mkdir()
            audit.write_text('{"status": "PASS"}\n', encoding="utf-8")
            evidence = root / ".qikvrt" / "evidence" / "test"

            report = sanitizer.sanitize(root, evidence)

            self.assertEqual(report["status"], "PASS")
            self.assertFalse(audit.exists())
            self.assertEqual(
                mutable.read_text(encoding="utf-8"),
                '{"accepted": false}\n',
            )
            stored = evidence / "files" / "untracked" / "audit" / "runtime.json"
            self.assertEqual(stored.read_text(encoding="utf-8"), '{"status": "PASS"}\n')
            report_json = json.loads((evidence / "REPORT.json").read_text(encoding="utf-8"))
            self.assertEqual(report_json["untrackedOutputsPreservedAndRemoved"], ["audit/runtime.json"])
            status = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(status.stdout, "")

    def test_rejects_immutable_tracked_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            self._fixture(root)
            source = root / "source.py"
            source.write_text("VALUE = 2\n", encoding="utf-8")
            evidence = root / ".qikvrt" / "evidence" / "test"

            with self.assertRaisesRegex(
                sanitizer.SanitationError,
                "immutable tracked repository content",
            ):
                sanitizer.sanitize(root, evidence)

            self.assertEqual(source.read_text(encoding="utf-8"), "VALUE = 2\n")
            report = json.loads((evidence / "REPORT.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "BLOCK")
            self.assertEqual(report["immutableTrackedChanges"], ["source.py"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
