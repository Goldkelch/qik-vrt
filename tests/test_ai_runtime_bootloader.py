#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ai_runtime_bootloader", ROOT / "tools/ai_runtime_bootloader.py"
)
assert SPEC and SPEC.loader
BOOTLOADER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOOTLOADER)


class AIRuntimeBootloaderContractTests(unittest.TestCase):
    def test_root_entrypoint_names_executable_bootloader(self) -> None:
        entry = (ROOT / "AI").read_text(encoding="utf-8")
        self.assertIn("QIK-VRT AI RUNTIME ENTRYPOINT", entry)
        self.assertIn("python3 -B tools/ai_runtime_bootloader.py --profile all", entry)
        self.assertIn("It performs no network access", entry)
        self.assertIn(
            "Installation, task execution, commits, merges, releases, and publication remain separate authorized effects",
            entry,
        )

    def test_context_binds_complete_runtime_lifecycle(self) -> None:
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text(encoding="utf-8"))
        boot = context["runtime_bootloader"]
        self.assertEqual(boot["implementation"], "tools/ai_runtime_bootloader.py")
        self.assertFalse(boot["network_required"])
        self.assertFalse(boot["writes_repository"])
        self.assertEqual(boot["accepted_states"], ["PASS", "CONTINUE"])
        self.assertEqual(boot["blocking_state"], "BLOCK")
        self.assertGreaterEqual(len(boot["lifecycle"]), 8)
        self.assertEqual(
            context["progress_protocol"]["machine_schema"],
            "schemas/human_machine_progress.schema.json",
        )
        self.assertIn(
            "docs/HUMAN_MACHINE_PROGRESS_STANDARD.md",
            context["required_read_order"],
        )
        self.assertIn(
            "schemas/human_machine_progress.schema.json",
            context["required_read_order"],
        )
        for authority in (
            "tools/ai_handoff.py",
            "tools/qikvrt_integrity.py",
            "tools/qikvrt_tool_cache.py",
            "tools/bootstrap-runtime.sh",
        ):
            self.assertIn(authority, boot["reused_authorities"])

    def test_bootloader_is_standard_library_and_exposes_cli(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", "tools/ai_runtime_bootloader.py", "--help"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--profile", completed.stdout)
        self.assertIn("--json", completed.stdout)
        self.assertIn("--task", completed.stdout)

    def test_handoff_accepts_current_context_schema(self) -> None:
        context = json.loads((ROOT / "AI_CONTEXT.json").read_text(encoding="utf-8"))
        completed = subprocess.run(
            [sys.executable, "-B", "tools/ai_handoff.py"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(
            completed.returncode,
            0,
            f"current context schema {context['schema']!r} rejected: "
            f"{completed.stderr}",
        )
        self.assertIn("AI_HANDOFF_STATUS=VALID", completed.stdout)
        self.assertIn("AI_PROGRESS_CHECK=", completed.stdout)

    def test_bootloader_source_preserves_effect_boundary(self) -> None:
        source = (ROOT / "tools/ai_runtime_bootloader.py").read_text(encoding="utf-8")
        self.assertIn("no network access", source)
        self.assertIn("tools/qikvrt_integrity.py", source)
        self.assertIn("tools/qikvrt_tool_cache.py", source)
        self.assertIn("tools/bootstrap-runtime.sh", source)
        self.assertIn('report["state"] = "BLOCK"', source)
        self.assertNotIn("shell=True", source)

    def test_ci_retains_full_history_as_authority_side_cross_check(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "qikvrt_ci.yml"
        ).read_text(encoding="utf-8")
        checkout = (
            "      - uses: "
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 "
            "# v7.0.1\n"
            "        with:\n"
            "          fetch-depth: 0\n"
        )
        self.assertIn(checkout, workflow)

    def test_manuscript_workflow_provisions_declared_poppler_before_h5(self) -> None:
        workflow = (
            ROOT / ".github" / "workflows" / "qikvrt_manuscript_proof.yml"
        ).read_text(encoding="utf-8")
        provision = workflow.index("Provision and verify declared Poppler runtime")
        verify_h5 = workflow.index("Verify VRTCore SMG H5 package")
        self.assertLess(provision, verify_h5)
        for command in ("pdfinfo", "pdftotext", "pdftoppm"):
            self.assertIn(f"command -v {command}", workflow)
            self.assertIn(f"{command} -v", workflow)
        self.assertIn("apt-get update -o Acquire::Retries=3", workflow)
        self.assertIn(
            "apt-get install --yes --no-install-recommends poppler-utils",
            workflow,
        )
        self.assertIn("poppler-utils-package=${Version}", workflow)

    def test_handoff_is_portable_when_source_commit_is_not_in_local_git(self) -> None:
        with tempfile.TemporaryDirectory() as empty_objects:
            environment = dict(os.environ)
            environment.update(
                {
                    "GIT_OBJECT_DIRECTORY": empty_objects,
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES": "",
                    "GIT_NO_LAZY_FETCH": "1",
                    "GIT_NO_REPLACE_OBJECTS": "1",
                    "GIT_TERMINAL_PROMPT": "0",
                }
            )
            completed = subprocess.run(
                [sys.executable, "-B", "tools/ai_handoff.py"],
                cwd=ROOT,
                env=environment,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("AI_HANDOFF_STATUS=VALID", completed.stdout)
        self.assertNotIn("source commit is unavailable", completed.stderr)


class AIRuntimeRemoteTopologyTests(unittest.TestCase):
    """Exercise the documented topology with real local Git repositories."""

    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.git("init", "--quiet")
        patch = mock.patch.object(BOOTLOADER, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)
        self.context = {
            "personal_working_memory_origin": {
                "personal_working_copy_remote": "origin",
                "canonical_source_remote": "upstream",
            }
        }

    def git(self, *args: str) -> None:
        subprocess.run(
            ["git", *args], cwd=self.root, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10,
        )

    def resolve(self) -> tuple[str, str]:
        return BOOTLOADER.repository_remote(self.context)

    def test_local_only_copy_uses_declared_source_without_creating_origin(self) -> None:
        url = "https://github.com/Goldkelch/qik-vrt.git"
        self.git("remote", "add", "upstream", url)
        before = (self.root / ".git/config").read_bytes()
        self.assertEqual(self.resolve(), ("upstream", url))
        self.assertEqual((self.root / ".git/config").read_bytes(), before)
        self.assertEqual(BOOTLOADER.git_value("remote"), "upstream")

    def test_existing_origin_only_copy_remains_supported(self) -> None:
        url = "git@github.com:ingolf-lohmann/qik-vrt.git"
        self.git("remote", "add", "origin", url)
        self.assertEqual(self.resolve(), ("origin", url))

    def test_personal_origin_is_not_relabelled_as_authority(self) -> None:
        personal = "https://github.com/ingolf-lohmann/qik-vrt.git"
        self.git("remote", "add", "origin", personal)
        self.git("remote", "add", "upstream", "https://github.com/Goldkelch/qik-vrt.git")
        self.assertEqual(self.resolve(), ("origin", personal))

    def test_context_declared_names_are_used(self) -> None:
        self.context["personal_working_memory_origin"].update(
            personal_working_copy_remote="personal", canonical_source_remote="source"
        )
        url = "https://github.com/Goldkelch/qik-vrt.git"
        self.git("remote", "add", "source", url)
        self.assertEqual(self.resolve(), ("source", url))

    def test_no_remote_still_blocks(self) -> None:
        with self.assertRaisesRegex(BOOTLOADER.BootBlock, "neither declared"):
            self.resolve()

    def test_unrelated_remote_is_not_an_identity_fallback(self) -> None:
        self.git("remote", "add", "unrelated", "https://github.com/example/repo.git")
        with self.assertRaisesRegex(BOOTLOADER.BootBlock, "neither declared"):
            self.resolve()

    def test_ambiguous_personal_remote_does_not_fall_back_to_source(self) -> None:
        self.git("remote", "add", "origin", "https://github.com/example/one.git")
        self.git("config", "--add", "remote.origin.url", "https://github.com/example/two.git")
        self.git("remote", "add", "upstream", "https://github.com/Goldkelch/qik-vrt.git")
        with self.assertRaisesRegex(BOOTLOADER.BootBlock, "one non-empty fetch URL"):
            self.resolve()

    def test_empty_url_does_not_fall_back_to_source(self) -> None:
        self.git("config", "remote.origin.url", "")
        self.git("remote", "add", "upstream", "https://github.com/Goldkelch/qik-vrt.git")
        with self.assertRaisesRegex(BOOTLOADER.BootBlock, "one non-empty fetch URL"):
            self.resolve()

    def test_missing_or_invalid_contract_blocks(self) -> None:
        invalid = [
            {},
            {"personal_working_memory_origin": []},
            {"personal_working_memory_origin": {}},
            {"personal_working_memory_origin": {
                "personal_working_copy_remote": "upstream",
                "canonical_source_remote": "upstream",
            }},
            {"personal_working_memory_origin": {
                "personal_working_copy_remote": "--get-all",
                "canonical_source_remote": "upstream",
            }},
        ]
        for context in invalid:
            with self.subTest(context=context), self.assertRaises(BOOTLOADER.BootBlock):
                BOOTLOADER.repository_remote(context)


if __name__ == "__main__":
    unittest.main(verbosity=2)
