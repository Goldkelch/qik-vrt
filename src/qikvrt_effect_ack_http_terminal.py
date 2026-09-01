#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Loopback-only reference backend for the QIKVRT Firefox terminal.

Experimental HTTP-profile demonstrator. It proves capability discovery,
Structured-Field prepare/commit, exact-bound single-use commit, and post-effect
reobservation without granting repository, publication, deployment, or other
external-effect capability.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

MAX_BODY = 2 * 1024 * 1024
TOKEN_TTL_SECONDS = 120
HOST = "127.0.0.1"
DEFAULT_PORT = 8771
MLP_TOS_SHA256 = "5a74c9645d6cdcb2d92770517e31eb7697e180b2ccc4b7fb777c9b558b84ae7e"
EMUTOS_ROM_SHA256 = "f810041373d8efe15d55ec049fd4dd9be9b0fc521bbe6416b99d833f7fd6805d"
REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
ATARI_BOOT_ID = re.compile(r"^[0-9a-f]{32}$")
ATARI_MAX_CONCURRENT_BOOTS = 2
ATARI_MAX_LOG_LINES = 256
SF_KEY = re.compile(r"^[a-z*][a-z0-9_.*-]*$")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sf_bytes(raw: bytes) -> str:
    return ":" + base64.b64encode(raw).decode("ascii") + ":"


def parse_sf_bytes(value: str) -> bytes:
    if len(value) < 2 or not (value.startswith(":") and value.endswith(":")):
        raise ValueError("Structured Field Byte Sequence required")
    try:
        return base64.b64decode(value[1:-1], validate=True)
    except (ValueError, base64.binascii.Error) as exc:
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
        raise ValueError("unknown Effect-Ack-Request member in version 1")
    try:
        version = int(members.get("v", ""))
    except ValueError as exc:
        raise ValueError("Effect-Ack-Request v must be an integer") from exc
    if version != 1:
        raise ValueError("unsupported Effect-Ack-Request version")
    mode = members.get("mode")
    if mode not in {"prepare", "commit"}:
        raise ValueError("Effect-Ack-Request mode must be prepare or commit")
    if mode == "prepare":
        if set(members) != {"v", "mode"}:
            raise ValueError("prepare must not carry token or hash")
        return {"v": 1, "mode": "prepare"}
    if set(members) != {"v", "mode", "token", "hash"}:
        raise ValueError("commit requires token and hash")
    token_bytes = parse_sf_bytes(members["token"])
    try:
        token = token_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("commit token must be ASCII") from exc
    hash_bytes = parse_sf_bytes(members["hash"])
    if len(hash_bytes) != 32:
        raise ValueError("commit hash must contain exactly 32 octets")
    return {"v": 1, "mode": "commit", "token": token, "hash": hash_bytes.hex()}


def git_read(*args: str) -> str | None:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL, timeout=2).strip()
    except (OSError, subprocess.SubprocessError):
        return None


@dataclass
class Prepared:
    token: str
    input_hash: str
    record_hash: str
    expires_at: float
    used: bool = False


@dataclass
class AtariBoot:
    """One bounded, local Hatari execution request.

    The process is deliberately observed through immutable output files and a
    small append-only log projection.  It is not an assertion that an Atari
    framebuffer, a browser, an external effect, or a general Effect Ack was
    observed.
    """

    boot_id: str
    started_utc: str
    workdir: Path
    process: Any | None = None
    state: str = "BOOTING"
    exit_code: int | None = None
    reason: str | None = None
    log_lines: list[str] = field(default_factory=list)
    log_start: int = 0
    virtual_megast_execution_observed: bool = False
    request_frame_sha256: str | None = None
    trace_sha256: str | None = None

    def append_log(self, line: str) -> None:
        value = line.rstrip("\r\n")
        if not value:
            return
        self.log_lines.append(value[:2048])
        if len(self.log_lines) > ATARI_MAX_LOG_LINES:
            discarded = len(self.log_lines) - ATARI_MAX_LOG_LINES
            del self.log_lines[:discarded]
            self.log_start += discarded

    def projection(self) -> dict[str, Any]:
        process_alive = self.process is not None and self.process.poll() is None
        return {
            "schema": "qikvrt_atari_terminal_boot_status_v1",
            "state": self.state,
            "boot_id": self.boot_id,
            "started_utc": self.started_utc,
            "process_alive": process_alive,
            "exit_code": self.exit_code,
            "reason": self.reason,
            "log_start": self.log_start,
            "log_tail": list(self.log_lines),
            "virtual_megast_execution_observed": self.virtual_megast_execution_observed,
            "request_frame_sha256": self.request_frame_sha256,
            "trace_sha256": self.trace_sha256,
            "physical_megast_execution": False,
            "browser_execution_observed": False,
            "effect_ack_done": False,
            "external_effect": "NONE",
        }


class State:
    def __init__(self) -> None:
        self.secret = secrets.token_bytes(32)
        self.lock = threading.Lock()
        self.prepared: dict[str, Prepared] = {}
        self.records: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.atari_boots: dict[str, AtariBoot] = {}

    def record(self, *, state: str, input_hash: str, ordinary_release: bool, reason: str) -> tuple[str, dict[str, Any]]:
        body = {
            "schema": "qikvrt_effect_ack_http_terminal_record_v1",
            "wire_version": 1,
            "message_type": "effect-ack-record",
            "state": state,
            "input_hash": "sha256:" + input_hash,
            "policy_id": "QIKVRT_LOOPBACK_TERMINAL_V1",
            "policy_version": 1,
            "policy_allows_release": ordinary_release,
            "ordinary_release": ordinary_release,
            "responsibility_owner": "LOCAL_INTERACTIVE_USER",
            "reason": reason,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "external_effect": "NONE",
        }
        digest = sha256(canonical_json(body))
        body["record_hash"] = "sha256:" + digest
        self.records[digest] = body
        return digest, body

    def make_token(self, input_hash: str, record_hash: str) -> str:
        nonce = secrets.token_bytes(24)
        expires = int(time.time()) + TOKEN_TTL_SECONDS
        payload = nonce + expires.to_bytes(8, "big") + bytes.fromhex(input_hash) + bytes.fromhex(record_hash)
        mac = hmac.new(self.secret, payload, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(payload + mac).decode("ascii").rstrip("=")
        self.prepared[token] = Prepared(token, input_hash, record_hash, float(expires))
        return token


STATE = State()


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def parse_receipt_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if not separator or not re.fullmatch(r"[A-Z0-9_]+", key):
                raise ValueError("malformed receipt.env")
            values[key] = value
    except (OSError, UnicodeError, ValueError):
        return {}
    return values


def active_atari_boots() -> int:
    return sum(boot.state == "BOOTING" and boot.process is not None and boot.process.poll() is None for boot in STATE.atari_boots.values())


def finish_atari_boot(boot: AtariBoot) -> None:
    """Consume one local launcher process and materialize only observed facts."""

    process = boot.process
    if process is None:
        return
    try:
        output = process.stdout
        if output is not None:
            for line in output:
                with STATE.lock:
                    boot.append_log(line)
        exit_code = process.wait()
    except (OSError, subprocess.SubprocessError) as exc:
        with STATE.lock:
            boot.state = "HOLD"
            boot.reason = f"HATARI_ADAPTER_IO_FAILED:{type(exc).__name__}"
        return

    workdir = boot.workdir
    trace = workdir / "hatari.log"
    request = workdir / "drive" / "C" / "MLP.OPEN"
    receipt = parse_receipt_env(workdir / "receipt.env")
    with STATE.lock:
        boot.exit_code = exit_code
        if exit_code != 0:
            boot.state = "HOLD"
            boot.reason = f"HATARI_EXITED_{exit_code}"
            return
        if not trace.is_file() or not request.is_file() or not receipt:
            boot.state = "HOLD"
            boot.reason = "HATARI_RECEIPT_INCOMPLETE"
            return
        try:
            trace_sha = sha256(trace.read_bytes())
            request_sha = sha256(request.read_bytes())
        except OSError:
            boot.state = "HOLD"
            boot.reason = "HATARI_RECEIPT_UNREADABLE"
            return
        boot.trace_sha256 = trace_sha
        boot.request_frame_sha256 = request_sha
        expected = {
            "MLP_TOS_SHA256": MLP_TOS_SHA256,
            "MLP_OPEN_SHA256": request_sha,
            "HATARI_TRACE_SHA256": trace_sha,
            "MEGAST_VIRTUAL_EXECUTION_OBSERVED": "true",
            "PHYSICAL_MEGAST_EXECUTION": "false",
            "EFFECT_ACK_DONE": "false",
        }
        if any(receipt.get(key) != value for key, value in expected.items()):
            boot.state = "HOLD"
            boot.reason = "HATARI_RECEIPT_BINDING_FAILED"
            return
        boot.state = "VIRTUAL_MEGAST_EXECUTION_OBSERVED"
        boot.virtual_megast_execution_observed = True
        boot.reason = "EXACT_MLP_TOS_COMPLETED_IN_LOCAL_HATARI"


def start_atari_boot() -> tuple[int, dict[str, Any]]:
    """Start the existing exact MLP.TOS/Hatari launcher, or fail closed.

    This is intentionally a bounded local adapter.  A caller receives a boot
    identifier and must reobserve status; the initial process creation is not a
    browser, framebuffer, external-effect, or Effect-Ack observation.
    """

    hatari = shutil.which("hatari")
    if not hatari:
        return 503, {"state": "HOLD", "reason": "HATARI_UNAVAILABLE", "effect_ack_done": False, "external_effect": "NONE"}
    rom_value = os.environ.get("EMUTOS_ROM", "")
    if not rom_value:
        return 503, {"state": "HOLD", "reason": "EMUTOS_ROM_REQUIRED", "effect_ack_done": False, "external_effect": "NONE"}
    rom = Path(rom_value)
    if not rom.is_file():
        return 503, {"state": "HOLD", "reason": "EMUTOS_ROM_UNAVAILABLE", "effect_ack_done": False, "external_effect": "NONE"}
    try:
        if sha256(rom.read_bytes()) != EMUTOS_ROM_SHA256:
            return 422, {"state": "HOLD", "reason": "EMUTOS_ROM_BINDING_FAILED", "effect_ack_done": False, "external_effect": "NONE"}
    except OSError:
        return 503, {"state": "HOLD", "reason": "EMUTOS_ROM_UNREADABLE", "effect_ack_done": False, "external_effect": "NONE"}

    launcher = REPOSITORY_ROOT / "MLP.TOS" / "Hatari"
    mlp_tos = REPOSITORY_ROOT / "MLP.TOS" / "MLP.TOS"
    checksum = REPOSITORY_ROOT / "MLP.TOS" / "MLP.TOS.sha256"
    if not launcher.is_file() or not mlp_tos.is_file() or not checksum.is_file():
        return 503, {"state": "HOLD", "reason": "HATARI_ADAPTER_FILES_UNAVAILABLE", "effect_ack_done": False, "external_effect": "NONE"}
    try:
        if sha256(mlp_tos.read_bytes()) != MLP_TOS_SHA256:
            return 422, {"state": "HOLD", "reason": "EXACT_MLP_BINDING_REQUIRED", "effect_ack_done": False, "external_effect": "NONE"}
    except OSError:
        return 503, {"state": "HOLD", "reason": "MLP_TOS_UNREADABLE", "effect_ack_done": False, "external_effect": "NONE"}

    with STATE.lock:
        if active_atari_boots() >= ATARI_MAX_CONCURRENT_BOOTS:
            return 429, {"state": "HOLD", "reason": "ATARI_BOOT_CAPACITY_REACHED", "effect_ack_done": False, "external_effect": "NONE"}
        boot = AtariBoot(
            boot_id=secrets.token_hex(16),
            started_utc=utc_now(),
            workdir=Path(tempfile.mkdtemp(prefix="qikvrt-atari-boot-")),
        )
        boot.append_log("ATARI_BOOT_REQUEST_ACCEPTED")
        boot.append_log("MLP.TOS_SHA256=" + MLP_TOS_SHA256)
        STATE.atari_boots[boot.boot_id] = boot

    environment = dict(os.environ)
    environment.update({
        "HATARI_BIN": hatari,
        "EMUTOS_ROM": str(rom),
        "MLP_TOS": str(mlp_tos),
        "MLP_TOS_CHECKSUM": str(checksum),
        "QIKVRT_MLP_WORKDIR": str(boot.workdir),
        "QIKVRT_HATARI_TIMEOUT_SECONDS": "60",
    })
    try:
        process = subprocess.Popen(
            [str(launcher)],
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        with STATE.lock:
            boot.state = "HOLD"
            boot.reason = f"HATARI_LAUNCH_FAILED:{type(exc).__name__}"
            boot.append_log(boot.reason)
            return 503, boot.projection()
    with STATE.lock:
        boot.process = process
        boot.append_log("HATARI_PROCESS_STARTED")
    threading.Thread(target=finish_atari_boot, args=(boot,), daemon=True, name=f"qikvrt-atari-{boot.boot_id}").start()
    with STATE.lock:
        return 202, boot.projection()


class Handler(BaseHTTPRequestHandler):
    server_version = "QIKVRTEffectAckTerminal/1.0"

    def _json(
        self,
        code: int,
        body: dict[str, Any],
        *,
        state: str | None = None,
        record_hash: str | None = None,
        commit_token: str | None = None,
    ) -> None:
        payload = json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Access-Control-Allow-Origin", "https://github.com")
        self.send_header("Access-Control-Expose-Headers", "Effect-Ack, Link")
        self.send_header("Link", "</.well-known/effect-ack>; rel=\"effect-ack\"; type=\"application/json\"")
        if state and record_hash:
            state_token = {
                "EFFECT_NACK": "nack",
                "EFFECT_ACK_CONTINUE": "continue",
                "EFFECT_ACK_DONE": "done",
                "EFFECT_ACK_ISOLATE": "isolate",
                "EFFECT_ACK_BLOCK": "block",
            }[state]
            value = f"v=1, state={state_token}, hash={sf_bytes(bytes.fromhex(record_hash))}"
            if commit_token is not None:
                value += f", token={sf_bytes(commit_token.encode('ascii'))}"
            self.send_header("Effect-Ack", value)
        self.end_headers()
        self.wfile.write(payload)

    def _read_body(self) -> dict[str, Any]:
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("Transfer-Encoding unsupported")
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length required")
        length = int(raw_length)
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
        self.send_header("Access-Control-Allow-Origin", "https://github.com")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Effect-Ack-Request")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/.well-known/effect-ack":
            self._json(200, {
                "schema": "qikvrt_effect_ack_http_capability_v1",
                "versions": [1],
                "modes": ["prepare", "commit"],
                "protected_effects": ["terminal_input"],
                "external_effects": "NONE",
                "record_template": "/effect-ack/records/{sha256}",
            })
            return
        atari_status_prefix = "/qikvrt/atari/status/"
        if self.path.startswith(atari_status_prefix):
            boot_id = self.path[len(atari_status_prefix):]
            if not ATARI_BOOT_ID.fullmatch(boot_id):
                self._json(400, {"state": "HOLD", "reason": "INVALID_ATARI_BOOT_ID", "effect_ack_done": False})
                return
            with STATE.lock:
                boot = STATE.atari_boots.get(boot_id)
                body = boot.projection() if boot is not None else None
            if body is None:
                self._json(404, {"state": "HOLD", "reason": "ATARI_BOOT_NOT_FOUND", "effect_ack_done": False})
            else:
                self._json(200, body)
            return
        if self.path == "/terminal/state":
            head = git_read("rev-parse", "HEAD")
            tree = git_read("rev-parse", "HEAD^{tree}")
            with STATE.lock:
                body = {
                    "schema": "qikvrt_terminal_backend_state_v1",
                    "events": len(STATE.events),
                    "last_event": STATE.events[-1] if STATE.events else None,
                    "repository_head": head,
                    "repository_tree": tree,
                    "external_effects": "NONE",
                }
            self._json(200, body)
            return
        prefix = "/effect-ack/records/"
        if self.path.startswith(prefix):
            digest = self.path[len(prefix):]
            with STATE.lock:
                body = STATE.records.get(digest)
            if body is None:
                self._json(404, {"state": "HOLD", "reason": "record not found"})
            else:
                self._json(200, body, state=body["state"], record_hash=digest)
            return
        self._json(404, {"state": "HOLD", "reason": "not found"})

    def do_POST(self) -> None:
        try:
            if self.path == "/qikvrt/atari/boot":
                self._atari_boot(self._read_body())
                return
            request_binding = parse_effect_ack_request(self.headers.get("Effect-Ack-Request"))
            body = self._read_body()
            if self.path == "/terminal/prepare":
                if request_binding["mode"] != "prepare":
                    raise ValueError("prepare endpoint requires mode=prepare")
                self._prepare(body)
                return
            if self.path == "/terminal/commit":
                if request_binding["mode"] != "commit":
                    raise ValueError("commit endpoint requires mode=commit")
                self._commit(body, request_binding)
                return
            self._json(404, {"state": "HOLD", "reason": "not found"})
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            self._json(400, {"state": "HOLD", "ordinary_release": False, "reason": str(exc)})

    def _atari_boot(self, body: dict[str, Any]) -> None:
        if body.get("schema") != "qikvrt.atari-terminal-boot.v1" or body.get("mlp_sha256") != MLP_TOS_SHA256:
            self._json(422, {"state": "HOLD", "reason": "EXACT_MLP_BINDING_REQUIRED"})
            return
        status, response = start_atari_boot()
        self._json(status, response)

    def _prepare(self, body: dict[str, Any]) -> None:
        if body.get("schema") != "qikvrt_terminal_input_v1":
            digest, record = STATE.record(
                state="EFFECT_ACK_BLOCK",
                input_hash=sha256(canonical_json(body)),
                ordinary_release=False,
                reason="unsupported terminal schema",
            )
            self._json(422, {"record": record, "record_hash": digest}, state=record["state"], record_hash=digest)
            return
        input_hash = sha256(canonical_json(body))
        with STATE.lock:
            digest, record = STATE.record(
                state="EFFECT_ACK_DONE",
                input_hash=input_hash,
                ordinary_release=True,
                reason="loopback terminal input satisfies bounded local policy",
            )
            token = STATE.make_token(input_hash, digest)
        response = {
            "state": "EFFECT_ACK_DONE",
            "ordinary_release": False,
            "commit_token": token,
            "record_hash": digest,
            "record_url": f"/effect-ack/records/{digest}",
            "expires_in_seconds": TOKEN_TTL_SECONDS,
            "external_effect": "NONE",
        }
        self._json(200, response, state="EFFECT_ACK_DONE", record_hash=digest, commit_token=token)

    def _commit(self, body: dict[str, Any], binding: dict[str, Any]) -> None:
        token = binding["token"]
        record_hash = binding["hash"]
        commit_input_hash = sha256(canonical_json(body))
        with STATE.lock:
            prepared = STATE.prepared.get(token)
            if prepared is None or prepared.used or prepared.expires_at < time.time() or not hmac.compare_digest(prepared.record_hash, record_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "invalid stale used or mismatched token"})
                return
            if not hmac.compare_digest(prepared.input_hash, commit_input_hash):
                self._json(409, {"state": "HOLD", "ordinary_release": False, "reason": "commit payload differs from exact prepared payload"})
                return
            prepared.used = True
            event = {
                "event_id": len(STATE.events) + 1,
                "kind": "TERMINAL_INPUT_ACCEPTED",
                "record_hash": record_hash,
                "input_hash": commit_input_hash,
                "text": str(body.get("text", ""))[:4096],
                "audio_present": body.get("audio") is not None,
                "video_present": body.get("video") is not None,
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "external_effect": "NONE",
            }
            STATE.events.append(event)
            digest, record = STATE.record(
                state="EFFECT_ACK_DONE",
                input_hash=prepared.input_hash,
                ordinary_release=True,
                reason="single-use exact-bound loopback commit executed",
            )
        self._json(
            200,
            {"state": "EFFECT_ACK_DONE", "ordinary_release": True, "post_effect": event, "successor_record": record},
            state="EFFECT_ACK_DONE",
            record_hash=digest,
        )

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("BLOCK: reference terminal bridge is loopback-only")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(json.dumps({"state": "READY", "host": args.host, "port": args.port, "external_effects": "NONE"}, sort_keys=True), flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
