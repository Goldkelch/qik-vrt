#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""End-to-end TCP/IP test of the GitHub-compatible QIK-VRT shim."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
sys.path.insert(0, str(REPOSITORY_ROOT))

from qikvrt_api_handler import validate_audit_chain  # noqa: E402
from qikvrt_effect_ack import EffectState  # noqa: E402
from tools.qikvrt_validate_state_run import (  # noqa: E402
    EXPECTED_WORKFLOW_PATH,
    MAX_RESPONSE_BYTES,
    StateRunValidationError,
    _NoRedirectHandler,
    fetch_run_metadata,
    parse_run_metadata,
    validate_run_binding,
)


class TcpIpEndToEndTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="qikvrt-tcpip-e2e-")
        self.state = Path(self.temporary.name) / "state"
        self.state.mkdir()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
            reservation.bind(("127.0.0.1", 0))
            self.port = reservation.getsockname()[1]
        token_material = b"qikvrt-e2e-future-scoped-token-32"
        self.token = "b64url:" + base64.urlsafe_b64encode(token_material).rstrip(b"=").decode("ascii")
        environment = os.environ.copy()
        environment.update(
            {
                "PYTHONNOUSERSITE": "1",
                "QIKVRT_API_HOST": "127.0.0.1",
                "QIKVRT_API_PORT": str(self.port),
                "QIKVRT_API_TOKEN": self.token,
                "QIKVRT_API_TOKEN_EXPIRES_UTC": "2099-01-01T00:00:00Z",
                "QIKVRT_ALLOWED_REPOSITORY": "owner/repo",
                "QIKVRT_API_PRINCIPAL": "e2e-responsible-operator",
                "QIKVRT_REPO_ROOT": str(self.state),
                "QIKVRT_RATE_LIMIT_PER_MINUTE": "10000",
            }
        )
        self.server = subprocess.Popen(
            [sys.executable, "-S", "src/qikvrt_github_api_shim.py"],
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._wait_until_ready()

    def tearDown(self) -> None:
        self.server.terminate()
        try:
            self.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.server.kill()
            self.server.wait(timeout=5)
        self.server.communicate(timeout=5)
        self.temporary.cleanup()

    def _wait_until_ready(self) -> None:
        last_error: Exception | None = None
        for _ in range(100):
            if self.server.poll() is not None:
                stdout, stderr = self.server.communicate(timeout=2)
                self.fail(
                    f"shim exited before readiness (rc={self.server.returncode})\n"
                    f"stdout={stdout}\nstderr={stderr}"
                )
            try:
                status, _ = self.request("GET", "/health", token=False)
                if status == 200:
                    return
            except Exception as exc:  # service may not have bound yet
                last_error = exc
            time.sleep(0.05)
        self.fail(f"shim did not become ready: {last_error}")

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, object] | None = None,
        *,
        token: bool = True,
    ) -> tuple[int, dict[str, object]]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        headers: dict[str, str] = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read().decode("utf-8"))

    @staticmethod
    def workflow(inputs: dict[str, object]) -> dict[str, object]:
        return {"ref": "main", "inputs": inputs}

    def test_complete_api_flow_and_all_five_effect_states(self) -> None:
        workflow = (REPOSITORY_ROOT / ".github/workflows/qikvrt_mesh_api.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(".qikvrt/api/provenance/**", workflow)
        self.assertIn("Refuse non-default workflow dispatch", workflow)
        self.assertIn("Bind current Authority default-branch head", workflow)
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", workflow)
        validator_command = "python3 -I tools/qikvrt_validate_state_run.py"
        download_action = "actions/download-artifact@"
        self.assertIn(validator_command, workflow)
        self.assertLess(workflow.index(validator_command), workflow.index(download_action))

        expected_run_id = "123456789"
        expected_sha = "a" * 40
        expected_repository = "owner/repo"
        run_metadata: dict[str, object] = {
            "id": int(expected_run_id),
            "repository": {"full_name": expected_repository},
            "path": EXPECTED_WORKFLOW_PATH + "@main",
            "head_sha": expected_sha,
            "event": "workflow_dispatch",
            "status": "completed",
            "conclusion": "success",
        }
        validate_run_binding(
            run_metadata,
            run_id=expected_run_id,
            repository=expected_repository,
            head_sha=expected_sha,
        )
        invalid_bindings: tuple[tuple[str, object], ...] = (
            ("id", 123456788),
            ("repository", {"full_name": "other/repo"}),
            ("path", ".github/workflows/other.yml"),
            ("head_sha", "b" * 40),
            ("event", "pull_request"),
            ("status", "in_progress"),
            ("conclusion", "failure"),
        )
        for field, invalid_value in invalid_bindings:
            with self.subTest(state_run_binding=field):
                invalid_metadata = dict(run_metadata)
                invalid_metadata[field] = invalid_value
                with self.assertRaises(StateRunValidationError):
                    validate_run_binding(
                        invalid_metadata,
                        run_id=expected_run_id,
                        repository=expected_repository,
                        head_sha=expected_sha,
                    )

        with self.assertRaises(StateRunValidationError):
            parse_run_metadata(b'{"id":1,"id":2}')
        with self.assertRaises(StateRunValidationError):
            parse_run_metadata(b'{"id":NaN}')
        with self.assertRaises(StateRunValidationError):
            parse_run_metadata(b" " * (MAX_RESPONSE_BYTES + 1))

        class FakeResponse:
            def __init__(self, raw: bytes, url: str) -> None:
                self.raw = raw
                self.url = url
                self.status = 200
                self.headers = {
                    "Content-Type": "application/json",
                    "Content-Length": str(len(raw)),
                }

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *_: object) -> None:
                return None

            def geturl(self) -> str:
                return self.url

            def read(self, limit: int) -> bytes:
                return self.raw[:limit]

        class FakeOpener:
            def __init__(self, raw: bytes, *, redirect: bool = False) -> None:
                self.raw = raw
                self.redirect = redirect
                self.request: urllib.request.Request | None = None

            def open(
                self, request: urllib.request.Request, *, timeout: int
            ) -> FakeResponse:
                self.request = request
                self.assert_timeout = timeout
                url = request.full_url + ("/redirected" if self.redirect else "")
                return FakeResponse(self.raw, url)

        raw_metadata = json.dumps(run_metadata, separators=(",", ":")).encode("utf-8")
        fake_opener = FakeOpener(raw_metadata)
        fetched = fetch_run_metadata(
            api_url="https://api.github.com",
            repository=expected_repository,
            run_id=expected_run_id,
            token="test-token",
            opener=fake_opener,
        )
        self.assertEqual(fetched, run_metadata)
        self.assertIsNotNone(fake_opener.request)
        self.assertEqual(
            fake_opener.request.full_url,  # type: ignore[union-attr]
            "https://api.github.com/repos/owner/repo/actions/runs/123456789",
        )
        self.assertEqual(
            fake_opener.request.get_header("Authorization"),  # type: ignore[union-attr]
            "Bearer test-token",
        )
        with self.assertRaises(StateRunValidationError):
            fetch_run_metadata(
                api_url="https://api.github.com",
                repository=expected_repository,
                run_id=expected_run_id,
                token="test-token",
                opener=FakeOpener(raw_metadata, redirect=True),
            )
        with self.assertRaises(StateRunValidationError):
            fetch_run_metadata(
                api_url="https://attacker.example",
                repository=expected_repository,
                run_id=expected_run_id,
                token="must-not-be-sent",
                server_url="https://github.com",
                opener=FakeOpener(raw_metadata),
            )
        self.assertIsNone(
            _NoRedirectHandler().redirect_request(
                urllib.request.Request("https://api.github.com/source"),
                None,
                302,
                "Found",
                {},
                "https://api.github.com/target",
            )
        )

        workflow_path = "/repos/owner/repo/actions/workflows/qikvrt_mesh_api.yml/dispatches"
        repository_path = "/repos/owner/repo/dispatches"
        health_status, health = self.request("GET", "/health", token=False)
        self.assertEqual(health_status, 200)
        self.assertTrue(health["authentication_configured"])

        unauthorized_status, unauthorized = self.request(
            "POST",
            workflow_path,
            self.workflow(
                {
                    "operation": "release_status",
                    "artifact_id": "status",
                    "dry_run": "true",
                    "request_id": "e2e-unauthorized-001",
                    "effect_accepted": "false",
                }
            ),
            token=False,
        )
        self.assertEqual(unauthorized_status, 401)
        self.assertEqual(unauthorized["status"], "BLOCK")

        payload = b"QIK-VRT TCP/IP end-to-end payload"
        payload_b64 = base64.b64encode(payload).decode("ascii")
        sha256 = hashlib.sha256(payload).hexdigest()
        ingest_inputs: dict[str, object] = {
            "operation": "ingest",
            "artifact_id": "e2e-payload",
            "payload_b64": payload_b64,
            "expected_sha256": sha256,
            "dry_run": "false",
            "request_id": "e2e-ingest-001",
            "effect_accepted": "true",
            "responsibility_owner": "e2e-responsible-operator",
        }
        ingest_status, ingest = self.request(
            "POST", workflow_path, self.workflow(ingest_inputs)
        )
        self.assertEqual(ingest_status, 202)
        self.assertEqual(ingest["status"], "ACCEPTED")
        self.assertEqual(
            ingest["handler_result"]["effect_state"],  # type: ignore[index]
            EffectState.EFFECT_ACK_DONE.value,
        )

        replay_status, replay = self.request(
            "POST", workflow_path, self.workflow(ingest_inputs)
        )
        self.assertEqual(replay_status, 202)
        self.assertTrue(replay["handler_result"]["replayed"])  # type: ignore[index]

        verify_status, verify = self.request(
            "POST",
            workflow_path,
            self.workflow(
                {
                    "operation": "verify",
                    "artifact_id": "e2e-payload",
                    "expected_sha256": sha256,
                    "dry_run": "true",
                    "request_id": "e2e-verify-001",
                    "effect_accepted": "false",
                }
            ),
        )
        self.assertEqual(verify_status, 202)
        self.assertEqual(
            verify["handler_result"]["effect_state"],  # type: ignore[index]
            EffectState.EFFECT_ACK_DONE.value,
        )
        self.assertTrue(verify["handler_result"]["sha256_match"])  # type: ignore[index]

        stage_status, stage = self.request(
            "POST",
            workflow_path,
            self.workflow(
                {
                    "operation": "stage",
                    "artifact_id": "status",
                    "dry_run": "true",
                    "request_id": "e2e-stage-001",
                    "effect_accepted": "false",
                }
            ),
        )
        self.assertEqual(stage_status, 202)
        self.assertEqual(
            stage["handler_result"]["effect_state"],  # type: ignore[index]
            EffectState.EFFECT_ACK_DONE.value,
        )

        release_status, release = self.request(
            "POST",
            workflow_path,
            self.workflow(
                {
                    "operation": "release_status",
                    "artifact_id": "status",
                    "dry_run": "true",
                    "request_id": "e2e-release-001",
                    "effect_accepted": "false",
                }
            ),
        )
        self.assertEqual(release_status, 202)
        self.assertEqual(release["status"], "CONTINUE")
        self.assertEqual(
            release["handler_result"]["effect_state"],  # type: ignore[index]
            EffectState.EFFECT_ACK_CONTINUE.value,
        )
        self.assertEqual(
            release["handler_result"]["remote_byte_exact_asset_hash"],  # type: ignore[index]
            "NOT_CONFIRMED",
        )

        nack_status, nack = self.request(
            "POST",
            workflow_path,
            self.workflow(
                {
                    "operation": "verify",
                    "artifact_id": "absent",
                    "expected_sha256": sha256,
                    "dry_run": "true",
                    "request_id": "e2e-nack-001",
                    "effect_accepted": "false",
                }
            ),
        )
        self.assertEqual(nack_status, 422)
        self.assertEqual(
            nack["handler_result"]["effect_state"],  # type: ignore[index]
            EffectState.EFFECT_NACK.value,
        )

        block_status, block = self.request(
            "POST",
            workflow_path,
            self.workflow(
                {
                    "operation": "ingest",
                    "artifact_id": "bad-hash",
                    "payload_b64": payload_b64,
                    "expected_sha256": "0" * 64,
                    "dry_run": "true",
                    "request_id": "e2e-block-001",
                    "effect_accepted": "false",
                }
            ),
        )
        self.assertEqual(block_status, 409)
        self.assertEqual(
            block["handler_result"]["effect_state"],  # type: ignore[index]
            EffectState.EFFECT_ACK_BLOCK.value,
        )

        conflicting = dict(ingest_inputs)
        conflicting["artifact_id"] = "must-not-be-written"
        conflict_status, conflict = self.request(
            "POST", workflow_path, self.workflow(conflicting)
        )
        self.assertEqual(conflict_status, 423)
        self.assertEqual(
            conflict["handler_result"]["effect_state"],  # type: ignore[index]
            EffectState.EFFECT_ACK_ISOLATE.value,
        )

        repository_status, repository = self.request(
            "POST",
            repository_path,
            {
                "event_type": "qikvrt_mesh_api",
                "client_payload": {
                    "operation": "release_status",
                    "artifact_id": "status",
                    "dry_run": "true",
                    "request_id": "e2e-repository-dispatch-001",
                    "effect_accepted": "false",
                },
            },
        )
        self.assertEqual(repository_status, 202)
        self.assertEqual(repository["status"], "CONTINUE")

        observed_states = {
            ingest["handler_result"]["effect_state"],  # type: ignore[index]
            release["handler_result"]["effect_state"],  # type: ignore[index]
            nack["handler_result"]["effect_state"],  # type: ignore[index]
            block["handler_result"]["effect_state"],  # type: ignore[index]
            conflict["handler_result"]["effect_state"],  # type: ignore[index]
        }
        self.assertEqual(observed_states, {state.value for state in EffectState})

        inbox = self.state / ".qikvrt" / "api" / "inbox"
        self.assertEqual((inbox / "e2e-payload.bin").read_bytes(), payload)
        self.assertFalse((inbox / "must-not-be-written.bin").exists())
        self.assertEqual(
            (inbox / "e2e-payload.bin.sha256").read_text(encoding="utf-8"),
            f"{sha256}  e2e-payload.bin\n",
        )
        audit = self.state / ".qikvrt" / "api" / "audit" / "events.jsonl"
        last = validate_audit_chain(audit)
        self.assertEqual(last["sequence"], 18)
        self.assertEqual(last["event"], "request_result")


if __name__ == "__main__":
    unittest.main(verbosity=2)
