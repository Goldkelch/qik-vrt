from __future__ import annotations

import importlib.util
import json
import threading
import time
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "qikvrt_effect_ack_http_terminal.py"
_spec = importlib.util.spec_from_file_location("qikvrt_effect_ack_http_terminal", MODULE_PATH)
assert _spec and _spec.loader
terminal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(terminal)


class EffectAckHttpTerminalContractTests(unittest.TestCase):
    def test_repository_contract_files_parse(self) -> None:
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8"))
        policy = json.loads((ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json").read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "docs/terminal/QIKVRT_TERMINAL_FRAME_V1.schema.json").read_text(encoding="utf-8"))
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-03.xml")
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml")
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertIn("alarms", manifest["permissions"])
        self.assertIn("http://127.0.0.1:8771/*", manifest["host_permissions"])
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
        status, headers, body = self.request("/terminal/prepare", method="POST", body=payload, headers={"Effect-Ack-Request": "v=1, mode=prepare"})
        self.assertEqual(status, 200)
        self.assertIn("state=done", headers["Effect-Ack"])
        self.assertFalse(body["ordinary_release"])
        self.assertEqual(body["external_effect"], "NONE")
        return body

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

        status, _, record = self.request(prepared["record_url"])
        self.assertEqual(status, 200)
        self.assertEqual(record["state"], "EFFECT_ACK_DONE")
        self.assertEqual(record["external_effect"], "NONE")

        wrong = dict(payload)
        wrong["text"] = "different"
        status, _, rejected = self.request(
            "/terminal/commit", method="POST", body=wrong,
            headers={"X-QIKVRT-Commit-Token": prepared["commit_token"], "X-QIKVRT-Record-Hash": prepared["record_hash"]},
        )
        self.assertEqual(status, 409)
        self.assertIn("differs", rejected["reason"])

        status, _, committed = self.request(
            "/terminal/commit", method="POST", body=payload,
            headers={"X-QIKVRT-Commit-Token": prepared["commit_token"], "X-QIKVRT-Record-Hash": prepared["record_hash"]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(committed["ordinary_release"])
        self.assertEqual(committed["post_effect"]["external_effect"], "NONE")
        self.assertEqual(committed["post_effect"]["text"], "eins und nicht keins")

        status, _, replay = self.request(
            "/terminal/commit", method="POST", body=payload,
            headers={"X-QIKVRT-Commit-Token": prepared["commit_token"], "X-QIKVRT-Record-Hash": prepared["record_hash"]},
        )
        self.assertEqual(status, 409)
        self.assertIn("used", replay["reason"])

        status, _, observed = self.request("/terminal/state")
        self.assertEqual(status, 200)
        self.assertEqual(observed["events"], 1)
        self.assertEqual(observed["last_event"]["kind"], "TERMINAL_INPUT_ACCEPTED")

    def test_expired_token_fails_closed(self) -> None:
        payload = {"schema": "qikvrt_terminal_input_v1", "submitted_at": "2026-08-16T21:00:00Z", "page": "AI", "text": "x", "audio": None, "video": None}
        prepared = self.prepare(payload)
        terminal.STATE.prepared[prepared["commit_token"]].expires_at = time.time() - 1
        status, _, body = self.request(
            "/terminal/commit", method="POST", body=payload,
            headers={"X-QIKVRT-Commit-Token": prepared["commit_token"], "X-QIKVRT-Record-Hash": prepared["record_hash"]},
        )
        self.assertEqual(status, 409)
        self.assertFalse(body["ordinary_release"])


if __name__ == "__main__":
    unittest.main()
