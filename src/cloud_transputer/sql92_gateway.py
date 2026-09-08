#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Loopback SQL terminal adapter with exact-bound EFFECT_ACK gating.

The public path remains the authenticated Firefox/noVNC terminal. This adapter
provides a local browser UI plus Prepare -> Commit -> Readback for one bounded
SQL statement. EFFECT_ACK_DONE is scoped to the local database operation and
its readback; it is not repository, publication, deployment, or global QIK-VRT
completion.
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
import subprocess
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

HOST = "127.0.0.1"
DEFAULT_PORT = 8772
MAX_BODY = 64 * 1024
MAX_SQL = 8192
TOKEN_TTL = 120
ALLOWED_PREFIXES = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP")
STATE_CHANGING = ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sf_bytes(value: bytes) -> str:
    return ":" + base64.b64encode(value).decode("ascii") + ":"


def parse_sf_bytes(value: str) -> bytes:
    if len(value) < 2 or not (value.startswith(":") and value.endswith(":")):
        raise ValueError("Structured Field Byte Sequence required")
    return base64.b64decode(value[1:-1], validate=True)


def parse_effect_ack_request(raw: str | None) -> dict[str, Any]:
    if not raw:
        raise ValueError("Effect-Ack-Request required")
    members: dict[str, str] = {}
    for part in raw.split(","):
        if "=" not in part:
            raise ValueError("malformed Effect-Ack-Request")
        key, value = part.split("=", 1)
        key, value = key.strip().lower(), value.strip()
        if key in members:
            raise ValueError("duplicate Effect-Ack-Request member")
        members[key] = value
    if members.get("v") != "1":
        raise ValueError("unsupported Effect-Ack version")
    mode = members.get("mode")
    if mode == "prepare" and set(members) == {"v", "mode"}:
        return {"mode": "prepare"}
    if mode == "commit" and set(members) == {"v", "mode", "token", "hash"}:
        token = parse_sf_bytes(members["token"]).decode("ascii")
        digest = parse_sf_bytes(members["hash"])
        if len(digest) != 32:
            raise ValueError("commit hash must be SHA-256")
        return {"mode": "commit", "token": token, "hash": digest.hex()}
    raise ValueError("invalid Effect-Ack prepare/commit shape")


def normalize_sql(sql: str, *, readback: bool = False) -> tuple[str, str]:
    if not isinstance(sql, str):
        raise ValueError("SQL must be text")
    text = sql.strip()
    if not text or len(text.encode("utf-8")) > MAX_SQL or "\x00" in text or "\\" in text:
        raise ValueError("SQL outside bounded terminal contract")
    if text.endswith(";"):
        text = text[:-1].rstrip()
    if ";" in text:
        raise ValueError("exactly one SQL statement is allowed")
    match = re.match(r"^([A-Za-z]+)\b", text)
    if not match:
        raise ValueError("SQL statement class not recognized")
    prefix = match.group(1).upper()
    if prefix not in ALLOWED_PREFIXES:
        raise ValueError("SQL statement class is not admitted")
    if readback and prefix != "SELECT":
        raise ValueError("readback_sql must be SELECT")
    return text, prefix


def validate_request(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema") != "qikvrt_sql92_request_v1":
        raise ValueError("unsupported SQL terminal request schema")
    sql, sql_class = normalize_sql(value.get("sql"))
    readback_sql, _ = normalize_sql(value.get("readback_sql"), readback=True)
    return {
        "schema": "qikvrt_sql92_request_v1",
        "sql": sql,
        "readback_sql": readback_sql,
        "sql_class": sql_class,
    }


@dataclass
class Prepared:
    request_hash: str
    expires_at: float
    used: bool = False


class GatewayState:
    def __init__(self, state_dir: Path, pg_port: int) -> None:
        self.state_dir = state_dir
        self.receipt_dir = state_dir / "sql92" / "receipts"
        self.receipt_dir.mkdir(parents=True, exist_ok=True)
        self.pg_port = pg_port
        self.secret = secrets.token_bytes(32)
        self.prepared: dict[str, Prepared] = {}
        self.lock = threading.Lock()
        self.sequence = 0

    def token(self, request_hash: str) -> str:
        expiry = int(time.time()) + TOKEN_TTL
        nonce = secrets.token_bytes(24)
        payload = nonce + expiry.to_bytes(8, "big") + bytes.fromhex(request_hash)
        mac = hmac.new(self.secret, payload, hashlib.sha256).digest()
        token = base64.urlsafe_b64encode(payload + mac).decode("ascii").rstrip("=")
        self.prepared[token] = Prepared(request_hash, float(expiry))
        return token

    def run_psql(self, sql: str) -> list[str]:
        proc = subprocess.run(
            [
                "psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1",
                "-h", "127.0.0.1", "-p", str(self.pg_port), "-U", "qikvrt", "-d", "qikvrt",
            ],
            input=sql + ";\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
            env={**os.environ, "PGAPPNAME": "qikvrt-sql92-effect-ack"},
        )
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or "psql failed").strip()[:2048])
        return [line for line in proc.stdout.splitlines() if line.strip()]

    def persist_receipt(self, value: dict[str, Any]) -> str:
        encoded = canonical_json(value)
        digest = sha256_bytes(encoded)
        self.sequence += 1
        path = self.receipt_dir / f"{self.sequence:08d}-{digest}.json"
        path.write_bytes(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n")
        return digest


HTML = """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>QIK-VRT SQL92 Universal Terminal</title><style>
body{font:15px system-ui,sans-serif;margin:2rem;max-width:1000px;background:#111;color:#eee}textarea{width:100%;min-height:8rem;background:#181818;color:#eee;border:1px solid #555;padding:.75rem}button{margin:.5rem .5rem .5rem 0;padding:.6rem 1rem}pre{white-space:pre-wrap;background:#181818;padding:1rem;border:1px solid #444}a{color:#9cf}.grid{display:grid;gap:1rem;grid-template-columns:1fr 1fr}@media(max-width:760px){.grid{grid-template-columns:1fr}}</style></head>
<body><h1>QIK-VRT SQL92 / EFFECT_ACK terminal</h1>
<p>Loopback database surface inside the personalized Firefox terminal. Prepare is non-effecting; Commit is single-use and exact-bound; completion requires post-operation readback.</p>
<div class=\"grid\"><div><h2>SQL</h2><textarea id=\"sql\">SELECT 20 + 22 AS answer</textarea></div><div><h2>Readback SELECT</h2><textarea id=\"readback\">SELECT 20 + 22 AS answer</textarea></div></div>
<button id=\"prepare\">Prepare</button><button id=\"commit\" disabled>Commit + Readback</button><a href=\"/state\">state</a> · <a href=\"/.well-known/qikvrt-sql92\">capability</a>
<pre id=\"out\">READY</pre>
<script>
let prepared=null; const out=document.getElementById('out');
const body=()=>({schema:'qikvrt_sql92_request_v1',sql:document.getElementById('sql').value,readback_sql:document.getElementById('readback').value});
document.getElementById('prepare').onclick=async()=>{prepared=null;document.getElementById('commit').disabled=true;const r=await fetch('/prepare',{method:'POST',headers:{'Content-Type':'application/json','Effect-Ack-Request':'v=1, mode=prepare'},body:JSON.stringify(body())});const j=await r.json();out.textContent=JSON.stringify(j,null,2);if(r.ok){prepared=j;document.getElementById('commit').disabled=false;}};
document.getElementById('commit').onclick=async()=>{if(!prepared)return;const token=btoa(prepared.commit_token);const hash=btoa(String.fromCharCode(...prepared.request_hash.match(/../g).map(x=>parseInt(x,16))));const h=`v=1, mode=commit, token=:${token}:, hash=:${hash}:`;const r=await fetch('/commit',{method:'POST',headers:{'Content-Type':'application/json','Effect-Ack-Request':h},body:JSON.stringify(body())});const j=await r.json();out.textContent=JSON.stringify(j,null,2);prepared=null;document.getElementById('commit').disabled=true;};
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "QIKVRTSQL92Terminal/1.0"

    @property
    def state(self) -> GatewayState:
        return self.server.gateway_state  # type: ignore[attr-defined]

    def send_json(self, code: int, body: dict[str, Any], *, effect_state: str | None = None, digest: str | None = None, token: str | None = None) -> None:
        payload = json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if effect_state and digest:
            value = f"v=1, state={effect_state}, hash={sf_bytes(bytes.fromhex(digest))}"
            if token:
                value += f", token={sf_bytes(token.encode('ascii'))}"
            self.send_header("Effect-Ack", value)
        self.end_headers()
        self.wfile.write(payload)

    def read_json(self) -> dict[str, Any]:
        raw = self.headers.get("Content-Length")
        if raw is None:
            raise ValueError("Content-Length required")
        length = int(raw)
        if length < 1 or length > MAX_BODY:
            raise ValueError("body outside bounded terminal contract")
        if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
            raise ValueError("application/json required")
        value = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON object required")
        return value

    def do_GET(self) -> None:
        if self.path == "/":
            payload = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
        if self.path == "/.well-known/qikvrt-sql92":
            self.send_json(200, {
                "schema": "qikvrt_sql92_terminal_capability_v1",
                "modes": ["prepare", "commit", "readback"],
                "database": "qikvrt",
                "sql_profile": "SQL92_ORIENTED_POSTGRESQL_SUBSET",
                "full_sql92_conformance_claimed": False,
                "effect_ack": "EXACT_BOUND_SINGLE_USE_LOCAL_DATABASE_EFFECT",
                "transport_ack_is_effect_ack": False,
            })
            return
        if self.path == "/state":
            body: dict[str, Any] = {"schema": "qikvrt_sql92_terminal_state_v1"}
            for name in ("runtime.json", "authority-mirror.json"):
                path = self.state.state_dir / name
                key = name[:-5]
                try:
                    body[key] = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    body[key] = None
            body["receipt_count"] = len(list(self.state.receipt_dir.glob("*.json")))
            self.send_json(200, body)
            return
        self.send_json(404, {"state": "HOLD", "reason": "not found"})

    def do_POST(self) -> None:
        try:
            binding = parse_effect_ack_request(self.headers.get("Effect-Ack-Request"))
            request = validate_request(self.read_json())
            digest = sha256_bytes(canonical_json(request))
            if self.path == "/prepare":
                if binding["mode"] != "prepare":
                    raise ValueError("prepare endpoint requires mode=prepare")
                with self.state.lock:
                    token = self.state.token(digest)
                self.send_json(200, {
                    "schema": "qikvrt_sql92_prepare_receipt_v1",
                    "state": "PREPARED_NO_EFFECT",
                    "ordinary_release": False,
                    "commit_token": token,
                    "request_hash": digest,
                    "expires_in_seconds": TOKEN_TTL,
                    "sql_class": request["sql_class"],
                }, effect_state="continue", digest=digest, token=token)
                return
            if self.path == "/commit":
                if binding["mode"] != "commit":
                    raise ValueError("commit endpoint requires mode=commit")
                self.commit(request, digest, binding)
                return
            self.send_json(404, {"state": "HOLD", "reason": "not found"})
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            self.send_json(400, {"state": "HOLD", "ordinary_release": False, "reason": str(exc)})

    def commit(self, request: dict[str, Any], digest: str, binding: dict[str, Any]) -> None:
        token = binding["token"]
        with self.state.lock:
            prepared = self.state.prepared.get(token)
            if prepared is None or prepared.used or prepared.expires_at < time.time():
                self.send_json(409, {"state": "HOLD", "ordinary_release": False, "reason": "invalid stale or used token"})
                return
            if not hmac.compare_digest(prepared.request_hash, digest) or not hmac.compare_digest(binding["hash"], digest):
                self.send_json(409, {"state": "HOLD", "ordinary_release": False, "reason": "exact prepared request binding mismatch"})
                return
            prepared.used = True
        try:
            result_rows = self.state.run_psql(request["sql"])
            readback_rows = self.state.run_psql(request["readback_sql"])
        except (OSError, subprocess.SubprocessError, RuntimeError) as exc:
            receipt = {
                "schema": "qikvrt_sql92_effect_receipt_v1",
                "effect_ack_state": "EFFECT_NACK",
                "ordinary_release": False,
                "request_hash": digest,
                "sql_class": request["sql_class"],
                "reason": str(exc)[:2048],
                "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            receipt_hash = self.state.persist_receipt(receipt)
            self.send_json(503, {"receipt": receipt, "receipt_hash": receipt_hash}, effect_state="nack", digest=receipt_hash)
            return
        receipt = {
            "schema": "qikvrt_sql92_effect_receipt_v1",
            "effect_ack_state": "EFFECT_ACK_DONE",
            "effect_domain": "LOCAL_QIKVRT_DATABASE_ONLY",
            "ordinary_release": True,
            "request_hash": digest,
            "sql_class": request["sql_class"],
            "state_changing": request["sql_class"] in STATE_CHANGING,
            "result_rows": result_rows[:256],
            "readback_rows": readback_rows[:256],
            "result_sha256": sha256_bytes(canonical_json(result_rows)),
            "readback_sha256": sha256_bytes(canonical_json(readback_rows)),
            "authoritative_external_effect": False,
            "repository_effect": False,
            "publication_effect": False,
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        receipt_hash = self.state.persist_receipt(receipt)
        self.send_json(200, {"receipt": receipt, "receipt_hash": receipt_hash}, effect_state="done", digest=receipt_hash)

    def log_message(self, fmt: str, *args: Any) -> None:
        return


class Server(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], state: GatewayState) -> None:
        super().__init__(address, Handler)
        self.gateway_state = state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--pg-port", type=int, default=int(os.environ.get("QIKVRT_SQL_PORT", "5432")))
    parser.add_argument("--state-dir", default=os.environ.get("QIKVRT_STATE_DIR", "/var/lib/qikvrt/state"))
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("BLOCK: SQL92 terminal adapter is loopback-only")
    state = GatewayState(Path(args.state_dir), args.pg_port)
    print(json.dumps({"state": "READY", "host": args.host, "port": args.port, "external_effects": "LOCAL_DATABASE_ONLY"}, sort_keys=True), flush=True)
    Server((args.host, args.port), state).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
