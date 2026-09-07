from __future__ import annotations

import base64
import hashlib
import http.client
import json
import os
import pathlib
import re
import secrets
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEPLOY = ROOT / "deploy" / "universal-terminal"


class CloudTransputerServicePlaneTests(unittest.TestCase):
    def test_fixed_mesh_path_is_single_canonical_proxy_surface(self) -> None:
        compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        nginx = (DEPLOY / "nginx.conf").read_text(encoding="utf-8")
        entrypoint = (DEPLOY / "entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn("127.0.0.1:${QIKVRT_MESH_HOST_PORT:-8080}:8080", compose)
        self.assertIn("location = /qik-vrt/mesh/v1/", nginx)
        self.assertIn("location /qik-vrt/mesh/v1/terminal/", nginx)
        self.assertIn("location /qik-vrt/mesh/v1/effect-ack/", nginx)
        self.assertIn("http://qikvrt-gateway:8080/qik-vrt/mesh/v1/", entrypoint)

    def test_service_plane_is_loopback_published_and_fail_closed(self) -> None:
        compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        for service in (
            "qikvrt-universal-terminal",
            "qikvrt-gateway",
            "qikvrt-smtpd",
            "qikvrt-snmpd",
            "qikvrt-dnsd",
            "qikvrt-sshd",
            "qikvrt-sqld",
            "qikvrt-mirror",
        ):
            self.assertIn(service + ":", compose)
        published = re.findall(r'"([^"]+)"', compose)
        host_bindings = [value for value in published if ":" in value and ("${QIKVRT_" in value)]
        self.assertTrue(host_bindings)
        self.assertTrue(all(value.startswith("127.0.0.1:") for value in host_bindings))
        self.assertIn("QIKVRT_DB_PASSWORD: ${QIKVRT_DB_PASSWORD:-}", compose)
        self.assertNotIn("0.0.0.0:${QIKVRT_", compose)

    def test_mirror_is_read_only_network_export(self) -> None:
        script = (DEPLOY / "mirror-bootstrap.sh").read_text(encoding="utf-8")
        self.assertIn("git clone --mirror", script)
        self.assertIn("git ls-remote", script)
        self.assertIn('"mutation_performed":False', script)
        self.assertIn("git daemon", script)
        self.assertNotIn("git push", script)

    def test_smtp_is_non_relaying_sink(self) -> None:
        script = (DEPLOY / "qikvrt_smtpd.py").read_text(encoding="utf-8")
        self.assertIn('"relay_performed": False', script)
        self.assertNotIn("smtplib", script)
        self.assertIn("MAX_MESSAGE_BYTES", script)

    def test_c90_m68000_contract_is_explicit(self) -> None:
        dockerfile = (DEPLOY / "Dockerfile").read_text(encoding="utf-8")
        source = (DEPLOY / "qikvrt_ip_bootstrap.c").read_text(encoding="utf-8")
        self.assertIn("gcc-m68k-linux-gnu", dockerfile)
        self.assertIn("-m68000 -std=c90 -pedantic-errors", dockerfile)
        self.assertIn("qikvrt_ip_bootstrap.o", dockerfile)
        self.assertIn("Strict ISO C90 source", source)
        self.assertNotIn("//", source)

    def test_profile_packaging_preserves_workdir_for_runtime_permissions(self) -> None:
        """Execute the real RUN body: an unscoped cd must fail, not pass a grep."""
        dockerfile = (DEPLOY / "Dockerfile").read_text(encoding="utf-8")
        blocks = [
            block for block in dockerfile.split("\n\n")
            if block.startswith("RUN mkdir -p /opt/qikvrt/runtime/bootstrap-profile/")
        ]
        self.assertEqual(len(blocks), 1, "locate the actual profile RUN instruction")
        with tempfile.TemporaryDirectory(prefix="qikvrt-profile-") as temporary:
            base = pathlib.Path(temporary)
            repo = base / "repo"
            extension = repo / "browser/firefox/qikvrt-terminal"
            extension.mkdir(parents=True)
            (extension / "manifest.json").write_text('{"manifest_version": 2}\n', encoding="utf-8")
            deploy = repo / "deploy/universal-terminal"
            deploy.mkdir(parents=True)
            scripts = [
                deploy / name for name in (
                    "entrypoint.sh", "runtime-health.sh", "service-entrypoint.sh",
                    "mirror-bootstrap.sh", "qikvrt_smtpd.py",
                )
            ]
            binaries = base / "bin"
            binaries.mkdir()
            scripts.append(binaries / "qikvrt-ip-bootstrap")
            for script in scripts:
                script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                script.chmod(0o644)
            # Map only absolute image paths into the fixture; preserve every
            # relative path and all shell control flow from the Dockerfile.
            command = blocks[0][len("RUN "):]
            for original, replacement in (
                ("/opt/qikvrt", repo), ("/var/lib/qikvrt", base / "data"),
                ("/usr/local/bin", binaries),
            ):
                command = command.replace(original, str(replacement))
            result = subprocess.run(
                ["/bin/sh", "-eu", "-c", command], cwd=repo, text=True,
                capture_output=True, timeout=15, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for script in scripts:
                self.assertTrue(script.stat().st_mode & stat.S_IXUSR, str(script))
            profile = repo / "runtime/bootstrap-profile"
            with zipfile.ZipFile(profile / "extensions/qikvrt-ai-terminal@goldkelch.local.xpi") as archive:
                self.assertEqual(archive.namelist(), ["manifest.json"])
            self.assertIn("browser.startup.homepage", (profile / "user.js").read_text(encoding="utf-8"))

    def test_effect_ack_is_reachable_only_through_explicit_proxy_or_terminal(self) -> None:
        entrypoint = (DEPLOY / "entrypoint.sh").read_text(encoding="utf-8")
        compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn('HTTP_HOST="${QIKVRT_HTTP_HOST:-127.0.0.1}"', entrypoint)
        self.assertIn("QIKVRT_HTTP_HOST: 127.0.0.1", compose)
        self.assertNotIn("QIKVRT_HTTP_HOST: 0.0.0.0", compose)
        self.assertNotIn('\":8771\"', compose)

    def test_sql_password_has_no_repository_default(self) -> None:
        compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        service = (DEPLOY / "service-entrypoint.sh").read_text(encoding="utf-8")
        self.assertIn("QIKVRT_DB_PASSWORD: ${QIKVRT_DB_PASSWORD:-}", compose)
        self.assertIn("QIKVRT_DB_PASSWORD is required for sqld", service)
        self.assertIn('if [ -z "$DB_PASSWORD" ]', service)
        self.assertNotIn("postgres:postgres", compose)


    def test_gateway_shares_namespace_without_exporting_reference_backend(self) -> None:
        compose = (DEPLOY / "compose.yaml").read_text(encoding="utf-8")
        nginx = (DEPLOY / "nginx.conf").read_text(encoding="utf-8")
        gateway = compose.split("\n  qikvrt-gateway:\n", 1)[1].split("\n  qikvrt-smtpd:", 1)[0]
        self.assertIn("network_mode: service:qikvrt-universal-terminal", gateway)
        self.assertNotIn("\n    ports:", gateway)
        self.assertIn("proxy_pass http://127.0.0.1:8771/;", nginx)
        self.assertIn("proxy_pass http://127.0.0.1:6080/;", nginx)
        self.assertNotIn('"8771"', compose)

    def test_reference_backend_still_rejects_non_loopback_bind(self) -> None:
        result = subprocess.run(
            [sys.executable, "-B", "-S", str(ROOT / "src/qikvrt_effect_ack_http_terminal.py"),
             "--host", "0.0.0.0"], text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reference terminal bridge is loopback-only", result.stderr)

    def test_real_runtime_producer_and_health_consumer_agree_and_fail_closed(self) -> None:
        def python_body(path: pathlib.Path) -> str:
            text = path.read_text(encoding="utf-8")
            self.assertEqual(text.count("<<'PY'\n"), 1)
            return text.split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]

        producer = python_body(DEPLOY / "entrypoint.sh")
        consumer = python_body(DEPLOY / "runtime-health.sh")
        with tempfile.TemporaryDirectory(prefix="qikvrt-health-") as temporary:
            state = pathlib.Path(temporary) / "runtime.json"
            generated = subprocess.run(
                [sys.executable, "-B", "-S", "-", str(state), "fixture-terminal",
                 temporary, "about:blank", "6080", "127.0.0.1", "8771"],
                input=producer, text=True, capture_output=True, timeout=10, check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)
            valid = json.loads(state.read_text(encoding="utf-8"))
            cases = [
                ({}, True),
                ({"schema": "qikvrt_universal_terminal_runtime_state_v1"}, False),
                ({"effect_ack_host": "0.0.0.0"}, False),
                ({"external_effect_claimed": True}, False),
                ({"pass": True}, False),
                ({"final_pass": True}, False),
                ({"effect_ack_done": True}, False),
            ]
            for mutation, accepted in cases:
                with self.subTest(mutation=mutation):
                    state.write_text(json.dumps(dict(valid, **mutation)), encoding="utf-8")
                    checked = subprocess.run(
                        [sys.executable, "-B", "-S", "-", str(state)],
                        input=consumer, text=True, capture_output=True, timeout=10, check=False,
                    )
                    self.assertEqual(checked.returncode == 0, accepted, checked.stderr)

    def test_sql_without_password_fails_before_initialization(self) -> None:
        environment = dict(os.environ, QIKVRT_SERVICE_MODE="sqld", QIKVRT_DB_PASSWORD="")
        result = subprocess.run(
            ["/bin/sh", str(DEPLOY / "service-entrypoint.sh")],
            env=environment, text=True, capture_output=True, timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 64, result.stdout + result.stderr)
        self.assertIn("QIKVRT_DB_PASSWORD is required for sqld", result.stderr)



@unittest.skipUnless(os.environ.get("QIKVRT_SERVICE_PLANE_LIVE") == "1", "requires the real CI service plane")
class LiveServicePlaneTests(unittest.TestCase):
    """These tests run only after the exact image is started by the dedicated CI."""

    def test_mesh_websocket_carries_real_framebuffer(self) -> None:
        def exact(reader, length):
            data = reader.read(length)
            if data is None or len(data) != length:
                raise AssertionError("truncated WebSocket/RFB stream")
            return data

        with socket.create_connection(("127.0.0.1", 8080), timeout=15) as sock:
            sock.settimeout(15)
            key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
            request = (
                "GET /qik-vrt/mesh/v1/terminal/websockify HTTP/1.1\r\n"
                "Host: 127.0.0.1:8080\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n"
                "Sec-WebSocket-Protocol: binary\r\n\r\n"
            )
            sock.sendall(request.encode("ascii"))
            with sock.makefile("rb") as reader:
                self.assertIn(b" 101 ", reader.readline(4096))
                headers = {}
                for _ in range(64):
                    line = reader.readline(4096)
                    if line == b"\r\n":
                        break
                    self.assertTrue(line and b":" in line, line)
                    name, value = line.split(b":", 1)
                    headers[name.lower()] = value.strip()
                else:
                    self.fail("unbounded upgrade headers")
                accept = base64.b64encode(hashlib.sha1(
                    (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
                ).digest())
                self.assertEqual(headers[b"sec-websocket-accept"], accept)
                self.assertEqual(headers.get(b"sec-websocket-protocol"), b"binary")
                pending = bytearray()

                def send(payload, opcode=2):
                    self.assertLess(len(payload), 126)
                    mask = secrets.token_bytes(4)
                    sock.sendall(bytes([0x80 | opcode, 0x80 | len(payload)]) + mask +
                                 bytes(value ^ mask[i % 4] for i, value in enumerate(payload)))

                def receive(length):
                    while len(pending) < length:
                        first, second = exact(reader, 2)
                        self.assertFalse(second & 0x80, "server frames must not be masked")
                        count = second & 0x7f
                        if count == 126:
                            count = struct.unpack("!H", exact(reader, 2))[0]
                        elif count == 127:
                            count = struct.unpack("!Q", exact(reader, 8))[0]
                        self.assertLessEqual(count, 16 * 1024 * 1024)
                        payload = exact(reader, count)
                        opcode = first & 0x0f
                        if opcode == 9:
                            send(payload, 10)
                            continue
                        self.assertIn(opcode, (0, 2), "unexpected text/close frame")
                        pending.extend(payload)
                    value = bytes(pending[:length])
                    del pending[:length]
                    return value

                self.assertEqual(receive(12), b"RFB 003.008\n")
                send(b"RFB 003.008\n")
                types = receive(receive(1)[0])
                self.assertIn(1, types, "this CI-only loopback VNC fixture expects no password")
                send(b"\x01")
                self.assertEqual(receive(4), b"\0\0\0\0")
                send(b"\x01")  # shared ClientInit
                init = receive(24)
                width, height = struct.unpack("!HH", init[:4])
                self.assertGreater(width, 0)
                self.assertGreater(height, 0)
                self.assertLessEqual(width * height, 4_000_000)
                name_length = struct.unpack("!I", init[20:24])[0]
                self.assertLessEqual(name_length, 4096)
                desktop_name = receive(name_length).decode("utf-8", "replace")
                # Request a known pixel format and only raw rectangles.
                send(b"\0\0\0\0" + struct.pack("!BBBBHHHBBB3x", 32, 24, 0, 1, 255, 255, 255, 16, 8, 0))
                send(struct.pack("!BBHi", 2, 0, 1, 0))
                send(struct.pack("!BBHH", 5, 0, 10, 10))  # harmless pointer input through the same proxy
                send(struct.pack("!BBHHHH", 3, 0, 0, 0, width, height))
                update = receive(4)
                self.assertEqual(update[0], 0)
                rectangles = struct.unpack("!H", update[2:])[0]
                self.assertGreater(rectangles, 0)
                pixels = bytearray(width * height * 3)
                observed_pixels = 0
                for _ in range(rectangles):
                    x, y, w, h, encoding = struct.unpack("!HHHHi", receive(12))
                    self.assertEqual(encoding, 0)
                    self.assertLessEqual(x + w, width)
                    self.assertLessEqual(y + h, height)
                    raw = receive(w * h * 4)
                    observed_pixels += w * h
                    rgb = bytearray(w * h * 3)
                    rgb[0::3], rgb[1::3], rgb[2::3] = raw[2::4], raw[1::4], raw[0::4]
                    for row in range(h):
                        offset = ((y + row) * width + x) * 3
                        pixels[offset:offset + w * 3] = rgb[row * w * 3:(row + 1) * w * 3]
                self.assertEqual(observed_pixels, width * height, "initial full-frame readback is required")

                def chunk(kind, data):
                    return struct.pack("!I", len(data)) + kind + data + struct.pack("!I", zlib.crc32(kind + data))

                scanlines = b"".join(b"\0" + pixels[row * width * 3:(row + 1) * width * 3] for row in range(height))
                png = (b"\x89PNG\r\n\x1a\n" +
                       chunk(b"IHDR", struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
                       chunk(b"IDAT", zlib.compress(scanlines)) + chunk(b"IEND", b""))
                evidence = pathlib.Path(os.environ["QIKVRT_SERVICE_EVIDENCE_DIR"])
                evidence.mkdir(parents=True, exist_ok=True)
                (evidence / "firefox-framebuffer.png").write_bytes(png)
                (evidence / "framebuffer.json").write_text(json.dumps({
                    "width": width, "height": height, "desktop_name": desktop_name,
                    "sha256": hashlib.sha256(png).hexdigest(),
                    "scope": "CI_PROXY_RFB_READBACK", "browser_javascript_ui_tested": False,
                }, indent=2) + "\n", encoding="utf-8")

    def test_effect_ack_exact_commit_and_authoritative_local_readback(self) -> None:
        prefix = "/qik-vrt/mesh/v1/effect-ack"

        def call(path, body=None, binding=None):
            connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=10)
            headers = {}
            payload = None
            if body is not None:
                payload = json.dumps(body).encode("utf-8")
                headers["Content-Type"] = "application/json"
                headers["Effect-Ack-Request"] = binding
            try:
                connection.request("POST" if body is not None else "GET", prefix + path, payload, headers)
                response = connection.getresponse()
                return response.status, json.loads(response.read())
            finally:
                connection.close()

        status, before = call("/terminal/state")
        self.assertEqual(status, 200)
        self.assertEqual(before["repository_head"], os.environ["QIKVRT_HEAD"])
        self.assertEqual(before["repository_tree"], os.environ["QIKVRT_TREE"])
        body = {"schema": "qikvrt_terminal_input_v1", "text": "CI exact-bound local input",
                "head": os.environ["QIKVRT_HEAD"], "tree": os.environ["QIKVRT_TREE"]}
        status, prepared = call("/terminal/prepare", body, "v=1, mode=prepare")
        self.assertEqual(status, 200)
        self.assertIs(prepared["ordinary_release"], False)
        self.assertEqual(call("/terminal/state")[1]["events"], before["events"])
        token = base64.b64encode(prepared["commit_token"].encode("ascii")).decode("ascii")
        digest = base64.b64encode(bytes.fromhex(prepared["record_hash"])).decode("ascii")
        binding = f"v=1, mode=commit, token=:{token}:, hash=:{digest}:"
        status, rejected = call("/terminal/commit", dict(body, text="different input"), binding)
        self.assertEqual(status, 409)
        self.assertIs(rejected["ordinary_release"], False)
        status, committed = call("/terminal/commit", body, binding)
        self.assertEqual(status, 200)
        self.assertEqual(committed["post_effect"]["external_effect"], "NONE")
        self.assertIs(committed["ordinary_release"], True)
        self.assertEqual(call("/terminal/commit", body, binding)[0], 409)
        status, after = call("/terminal/state")
        self.assertEqual(status, 200)
        self.assertEqual(after["events"], before["events"] + 1)
        self.assertEqual(after["last_event"], committed["post_effect"])
        evidence = pathlib.Path(os.environ["QIKVRT_SERVICE_EVIDENCE_DIR"])
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "effect-ack-local-readback.json").write_text(json.dumps({
            "scope": "CI_LOCAL_TERMINAL_INPUT_ONLY", "before": before, "after": after,
            "external_authority_effect": False, "global_effect_ack_done": False,
        }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
