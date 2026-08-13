#!/usr/bin/env python3
# Copyright 2026 Ingolf Lohmann.
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Regression tests for the repaired launcher, gates, logger and publisher."""
from __future__ import annotations

import hashlib
import json
import pathlib
import os
import sys
import tempfile
import unittest
from unittest import mock

REPOSITORY_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import qikvrt
from tools import qikvrt_cicd_publish as cicd
from tools import qikvrt_initial_acceptance_gate as acceptance
from tools import qikvrt_integrity as integrity
from tools import qikvrt_master_acceptance_gate as master
from tools import qikvrt_runtime_logger as qlog
from tools.qikvrt_subprocess import run_bounded


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class LoggerTests(unittest.TestCase):
    def test_jsonl_and_canonical_nonzero_run_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_dir = pathlib.Path(directory)
            log_file = log_dir / "run.jsonl"
            with mock.patch.object(qlog, "LOG_DIR", log_dir), mock.patch.object(qlog, "LOG_FILE", log_file):
                qlog.reset_log("test")
                qlog.write_event("path_test", path=pathlib.Path(r"C:\\QIK VRT\\file.txt"))
                qlog.write_event("numeric_test", metric=float("nan"))
                self.assertEqual(
                    qlog.finish(
                        20,
                        status="CONTINUE",
                        error_class="ACCEPTANCE_REQUIRED",
                        continue_path="ACCEPT_AND_RERUN",
                        repair_hint="Persist acceptance.",
                    ),
                    20,
                )
            events = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[0]["event"], "run_start")
            self.assertEqual(events[-1]["status"], "CONTINUE")
            self.assertEqual(events[-1]["error_class"], "ACCEPTANCE_REQUIRED")
            self.assertIn("C:/", events[1]["path"])
            self.assertEqual(events[2]["metric"], "nan")
            pointer = json.loads(
                (log_dir / "qikvrt_last_run.json").read_text(encoding="utf-8")
            )
            self.assertEqual(pointer["sha256"], sha256(log_file))
            outside = log_dir / "outside.log"
            outside.write_text("must remain unchanged\n", encoding="utf-8")
            log_file.unlink()
            os.symlink(outside, log_file)
            with mock.patch.object(qlog, "LOG_DIR", log_dir), mock.patch.object(
                qlog, "LOG_FILE", log_file
            ), self.assertRaises(OSError):
                qlog.reset_log("symlink-test")
            self.assertEqual(outside.read_text(encoding="utf-8"), "must remain unchanged\n")
            with mock.patch.object(qlog, "LOG_DIR", log_dir), mock.patch.object(
                qlog, "LOG_FILE", log_file
            ), self.assertRaises(OSError):
                qlog._write_latest_pointer("BLOCK", 1)
            self.assertEqual(outside.read_text(encoding="utf-8"), "must remain unchanged\n")

            with mock.patch.object(qlog, "LOG_DIR", log_dir), mock.patch.object(
                qlog, "LOG_FILE", qlog.DEFAULT_LOG_FILE
            ):
                first = qlog.reset_log("first-concurrent-safe-run")
                second = qlog.reset_log("second-concurrent-safe-run")
                self.assertNotEqual(first, second)
                self.assertTrue(first.is_file())
                self.assertTrue(second.is_file())


class AcceptanceTests(unittest.TestCase):
    def test_acceptance_record_cannot_be_written_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as repository, tempfile.TemporaryDirectory() as outside:
            root = pathlib.Path(repository)
            external = pathlib.Path(outside) / "acceptance.json"
            with mock.patch.object(acceptance, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "escapes the repository"):
                    acceptance._atomic_write_json(external, {"accepted": True})
            self.assertFalse(external.exists())
            redirected = root / "redirected"
            redirected.mkdir()
            link = root / ".qikvrt"
            os.symlink(redirected, link)
            with mock.patch.object(acceptance, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "contains a symlink"):
                    acceptance._atomic_write_json(
                        link / "runtime" / "authorization.json", {"accepted": True}
                    )

    def test_acceptance_is_bound_expires_and_precedes_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            state = root / ".qikvrt" / "runtime"
            record = state / "launcher_acceptance_record.json"
            log_dir = root / "logs"
            log_file = log_dir / "last.jsonl"
            launcher = root / "qikvrt.py"
            launcher.write_text("print('test')\n", encoding="utf-8")
            (root / "tools").mkdir()
            for relative in acceptance.CONTEXT_FILES[1:]:
                path = root / relative
                path.write_text(f"# {relative}\n", encoding="utf-8")
            (root / "REPOSITORY_FILE_MANIFEST.json").write_text(
                '{"files": [], "repository_content_tree_sha256": "' + "b" * 64 + '"}\n',
                encoding="utf-8",
            )
            patches = (
                mock.patch.object(acceptance, "ROOT", root),
                mock.patch.object(acceptance, "STATE_DIR", state),
                mock.patch.object(acceptance, "ACCEPTANCE_FILE", record),
                mock.patch.object(qlog, "LOG_DIR", log_dir),
                mock.patch.object(qlog, "LOG_FILE", log_file),
            )
            with patches[0], patches[1], patches[2], patches[3], patches[4], mock.patch.object(
                acceptance, "_acceptance_file_is_tracked", return_value=False
            ):
                qlog.reset_log("test")
                self.assertFalse(acceptance.require_acceptance("master-gate"))
                data = acceptance.persist_acceptance(
                    "test operator", "test scope", ("master-gate",), 60
                )
                self.assertTrue(acceptance.require_acceptance("master-gate"))
                self.assertFalse(acceptance.load_acceptance("cicd-publish"))
                qlog.log_command_start("safe command")
                self.assertTrue(acceptance.validate_log_order(log_file))
                self.assertEqual(data["launcher_sha256"], sha256(launcher))
                self.assertEqual(record.parent, state)
                self.assertNotIn("state/launcher_acceptance_record.json", record.as_posix())
                (root / "tools/qikvrt_master_acceptance_gate.py").write_text(
                    "# changed after acceptance\n", encoding="utf-8"
                )
                self.assertFalse(acceptance.load_acceptance("master-gate"))

    def test_shipped_legacy_record_is_not_accepted(self) -> None:
        legacy = {
            "accepted": True,
            "product_owner_acceptance": True,
            "accepted_by": "someone else",
            "accepted_utc": "2026-01-01T00:00:00Z",
            "accepted_scope": "old checkout",
            "source_code_license": "Apache-2.0",
            "non_source_license": "CC-BY-NC-ND-4.0",
            "python_runtime_third_party_license": "Python Software Foundation License Version 2",
        }
        self.assertFalse(acceptance._valid_record(legacy, "master-gate"))


class LauncherTests(unittest.TestCase):
    def test_direct_master_help_finishes_log(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_dir = pathlib.Path(directory)
            log_file = log_dir / "last.jsonl"
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("QIKVRT_LAUNCHED_BY_QIKVRT", None)
                with mock.patch.object(qlog, "LOG_DIR", log_dir), mock.patch.object(
                    qlog, "LOG_FILE", log_file
                ):
                    self.assertEqual(master.main(["--help"]), 0)
            events = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["event"] for event in events], ["run_start", "run_end"])
            test_root = log_dir / "isolated-test-root"
            (test_root / "tests").mkdir(parents=True)
            (test_root / "tests/test_sentinel.py").write_text("# sentinel test\n", encoding="utf-8")

            def capture_environment(
                command: list[str], **kwargs: object
            ) -> mock.Mock:
                del command
                self.assertNotIn("QIKVRT_LAUNCHED_BY_QIKVRT", kwargs["env"])
                return mock.Mock(
                    stdout="", stderr="", timed_out=False,
                    output_limit_exceeded=False, returncode=0,
                )

            with mock.patch.object(master, "ROOT", test_root), mock.patch.object(
                master, "run_bounded", side_effect=capture_environment
            ):
                self.assertEqual(
                    master.run_test_modules(),
                    (True, "all 1 test modules executed with exit code 0"),
                )

    def test_help_finishes_log_without_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_dir = pathlib.Path(directory)
            log_file = log_dir / "last.jsonl"
            with mock.patch.object(qlog, "LOG_DIR", log_dir), mock.patch.object(qlog, "LOG_FILE", log_file):
                self.assertEqual(qikvrt.main(["--help"]), 0)
            events = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([event["event"] for event in events], ["run_start", "run_end"])
            windows_launcher = (REPOSITORY_ROOT / "qikvrt.cmd").read_text(encoding="utf-8")
            self.assertIn('"%PY_EXE%" %PY_ARGS% "%SCRIPT_DIR%qikvrt.py"', windows_launcher)
            self.assertNotIn('set "PY_EXE=py -3"', windows_launcher)

    def test_passthrough_accept_word_cannot_persist_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_dir = pathlib.Path(directory)
            log_file = log_dir / "last.jsonl"
            with mock.patch.object(qlog, "LOG_DIR", log_dir), mock.patch.object(qlog, "LOG_FILE", log_file), \
                 mock.patch.object(acceptance, "persist_acceptance") as persist, \
                 mock.patch.object(acceptance, "require_acceptance", return_value=True), \
                 mock.patch.object(qikvrt, "run_command", return_value=0) as run:
                self.assertEqual(qikvrt.main(["master-gate", "--", "accept"]), 0)
            persist.assert_not_called()
            run.assert_called_once_with("master-gate", ["accept"])

    def test_acceptance_persistence_failure_has_canonical_block_end(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_dir = pathlib.Path(directory)
            log_file = log_dir / "last.jsonl"
            with mock.patch.object(qlog, "LOG_DIR", log_dir), mock.patch.object(
                qlog, "LOG_FILE", log_file
            ), mock.patch.object(
                acceptance, "persist_acceptance", side_effect=ValueError("invalid content tree")
            ):
                self.assertEqual(qikvrt.main(["--accept"]), 1)
            events = [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events[-1]["event"], "run_end")
            self.assertEqual(events[-1]["status"], "BLOCK")
            self.assertEqual(events[-1]["error_class"], "LAUNCHER_ACCEPTANCE_PERSIST_FAILED")


class IntegrityTests(unittest.TestCase):
    def test_master_integrity_check_delegates_to_canonical_verifier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            result = integrity.Verification(True, "canonical snapshot verified")
            with mock.patch.object(master, "ROOT", root), mock.patch.object(
                integrity, "verify", return_value=result
            ) as verifier:
                self.assertEqual(
                    master.check_repository_integrity(),
                    (True, "canonical snapshot verified"),
                )
            verifier.assert_called_once_with(root)

    def test_master_integrity_check_propagates_block_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            result = integrity.Verification(False, "content-tree digest mismatch")
            with mock.patch.object(master, "ROOT", root), mock.patch.object(
                integrity, "verify", return_value=result
            ), mock.patch.object(integrity, "generate") as repair:
                ok, message = master.check_repository_integrity()
            self.assertFalse(ok)
            self.assertEqual(message, "content-tree digest mismatch")
            repair.assert_not_called()


class CicdTests(unittest.TestCase):
    def test_github_remote_url_is_bound_to_selected_repository(self) -> None:
        self.assertEqual(
            cicd._github_repository_from_remote("git@github.com:Owner/Repo.git"),
            "Owner/Repo",
        )
        self.assertEqual(
            cicd._github_repository_from_remote("https://github.com/Owner/Repo.git"),
            "Owner/Repo",
        )
        self.assertIsNone(cicd._github_repository_from_remote("https://example.com/Owner/Repo.git"))
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            asset = root / "release.bin"
            asset.write_bytes(b"planned release bytes")
            for command in (
                ["git", "init", "-q"],
                ["git", "add", "--", asset.name],
                [
                    "git", "-c", "user.email=test@example.invalid", "-c", "user.name=QIK-VRT",
                    "commit", "-qm", "initial",
                ],
            ):
                self.assertEqual(run_bounded(command, cwd=root, timeout=10).returncode, 0)
            with mock.patch.object(cicd, "ROOT", root):
                descriptor = cicd._asset_descriptor(asset.name)
                ok, _steps, _reason = cicd._verify_plan_assets({"assets": [descriptor]})
                self.assertTrue(ok)
                self.assertTrue(cicd._release_assets_match({
                    "assets": [{
                        "name": asset.name,
                        "size": descriptor["bytes"],
                        "digest": f"sha256:{descriptor['sha256']}",
                    }],
                }, [descriptor]))
                (root / "asset-alias.bin").symlink_to(asset.name)
                with self.assertRaisesRegex(ValueError, "symlink"):
                    cicd._asset_descriptor("asset-alias.bin")
                asset.write_bytes(b"changed after planning")
                ok, _steps, reason = cicd._verify_plan_assets({"assets": [descriptor]})
                self.assertFalse(ok)
                self.assertIn("changed after planning", reason)

    def test_publication_journal_rejects_outside_path_without_unbounded_parent_walk(self) -> None:
        with tempfile.TemporaryDirectory() as repository, tempfile.TemporaryDirectory() as outside:
            root = pathlib.Path(repository)
            journal = cicd.PublicationJournal(
                pathlib.Path(outside) / "journal.json", {"actions": []}
            )
            with mock.patch.object(cicd, "ROOT", root), self.assertRaisesRegex(
                ValueError, "escapes repository root"
            ):
                journal.record("PREPARED")

    def test_execute_preflight_rejects_untracked_source(self) -> None:
        head = "a" * 40
        plan = {
            "github_repository": "owner/repo",
            "github_remote": "origin",
            "github_branch": "main",
            "github_tag": "release",
            "actions": [{
                "effect": "github_push",
                "command": ["git", "push", "origin", "HEAD:refs/heads/main"],
            }],
        }

        def fake_run(command: list[str], timeout: int = 180) -> dict[str, object]:
            del timeout
            stdout = ""
            if command[1:] == ["rev-parse", "--is-inside-work-tree"]:
                stdout = "true\n"
            elif command[1:] == ["rev-parse", "HEAD"]:
                stdout = head + "\n"
            elif command[1:] == ["status", "--porcelain"]:
                stdout = "?? uncommitted-source.py\n"
            return {"command": command, "returncode": 0, "stdout": stdout, "stderr": ""}

        with mock.patch.object(cicd, "_run", side_effect=fake_run) as runner:
            code, _steps, reason = cicd.execute_plan(plan)
        self.assertEqual(code, 20)
        self.assertIn("untracked source changes", reason)
        self.assertNotIn(["git", "push", "origin", "HEAD:refs/heads/main"], [
            call.args[0] for call in runner.call_args_list
        ])
        bounded = run_bounded(
            [sys.executable, "-c", "import sys; sys.stdout.write('x' * 4096)"],
            timeout=5,
            max_output_bytes=1024,
        )
        self.assertTrue(bounded.output_limit_exceeded)
        self.assertLessEqual(len(bounded.stdout.encode("utf-8")), 1024)

        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            journal = cicd.PublicationJournal(root / "journal.json", plan)

            def successful_run(command: list[str], timeout: int = 180) -> dict[str, object]:
                del timeout
                stdout = ""
                if command[1:] == ["rev-parse", "--is-inside-work-tree"]:
                    stdout = "true\n"
                elif command[1:] == ["rev-parse", "HEAD"]:
                    stdout = head + "\n"
                elif command[1:] == ["remote", "get-url", "--push", "origin"]:
                    stdout = "https://github.com/owner/repo.git\n"
                elif command[1:] == ["ls-remote", "origin", "refs/heads/main"]:
                    stdout = f"{head}\trefs/heads/main\n"
                return {"command": command, "returncode": 0, "stdout": stdout, "stderr": ""}

            with mock.patch.object(cicd, "ROOT", root), mock.patch.object(
                cicd, "_run", side_effect=successful_run
            ):
                code, _steps, _reason = cicd.execute_plan(plan, journal)
            self.assertEqual(code, 0)
            durable = json.loads(journal.path.read_text(encoding="utf-8"))
            self.assertEqual(durable["state"], "COMMITTED")
            self.assertEqual(
                [event["state"] for event in durable["events"]],
                ["PREPARED", "APPLIED", "VERIFIED", "COMMITTED"],
            )

    def test_execute_requires_repository_owned_github_capability_before_journal(self) -> None:
        head = "a" * 40
        plan = {
            "github_repository": "owner/repo",
            "github_remote": "origin",
            "github_branch": "main",
            "github_tag": "release",
            "actions": [{
                "effect": "github_push",
                "command": ["git", "push", "origin", "HEAD:refs/heads/main"],
            }],
            "assets": [],
        }

        def fake_run(command: list[str], timeout: int = 180) -> dict[str, object]:
            del timeout
            stdout = ""
            returncode = 0
            if command[1:] == ["rev-parse", "--is-inside-work-tree"]:
                stdout = "true\n"
            elif command[1:] == ["rev-parse", "HEAD"]:
                stdout = head + "\n"
            elif command[1:] == ["remote", "get-url", "--push", "origin"]:
                stdout = "https://github.com/owner/repo.git\n"
            elif any(part.endswith("qikvrt_github_publish_runtime.py") for part in command):
                returncode = 20
                stdout = '{"state":"CREDENTIAL_REQUIRED"}\n'
            return {
                "command": command,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": "",
            }

        with tempfile.TemporaryDirectory() as directory:
            journal = cicd.PublicationJournal(pathlib.Path(directory) / "journal.json", plan)
            with mock.patch.object(cicd, "_run", side_effect=fake_run) as runner:
                code, _steps, reason = cicd.execute_plan(plan, journal)
            self.assertEqual(code, 20)
            self.assertIn("repository-owned GitHub publication capability", reason)
            self.assertFalse(journal.path.exists())
            executed = [call.args[0] for call in runner.call_args_list]
            self.assertFalse(any(command[:2] == ["git", "push"] for command in executed))

    def test_missing_effect_authorization_writes_no_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with mock.patch.object(cicd, "ROOT", root), \
                 mock.patch.object(cicd, "publisher_effect_is_authorized", return_value=False), \
                 mock.patch.object(cicd, "run_master_gate") as master_gate:
                self.assertEqual(cicd.main(["--mode", "plan"]), 20)
            master_gate.assert_not_called()
            self.assertFalse(
                (root / ".qikvrt/evidence" / "QIKVRT_CICD_EVIDENCE_LEDGER.json").exists()
            )

            with mock.patch.object(cicd, "ROOT", root), \
                 mock.patch.object(cicd, "publisher_effect_is_authorized", return_value=True), \
                 mock.patch.object(cicd, "run_master_gate", return_value=(20, "", "master authorization required")):
                self.assertEqual(cicd.main(["--mode", "plan"]), 20)
            self.assertFalse(
                (root / ".qikvrt/evidence" / "QIKVRT_CICD_EVIDENCE_LEDGER.json").exists()
            )

    def test_default_and_plan_never_execute_external_actions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            with mock.patch.object(cicd, "ROOT", root), \
                 mock.patch.object(cicd, "publisher_effect_is_authorized", return_value=True), \
                 mock.patch.object(cicd, "run_master_gate", return_value=(0, "", "")), \
                 mock.patch.object(cicd, "execute_plan") as execute:
                self.assertEqual(cicd.main([]), 0)
                self.assertEqual(cicd.main(["--mode", "plan"]), 0)
            execute.assert_not_called()
            evidence = json.loads(
                (root / ".qikvrt/evidence" / "QIKVRT_CICD_EVIDENCE_LEDGER.json").read_text(encoding="utf-8")
            )
            self.assertEqual(evidence["status"], "PASS_PUBLISH_PLAN")
            self.assertFalse(evidence["external_done_claim"])
            zenodo = cicd.parse_args(["--zenodo-enable"])
            self.assertTrue(any("not implemented" in error for error in cicd.validate_args(zenodo)))
            unused_asset = cicd.parse_args(["--asset", "README.md"])
            self.assertIn("release assets require github-release", cicd.validate_args(unused_asset))

    def test_execute_requires_two_explicit_confirmations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            args = [
                "--mode", "execute", "--github-enable", "--github-push",
                "--github-repository", "owner/repo",
            ]
            with mock.patch.object(cicd, "ROOT", root), \
                 mock.patch.object(cicd, "publisher_effect_is_authorized", return_value=True), \
                 mock.patch.object(cicd, "run_master_gate", return_value=(0, "", "")), \
                 mock.patch.object(cicd, "execute_plan") as execute:
                self.assertEqual(cicd.main(args), 20)
            execute.assert_not_called()
            evidence = json.loads(
                (root / ".qikvrt/evidence" / "QIKVRT_CICD_EVIDENCE_LEDGER.json").read_text(encoding="utf-8")
            )
            self.assertEqual(evidence["status"], "CONTINUE_EXPLICIT_CONFIRMATION_REQUIRED")


if __name__ == "__main__":
    unittest.main()
