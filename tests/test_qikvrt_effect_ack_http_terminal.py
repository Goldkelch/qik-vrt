from __future__ import annotations

import base64
import importlib.util
import json
import socket
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

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "src" / "qikvrt_effect_ack_http_terminal.py"
_spec = importlib.util.spec_from_file_location("qikvrt_effect_ack_http_terminal", MODULE_PATH)
assert _spec and _spec.loader
terminal = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = terminal
_spec.loader.exec_module(terminal)


def sf_bytes(raw: bytes) -> str:
    return ":" + base64.b64encode(raw).decode("ascii") + ":"


def commit_field(token: str, digest: str, *, version: int = 1) -> str:
    return f"v={version}, mode=commit, token={sf_bytes(token.encode('ascii'))}, hash={sf_bytes(bytes.fromhex(digest))}"


class EffectAckHttpTerminalContractTests(unittest.TestCase):
    def test_repository_contract_files_parse(self) -> None:
        manifest = json.loads((ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8"))
        policy = json.loads((ROOT / "policy/QIKVRT_EFFECT_ACK_HTTP_TERMINAL_V1.json").read_text(encoding="utf-8"))
        peer_policy = json.loads((ROOT / "policy/QIKVRT_HTTP_TERMINAL_PEER_V2.json").read_text(encoding="utf-8"))
        schema = json.loads((ROOT / "docs/terminal/QIKVRT_TERMINAL_FRAME_V1.schema.json").read_text(encoding="utf-8"))
        peer_schema = json.loads((ROOT / "docs/terminal/QIKVRT_HTTP_TERMINAL_PEER_V2.schema.json").read_text(encoding="utf-8"))
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-03.xml")
        ET.parse(ROOT / "external/ietf/draft-lohmann-qikvrt-effect-ack-http-00.xml")
        self.assertEqual(manifest["manifest_version"], 3)
        self.assertNotIn("alarms", manifest["permissions"])
        self.assertIn("http://127.0.0.1:8771/*", manifest["host_permissions"])
        self.assertEqual(policy["http"]["request_field"], "Effect-Ack-Request")
        self.assertEqual(policy["http"]["response_field"], "Effect-Ack")
        self.assertEqual(policy["http"]["link_relation"], "effect-ack")
        self.assertEqual(peer_policy["policy_id"], terminal.PEER_POLICY_ID)
        self.assertEqual(peer_policy["policy_projection"], terminal.PEER_POLICY_PROJECTION)
        self.assertEqual(peer_policy["policy_sha256"], terminal.PEER_POLICY_SHA256)
        self.assertEqual(peer_policy["transport"]["scope"], "LOOPBACK_HTTP_ONLY")
        self.assertEqual(peer_policy["boundaries"]["tls_mtls"], "OPEN")
        self.assertEqual(peer_policy["deterministic_serialization"]["terminal_input_schema"], "qikvrt_terminal_input_v2")
        self.assertIn("floating_point", peer_policy["deterministic_serialization"]["forbidden_terminal_input_values"])
        self.assertEqual(schema["properties"]["schema"]["const"], "qikvrt_terminal_frame_v1")
        self.assertEqual(peer_schema["properties"]["schema"]["const"], "qikvrt_terminal_peer_request_v2")
        self.assertEqual(peer_schema["$defs"]["terminal_input"]["properties"]["schema"]["const"], "qikvrt_terminal_input_v2")
        self.assertEqual(peer_schema["$defs"]["media_descriptor"]["additionalProperties"], False)
        self.assertEqual(peer_schema["x-runtime-canonicalization"]["floating_point"], "FORBIDDEN")
        self.assertEqual(
            peer_schema["x-runtime-canonicalization"]["sort_object_keys"],
            "UNICODE_SCALAR_VALUE_LEXICOGRAPHIC_ASCENDING",
        )
        self.assertEqual(peer_schema["x-required-http-headers"]["Idempotency-Key"], "$request_id")

    def test_firefox_source_preserves_terminal_boundaries(self) -> None:
        background = (ROOT / "browser/firefox/qikvrt-terminal/background.js").read_text(encoding="utf-8")
        content = (ROOT / "browser/firefox/qikvrt-terminal/content.js").read_text(encoding="utf-8")
        manifest = (ROOT / "browser/firefox/qikvrt-terminal/manifest.json").read_text(encoding="utf-8")
        self.assertNotIn("browser.alarms", background)
        self.assertNotIn("periodInMinutes", background)
        self.assertNotIn("setInterval", background)
        self.assertNotIn("setTimeout", background)
        self.assertIn("Observation advances only from an explicit UI/client message", background)
        self.assertIn("persistObservedFrame", background)
        self.assertIn("validated DONE prepare result required", background)
        self.assertIn("record_validated", background)
        self.assertIn("compact/full record hash mismatch", background)
        self.assertIn("Effect-Ack-Request", background)
        self.assertNotIn("X-QIKVRT-Commit-Token", background)
        self.assertNotIn("X-QIKVRT-Record-Hash", background)
        self.assertIn("getUserMedia({audio: true", content)
        self.assertIn("getUserMedia({audio: false, video:", content)
        self.assertIn("preparedRequest", content)
        self.assertIn("explicit Observe required", content)
        self.assertNotIn("applyPreferences().then(observe)", content)
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
        self.assertEqual(terminal.parse_effect_ack_request("v=2, mode=prepare"), {"v": 2, "mode": "prepare"})
        with self.assertRaises(ValueError):
            terminal.parse_effect_ack_request("v=3, mode=prepare")


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


class DurablePeerTerminalE2ETests(unittest.TestCase):
    """Two local HTTP daemons with persistent V2 prepare/commit/replay state."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.nodes: dict[str, tuple[ThreadingHTTPServer, threading.Thread, terminal.DurableState]] = {}
        self.node_paths = {
            "a": Path(self.temporary.name) / "node-a",
            "b": Path(self.temporary.name) / "node-b",
        }
        self.start_node("a", node_id="peer-a", endpoint_id="terminal-a")
        self.start_node("b", node_id="peer-b", endpoint_id="terminal-b")

    def tearDown(self) -> None:
        for name in tuple(self.nodes):
            self.stop_node(name)
        self.temporary.cleanup()

    def start_node(self, name: str, *, node_id: str, endpoint_id: str) -> None:
        state = terminal.DurableState(self.node_paths[name], node_id=node_id, endpoint_id=endpoint_id)
        server = ThreadingHTTPServer(("127.0.0.1", 0), terminal.Handler)
        server.qikvrt_state = state
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.nodes[name] = (server, thread, state)

    def stop_node(self, name: str) -> None:
        server, thread, state = self.nodes.pop(name)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        state.close()

    def restart_node_b(self) -> None:
        self.stop_node("b")
        self.start_node("b", node_id="peer-b", endpoint_id="terminal-b")

    def base(self, name: str) -> str:
        return f"http://127.0.0.1:{self.nodes[name][0].server_port}"

    def request(self, name: str, path: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None):
        data = None if body is None else json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        request_headers = dict(headers or {})
        if data is not None:
            request_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(self.base(name) + path, method=method, data=data, headers=request_headers)
        try:
            response = urllib.request.urlopen(request, timeout=3)
            return response.status, response.headers, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers, json.loads(exc.read().decode("utf-8"))

    def raw_request(
        self,
        name: str,
        path: str,
        *,
        body: dict | None = None,
        headers: list[tuple[str, str]],
        raw_body: bytes | None = None,
    ) -> tuple[int, dict]:
        """Send raw fields so duplicate HTTP header handling is observable."""

        if raw_body is None:
            assert body is not None
            data = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
        else:
            data = raw_body
        values = [("Host", "127.0.0.1"), ("Connection", "close"), *headers]
        if not any(key.lower() == "content-length" for key, _ in values):
            values.append(("Content-Length", str(len(data))))
        raw = [f"POST {path} HTTP/1.1\r\n".encode("ascii")]
        raw.extend(f"{key}: {value}\r\n".encode("ascii") for key, value in values)
        raw.append(b"\r\n")
        raw.append(data)
        response = b""
        with socket.create_connection(("127.0.0.1", self.nodes[name][0].server_port), timeout=3) as client:
            client.sendall(b"".join(raw))
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                response += chunk
        head, raw_body = response.split(b"\r\n\r\n", 1)
        status_line = head.split(b"\r\n", 1)[0].split()
        return int(status_line[1]), json.loads(raw_body.decode("utf-8"))

    @staticmethod
    def envelope(*, request_id: str, path: str, text: str = "deterministic terminal input") -> dict:
        return {
            "schema": "qikvrt_terminal_peer_request_v2",
            "request_id": request_id,
            "source_node_id": "peer-a",
            "target_node_id": "peer-b",
            "target_endpoint_id": "terminal-b",
            "effective_method": "POST",
            "effective_target": path,
            "policy_id": terminal.PEER_POLICY_ID,
            "policy_sha256": terminal.PEER_POLICY_SHA256,
            "responsibility_owner": "LOCAL_INTERACTIVE_USER",
            "terminal_input": {
                "schema": "qikvrt_terminal_input_v2",
                "submitted_at": "2026-08-28T12:00:00Z",
                "page": "https://example.invalid/terminal",
                "text": text,
                "audio": None,
                "video": None,
            },
        }

    @staticmethod
    def media_descriptor(kind: str, content_type: str, raw: bytes) -> dict:
        return {
            "schema": "qikvrt_terminal_media_descriptor_v1",
            "kind": kind,
            "content_type": content_type,
            "byte_length": len(raw),
            "sha256": "sha256:" + terminal.sha256(raw),
            "base64": base64.b64encode(raw).decode("ascii"),
        }

    @staticmethod
    def headers(envelope: dict, *, mode: str, token: str | None = None, digest: str | None = None) -> dict[str, str]:
        result = {
            "Idempotency-Key": envelope["request_id"],
            "X-QIKVRT-Source-Node": envelope["source_node_id"],
            "X-QIKVRT-Target-Node": envelope["target_node_id"],
            "X-QIKVRT-Target-Endpoint": envelope["target_endpoint_id"],
        }
        if mode == "prepare":
            result["Effect-Ack-Request"] = "v=2, mode=prepare"
        else:
            assert token is not None and digest is not None
            result["Effect-Ack-Request"] = commit_field(token, digest, version=2)
        return result

    def test_two_daemon_restart_replay_is_idempotent_and_target_bound(self) -> None:
        for node, expected in (("a", "peer-a"), ("b", "peer-b")):
            status, _, capability = self.request(node, "/.well-known/effect-ack")
            self.assertEqual(status, 200)
            self.assertEqual(capability["versions"], [1, 2])
            self.assertEqual(capability["peer_profile"]["node_id"], expected)
            self.assertEqual(capability["peer_profile"]["transport_scope"], "LOOPBACK_HTTP_ONLY")
            self.assertEqual(capability["peer_profile"]["tls_mtls"], "OPEN")

        prepare = self.envelope(request_id="receipt-001", path="/terminal/prepare")
        status, _, wrong_target = self.request(
            "a", "/terminal/prepare", method="POST", body=prepare, headers=self.headers(prepare, mode="prepare")
        )
        self.assertEqual(status, 400)
        self.assertIn("not this node endpoint", wrong_target["reason"])
        self.assertEqual(self.nodes["a"][2].events, [])

        status, headers, prepared = self.request(
            "b", "/terminal/prepare", method="POST", body=prepare, headers=self.headers(prepare, mode="prepare")
        )
        self.assertEqual(status, 200)
        self.assertIn("v=2", headers["Effect-Ack"])
        self.assertFalse(prepared["ordinary_release"])
        self.assertEqual(prepared["idempotency_key"], "receipt-001")
        self.assertEqual(self.nodes["b"][2].sequence, 2)

        status, record_headers, prepared_record = self.request("b", prepared["record_url"])
        self.assertEqual(status, 200)
        self.assertIn("v=2", record_headers["Effect-Ack"])
        self.assertEqual(prepared_record["wire_version"], 2)
        self.assertEqual(prepared_record["node_binding"]["target_node_id"], "peer-b")

        self.restart_node_b()
        self.assertIn(prepared["commit_token"], self.nodes["b"][2].prepared)

        commit = self.envelope(request_id="receipt-001", path="/terminal/commit")
        status, headers, committed = self.request(
            "b",
            "/terminal/commit",
            method="POST",
            body=commit,
            headers=self.headers(
                commit,
                mode="commit",
                token=prepared["commit_token"],
                digest=prepared["record_hash"],
            ),
        )
        self.assertEqual(status, 200)
        self.assertIn("v=2", headers["Effect-Ack"])
        self.assertTrue(committed["ordinary_release"])
        self.assertEqual(committed["post_effect"]["external_effect"], "NONE")
        self.assertEqual(self.nodes["b"][2].events, [committed["post_effect"]])

        self.restart_node_b()
        status, _, replay = self.request(
            "b",
            "/terminal/commit",
            method="POST",
            body=commit,
            headers=self.headers(
                commit,
                mode="commit",
                token=prepared["commit_token"],
                digest=prepared["record_hash"],
            ),
        )
        self.assertEqual(status, 200)
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["post_effect"], committed["post_effect"])
        self.assertEqual(len(self.nodes["b"][2].events), 1)

        changed = self.envelope(request_id="receipt-001", path="/terminal/commit", text="different exact bytes")
        status, _, conflict = self.request(
            "b",
            "/terminal/commit",
            method="POST",
            body=changed,
            headers=self.headers(
                changed,
                mode="commit",
                token=prepared["commit_token"],
                digest=prepared["record_hash"],
            ),
        )
        self.assertEqual(status, 409)
        self.assertFalse(conflict["ordinary_release"])
        self.assertIn("Idempotency-Key", conflict["reason"])
        self.assertEqual(len(self.nodes["b"][2].events), 1)

    def test_peer_headers_are_exactly_bound_to_the_envelope(self) -> None:
        prepare = self.envelope(request_id="receipt-002", path="/terminal/prepare")
        headers = self.headers(prepare, mode="prepare")
        headers["X-QIKVRT-Source-Node"] = "other-peer"
        status, _, rejected = self.request("b", "/terminal/prepare", method="POST", body=prepare, headers=headers)
        self.assertEqual(status, 400)
        self.assertFalse(rejected["ordinary_release"])
        self.assertIn("Source-Node", rejected["reason"])
        self.assertEqual(self.nodes["b"][2].events, [])

    def test_v2_closed_canonical_input_accepts_typed_media_and_rejects_ambiguous_values(self) -> None:
        self.assertEqual(
            terminal.canonical_json_v2({"z": "a\né", "a": "\x01", "count": 1, "flag": True, "nil": None}),
            b'{"a":"\\u0001","count":1,"flag":true,"nil":null,"z":"a\\n\xc3\xa9"}',
        )
        with self.assertRaisesRegex(ValueError, "closed canonical JSON domain"):
            terminal.canonical_json_v2({"not_permitted": 1.0})
        prepare = self.envelope(request_id="receipt-closed-001", path="/terminal/prepare")
        prepare["terminal_input"]["audio"] = self.media_descriptor("audio", "audio/webm", b"audio-bytes")
        prepare["terminal_input"]["video"] = self.media_descriptor("video_snapshot", "image/webp", b"image-bytes")
        reordered = dict(prepare["terminal_input"])
        reordered["audio"] = dict(reversed(list(prepare["terminal_input"]["audio"].items())))
        self.assertEqual(terminal.canonical_json_v2(prepare["terminal_input"]), terminal.canonical_json_v2(reordered))
        self.assertEqual(
            terminal.sha256(terminal.canonical_json_v2(prepare["terminal_input"])),
            terminal.sha256(terminal.canonical_json_v2(reordered)),
        )
        status, _, accepted = self.request(
            "b", "/terminal/prepare", method="POST", body=prepare, headers=self.headers(prepare, mode="prepare")
        )
        self.assertEqual(status, 200)
        self.assertFalse(accepted["ordinary_release"])

        cases: list[tuple[str, dict, str]] = []
        float_length = json.loads(json.dumps(self.envelope(request_id="receipt-closed-002", path="/terminal/prepare")))
        float_length["terminal_input"]["audio"] = self.media_descriptor("audio", "audio/webm", b"a")
        float_length["terminal_input"]["audio"]["byte_length"] = 1.0
        cases.append(("floating point length", float_length, "integer"))
        noncanonical_base64 = json.loads(json.dumps(self.envelope(request_id="receipt-closed-003", path="/terminal/prepare")))
        noncanonical_base64["terminal_input"]["audio"] = self.media_descriptor("audio", "audio/webm", b"a")
        noncanonical_base64["terminal_input"]["audio"]["base64"] = "YQ"
        cases.append(("unpadded base64", noncanonical_base64, "base64"))
        digest_mismatch = json.loads(json.dumps(self.envelope(request_id="receipt-closed-004", path="/terminal/prepare")))
        digest_mismatch["terminal_input"]["audio"] = self.media_descriptor("audio", "audio/webm", b"a")
        digest_mismatch["terminal_input"]["audio"]["sha256"] = "sha256:" + "0" * 64
        cases.append(("digest mismatch", digest_mismatch, "bytes"))
        arbitrary_object = json.loads(json.dumps(self.envelope(request_id="receipt-closed-005", path="/terminal/prepare")))
        arbitrary_object["terminal_input"]["audio"] = {"opaque": {"untyped": True}}
        cases.append(("arbitrary media object", arbitrary_object, "descriptor"))
        for label, candidate, reason in cases:
            with self.subTest(case=label):
                status, _, rejected = self.request(
                    "b", "/terminal/prepare", method="POST", body=candidate, headers=self.headers(candidate, mode="prepare")
                )
                self.assertEqual(status, 400)
                self.assertFalse(rejected["ordinary_release"])
                self.assertIn(reason, rejected["reason"])
        duplicate_key = self.envelope(request_id="receipt-closed-duplicate", path="/terminal/prepare")
        raw_body = (
            b'{"schema":"qikvrt_terminal_peer_request_v2","request_id":"receipt-closed-duplicate",'
            b'"source_node_id":"peer-a","target_node_id":"peer-b","target_endpoint_id":"terminal-b",'
            b'"effective_method":"POST","effective_target":"/terminal/prepare",'
            + f'"policy_id":"{terminal.PEER_POLICY_ID}","policy_sha256":"{terminal.PEER_POLICY_SHA256}",'.encode("ascii")
            + b'"responsibility_owner":"LOCAL_INTERACTIVE_USER","terminal_input":'
            b'{"schema":"qikvrt_terminal_input_v2","submitted_at":"2026-08-28T12:00:00Z",'
            b'"page":"https://example.invalid/terminal","text":"first","text":"second","audio":null,"video":null}}'
        )
        status, rejected = self.raw_request(
            "b",
            "/terminal/prepare",
            headers=[("Content-Type", "application/json"), *self.headers(duplicate_key, mode="prepare").items()],
            raw_body=raw_body,
        )
        self.assertEqual(status, 400)
        self.assertFalse(rejected["ordinary_release"])
        self.assertIn("duplicate member", rejected["reason"])
        surrogate = self.envelope(request_id="receipt-closed-006", path="/terminal/prepare")["terminal_input"]
        surrogate["text"] = "\ud800"
        with self.assertRaisesRegex(ValueError, "UTF-8"):
            terminal.validate_terminal_input_v2(surrogate)

    def test_peer_rejects_duplicate_or_ambiguous_framing_headers(self) -> None:
        prepare = self.envelope(request_id="receipt-003", path="/terminal/prepare")
        standard = [
            ("Content-Type", "application/json"),
            *self.headers(prepare, mode="prepare").items(),
        ]
        encoded = json.dumps(prepare, sort_keys=True, separators=(",", ":")).encode("utf-8")
        cases = [
            ("Effect-Ack-Request", standard + [("Effect-Ack-Request", "v=2, mode=prepare")]),
            ("Idempotency-Key", standard + [("Idempotency-Key", "different-request")]),
            ("X-QIKVRT-Source-Node", standard + [("X-QIKVRT-Source-Node", "different-source")]),
            ("X-QIKVRT-Target-Node", standard + [("X-QIKVRT-Target-Node", "different-target")]),
            ("X-QIKVRT-Target-Endpoint", standard + [("X-QIKVRT-Target-Endpoint", "different-endpoint")]),
            (
                "Content-Length",
                standard + [("Content-Length", str(len(encoded))), ("Content-Length", str(len(encoded)))],
            ),
            ("Transfer-Encoding", standard + [("Transfer-Encoding", "chunked")]),
        ]
        for label, headers in cases:
            with self.subTest(header=label):
                status, rejected = self.raw_request("b", "/terminal/prepare", body=prepare, headers=headers)
                self.assertEqual(status, 400)
                self.assertFalse(rejected["ordinary_release"])
                self.assertEqual(self.nodes["b"][2].sequence, 0)
                self.assertEqual(self.nodes["b"][2].peer_prepared_by_request, {})


class DurablePeerTerminalStateHardeningTests(unittest.TestCase):
    def test_durable_state_directory_is_exclusive_and_releases(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state_dir = Path(raw) / "node"
            first = terminal.DurableState(state_dir, node_id="peer-a", endpoint_id="terminal-a")
            try:
                with self.assertRaisesRegex(ValueError, "already locked"):
                    terminal.DurableState(state_dir, node_id="peer-a", endpoint_id="terminal-a")
            finally:
                first.close()
            second = terminal.DurableState(state_dir, node_id="peer-a", endpoint_id="terminal-a")
            second.close()

    def test_durable_state_rejects_symlink_state_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            direct = root / "direct"
            direct.mkdir()
            redirected = root / "redirected"
            redirected.symlink_to(direct, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                terminal.DurableState(redirected, node_id="peer-a", endpoint_id="terminal-a")

    def test_durable_state_rejects_unterminated_ledger_tail(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state_dir = Path(raw) / "node"
            state = terminal.DurableState(state_dir, node_id="peer-a", endpoint_id="terminal-a")
            try:
                state.record(
                    state="EFFECT_ACK_DONE",
                    input_hash="0" * 64,
                    ordinary_release=True,
                    reason="test durable receipt",
                    wire_version=2,
                    policy_id=terminal.PEER_POLICY_ID,
                    policy_version=2,
                    responsibility_owner="LOCAL_INTERACTIVE_USER",
                    request_id="receipt-tail",
                    request_fingerprint="1" * 64,
                    node_binding={"node": "peer-a"},
                )
            finally:
                state.close()
            ledger = state_dir / "terminal-ledger.jsonl"
            ledger.write_bytes(ledger.read_bytes()[:-1])
            with self.assertRaisesRegex(ValueError, "unterminated"):
                terminal.DurableState(state_dir, node_id="peer-a", endpoint_id="terminal-a")


if __name__ == "__main__":
    unittest.main()
