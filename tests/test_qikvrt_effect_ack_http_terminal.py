from __future__ import annotations

import base64
import io
import importlib.util
import json
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "qikvrt_effect_ack_http_terminal.py"
_spec = importlib.util.spec_from_file_location("qikvrt_effect_ack_http_terminal", MODULE_PATH)
assert _spec and _spec.loader
terminal = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = terminal
_spec.loader.exec_module(terminal)


def sf_bytes(raw: bytes) -> str:
    return ":" + base64.b64encode(raw).decode("ascii") + ":"


def commit_field(token: str, digest: str) -> str:
    return f"v=1, mode=commit, token={sf_bytes(token.encode('ascii'))}, hash={sf_bytes(bytes.fromhex(digest))}"


class EffectAckHttpTerminalContractTests(unittest.TestCase):
    def test_repository_contract_files_parse(self) -> None:
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8"))
        policy = json.loads((ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json").read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "docs/terminal/QIKVRT_TERMINAL_FRAME_V1.schema.json").read_text(encoding="utf-8"))
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-03.xml")
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml")
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("alarms", manifest["permissions"])
        self.assertIn("http://127.0.0.1/*", manifest["host_permissions"])
        self.assertIn("http://127.0.0.1:8771", manifest["content_security_policy"]["extension_pages"])
        self.assertEqual(policy["http"]["request_field"], "Effect-Ack-Request")
        self.assertEqual(policy["http"]["response_field"], "Effect-Ack")
        self.assertEqual(policy["http"]["link_relation"], "effect-ack")
        self.assertEqual(schema["properties"]["schema"]["const"], "qikvrt_terminal_frame_v1")

    def test_firefox_source_preserves_terminal_boundaries(self) -> None:
        background = (ROOT / "browser/firefox/qikvrt-terminal/background.js").read_text(encoding="utf-8")
        content = (ROOT / "browser/firefox/qikvrt-terminal/content.js").read_text(encoding="utf-8")
        manifest = (ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8")
        self.assertIn("browser.alarms", background)
        self.assertIn("WATCHDOG_PERIOD_MINUTES = 5", background)
        self.assertIn("validated DONE prepare result required", background)
        self.assertIn("record_validated", background)
        self.assertIn("compact/full record hash mismatch", background)
        self.assertIn("Effect-Ack-Request", background)
        self.assertNotIn("X-QIKVRT-Commit-Token", background)
        self.assertNotIn("X-QIKVRT-Record-Hash", background)
        self.assertIn("getUserMedia({audio: true", content)
        self.assertIn("getUserMedia({audio: false, video:", content)
        self.assertIn("preparedRequest", content)
        self.assertIn("Prepare ≠ effect", content)
        self.assertNotIn('"service_worker"', manifest)
        self.assertNotIn("8766", background + manifest)

    def test_http_draft_defines_backward_compatible_two_phase_profile(self) -> None:
        text = (ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml").read_text(encoding="utf-8")
        for value in (
            "Effect-Ack-Request",
            "Effect-Ack",
            "effect-ack",
            "mode=prepare",
            "mode=commit",
            "single-use",
            "Backward Compatibility",
            "HTML Integration",
        ):
            self.assertIn(value, text)
        self.assertIn("MUST NOT execute the protected effect", text)

    def test_structured_request_parser_is_closed_and_exact(self) -> None:
        parsed = terminal.parse_effect_ack_request("v=1, mode=prepare")
        self.assertEqual(parsed, {"v": 1, "mode": "prepare"})
        token = "abc_DEF-123"
        digest = "00" * 32
        parsed = terminal.parse_effect_ack_request(commit_field(token, digest))
        self.assertEqual(parsed["token"], token)
        self.assertEqual(parsed["hash"], digest)
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=1, mode=prepare, token=:YQ==:")
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=1, mode=commit")
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=2, mode=prepare")


class LoopbackTerminalE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        terminal.STATE = terminal.State()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), terminal.Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None):
        data = None if body is None else json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        request_headers = dict(headers or {})
        if data is not None:
            request_headers.setdefault("Content-Type", "application/json")
        req = urllib.request.Request(self.base + path, method=method, data=data, headers=request_headers)
        try:
            response = urllib.request.urlopen(req, timeout=3)
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, response.headers, payload
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read().decode("utf-8"))
            return exc.code, exc.headers, payload

    def prepare(self, payload: dict):
        status, headers, body = self.request(
            "/terminal/prepare",
            method="POST",
            body=payload,
            headers={"Effect-Ack-Request": "v=1, mode=prepare"},
        )
        self.assertEqual(status, 200)
        self.assertIn("state=done", headers["Effect-Ack"])
        self.assertIn("token=:", headers["Effect-Ack"])
        self.assertFalse(body["ordinary_release"])
        self.assertEqual(body["external_effect"], "NONE")
        return body

    def commit_headers(self, prepared: dict) -> dict[str, str]:
        return {"Effect-Ack-Request": commit_field(prepared["commit_token"], prepared["record_hash"])}

    def test_discovery_prepare_commit_reobserve_and_replay_block(self) -> None:
        status, headers, capability = self.request("/.well-known/effect-ack")
        self.assertEqual(status, 200)
        self.assertIn('rel="effect-ack"', headers["Link"])
        self.assertEqual(capability["external_effects"], "NONE")

        payload = {
            "schema": "qikvrt_terminal_input_v1",
            "submitted_at": "2026-08-16T21:00:00Z",
            "page": "https://github.com/Goldkelch/qik-vrt/blob/main/AI",
            "text": "eins und nicht keins",
            "audio": None,
            "video": None,
        }
        prepared = self.prepare(payload)

        status, record_headers, record = self.request(prepared["record_url"])
        self.assertEqual(status, 200)
        self.assertEqual(record["state"], "EFFECT_ACK_DONE")
        self.assertEqual(record["external_effect"], "NONE")
        self.assertIn("state=done", record_headers["Effect-Ack"])
        self.assertNotIn("token=:", record_headers["Effect-Ack"])

        wrong = dict(payload)
        wrong["text"] = "different"
        status, _, rejected = self.request(
            "/terminal/commit", method="POST", body=wrong, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 409)
        self.assertIn("differs", rejected["reason"])

        status, _, committed = self.request(
            "/terminal/commit", method="POST", body=payload, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 200)
        self.assertTrue(committed["ordinary_release"])
        self.assertEqual(committed["post_effect"]["external_effect"], "NONE")
        self.assertEqual(committed["post_effect"]["text"], "eins und nicht keins")

        status, _, replay = self.request(
            "/terminal/commit", method="POST", body=payload, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 409)
        self.assertIn("used", replay["reason"])

        status, _, observed = self.request("/terminal/state")
        self.assertEqual(status, 200)
        self.assertEqual(observed["events"], 1)
        self.assertEqual(observed["last_event"]["kind"], "TERMINAL_INPUT_ACCEPTED")

    def test_expired_token_fails_closed(self) -> None:
        payload = {
            "schema": "qikvrt_terminal_input_v1",
            "submitted_at": "2026-08-16T21:00:00Z",
            "page": "AI",
            "text": "x",
            "audio": None,
            "video": None,
        }
        prepared = self.prepare(payload)
        terminal.STATE.prepared[prepared["commit_token"]].expires_at = time.time() - 1
        status, _, body = self.request(
            "/terminal/commit", method="POST", body=payload, headers=self.commit_headers(prepared)
        )
        self.assertEqual(status, 409)
        self.assertFalse(body["ordinary_release"])

    def test_missing_or_malformed_effect_ack_request_fails_closed(self) -> None:
        payload = {"schema": "qikvrt_terminal_input_v1", "text": "x"}
        status, _, body = self.request("/terminal/prepare", method="POST", body=payload)
        self.assertEqual(status, 400)
        self.assertFalse(body["ordinary_release"])
        status, _, body = self.request(
            "/terminal/commit",
            method="POST",
            body=payload,
            headers={"Effect-Ack-Request": "v=1, mode=commit"},
        )
        self.assertEqual(status, 400)
        self.assertFalse(body["ordinary_release"])

    def test_atari_boot_requires_the_exact_materialized_mlp_digest(self) -> None:
        status, _, body = self.request(
            "/qikvrt/atari/boot",
            method="POST",
            body={"schema": "qikvrt.atari-terminal-boot.v1", "mlp_sha256": "00" * 32},
        )
        self.assertEqual(status, 422)
        self.assertEqual(body["state"], "HOLD")
        self.assertEqual(body["reason"], "EXACT_MLP_BINDING_REQUIRED")

    def test_atari_boot_fails_closed_when_no_local_hatari_adapter_exists(self) -> None:
        original = terminal.shutil.which
        terminal.shutil.which = lambda name: None
        try:
            status, _, body = self.request(
                "/qikvrt/atari/boot",
                method="POST",
                body={
                    "schema": "qikvrt.atari-terminal-boot.v1",
                    "mlp_sha256": terminal.MLP_TOS_SHA256,
                },
            )
        finally:
            terminal.shutil.which = original
        self.assertEqual(status, 503)
        self.assertEqual(body["state"], "HOLD")
        self.assertEqual(body["reason"], "HATARI_UNAVAILABLE")
        self.assertFalse(body["effect_ack_done"])

    def test_atari_boot_requires_bound_rom_after_hatari_is_available(self) -> None:
        with mock.patch.object(terminal.shutil, "which", return_value="/opt/hatari"), \
             mock.patch.dict(terminal.os.environ, {"EMUTOS_ROM": ""}):
            status, _, body = self.request(
                "/qikvrt/atari/boot",
                method="POST",
                body={
                    "schema": "qikvrt.atari-terminal-boot.v1",
                    "mlp_sha256": terminal.MLP_TOS_SHA256,
                },
            )
        self.assertEqual(status, 503)
        self.assertEqual(body["state"], "HOLD")
        self.assertEqual(body["reason"], "EMUTOS_ROM_REQUIRED")
        self.assertFalse(body["effect_ack_done"])

    def test_atari_boot_starts_adapter_and_exposes_reobservable_receipt(self) -> None:
        class FakeProcess:
            def __init__(self, *_args, **kwargs) -> None:
                workdir = Path(kwargs["env"]["QIKVRT_MLP_WORKDIR"])
                drive = workdir / "drive" / "C"
                drive.mkdir(parents=True)
                request = b"QIKMLP1\r\nPROGRAM MLP\r\n"
                trace = b"Hatari v2.4.1\nPexec(0, C:\\MLP.TOS\n"
                (drive / "MLP.OPEN").write_bytes(request)
                (workdir / "hatari.log").write_bytes(trace)
                (workdir / "receipt.env").write_text(
                    "\n".join((
                        f"MLP_TOS_SHA256={terminal.MLP_TOS_SHA256}",
                        f"MLP_OPEN_SHA256={terminal.sha256(request)}",
                        f"HATARI_TRACE_SHA256={terminal.sha256(trace)}",
                        "MEGAST_VIRTUAL_EXECUTION_OBSERVED=true",
                        "PHYSICAL_MEGAST_EXECUTION=false",
                        "EFFECT_ACK_DONE=false",
                    )) + "\n",
                    encoding="utf-8",
                )
                self.stdout = io.StringIO("Hatari v2.4.1\nPexec(0, C:\\MLP.TOS\n")
                self.returncode = None

            def poll(self):
                return self.returncode

            def wait(self):
                self.returncode = 0
                return 0

        with tempfile.TemporaryDirectory() as temp:
            rom = Path(temp) / "etos512ca.img"
            rom.write_bytes(b"bound test rom")
            with mock.patch.object(terminal.shutil, "which", return_value="/opt/hatari"), \
                 mock.patch.object(terminal.subprocess, "Popen", FakeProcess), \
                 mock.patch.object(terminal, "EMUTOS_ROM_SHA256", terminal.sha256(rom.read_bytes())), \
                 mock.patch.dict(terminal.os.environ, {"EMUTOS_ROM": str(rom)}):
                status, _, accepted = self.request(
                    "/qikvrt/atari/boot",
                    method="POST",
                    body={
                        "schema": "qikvrt.atari-terminal-boot.v1",
                        "mlp_sha256": terminal.MLP_TOS_SHA256,
                    },
                )
        self.assertEqual(status, 202)
        self.assertEqual(accepted["state"], "BOOTING")
        self.assertRegex(accepted["boot_id"], r"^[0-9a-f]{32}$")
        for _ in range(30):
            status, _, observed = self.request("/qikvrt/atari/status/" + accepted["boot_id"])
            if observed["state"] != "BOOTING":
                break
            time.sleep(0.01)
        self.assertEqual(status, 200)
        self.assertEqual(observed["state"], "VIRTUAL_MEGAST_EXECUTION_OBSERVED")
        self.assertTrue(observed["virtual_megast_execution_observed"])
        self.assertFalse(observed["effect_ack_done"])
        self.assertEqual(observed["external_effect"], "NONE")

    def test_atari_status_rejects_invalid_or_unknown_boot_identifier(self) -> None:
        status, _, invalid = self.request("/qikvrt/atari/status/not-a-boot-id")
        self.assertEqual(status, 400)
        self.assertEqual(invalid["reason"], "INVALID_ATARI_BOOT_ID")
        status, _, unknown = self.request("/qikvrt/atari/status/" + "0" * 32)
        self.assertEqual(status, 404)
        self.assertEqual(unknown["reason"], "ATARI_BOOT_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
