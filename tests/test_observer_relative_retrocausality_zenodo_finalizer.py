from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "release/observer-relative-retrocausality-current-synthesis-zenodo-v2"
    / "finalize_authorized_controls.py"
)
SPEC = importlib.util.spec_from_file_location("orr_zenodo_finalizer", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
controls = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = controls
SPEC.loader.exec_module(controls)


class ObserverRelativeRetrocausalityZenodoFinalizerTests(unittest.TestCase):
    @staticmethod
    def run_command(
        arguments: list[str],
        *,
        cwd: Path,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            arguments,
            cwd=cwd,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )

    def action(self) -> dict[str, object]:
        state = controls.release_state()
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
        source_head = completed.stdout.strip()
        authorization_id = "qikvrt-orr-zenodo-v2-test-20260814-001"
        statement = controls.publish._canonical_authorization_statement(
            authorization_id,
            controls.PUBLICATION_ID,
            state["receipt_identity"]["sha256"],
            state["metadata_sha256"],
            state["bundle_identity"]["sha256"],
        )
        return {
            "authorization_id": authorization_id,
            "nonce": "a" * 64,
            "source_head": source_head,
            "authorized_at": "2026-08-14T10:30:00Z",
            "exact_statement": statement,
        }

    def action_input(self, action: dict[str, object]) -> dict[str, object]:
        return {
            "schema": controls.INPUT_SCHEMA,
            "principal": controls.PRINCIPAL,
            **action,
        }

    def test_builds_exact_controls_without_writing(self) -> None:
        state = controls.release_state()
        action = self.action()
        authorization_raw, manifest_raw = controls.build_controls(action, state)
        authorization = json.loads(authorization_raw)
        manifest = json.loads(manifest_raw)
        self.assertEqual(authorization["source_head"], action["source_head"])
        self.assertEqual(authorization["authorization_event"]["exact_statement"], action["exact_statement"])
        self.assertEqual(authorization["principal"], controls.PRINCIPAL)
        self.assertEqual(len(authorization["uploads"]), 21)
        self.assertEqual(manifest["schema"], controls.publish.SCHEMA_V2)
        self.assertEqual(manifest["source_head"], action["source_head"])
        self.assertEqual(len(manifest["files"]), 21)

    def test_rejects_tampered_authorization_statement_before_writing(self) -> None:
        state = controls.release_state()
        action = self.action()
        action["exact_statement"] = "AUTHORIZE_EXACT_UPLOAD altered"
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "authorization.json"
            input_path.write_text(
                json.dumps(self.action_input(action)), encoding="utf-8"
            )
            with self.assertRaisesRegex(SystemExit, "exact statement differs"):
                controls.load_action(input_path, state)

    def test_accepts_canonical_external_authorization_input(self) -> None:
        state = controls.release_state()
        action = self.action()
        with tempfile.TemporaryDirectory() as temporary:
            input_path = Path(temporary) / "authorization.json"
            input_path.write_text(
                json.dumps(self.action_input(action)), encoding="utf-8"
            )
            parsed = controls.load_action(input_path, state)
        self.assertEqual(parsed, action)

    def test_release_state_has_exact_proof_bearing_files(self) -> None:
        state = controls.release_state()
        self.assertEqual(len(state["files"]), 21)
        self.assertEqual(len(state["authorization_uploads"]), 21)
        self.assertEqual(state["metadata"]["creators"], [{"name": "Lohmann, Ingolf"}])
        self.assertGreaterEqual(state["returned_at"], "2026-08-14T09:25:59Z")

    def test_write_then_committed_descendant_check_is_local_only(self) -> None:
        """Exercise the real two-commit transition in an isolated worktree."""
        state = controls.release_state()
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            isolated = temporary_root / "isolated"
            self.run_command(
                ["git", "worktree", "add", "--detach", str(isolated), "HEAD"],
                cwd=ROOT,
            )
            try:
                isolated_script = (
                    isolated
                    / "release/observer-relative-retrocausality-current-synthesis-zenodo-v2"
                    / "finalize_authorized_controls.py"
                )
                isolated_script.write_bytes(SCRIPT.read_bytes())
                self.run_command(
                    ["git", "add", isolated_script.relative_to(isolated).as_posix()],
                    cwd=isolated,
                )
                self.run_command(
                    [
                        "git",
                        "-c",
                        "user.name=Zenodo Finalizer Test",
                        "-c",
                        "user.email=zenodo-finalizer-test@example.invalid",
                        "commit",
                        "-m",
                        "test: add local Zenodo finalizer",
                    ],
                    cwd=isolated,
                )
                source_head = self.run_command(
                    ["git", "rev-parse", "HEAD"], cwd=isolated
                ).stdout.strip()
                action = self.action()
                action["source_head"] = source_head
                action["nonce"] = "b" * 64
                input_path = temporary_root / "authorization.json"
                input_path.write_text(
                    json.dumps(self.action_input(action)), encoding="utf-8"
                )
                environment = dict(os.environ)
                environment.pop("GITHUB_REPOSITORY", None)
                environment.pop("GITHUB_SHA", None)
                environment["PYTHONPATH"] = str(isolated)
                written = self.run_command(
                    [
                        sys.executable,
                        "-B",
                        str(isolated_script),
                        "--write",
                        "--authorization-input",
                        str(input_path),
                    ],
                    cwd=isolated,
                    environment=environment,
                )
                self.assertIn("PASS materialized final controls uploads=21", written.stdout)
                self.assertTrue((isolated / controls.AUTHORIZATION_PATH.relative_to(ROOT)).is_file())
                self.assertTrue((isolated / controls.MANIFEST_PATH.relative_to(ROOT)).is_file())
                self.run_command(
                    [
                        "git",
                        "add",
                        controls.AUTHORIZATION_PATH.relative_to(ROOT).as_posix(),
                        controls.MANIFEST_PATH.relative_to(ROOT).as_posix(),
                    ],
                    cwd=isolated,
                )
                self.run_command(
                    [
                        "git",
                        "-c",
                        "user.name=Zenodo Finalizer Test",
                        "-c",
                        "user.email=zenodo-finalizer-test@example.invalid",
                        "commit",
                        "-m",
                        "test: materialize final Zenodo controls",
                    ],
                    cwd=isolated,
                )
                checked = self.run_command(
                    [sys.executable, "-B", str(isolated_script), "--check"],
                    cwd=isolated,
                    environment=environment,
                )
                self.assertIn("PASS verified final controls uploads=21", checked.stdout)
            finally:
                self.run_command(
                    ["git", "worktree", "remove", "--force", str(isolated)],
                    cwd=ROOT,
                )


if __name__ == "__main__":
    unittest.main()
