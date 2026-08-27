#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import json
import hmac
import os
import re
import ssl
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from qikvrt_api_handler import (
    HandlerConfig,
    decode_secret_material,
    run_handler,
    secure_read_bytes,
)
from qikvrt_effect_ack import EffectState

REPOSITORY_COMPONENT = r"([A-Za-z0-9_.-]{1,100})"
DISPATCH_RE = re.compile(rf"^/repos/{REPOSITORY_COMPONENT}/{REPOSITORY_COMPONENT}/actions/workflows/qikvrt_mesh_api\.yml/dispatches$")
REPO_DISPATCH_RE = re.compile(rf"^/repos/{REPOSITORY_COMPONENT}/{REPOSITORY_COMPONENT}/dispatches$")
MAX_REQUEST_BYTES = 1024 * 1024
MAX_OPENAPI_BYTES = 512 * 1024
_RATE_LOCK = threading.Lock()
_RATE_WINDOWS: dict[str, tuple[int, int]] = {}


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number is not permitted: {value}")


def _parse_expiry(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        return None
    return value.astimezone(timezone.utc)

def _api_credential_valid() -> bool:
    token = os.environ.get("QIKVRT_API_TOKEN", "")
    expiry = _parse_expiry(os.environ.get("QIKVRT_API_TOKEN_EXPIRES_UTC", ""))
    try:
        decode_secret_material(token, field="QIKVRT_API_TOKEN")
    except ValueError:
        return False
    return bool(expiry is not None and expiry > datetime.now(timezone.utc))


def _attestation_configuration_valid() -> bool:
    secret = os.environ.get("QIKVRT_REMOTE_ATTESTATION_SECRET", "")
    signer = os.environ.get("QIKVRT_TRUSTED_ATTESTATION_SIGNER", "").strip()
    if not secret and not signer:
        return True
    if not secret or not signer or len(signer) > 256:
        return False
    try:
        secret_material = decode_secret_material(
            secret, field="QIKVRT_REMOTE_ATTESTATION_SECRET"
        )
        token_material = decode_secret_material(
            os.environ.get("QIKVRT_API_TOKEN", ""), field="QIKVRT_API_TOKEN"
        )
    except ValueError:
        return False
    return not hmac.compare_digest(secret_material, token_material)


def _security_configuration_valid() -> bool:
    repository = os.environ.get("QIKVRT_ALLOWED_REPOSITORY", "")
    principal = os.environ.get("QIKVRT_API_PRINCIPAL", "").strip()
    try:
        socket_timeout = float(os.environ.get("QIKVRT_SOCKET_TIMEOUT_SECONDS", "10"))
        rate_limit = int(os.environ.get("QIKVRT_RATE_LIMIT_PER_MINUTE", "120"))
    except ValueError:
        return False
    return bool(
        _api_credential_valid()
        and _attestation_configuration_valid()
        and re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", repository)
        and principal
        and len(principal) <= 256
        and 0.1 <= socket_timeout <= 120
        and 1 <= rate_limit <= 100_000
    )


class QikvrtGitHubApiShim(BaseHTTPRequestHandler):
    server_version = "QIKVRTGitHubApiShim/2.0"

    def setup(self) -> None:
        super().setup()
        try:
            timeout = float(os.environ.get("QIKVRT_SOCKET_TIMEOUT_SECONDS", "10"))
        except ValueError:
            timeout = 10.0
        self.connection.settimeout(timeout if 0.1 <= timeout <= 120 else 10.0)

    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _send_yaml(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/vnd.oai.openapi;version=3.0.3")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _repository_root() -> Path:
        configured = os.environ.get("QIKVRT_REPO_ROOT", "")
        return Path(configured).resolve() if configured else Path(__file__).resolve().parents[1]

    def _capabilities(self) -> dict:
        configured = _security_configuration_valid()
        return {
            "schema": "qikvrt_mesh_api_capabilities_v1",
            "service": "QIKVRT GitHub-Compatible REST API Shim",
            "configuration_valid": configured,
            "public_read_endpoints": ["/health", "/capabilities", "/openapi.yaml"],
            "authenticated_command_endpoints": [
                "/repos/{owner}/{repo}/actions/workflows/qikvrt_mesh_api.yml/dispatches",
                "/repos/{owner}/{repo}/dispatches",
            ],
            "operations": ["ingest", "verify", "stage", "release_status"],
            "execution_boundary": "GitHub dispatch acceptance and local handler results require exact-run/artifact reobservation.",
            "ordinary_release": False,
            "general_effect_ack_done": False,
        }

    def _read_json(self) -> dict:
        if self.headers.get("Transfer-Encoding") is not None:
            raise ValueError("Transfer-Encoding is not supported")
        lengths = self.headers.get_all("Content-Length", failobj=[])
        if len(lengths) != 1:
            raise ValueError("exactly one Content-Length header is required")
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            raise ValueError("Content-Type must be application/json")
        try:
            n = int(self.headers.get("Content-Length", "0") or "0")
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if n <= 0:
            raise ValueError("JSON request body is required")
        if n > MAX_REQUEST_BYTES:
            raise ValueError("request too large")
        raw = self.rfile.read(n)
        try:
            body = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_unique_json_object,
                parse_constant=_reject_json_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise ValueError("malformed UTF-8 JSON request") from exc
        if not isinstance(body, dict):
            raise ValueError("JSON request body must be an object")
        return body

    def _authorized(self) -> bool:
        token = os.environ.get("QIKVRT_API_TOKEN", "")
        if not _api_credential_valid():
            return False
        supplied = self.headers.get("Authorization", "")
        return hmac.compare_digest(supplied.encode("utf-8"), f"Bearer {token}".encode("utf-8"))

    def _rate_allowed(self) -> bool:
        try:
            limit = int(os.environ.get("QIKVRT_RATE_LIMIT_PER_MINUTE", "120"))
        except ValueError:
            return False
        if not 1 <= limit <= 100_000:
            return False
        identity = self.client_address[0]
        window = int(time.time() // 60)
        with _RATE_LOCK:
            if len(_RATE_WINDOWS) > 4096:
                stale = [key for key, (seen_window, _) in _RATE_WINDOWS.items() if seen_window != window]
                for key in stale:
                    _RATE_WINDOWS.pop(key, None)
            prior_window, count = _RATE_WINDOWS.get(identity, (window, 0))
            if prior_window != window:
                prior_window, count = window, 0
            count += 1
            _RATE_WINDOWS[identity] = (prior_window, count)
            return count <= limit

    @staticmethod
    def _boolean(raw: object, *, field: str) -> bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.lower() in ("true", "false"):
            return raw.lower() == "true"
        raise ValueError(f"{field} must be true or false")

    def do_GET(self):
        if self.path == "/capabilities":
            self._send_json(200, self._capabilities())
            return
        if self.path == "/openapi.yaml":
            try:
                specification = secure_read_bytes(
                    self._repository_root() / "api" / "qikvrt_github_api.openapi.yaml",
                    max_bytes=MAX_OPENAPI_BYTES,
                )
            except (OSError, RuntimeError):
                self._send_json(503, {"status": "BLOCK", "reason": "OpenAPI specification unavailable"})
                return
            self._send_yaml(200, specification)
            return
        if self.path == "/health":
            valid = _security_configuration_valid()
            attestation_configured = bool(
                os.environ.get("QIKVRT_REMOTE_ATTESTATION_SECRET", "")
                and os.environ.get("QIKVRT_TRUSTED_ATTESTATION_SIGNER", "").strip()
            )
            self._send_json(
                200 if valid else 503,
                {
                    "status": "ALIVE" if valid else "BLOCK",
                    "service": "QIKVRT GitHub-Compatible REST API Shim",
                    "tcpip": True,
                    "github_compatible_dispatch": True,
                    "configuration_valid": valid,
                    "authentication_configured": _api_credential_valid(),
                    "remote_attestation_configured": attestation_configured,
                },
            )
            return
        self._send_json(404, {"status": "BLOCK", "reason": "not found"})

    def do_POST(self):
        if not self._rate_allowed():
            self._send_json(429, {"status": "BLOCK", "reason": "rate limit exceeded"})
            return
        if not self._authorized():
            self._send_json(401, {"status": "BLOCK", "reason": "unauthorized"})
            return
        parsed = urlparse(self.path)
        if parsed.query or parsed.params or parsed.fragment:
            self._send_json(404, {"status": "BLOCK", "reason": "unknown endpoint"})
            return
        m = DISPATCH_RE.match(parsed.path)
        mr = REPO_DISPATCH_RE.match(parsed.path)
        if not (m or mr):
            self._send_json(404, {"status": "BLOCK", "reason": "unknown endpoint"})
            return
        try:
            body = self._read_json()
            if m:
                unknown = set(body) - {"ref", "inputs"}
                if unknown:
                    raise ValueError(f"unknown workflow dispatch fields: {sorted(unknown)}")
                owner, repo = m.group(1), m.group(2)
                ref = body.get("ref")
                if not isinstance(ref, str) or not ref.strip() or len(ref) > 255:
                    raise ValueError("workflow dispatch ref is required")
                inputs = body.get("inputs", {})
            else:
                unknown = set(body) - {"event_type", "client_payload"}
                if unknown:
                    raise ValueError(f"unknown repository dispatch fields: {sorted(unknown)}")
                owner, repo = mr.group(1), mr.group(2)
                if body.get("event_type") != "qikvrt_mesh_api":
                    raise ValueError("unsupported repository_dispatch event_type")
                inputs = body.get("client_payload", {}) if isinstance(body.get("client_payload", {}), dict) else {}
            if not isinstance(inputs, dict):
                raise ValueError("dispatch inputs must be an object")
            required_inputs = {
                "operation", "artifact_id", "dry_run", "request_id", "effect_accepted",
            }
            missing_inputs = required_inputs - set(inputs)
            if missing_inputs:
                raise ValueError(f"missing dispatch inputs: {sorted(missing_inputs)}")
            allowed_inputs = {
                "operation", "artifact_id", "payload_b64", "expected_sha256",
                "dry_run", "request_id", "effect_accepted",
                "responsibility_owner", "state_run_id", "remote_evidence_b64",
            }
            unknown_inputs = set(inputs) - allowed_inputs
            if unknown_inputs:
                raise ValueError(f"unknown dispatch inputs: {sorted(unknown_inputs)}")
            request_id = str(inputs.get("request_id", "") or self.headers.get("X-QIKVRT-Request-ID", "")).strip()
            if not request_id:
                raise ValueError("request_id is required")
            requested_repository = f"{owner}/{repo}"
            allowed_repository = os.environ.get("QIKVRT_ALLOWED_REPOSITORY", "")
            if not hmac.compare_digest(requested_repository, allowed_repository):
                raise ValueError("repository is outside this credential scope")
            principal = os.environ.get("QIKVRT_API_PRINCIPAL", "").strip()
            supplied_owner = str(inputs.get("responsibility_owner", "")).strip()
            if supplied_owner and supplied_owner != principal:
                raise ValueError("responsibility_owner must match the authenticated principal")
            cfg = HandlerConfig(
                root=Path(os.environ.get("QIKVRT_REPO_ROOT", os.getcwd())),
                operation=str(inputs.get("operation", "")),
                artifact_id=str(inputs.get("artifact_id", "")),
                payload_b64=str(inputs.get("payload_b64", "")),
                expected_sha256=str(inputs.get("expected_sha256", "")),
                dry_run=self._boolean(inputs.get("dry_run", "true"), field="dry_run"),
                repository=requested_repository,
                run_id="local-tcpip-shim",
                request_id=request_id,
                effect_accepted=self._boolean(inputs.get("effect_accepted", "false"), field="effect_accepted"),
                responsibility_owner=principal,
                origin_authenticated=True,
                remote_evidence_b64=str(inputs.get("remote_evidence_b64", "")),
                trusted_attestation_secret=os.environ.get("QIKVRT_REMOTE_ATTESTATION_SECRET", ""),
                trusted_attestation_signer=os.environ.get("QIKVRT_TRUSTED_ATTESTATION_SIGNER", "").strip(),
            )
            result = run_handler(cfg)
            effect_state = result.get("effect_state")
            status = {
                EffectState.EFFECT_ACK_DONE.value: 202,
                EffectState.EFFECT_ACK_CONTINUE.value: 202,
                EffectState.EFFECT_NACK.value: 422,
                EffectState.EFFECT_ACK_ISOLATE.value: 423,
                EffectState.EFFECT_ACK_BLOCK.value: 409,
            }.get(effect_state, 500)
            response_status = {
                EffectState.EFFECT_ACK_DONE.value: "ACCEPTED",
                EffectState.EFFECT_ACK_CONTINUE.value: "CONTINUE",
                EffectState.EFFECT_NACK.value: "NACK",
                EffectState.EFFECT_ACK_ISOLATE.value: "ISOLATE",
                EffectState.EFFECT_ACK_BLOCK.value: "BLOCK",
            }.get(effect_state, "INTERNAL_ERROR")
            self._send_json(status, {"status": response_status, "handler_result": result})
        except (ValueError, UnicodeError) as exc:
            self._send_json(400, {"status": "BLOCK", "reason": str(exc)})
        except Exception as exc:
            if os.environ.get("QIKVRT_API_LOG", "0") == "1":
                print(f"QIK-VRT adapter internal error: {type(exc).__name__}: {exc}", file=sys.stderr)
            self._send_json(500, {"status": "BLOCK", "reason": "internal adapter error"})

    def log_message(self, fmt, *args):
        if os.environ.get("QIKVRT_API_LOG", "0") == "1":
            super().log_message(fmt, *args)

def main() -> int:
    host = os.environ.get("QIKVRT_API_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("QIKVRT_API_PORT", "8766"))
    except ValueError:
        print("BLOCK QIKVRT_API_PORT must be an integer", file=sys.stderr)
        return 2
    if not 1 <= port <= 65535:
        print("BLOCK QIKVRT_API_PORT must be between 1 and 65535", file=sys.stderr)
        return 2
    try:
        decode_secret_material(
            os.environ.get("QIKVRT_API_TOKEN", ""),
            field="QIKVRT_API_TOKEN",
        )
    except ValueError as exc:
        print(f"BLOCK {exc}", file=sys.stderr)
        return 2
    allowed_repository = os.environ.get("QIKVRT_ALLOWED_REPOSITORY", "")
    principal = os.environ.get("QIKVRT_API_PRINCIPAL", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}", allowed_repository):
        print("BLOCK QIKVRT_ALLOWED_REPOSITORY must be an exact owner/repo scope", file=sys.stderr)
        return 2
    if not principal or len(principal) > 256:
        print("BLOCK QIKVRT_API_PRINCIPAL must identify the authenticated responsibility owner", file=sys.stderr)
        return 2
    expiry = _parse_expiry(os.environ.get("QIKVRT_API_TOKEN_EXPIRES_UTC", ""))
    if expiry is None or expiry <= datetime.now(timezone.utc):
        print("BLOCK QIKVRT_API_TOKEN_EXPIRES_UTC must be a future timezone-aware timestamp", file=sys.stderr)
        return 2
    if not _attestation_configuration_valid():
        print(
            "BLOCK remote attestation requires a signer plus a canonical b64url secret decoding to 32--128 bytes",
            file=sys.stderr,
        )
        return 2
    try:
        socket_timeout = float(os.environ.get("QIKVRT_SOCKET_TIMEOUT_SECONDS", "10"))
        rate_limit = int(os.environ.get("QIKVRT_RATE_LIMIT_PER_MINUTE", "120"))
    except ValueError:
        print("BLOCK socket timeout and rate limit must be numeric", file=sys.stderr)
        return 2
    if not 0.1 <= socket_timeout <= 120:
        print("BLOCK QIKVRT_SOCKET_TIMEOUT_SECONDS must be between 0.1 and 120", file=sys.stderr)
        return 2
    if not 1 <= rate_limit <= 100_000:
        print("BLOCK QIKVRT_RATE_LIMIT_PER_MINUTE must be between 1 and 100000", file=sys.stderr)
        return 2
    if host != "127.0.0.1" and os.environ.get("QIKVRT_ALLOW_NON_LOOPBACK") != "1":
        print("BLOCK non-loopback requires QIKVRT_ALLOW_NON_LOOPBACK=1", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((host, port), QikvrtGitHubApiShim)
    if host != "127.0.0.1":
        cert_file = os.environ.get("QIKVRT_TLS_CERT_FILE", "")
        key_file = os.environ.get("QIKVRT_TLS_KEY_FILE", "")
        if not cert_file or not key_file:
            print("BLOCK non-loopback service requires QIKVRT_TLS_CERT_FILE and QIKVRT_TLS_KEY_FILE", file=sys.stderr)
            server.server_close()
            return 2
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        server.socket = context.wrap_socket(server.socket, server_side=True)
    print(json.dumps({"status": "PASS", "listening": f"{host}:{port}"}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
