#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Loopback-only full Responsibility-Protocol gateway for the Mesh Appliance."""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from src.qikvrt_effect_ack import (
    ConnectionDecision,
    EffectAckRequest,
    EffectState,
    ResponsibilityProtocol,
    RiskLevel,
    canonical_json,
    effect_ack_sync,
    verify_protocol,
)

MAX_BODY = 2 * 1024 * 1024
TOKEN_TTL = 120
SF_KEY = re.compile(r"^[a-z*][a-z0-9_.*-]*$")
STATE_TOKEN = {
    EffectState.EFFECT_NACK: "nack",
    EffectState.EFFECT_ACK_CONTINUE: "continue",
    EffectState.EFFECT_ACK_DONE: "done",
    EffectState.EFFECT_ACK_ISOLATE: "isolate",
    EffectState.EFFECT_ACK_BLOCK: "block",
}


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sf_bytes(value: bytes) -> str:
    return ":" + base64.b64encode(value).decode("ascii") + ":"


def parse_sf_bytes(value: str) -> bytes:
    if not (isinstance(value, str) and len(value) >= 2 and value[0] == ":" and value[-1] == ":"):
        raise ValueError("Structured Field Byte Sequence required")
    try:
        return base64.b64decode(value[1:-1], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("malformed Structured Field Byte Sequence") from exc


def parse_effect_ack_request(raw: str | None) -> dict[str, Any]:
    if raw is None or not raw.strip():
        raise ValueError("Effect-Ack-Request required")
    members: dict[str, str] = {}
    for item in raw.split(","):
        if "=" not in item:
            raise ValueError("malformed Effect-Ack-Request dictionary")
        key, value = item.split("=", 1)
        key = key.strip().lower()
        value = value.strip()
        if not SF_KEY.fullmatch(key) or key in members:
            raise ValueError("invalid or duplicate Effect-Ack-Request member")
        members[key] = value
    if set(members) - {"v", "mode", "token", "hash"}:
        raise ValueError("unknown Effect-Ack-Request member")
    if members.get("v") != "1":
        raise ValueError("unsupported Effect-Ack-Request version")
    mode = members.get("mode")
    if mode not in {"evaluate", "prepare", "commit"}:
        raise ValueError("mode must be evaluate, prepare or commit")
    if mode in {"evaluate", "prepare"}:
        if set(members) != {"v", "mode"}:
            raise ValueError(f"{mode} must not carry token or hash")
        return {"mode": mode}
    if set(members) != {"v", "mode", "token", "hash"}:
        raise ValueError("commit requires token and hash")
    token = parse_sf_bytes(members["token"]).decode("ascii")
    hash_bytes = parse_sf_bytes(members["hash"])
    if len(hash_bytes) != 32:
        raise ValueError("commit hash must contain 32 octets")
    return {"mode": "commit", "token": token, "hash": hash_bytes.hex()}


def enum_value(cls: type[Any], value: Any, field: str) -> Any:
    try:
        return cls(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid {field}") from exc


def strings(value: Any, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be an array of strings")
    return tuple(value)


def payload_bytes(body: Mapping[str, Any]) -> bytes | None:
    if "payload_b64" in body:
        value = body["payload_b64"]
        if not isinstance(value, str):
            raise ValueError("payload_b64 must be a string")
        return base64.b64decode(value, validate=True)
    if "payload_text" in body:
        value = body["payload_text"]
        if not isinstance(value, str):
            raise ValueError("payload_text must be a string")
        return value.encode("utf-8")
    return None


def request_from_json(body: Mapping[str, Any]) -> EffectAckRequest:
    for field in ("protocol_root_id", "input_id"):
        if not isinstance(body.get(field), str) or not body[field]:
            raise ValueError(f"{field} must be a non-empty string")
    return EffectAckRequest(
        protocol_root_id=body["protocol_root_id"],
        input_id=body["input_id"],
        payload=payload_bytes(body),
        transport_ack=bool(body.get("transport_ack", False)),
        declared_input_hash=body.get("declared_input_hash"),
        origin_checked=bool(body.get("origin_checked", False)),
        context_checked=bool(body.get("context_checked", False)),
        semantics_reconstructed=bool(body.get("semantics_reconstructed", False)),
        effect_anticipated=bool(body.get("effect_anticipated", False)),
        risk_classified=bool(body.get("risk_classified", False)),
        risk_level=enum_value(RiskLevel, body.get("risk_level", "UNKNOWN"), "risk_level"),
        responsibility_assigned=bool(body.get("responsibility_assigned", False)),
        responsibility_owner=str(body.get("responsibility_owner", "")),
        connection_decision=enum_value(ConnectionDecision, body.get("connection_decision", "UNDECIDED"), "connection_decision"),
        policy_allows_release=bool(body.get("policy_allows_release", False)),
        reasons=strings(body.get("reasons"), "reasons"),
        evidence_refs=strings(body.get("evidence_refs"), "evidence_refs"),
        required_evidence_refs=strings(body.get("required_evidence_refs"), "required_evidence_refs"),
        open_questions=strings(body.get("open_questions"), "open_questions"),
        next_required_checks=strings(body.get("next_required_checks"), "next_required_checks"),
    )


def terminal_request(body: Mapping[str, Any]) -> EffectAckRequest:
    encoded = canonical_json(body).encode("utf-8")
    input_hash = "sha256:" + digest(encoded)
    if body.get("schema") != "qikvrt_terminal_input_v1":
        return EffectAckRequest(
            protocol_root_id="qikvrt:appliance:terminal-input",
            input_id=str(body.get("input_id", "unsupported")),
            payload=encoded,
            transport_ack=True,
            declared_input_hash=input_hash,
            connection_decision=ConnectionDecision.BLOCK,
            reasons=("UNSUPPORTED_TERMINAL_SCHEMA",),
        )
    return EffectAckRequest(
        protocol_root_id="qikvrt:appliance:terminal-input",
        input_id=str(body.get("input_id") or input_hash),
        payload=encoded,
        transport_ack=True,
        declared_input_hash=input_hash,
        origin_checked=True,
        context_checked=True,
        semantics_reconstructed=True,
        effect_anticipated=True,
        risk_classified=True,
        risk_level=RiskLevel.LOW,
        responsibility_assigned=True,
        responsibility_owner="LOCAL_APPLIANCE_USER",
        connection_decision=ConnectionDecision.RELEASE,
        policy_allows_release=True,
        reasons=("BOUNDED_LOOPBACK_TERMINAL_INPUT",),
        evidence_refs=(input_hash,),
        required_evidence_refs=(input_hash,),
    )


@dataclass
class Prepared:
    token: str
    input_hash: str
    protocol_hash: str
    payload: bytes
    expires_at: float
    used: bool = False


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.ledger = root / "responsibility-protocol.jsonl"
        self.secret = secrets.token_bytes(32)
        self.lock = threading.Lock()
        self.protocols: dict[str, dict[str, Any]] = {}
        self.prepared: dict[str, Prepared] = {}
        self.events: list[dict[str, Any]] = []

    def persist(self, protocol: ResponsibilityProtocol) -> str:
        verify_protocol(protocol)
        hex_digest = protocol.protocol_hash.removeprefix("sha256:")
        record = protocol.to_dict()
        with self.lock:
            self.protocols[hex_digest] = record
            with self.ledger.open("a", encoding="utf-8") as stream:
                stream.write(canonical_json(record) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        return hex_digest

    def prepare_token(self, payload: bytes, protocol_hash: str, input_hash: str) -> str:
        nonce = secrets.token_bytes(24)
        expiry = int(time.time()) + TOKEN_TTL
        material = nonce + expiry.to_bytes(8, "big") + bytes.fromhex(protocol_hash) + bytes.fromhex(input_hash)
        mac = hmac.new(self.secret, material, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(material + mac).decode("ascii").rstrip("=")
        self.prepared[token] = Prepared(token, input_hash, protocol_hash, payload, float(expiry))
        return token


STORE: Store


class Handler(BaseHTTPRequestHandler):
    server_version = "QIKVRTMeshAppliance/1.0"

    def _origin(self) -> str | None:
        origin = self.headers.get("Origin")
        allowed = {item.strip() for item in os.environ.get(
            "QIKVRT_ALLOWED_ORIGINS",
            "https://github.com,https://goldkelch.github.io,http://127.0.0.1:6080,http://localhost:6080",
        ).split(",") if item.strip()}
        return origin if origin in allowed else None

    def _send(self, code: int, body: Mapping[str, Any], protocol: Mapping[str, Any] | None = None, token: str | None = None) -> None:
        payload = json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Link", "</.well-known/effect-ack>; rel=\"effect-ack\"; type=\"application/json\"")
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Expose-Headers", "Effect-Ack, Link")
        if protocol:
            state = EffectState(protocol["state"])
            hex_digest = str(protocol["protocol_hash"]).removeprefix("sha256:")
            value = f"v=1, state={STATE_TOKEN[state]}, hash={sf_bytes(bytes.fromhex(hex_digest))}"
            if token:
                value += f", token={sf_bytes(token.encode('ascii'))}"
            self.send_header("Effect-Ack", value)
        self.end_headers()
        self.wfile.write(payload)

    def _read(self) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("Transfer-Encoding unsupported")
        raw = self.headers.get("Content-Length")
        if raw is None:
            raise ValueError("Content-Length required")
        length = int(raw)
        if length < 1 or length > MAX_BODY:
            raise ValueError("body outside bounded size")
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("application/json required")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Content-Length", "0")
        origin = self._origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Effect-Ack-Request")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/healthz":
            self._send(200, {"state": "READY", "service": "qikvrt-mesh-appliance", "external_effect": "NONE"})
            return
        if path == "/.well-known/effect-ack":
            self._send(200, {
                "schema": "qikvrt_effect_ack_capability_v1",
                "internet_draft": "draft-lohmann-qikvrt-effect-ack-00",
                "standards_status": "experimental_individual_internet_draft_profile",
                "versions": [1],
                "states": [state.value for state in EffectState],
                "modes": ["evaluate", "prepare", "commit"],
                "responsibility_protocol": "qikvrt_responsibility_protocol_v1",
                "protected_effects": ["terminal_input"],
                "external_effects": "NONE",
                "record_template": "/effect-ack/records/{sha256}",
            })
            return
        prefix = "/effect-ack/records/"
        if path.startswith(prefix):
            hex_digest = path[len(prefix):]
            if not re.fullmatch(r"[0-9a-f]{64}", hex_digest):
                self._send(400, {"state": "HOLD", "reason": "invalid record id"})
                return
            record = STORE.protocols.get(hex_digest)
            if record is None:
                self._send(404, {"state": "HOLD", "reason": "record not found"})
                return
            self._send(200, {
                "state": record["state"],
                "ordinary_release": record["ordinary_release"],
                "record_hash": "sha256:" + hex_digest,
                "responsibility_protocol": record,
            }, record)
            return
        if path == "/terminal/state":
            with STORE.lock:
                self._send(200, {
                    "schema": "qikvrt_appliance_terminal_state_v1",
                    "events": len(STORE.events),
                    "last_event": STORE.events[-1] if STORE.events else None,
                    "external_effect": "NONE",
                })
            return
        self._send(404, {"state": "HOLD", "reason": "not found"})

    def do_POST(self) -> None:
        try:
            binding = parse_effect_ack_request(self.headers.get("Effect-Ack-Request"))
            body = self._read()
            path = urlparse(self.path).path
            if path == "/v1/evaluate" and binding["mode"] == "evaluate":
                result = effect_ack_sync(request_from_json(body), timeout_ms=100)
                hex_digest = STORE.persist(result.protocol)
                self._send(200, {
                    **result.to_dict(),
                    "record_hash": hex_digest,
                    "record_url": f"/effect-ack/records/{hex_digest}",
                    "external_effect": "NONE",
                }, result.protocol.to_dict())
                return
            if path == "/terminal/prepare" and binding["mode"] == "prepare":
                result = effect_ack_sync(terminal_request(body), timeout_ms=100)
                hex_digest = STORE.persist(result.protocol)
                token = None
                if result.state is EffectState.EFFECT_ACK_DONE:
                    payload = canonical_json(body).encode("utf-8")
                    token = STORE.prepare_token(payload, hex_digest, result.protocol.input_hash.removeprefix("sha256:"))
                self._send(200, {
                    "state": result.state.value,
                    "ordinary_release": False,
                    "commit_token": token,
                    "record_hash": hex_digest,
                    "record_url": f"/effect-ack/records/{hex_digest}",
                    "responsibility_protocol": result.protocol.to_dict(),
                    "expires_in_seconds": TOKEN_TTL if token else 0,
                    "external_effect": "NONE",
                }, result.protocol.to_dict(), token)
                return
            if path == "/terminal/commit" and binding["mode"] == "commit":
                self._commit(body, binding)
                return
            raise ValueError("endpoint/mode mismatch")
        except (ValueError, TypeError, UnicodeError, json.JSONDecodeError, binascii.Error) as exc:
            self._send(400, {"state": "HOLD", "ordinary_release": False, "reason": str(exc)})

    def _commit(self, body: Mapping[str, Any], binding: Mapping[str, Any]) -> None:
        token = str(binding["token"])
        hex_digest = str(binding["hash"])
        payload = canonical_json(body).encode("utf-8")
        with STORE.lock:
            prepared = STORE.prepared.get(token)
            if prepared is None or prepared.used or prepared.expires_at < time.time() or not hmac.compare_digest(prepared.protocol_hash, hex_digest) or not hmac.compare_digest(prepared.payload, payload):
                self._send(409, {"state": "HOLD", "ordinary_release": False, "reason": "invalid, stale, used or mismatched token"})
                return
            prepared.used = True
            protocol = STORE.protocols[hex_digest]
            event = {
                "event_id": len(STORE.events) + 1,
                "kind": "TERMINAL_INPUT_ACCEPTED",
                "protocol_hash": "sha256:" + hex_digest,
                "input_hash": protocol["input_hash"],
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "external_effect": "NONE",
            }
            STORE.events.append(event)
        self._send(200, {
            "state": protocol["state"],
            "ordinary_release": bool(protocol["ordinary_release"]),
            "record_hash": hex_digest,
            "post_effect": event,
            "responsibility_protocol": protocol,
            "external_effect": "NONE",
        }, protocol)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("QIKVRT_EFFECT_ACK_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("QIKVRT_EFFECT_ACK_PORT", "8771")))
    parser.add_argument("--state-dir", default=os.environ.get("QIKVRT_STATE_DIR", "/var/lib/qikvrt/effect-ack"))
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "0.0.0.0"}:
        raise SystemExit("BLOCK: host outside appliance allowlist")
    global STORE
    STORE = Store(Path(args.state_dir))
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(json.dumps({"state": "READY", "host": args.host, "port": args.port, "profile": "draft-lohmann-qikvrt-effect-ack-00", "external_effect": "NONE"}, sort_keys=True), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
