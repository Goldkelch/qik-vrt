#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import json
import contextlib
import copy
import io
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import ai_runtime_bootloader as boot

ROOT = pathlib.Path(__file__).resolve().parents[1]


class AIBootSourceBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.context = {"required_read_order": ["AI", "AI_CONTEXT.json"]}
        for path in ("AI", "AI_CONTEXT.json", *boot.BOOT_SOURCE_PATHS):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "-qm", "source fixture")
        patcher = mock.patch.object(boot, "ROOT", self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", *args], cwd=self.root, text=True).strip()

    def test_binds_commit_tree_and_exact_source_bytes(self) -> None:
        subject = boot.capture_subject(self.context)
        boot.require_bound_subject(subject, subject["commit"])
        self.assertEqual(subject["commit"], self.git("rev-parse", "HEAD"))
        self.assertEqual(subject["tree"], self.git("rev-parse", "HEAD^{tree}"))
        ai = next(item for item in subject["inputs"] if item["path"] == "AI")
        self.assertEqual(ai["git_blob_sha1"], self.git("rev-parse", "HEAD:AI"))
        self.assertEqual(len(ai["sha256"]), 64)
        self.assertFalse(subject["dirty"])
        self.assertFalse(subject["remote_state_observed"])

    def test_dirty_worktree_is_not_a_committed_subject(self) -> None:
        (self.root / "AI").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(boot.BootBlock, "SOURCE_BYTES_NOT_COMMIT_BOUND"):
            boot.capture_subject(self.context)

    def test_assume_unchanged_cannot_hide_changed_input(self) -> None:
        self.git("update-index", "--assume-unchanged", "AI")
        (self.root / "AI").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(boot.BootBlock, "SOURCE_BYTES_NOT_COMMIT_BOUND"):
            boot.capture_subject(self.context)

    def test_untracked_work_is_not_exact_head_verification(self) -> None:
        (self.root / "new.txt").write_text("new\n", encoding="utf-8")
        with self.assertRaisesRegex(boot.BootBlock, "WORKTREE_NOT_COMMIT_BOUND"):
            boot.require_bound_subject(boot.capture_subject(self.context), None)

    def test_rejects_a_predecessor_even_when_tree_is_equal(self) -> None:
        old = self.git("rev-parse", "HEAD")
        self.git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                 "commit", "--allow-empty", "-qm", "successor")
        with self.assertRaisesRegex(boot.BootBlock, "EXPECTED_HEAD_MISMATCH"):
            boot.require_bound_subject(boot.capture_subject(self.context), old)

    def test_paths_are_confined_and_not_executable_input(self) -> None:
        for path in ("../outside", "/tmp/outside", "AI/../AI", "--help", "AI\n"):
            with self.subTest(path=path), self.assertRaises(boot.BootBlock):
                boot.capture_subject({"required_read_order": [path]})

    def test_symlinked_source_is_rejected(self) -> None:
        (self.root / "AI").unlink()
        (self.root / "AI").symlink_to("AI_CONTEXT.json")
        with self.assertRaisesRegex(boot.BootBlock, "SOURCE_PATH_INVALID"):
            boot.capture_subject(self.context)

    def test_malformed_routes_cannot_escape_failure_receipt(self) -> None:
        for routes in (None, [], {"runtime": 3}, {"runtime": [None]}):
            context = {**self.context, "entrypoint_contract": {"routes": routes}}
            with self.subTest(routes=routes), self.assertRaises(boot.BootBlock):
                boot.capture_subject(context)


class AIBootFailureReceiptTests(unittest.TestCase):
    def test_failed_gate_keeps_machine_readable_diagnostics(self) -> None:
        result = subprocess.CompletedProcess(["fixture"], 7, "partial", "cause")
        with mock.patch.object(boot.subprocess, "run", return_value=result):
            with self.assertRaises(boot.BootBlock) as raised:
                boot.run_gate("fixture gate", ["fixture"])
        self.assertEqual(raised.exception.gate["state"], "BLOCK")
        self.assertEqual(raised.exception.gate["exit_code"], 7)
        self.assertEqual(raised.exception.gate["stderr"], "cause")

    def test_timeout_is_an_explicit_non_success_result(self) -> None:
        with mock.patch.object(boot.subprocess, "run", side_effect=subprocess.TimeoutExpired("fixture", 180)):
            with self.assertRaises(boot.BootBlock) as raised:
                boot.run_gate("fixture gate", ["fixture"])
        self.assertEqual(raised.exception.gate["state"], "BLOCK")
        self.assertIsNone(raised.exception.gate["exit_code"])


class AIBootReceiptFlowTests(unittest.TestCase):
    def run_boot(self, state="PASS", failure=False, successor=False, argv=None):
        subject = {"commit": "a" * 40, "tree": "b" * 40, "ref": "fixture",
                   "dirty": False, "inputs": [], "remote_state_observed": False}
        after = {**subject, "commit": "c" * 40} if successor else subject
        def gate(name, command, accepted=None):
            result = {"name": name, "command": command, "state": state,
                      "exit_code": 20 if state == "CONTINUE" else 0, "stdout": "", "stderr": ""}
            if failure:
                result.update(state="BLOCK", exit_code=7, stderr="fixture failure")
                raise boot.BootBlock("fixture failure", result)
            return result
        out = io.StringIO()
        with mock.patch.object(boot, "capture_subject", side_effect=[subject, after]), \
                mock.patch.object(boot, "run_gate", side_effect=gate), contextlib.redirect_stdout(out):
            code = boot.main(argv or ["--json", "--profile", "core", "--expect-head", "a" * 40])
        return code, json.loads(out.getvalue())

    def test_success_is_only_bootstrap_readiness(self) -> None:
        code, report = self.run_boot()
        self.assertEqual((code, report["state"]), (0, "PASS"))
        self.assertTrue(report["source_reobserved_unchanged"])
        self.assertEqual(report["scope"], "LOCAL_BOOTSTRAP_ONLY")
        self.assertIsNone(report["first_blocker"])
        self.assertEqual(report["effect_state"], "EFFECT_ACK_CONTINUE")
        self.assertFalse(report["ordinary_release"])
        self.assertFalse(any(report["completion_claims"].values()))
        self.assertFalse(report["remote_state_observed"])
        self.assertFalse(report["continuation"]["task_execution_authorized"])

    def test_continue_is_zero_exit_but_not_effect_completion(self) -> None:
        code, report = self.run_boot(state="CONTINUE")
        self.assertEqual((code, report["state"]), (0, "CONTINUE"))
        self.assertEqual(report["continuation"]["state"], "RUNTIME_REQUIREMENTS_OPEN")
        self.assertFalse(report["ordinary_release"])

    def test_failed_gate_survives_in_receipt_with_resume_condition(self) -> None:
        code, report = self.run_boot(failure=True)
        self.assertEqual((code, report["state"]), (2, "BLOCK"))
        self.assertEqual(report["first_blocker"], report["gates"][-1])
        self.assertEqual(report["first_blocker"]["exit_code"], 7)
        self.assertFalse(report["source_reobserved_unchanged"])
        self.assertFalse(report["continuation"]["automatic_retry"])
        self.assertIn("retry_condition", report["continuation"])
        self.assertEqual(report["effect_state"], "EFFECT_ACK_BLOCK")

    def test_source_change_during_boot_cannot_keep_success(self) -> None:
        code, report = self.run_boot(successor=True)
        self.assertEqual((code, report["state"]), (2, "BLOCK"))
        self.assertEqual(report["first_blocker"]["name"], "source reobservation")
        self.assertFalse(report["source_reobserved_unchanged"])

    def test_invalid_expected_head_still_emits_failure_json(self) -> None:
        code, report = self.run_boot(argv=["--json", "--expect-head", "main"])
        self.assertEqual(code, 2)
        self.assertEqual(report["blocker"], "EXPECTED_HEAD_INVALID")

    def test_resume_preserves_task_as_data_not_shell(self) -> None:
        label = "review $(not-a-command)"
        code, report = self.run_boot(argv=["--json", "--task", label])
        self.assertEqual(code, 0)
        self.assertEqual(report["continuation"]["resume_command"][-2:], ["--task", label])
        self.assertNotIn("target postcondition readback", report["continuation"]["required_before_effect"])
        self.assertIn("target postcondition readback", report["continuation"]["required_after_effect"])

    def test_malformed_context_still_has_effect_and_resume_boundary(self) -> None:
        with mock.patch.object(boot, "load_context", return_value={"entrypoint_contract": None}):
            code, report = self.run_boot()
        self.assertEqual(code, 2)
        self.assertFalse(report["ordinary_release"])
        self.assertEqual(report["first_blocker"]["name"], "source binding")
        self.assertFalse(report["continuation"]["automatic_retry"])

    def test_discovery_cannot_grant_effect_authority(self) -> None:
        context = boot.load_context()
        for field, value in (("http_get_executes_task", True), ("authority_repository", "other/repo")):
            changed = copy.deepcopy(context)
            changed["entrypoint_contract"][field] = value
            with self.subTest(field=field), self.assertRaises(boot.BootBlock):
                boot.validate_entrypoint(changed)
        context["entrypoint_contract"]["effect_gate"]["bootstrap_may_issue_done"] = True
        with self.assertRaises(boot.BootBlock):
            boot.validate_entrypoint(context)


class AIRuntimeBootloaderContractTests(unittest.TestCase):
    def test_qr_discovery_reuses_existing_boot_and_effect_routes(self) -> None:
        context = boot.load_context()
        entry = boot.validate_entrypoint(context)
        discovery = json.loads((ROOT / ".well-known/qik-vrt-self-disclosure.json").read_text())
        self.assertEqual(discovery["ai_entrypoint"]["context"], "AI_CONTEXT.json")
        self.assertEqual(entry["effect_gate"]["implementation"], "src/qikvrt_effect_ack.py")
        for paths in entry["routes"].values():
            for path in paths:
                self.assertTrue((ROOT / path).is_file(), path)
        self.assertFalse(discovery["ai_entrypoint"]["http_get_executes_task"])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
