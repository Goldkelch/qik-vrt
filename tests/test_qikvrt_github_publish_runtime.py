#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import qikvrt_github_publish_runtime as publish_runtime


def command_result(
    command: list[str], stdout: str = "", returncode: int = 0, stderr: str = ""
) -> dict[str, object]:
    return {
        "command": command,
        "returncode": returncode,
        "stdout": publish_runtime.redact(stdout),
        "stderr": publish_runtime.redact(stderr),
        "raw_stdout": stdout,
    }


def prepare_args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "repository": "Goldkelch/qik-vrt",
        "remote": "origin",
        "base": "main",
        "install": False,
        "accept_third_party": False,
        "configure_local_git": True,
        "require_clean": True,
        "json": True,
        "receipt": "",
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class GitHubPublishRuntimeTests(unittest.TestCase):
    def test_offline_contract_is_repository_complete_and_effect_free(self) -> None:
        receipt = publish_runtime.validate_offline_contract()
        self.assertEqual(receipt["state"], "REPOSITORY_READY")
        self.assertTrue(receipt["repository_owned_capability"])
        self.assertFalse(receipt["network_used"])
        self.assertFalse(receipt["credential_checked"])
        self.assertFalse(receipt["credential_persisted"])
        self.assertEqual(receipt["toolchain"]["exact_version"], "2.96.0")
        self.assertEqual(receipt["toolchain"]["locked_targets"], 6)

    def test_cli_exposes_offline_prepare_login_and_exact_gh_lanes(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", "tools/qikvrt_github_publish_runtime.py", "--help"],
            cwd=ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for command in ("offline-check", "prepare", "login", "gh"):
            self.assertIn(command, completed.stdout)

    def test_prepare_reports_credentials_before_any_effect(self) -> None:
        head = "a" * 40

        def fake_run(command: list[str], **_kwargs: object) -> dict[str, object]:
            if command[:3] == ["git", "rev-parse", "--show-toplevel"]:
                return command_result(command, str(ROOT) + "\n")
            if command[:3] == ["git", "rev-parse", "--verify"]:
                return command_result(command, head + "\n")
            if command[:2] == ["git", "status"]:
                return command_result(command)
            if command[:3] == ["git", "remote", "get-url"]:
                return command_result(command, "https://github.com/Goldkelch/qik-vrt.git\n")
            if "auth" in command and "status" in command:
                return command_result(command, returncode=1, stderr="not logged in")
            self.fail(f"unexpected command after credential failure: {command}")

        with mock.patch.object(
            publish_runtime, "validate_offline_contract", return_value={"state": "REPOSITORY_READY"}
        ), mock.patch.object(
            publish_runtime,
            "resolve_exact_gh",
            return_value=("READY", pathlib.Path("/tmp/gh"), [], "ready"),
        ), mock.patch.object(publish_runtime, "_run", side_effect=fake_run), mock.patch.object(
            publish_runtime, "_configure_local_git_helper"
        ) as configure:
            code, receipt = publish_runtime.prepare(prepare_args())
        self.assertEqual(code, 20)
        self.assertEqual(receipt["state"], "CREDENTIAL_REQUIRED")
        self.assertFalse(receipt["publication_effect_executed"])
        self.assertFalse(receipt["credential_persisted"])
        configure.assert_not_called()

    def test_prepare_rejects_remote_identity_before_cli_or_auth(self) -> None:
        head = "a" * 40

        def fake_run(command: list[str], **_kwargs: object) -> dict[str, object]:
            if command[:3] == ["git", "rev-parse", "--show-toplevel"]:
                return command_result(command, str(ROOT) + "\n")
            if command[:3] == ["git", "rev-parse", "--verify"]:
                return command_result(command, head + "\n")
            if command[:2] == ["git", "status"]:
                return command_result(command)
            if command[:3] == ["git", "remote", "get-url"]:
                return command_result(command, "https://github.com/different/repository.git\n")
            self.fail(f"unexpected command after remote mismatch: {command}")

        with mock.patch.object(
            publish_runtime, "validate_offline_contract", return_value={"state": "REPOSITORY_READY"}
        ), mock.patch.object(publish_runtime, "_run", side_effect=fake_run), mock.patch.object(
            publish_runtime, "resolve_exact_gh"
        ) as resolver:
            code, receipt = publish_runtime.prepare(prepare_args())
        self.assertEqual(code, 20)
        self.assertEqual(receipt["state"], "REMOTE_MISMATCH")
        resolver.assert_not_called()

    def test_prepare_reports_missing_push_permission_without_git_effect(self) -> None:
        head = "a" * 40

        def fake_run(command: list[str], **_kwargs: object) -> dict[str, object]:
            if command[:3] == ["git", "rev-parse", "--show-toplevel"]:
                return command_result(command, str(ROOT) + "\n")
            if command[:3] == ["git", "rev-parse", "--verify"]:
                return command_result(command, head + "\n")
            if command[:2] == ["git", "status"]:
                return command_result(command)
            if command[:3] == ["git", "remote", "get-url"]:
                return command_result(command, "https://github.com/Goldkelch/qik-vrt.git\n")
            if "auth" in command and "status" in command:
                return command_result(command, "authenticated\n")
            if command[-2:] == ["--jq", ".login"]:
                return command_result(command, "read-only-actor\n")
            if f"repos/Goldkelch/qik-vrt" in command:
                return command_result(
                    command,
                    json.dumps({"default_branch": "main", "push": False, "visibility": "public"}) + "\n",
                )
            self.fail(f"unexpected command after permission failure: {command}")

        with mock.patch.object(
            publish_runtime, "validate_offline_contract", return_value={"state": "REPOSITORY_READY"}
        ), mock.patch.object(
            publish_runtime,
            "resolve_exact_gh",
            return_value=("READY", pathlib.Path("/tmp/gh"), [], "ready"),
        ), mock.patch.object(publish_runtime, "_run", side_effect=fake_run), mock.patch.object(
            publish_runtime, "_configure_local_git_helper"
        ) as configure:
            code, receipt = publish_runtime.prepare(prepare_args())
        self.assertEqual(code, 20)
        self.assertEqual(receipt["state"], "PERMISSION_REQUIRED")
        self.assertFalse(receipt["repository_push_permission"])
        configure.assert_not_called()

    def test_prepare_ready_binds_api_permission_base_and_git_transport(self) -> None:
        head = "a" * 40
        base_head = "b" * 40

        def fake_run(command: list[str], **_kwargs: object) -> dict[str, object]:
            if command[:3] == ["git", "rev-parse", "--show-toplevel"]:
                return command_result(command, str(ROOT) + "\n")
            if command[:3] == ["git", "rev-parse", "--verify"]:
                return command_result(command, head + "\n")
            if command[:2] == ["git", "status"]:
                return command_result(command)
            if command[:3] == ["git", "remote", "get-url"]:
                return command_result(command, "git@github.com:Goldkelch/qik-vrt.git\n")
            if "auth" in command and "status" in command:
                return command_result(command, "authenticated\n")
            if command[-2:] == ["--jq", ".login"]:
                return command_result(command, "integration-actor\n")
            if f"repos/Goldkelch/qik-vrt" in command and "git/ref" not in " ".join(command):
                return command_result(
                    command,
                    json.dumps({"default_branch": "main", "push": True, "visibility": "public"}) + "\n",
                )
            if any("git/ref/heads/main" in part for part in command):
                return command_result(command, base_head + "\n")
            if command[:3] == ["git", "ls-remote", "--exit-code"]:
                return command_result(command, f"{base_head}\trefs/heads/main\n")
            self.fail(f"unexpected command: {command}")

        helper_steps = [{"name": "helper", "returncode": 0, "stdout": "", "stderr": ""}]
        with mock.patch.object(
            publish_runtime, "validate_offline_contract", return_value={"state": "REPOSITORY_READY"}
        ), mock.patch.object(
            publish_runtime,
            "resolve_exact_gh",
            return_value=("READY", pathlib.Path("/tmp/gh"), [], "ready"),
        ), mock.patch.object(publish_runtime, "_run", side_effect=fake_run), mock.patch.object(
            publish_runtime, "_configure_local_git_helper", return_value=helper_steps
        ):
            code, receipt = publish_runtime.prepare(prepare_args())
        self.assertEqual(code, 0)
        self.assertEqual(receipt["state"], "READY")
        self.assertEqual(receipt["local_head"], head)
        self.assertEqual(receipt["remote_base_head"], base_head)
        self.assertTrue(receipt["repository_push_permission"])
        self.assertTrue(receipt["git_credential_helper_configured"])
        self.assertFalse(receipt["publication_effect_executed"])

    def test_local_git_helper_contains_exact_cli_path_but_no_secret(self) -> None:
        commands: list[list[str]] = []

        def fake_run(command: list[str], **_kwargs: object) -> dict[str, object]:
            commands.append(command)
            return command_result(command)

        token = "github" + "_pat_" + "SUPER_SECRET_VALUE_THAT_MUST_NOT_APPEAR"
        with mock.patch.dict(os.environ, {"GH_TOKEN": token}, clear=False), mock.patch.object(
            publish_runtime, "_run", side_effect=fake_run
        ):
            steps = publish_runtime._configure_local_git_helper(
                ROOT / ".qikvrt/toolchains/gh/2.96.0/linux-amd64/bin/gh"
            )
        self.assertEqual([step["returncode"] for step in steps], [0, 0])
        serialized = json.dumps(commands)
        self.assertIn("auth git-credential", serialized)
        self.assertIn("credential.https://github.com.helper", serialized)
        self.assertNotIn(token, serialized)
        self.assertNotIn("GH_TOKEN=", serialized)

    def test_redaction_removes_known_and_structured_token_material(self) -> None:
        token = "github" + "_pat_" + "THIS_IS_A_LONG_CALLER_OWNED_SECRET"
        with mock.patch.dict(os.environ, {"GH_TOKEN": token}, clear=False):
            redacted = publish_runtime.redact(
                f"GH_TOKEN={token} Authorization: bearer {token} https://x:{token}@github.com/o/r"
            )
        self.assertNotIn(token, redacted)
        self.assertGreaterEqual(redacted.count("[REDACTED]"), 2)

    def test_receipts_are_restricted_to_ignored_evidence_directory(self) -> None:
        with self.assertRaisesRegex(ValueError, "below .qikvrt/evidence"):
            publish_runtime._receipt_path("state/leaked-receipt.json")
        allowed = publish_runtime._receipt_path(
            ".qikvrt/evidence/test/GITHUB_PUBLISH_RUNTIME_RECEIPT.json"
        )
        self.assertTrue(allowed.as_posix().endswith(".qikvrt/evidence/test/GITHUB_PUBLISH_RUNTIME_RECEIPT.json"))

    def test_workflow_scopes_write_token_to_manual_effect_free_job(self) -> None:
        workflow = (ROOT / ".github/workflows/qikvrt_github_publish_runtime.yml").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertIn("if: github.event_name == 'workflow_dispatch'", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("GH_TOKEN: ${{ github.token }}", workflow)
        self.assertIn("--configure-local-git --require-clean --json", workflow)
        for forbidden in ("git push", "gh pr create", "gh pr merge", "gh release create"):
            self.assertNotIn(forbidden, workflow)
        self.assertIn("timeout-minutes:", workflow)
        self.assertIn("cancel-in-progress: true", workflow)

    def test_contract_keeps_credentials_and_consequential_effects_outside(self) -> None:
        contract = json.loads(publish_runtime.CONTRACT_PATH.read_text(encoding="utf-8"))
        auth = contract["authentication"]
        self.assertTrue(auth["credentials_are_external_capability"])
        self.assertFalse(auth["credentials_may_be_committed"])
        self.assertFalse(auth["credentials_may_be_cached"])
        self.assertFalse(auth["credentials_may_appear_in_receipts"])
        forbidden = set(contract["publication"]["forbidden_without_separate_authorization"])
        self.assertTrue(
            {"MERGE", "FORCE_PUSH", "RELEASE", "DEPLOYMENT", "ZENODO_MUTATION"}.issubset(forbidden)
        )
        self.assertFalse(contract["claim_boundaries"]["draft_pull_request_means_merged"])
        self_heal = json.loads(
            (ROOT / "state/autonomy/AUTONOMOUS_SELF_HEALING_CONTRACT_V1.json").read_text(
                encoding="utf-8"
            )
        )
        bridge = self_heal["github_publish_runtime"]
        self.assertEqual(bridge["contract_path"], publish_runtime.CONTRACT_PATH.relative_to(ROOT).as_posix())
        self.assertFalse(bridge["waiting_for_cli_or_credentials_holds_writer_lease"])
        self.assertFalse(bridge["credentials_persisted_in_repository"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
