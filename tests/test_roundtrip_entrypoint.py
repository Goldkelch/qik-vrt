# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI ChatGPT.
"""Bounded entrypoint/dispatch tests; never label mocked dispatch as the Roundtrip."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


entry = load("roundtrip_entry", ROOT / "tools/qikvrt_roundtrip_entrypoint.py")
runner = load("roundtrip_runner", ROOT / "roundtrip.py")


class EntrypointTests(unittest.TestCase):
    def fixture(self, root):
        originals = {}
        for relative in entry.PATHS:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            originals[relative] = ("Original instructions: " + relative + "\n").encode()
            path.write_bytes(originals[relative])
        return originals

    def test_first_position_preserves_every_original_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            originals = self.fixture(root)
            self.assertEqual(set(entry.materialize(root, check=False)), set(entry.PATHS))
            for relative, original in originals.items():
                self.assertEqual((root / relative).read_bytes(), entry.prefix(relative) + original)
            self.assertEqual(entry.materialize(root, check=True), [])

    def test_replay_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.fixture(root)
            entry.materialize(root, check=False)
            before = {p: (root / p).read_bytes() for p in entry.PATHS}
            self.assertEqual(entry.materialize(root, check=False), [])
            self.assertEqual(before, {p: (root / p).read_bytes() for p in entry.PATHS})

    def test_check_never_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            originals = self.fixture(root)
            with self.assertRaisesRegex(ValueError, "ROUNDTRIP_NOT_FIRST"):
                entry.materialize(root, check=True)
            self.assertEqual(originals, {p: (root / p).read_bytes() for p in entry.PATHS})

    def test_conflict_prevents_all_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            originals = self.fixture(root)
            (root / "next/AI").write_bytes(entry.START + b"conflict")
            with self.assertRaisesRegex(ValueError, "CONFLICTING"):
                entry.materialize(root, check=False)
            self.assertEqual((root / "AGENTS.md").read_bytes(), originals["AGENTS.md"])

    def test_missing_file_is_not_silently_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            originals = self.fixture(root)
            (root / "next/AI").unlink()
            with self.assertRaisesRegex(ValueError, "MISSING_OR_UNSAFE"):
                entry.materialize(root, check=False)
            self.assertEqual((root / "AI").read_bytes(), originals["AI"])

    def test_relative_links_resolve(self):
        self.assertIn(b"[../ROUNDTRIP.md](../ROUNDTRIP.md)", entry.prefix("next/AI"))
        self.assertIn(b"[ROUNDTRIP.md](ROUNDTRIP.md)", entry.prefix("README.md"))


class RunnerTests(unittest.TestCase):
    def invoke(self, root, result=0, extra=(), env=None):
        target = root / "next/tools/run_checks.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Test stub; not an executed proof\n")
        args = ["--repository", "Goldkelch/qik-vrt", "--output-dir", str(root.parent / "new-evidence"), *extra]
        with mock.patch.object(runner, "ROOT", root), mock.patch.object(runner, "RUNNER", target), \
             mock.patch.dict(os.environ, {"PYTHONOPTIMIZE": "", **(env or {})}), \
             mock.patch.object(runner.subprocess, "run", return_value=mock.Mock(returncode=result)) as call:
            code = runner.main(args)
            return code, call

    def test_delegates_to_existing_runner_and_keeps_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            code, call = self.invoke(root, result=7, extra=("--offline",))
            self.assertEqual(code, 7)
            command = call.call_args.args[0]
            self.assertEqual(command[1], "-B")
            self.assertIn(str(root / "next/tools/run_checks.py"), command)
            self.assertIn("--offline", command)
            self.assertEqual(call.call_args.kwargs["env"]["GITHUB_REPOSITORY"], "Goldkelch/qik-vrt")

    def test_success_is_only_delegated_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, call = self.invoke(Path(tmp) / "repo", result=0)
            self.assertEqual(code, 0)
            call.assert_called_once()

    def test_optimization_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                self.invoke(Path(tmp) / "repo", env={"PYTHONOPTIMIZE": "1"})
            self.assertEqual(error.exception.code, 2)

    def test_missing_runner_has_no_fallback(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            root = Path(tmp)
            with mock.patch.object(runner, "RUNNER", root / "missing.py"), \
                 mock.patch.dict(os.environ, {"PYTHONOPTIMIZE": ""}):
                with self.assertRaises(SystemExit) as error:
                    runner.main(["--repository", "Goldkelch/qik-vrt", "--output-dir", str(root / "out")])
                self.assertEqual(error.exception.code, 2)

    def test_existing_output_is_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            (Path(tmp) / "new-evidence").mkdir()
            with self.assertRaises(SystemExit) as error:
                self.invoke(Path(tmp) / "repo")
            self.assertEqual(error.exception.code, 2)

    def test_source_directory_is_not_an_evidence_sink(self):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
            root = Path(tmp) / "repo"
            with self.assertRaises(SystemExit) as error:
                self.invoke(root, extra=("--output-dir", str(root / "out")))
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
