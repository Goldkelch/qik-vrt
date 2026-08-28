# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import socket
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "platform" / "qikvrt-mesh-linux" / "qikvrt_meshd.c"
CORE = ROOT / "src" / "effect_ack_core.c"


def compile_daemon(output: Path, standard: str) -> None:
    subprocess.run(
        [
            "cc",
            f"-std={standard}",
            "-pedantic",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-D_POSIX_C_SOURCE=200112L",
            f"-I{ROOT / 'include'}",
            str(CORE),
            str(SOURCE),
            "-o",
            str(output),
        ],
        check=True,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def parse_response(raw: bytes) -> tuple[int, dict[str, str], dict[str, object]]:
    head, body = raw.split(b"\r\n\r\n", 1)
    lines = head.decode("ascii").split("\r\n")
    status = int(lines[0].split(" ", 2)[1])
    headers = {}
    for line in lines[1:]:
        name, value = line.split(":", 1)
        headers[name.lower()] = value.strip()
    assert int(headers["content-length"]) == len(body)
    return status, headers, json.loads(body)


class QikvrtMeshDaemonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="qikvrt-meshd-")
        cls.build = Path(cls.temporary.name)
        cls.binaries = {}
        for standard in ("c89", "c90"):
            binary = cls.build / f"qikvrt_meshd_{standard}"
            compile_daemon(binary, standard)
            cls.binaries[standard] = binary

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def start(
        self, *, max_requests: int = 1, io_timeout_ms: int = 5000
    ) -> tuple[subprocess.Popen[str], int]:
        process = subprocess.Popen(
            [
                str(self.binaries["c90"]),
                "--bind",
                "127.0.0.1",
                "--port",
                "0",
                "--max-requests",
                str(max_requests),
                "--io-timeout-ms",
                str(io_timeout_ms),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert process.stdout is not None
        ready = process.stdout.readline().strip()
        self.assertRegex(ready, r"^QIKVRT_MESHD_PORT=[0-9]+$")
        return process, int(ready.split("=", 1)[1])

    def exchange(self, port: int, request: bytes) -> tuple[int, dict[str, str], dict[str, object]]:
        chunks = []
        with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
            client.sendall(request)
            client.shutdown(socket.SHUT_WR)
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        return parse_response(b"".join(chunks))

    def finish(self, process: subprocess.Popen[str]) -> None:
        stdout, stderr = process.communicate(timeout=3)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "")
        self.assertEqual(process.returncode, 0)

    def request(self, method: str, path: str, body: bytes = b"", headers: dict[str, str] | None = None) -> bytes:
        fields = {"Host": "127.0.0.1", "Connection": "close"}
        fields.update(headers or {})
        lines = [f"{method} {path} HTTP/1.1"]
        lines.extend(f"{name}: {value}" for name, value in fields.items())
        return ("\r\n".join(lines) + "\r\n\r\n").encode("ascii") + body

    def test_c89_and_c90_manifestations_run_the_same_self_test(self) -> None:
        outputs = []
        for standard in ("c89", "c90"):
            completed = subprocess.run(
                [str(self.binaries[standard]), "--self-test"],
                check=True,
                text=True,
                capture_output=True,
            )
            payload = json.loads(completed.stdout)
            self.assertEqual(payload["self_test"], "PASS")
            self.assertEqual(payload["scope"], "VERIFIED_SNAPSHOT_CORE_ONLY")
            self.assertEqual(payload["external_effect"], "NOT_OBSERVED")
            self.assertEqual(completed.stderr, "")
            outputs.append(completed.stdout)
        self.assertEqual(outputs[0], outputs[1])

    def test_health_and_discovery_are_bounded_and_non_effecting(self) -> None:
        process, port = self.start(max_requests=2)
        status, headers, health = self.exchange(port, self.request("GET", "/healthz"))
        self.assertEqual(status, 200)
        self.assertEqual(headers["connection"], "close")
        self.assertEqual(health["mode"], "BLOCKING_NON_POLLING")
        self.assertEqual(health["external_effects"], "NONE")

        status, headers, capability = self.exchange(
            port, self.request("GET", "/.well-known/effect-ack")
        )
        self.assertEqual(status, 200)
        self.assertIn('rel="effect-ack"', headers["link"])
        self.assertEqual(capability["length"], 20)
        self.assertEqual(capability["decision_octet"], 12)
        self.assertEqual(
            capability["scope"], "UNAUTHENTICATED_DECISION_PROJECTION_ONLY"
        )
        self.assertEqual(capability["authentication"], "NOT_IMPLEMENTED")
        self.assertFalse(capability["ordinary_release"])
        self.assertEqual(capability["external_effects"], "NONE")
        self.finish(process)

    def test_exact_binary_snapshot_maps_to_bounded_core_state(self) -> None:
        complete = bytes([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 0, 1, 1, 1, 0, 0])
        process, port = self.start()
        status, _, payload = self.exchange(
            port,
            self.request(
                "POST",
                "/v1/effect-ack/evaluate",
                complete,
                {
                    "Content-Type": "application/octet-stream",
                    "Content-Length": "20",
                },
            ),
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["state"], "EFFECT_ACK_DONE")
        self.assertFalse(payload["ordinary_release"])
        self.assertTrue(payload["core_ordinary_release_candidate"])
        self.assertEqual(
            payload["scope"], "UNAUTHENTICATED_DECISION_PROJECTION_ONLY"
        )
        self.assertEqual(payload["external_effect"], "NOT_OBSERVED")
        self.finish(process)

    def test_invalid_octet_and_length_fail_closed(self) -> None:
        invalid = bytes([2]) + bytes(19)
        process, port = self.start(max_requests=2)
        status, _, payload = self.exchange(
            port,
            self.request(
                "POST",
                "/v1/effect-ack/evaluate",
                invalid,
                {"Content-Type": "application/octet-stream", "Content-Length": "20"},
            ),
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["state"], "EFFECT_ACK_BLOCK")
        self.assertFalse(payload["ordinary_release"])
        self.assertEqual(payload["scope"], "PARSE_BOUNDARY")

        status, _, payload = self.exchange(
            port,
            self.request(
                "POST",
                "/v1/effect-ack/evaluate",
                bytes(19),
                {"Content-Type": "application/octet-stream", "Content-Length": "19"},
            ),
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "BODY_LENGTH_MUST_BE_20")
        self.finish(process)

    def test_header_bound_is_enforced_without_polling(self) -> None:
        process, port = self.start()
        oversized = (
            b"GET /healthz HTTP/1.1\r\nHost: 127.0.0.1\r\nX-Fill: "
            + b"a" * 8200
            + b"\r\n\r\n"
        )
        status, _, payload = self.exchange(port, oversized)
        self.assertEqual(status, 431)
        self.assertEqual(payload["error"], "HEADER_LIMIT")
        self.assertEqual(payload["state"], "EFFECT_ACK_BLOCK")
        self.finish(process)

    def test_http_token_grammar_and_allow_header_are_explicit(self) -> None:
        process, port = self.start(max_requests=3)
        status, _, health = self.exchange(
            port,
            self.request("GET", "/healthz", headers={"X_Qikvrt": "1"}),
        )
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "OBSERVED")

        status, _, payload = self.exchange(port, self.request("G@T", "/healthz"))
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "MALFORMED_HEADERS")

        status, headers, payload = self.exchange(
            port, self.request("DELETE", "/healthz")
        )
        self.assertEqual(status, 405)
        self.assertEqual(headers["allow"], "GET, POST")
        self.assertEqual(payload["error"], "METHOD_NOT_ALLOWED")
        self.finish(process)

    def test_partial_header_hits_total_deadline_then_next_request_succeeds(self) -> None:
        process, port = self.start(max_requests=2, io_timeout_ms=200)
        chunks = []
        started = time.monotonic()
        with socket.create_connection(("127.0.0.1", port), timeout=3) as client:
            client.sendall(b"GET /healthz HTTP/1.1\r\nHost:")
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                chunks.append(chunk)
        elapsed = time.monotonic() - started
        status, _, payload = parse_response(b"".join(chunks))
        self.assertEqual(status, 408)
        self.assertEqual(payload["error"], "IO_DEADLINE_EXCEEDED")
        self.assertGreaterEqual(elapsed, 0.10)
        self.assertLess(elapsed, 2.0)

        status, _, health = self.exchange(port, self.request("GET", "/healthz"))
        self.assertEqual(status, 200)
        self.assertEqual(health["status"], "OBSERVED")
        self.finish(process)


if __name__ == "__main__":
    unittest.main()
