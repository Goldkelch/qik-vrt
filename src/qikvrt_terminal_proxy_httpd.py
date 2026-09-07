#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Authenticated HTTP/WebSocket boundary for the QIK-VRT universal terminal.

Direct noVNC exposure remains loopback-only.  This proxy is the only listener
intended for a non-loopback bind.  Such a bind is refused unless a Basic-auth
secret is supplied.  noVNC WebSockets and the existing EFFECT_ACK HTTP
semantics are delegated without creating a second effect protocol.
"""
from __future__ import annotations

import argparse
import base64
import hmac
import http.client
import json
import os
import select
import socket
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

LOOPBACK_NAMES = {"127.0.0.1", "localhost", "::1"}
HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
MAX_BODY = 2 * 1024 * 1024
MAX_SQL = 64 * 1024
TUNNEL_BUFFER = 64 * 1024
STATE_DIR = Path(os.environ.get("QIKVRT_STATE_DIR", "/var/lib/qikvrt/state"))


def load_password() -> str:
    direct = os.environ.get("QIKVRT_PROXY_PASSWORD", "")
    path = os.environ.get("QIKVRT_PROXY_PASSWORD_FILE", "")
    if direct and path:
        raise SystemExit(
            "BLOCK: configure QIKVRT_PROXY_PASSWORD or QIKVRT_PROXY_PASSWORD_FILE, not both"
        )
    if path:
        with open(path, encoding="utf-8") as handle:
            direct = handle.read().rstrip("\r\n")
    return direct


class ProxyServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        username: str,
        password: str,
        novnc_host: str,
        novnc_port: int,
        effect_host: str,
        effect_port: int,
    ) -> None:
        super().__init__(address, Handler)
        self.auth_username = username
        self.auth_password = password
        self.novnc_host = novnc_host
        self.novnc_port = novnc_port
        self.effect_host = effect_host
        self.effect_port = effect_port


class Handler(BaseHTTPRequestHandler):
    server_version = "QIKVRTTerminalProxy/1.0"
    protocol_version = "HTTP/1.1"

    @property
    def proxy(self) -> ProxyServer:
        return self.server  # type: ignore[return-value]

    def _json(self, code: int, value: object) -> None:
        body = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _health(self) -> None:
        self._json(
            200,
            {
                "schema": "qikvrt_terminal_proxy_health_v1",
                "state": "READY",
                "authentication_required": bool(self.proxy.auth_password),
                "novnc_upstream": "127.0.0.1",
                "effect_ack_upstream": "127.0.0.1",
                "external_effect_claimed": False,
                "pass": False,
                "final_pass": False,
                "effect_ack_done": False,
            },
        )

    def _authorized(self) -> bool:
        if not self.proxy.auth_password:
            return True
        raw = self.headers.get("Authorization", "")
        expected = (
            "Basic "
            + base64.b64encode(
                f"{self.proxy.auth_username}:{self.proxy.auth_password}".encode("utf-8")
            ).decode("ascii")
        )
        return hmac.compare_digest(raw, expected)

    def _challenge(self) -> None:
        body = b"authentication required\n"
        self.send_response(401)
        self.send_header(
            "WWW-Authenticate", 'Basic realm="QIK-VRT universal terminal"'
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self, maximum: int = MAX_BODY) -> bytes:
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("chunked request bodies are not accepted")
        raw = self.headers.get("Content-Length")
        if raw is None:
            return b""
        length = int(raw)
        if length < 0 or length > maximum:
            raise ValueError("request body outside bounded size")
        return self.rfile.read(length)

    def _state_file(self, name: str) -> None:
        path = STATE_DIR / name
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self._json(503, {"state": "REOBSERVE", "reason": str(exc)})
            return
        self._json(200, value)

    def _sql(self) -> None:
        if self.command == "GET":
            self._json(
                200,
                {
                    "schema": "qikvrt_sql_terminal_v1",
                    "database": "PostgreSQL",
                    "endpoint": "/qikvrt/sql",
                    "method": "POST",
                    "request": {"sql": "SELECT 1 AS qikvrt;"},
                    "scope": "authenticated bounded database role",
                    "sql92_conformance_claimed": False,
                    "external_effect_claimed": False,
                },
            )
            return
        if self.command != "POST":
            self.send_error(405)
            return
        try:
            raw = self._read_body(MAX_SQL)
            value = json.loads(raw.decode("utf-8"))
            sql = value.get("sql") if isinstance(value, dict) else None
            if not isinstance(sql, str) or not sql.strip() or len(sql.encode("utf-8")) > MAX_SQL:
                raise ValueError("non-empty bounded SQL string required")
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            self._json(400, {"state": "HOLD", "reason": str(exc)})
            return
        try:
            process = subprocess.run(
                [
                    "psql",
                    "-X",
                    "-q",
                    "-h",
                    "127.0.0.1",
                    "-p",
                    os.environ.get("QIKVRT_POSTGRES_PORT", "5432"),
                    "-U",
                    "qikvrt_terminal",
                    "-d",
                    "qikvrt_terminal",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "--csv",
                    "-c",
                    sql,
                ],
                text=True,
                input="",
                capture_output=True,
                timeout=10,
                check=False,
                env={**os.environ, "PGCONNECT_TIMEOUT": "3"},
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self._json(503, {"state": "REOBSERVE", "reason": str(exc)})
            return
        self._json(
            200 if process.returncode == 0 else 422,
            {
                "schema": "qikvrt_sql_terminal_result_v1",
                "returncode": process.returncode,
                "stdout": process.stdout[-256 * 1024 :],
                "stderr": process.stderr[-64 * 1024 :],
                "database_role": "qikvrt_terminal",
                "external_effect_claimed": False,
                "pass": False,
                "final_pass": False,
                "effect_ack_done": False,
            },
        )

    def _local_api(self) -> bool:
        path = self.path.split("?", 1)[0]
        if path == "/qikvrt/runtime":
            self._state_file("runtime.json")
            return True
        if path == "/qikvrt/services":
            self._state_file("services.json")
            return True
        if path == "/qikvrt/mesh":
            self._state_file("repository-mirror.json")
            return True
        if path == "/qikvrt/sql":
            self._sql()
            return True
        return False

    def _upstream(self) -> tuple[str, int]:
        path = self.path.split("?", 1)[0]
        if (
            path == "/.well-known/effect-ack"
            or path.startswith("/effect-ack/")
            or path.startswith("/terminal/")
        ):
            return self.proxy.effect_host, self.proxy.effect_port
        return self.proxy.novnc_host, self.proxy.novnc_port

    def _forward_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        for name, value in self.headers.items():
            lower = name.lower()
            if lower in HOP_HEADERS or lower in {"authorization", "host"}:
                continue
            headers[name] = value
        headers["Host"] = "127.0.0.1"
        headers["X-Forwarded-For"] = self.client_address[0]
        headers["X-Forwarded-Proto"] = self.headers.get(
            "X-Forwarded-Proto", "http"
        )
        return headers

    def _proxy_http(self) -> None:
        try:
            body = self._read_body()
        except (ValueError, OSError) as exc:
            self.send_error(400, str(exc))
            return
        host, port = self._upstream()
        conn = http.client.HTTPConnection(host, port, timeout=15)
        try:
            conn.request(
                self.command, self.path, body=body, headers=self._forward_headers()
            )
            response = conn.getresponse()
            payload = response.read()
            self.send_response(response.status, response.reason)
            for name, value in response.getheaders():
                lower = name.lower()
                if lower in HOP_HEADERS or lower == "content-length":
                    continue
                self.send_header(name, value)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)
        except (OSError, http.client.HTTPException) as exc:
            self.send_error(502, f"upstream unavailable: {exc}")
        finally:
            conn.close()

    def _proxy_websocket(self) -> None:
        host, port = self._upstream()
        upstream = socket.create_connection((host, port), timeout=15)
        upstream.settimeout(None)
        request = [f"{self.command} {self.path} HTTP/1.1\r\n"]
        for name, value in self.headers.items():
            if name.lower() in {"authorization", "proxy-authorization", "host"}:
                continue
            request.append(f"{name}: {value}\r\n")
        request.append("Host: 127.0.0.1\r\n\r\n")
        upstream.sendall("".join(request).encode("iso-8859-1"))
        response = bytearray()
        while b"\r\n\r\n" not in response:
            block = upstream.recv(4096)
            if not block:
                break
            response.extend(block)
            if len(response) > 64 * 1024:
                raise OSError("upstream WebSocket handshake exceeds bound")
        self.connection.sendall(response)
        if not response.startswith(
            (b"HTTP/1.1 101", b"HTTP/1.0 101")
        ):
            upstream.close()
            self.close_connection = True
            return

        peers = [self.connection, upstream]
        try:
            while True:
                ready, _, _ = select.select(peers, [], [], 60)
                if not ready:
                    continue
                for source in ready:
                    target = upstream if source is self.connection else self.connection
                    data = source.recv(TUNNEL_BUFFER)
                    if not data:
                        return
                    target.sendall(data)
        finally:
            upstream.close()
            self.close_connection = True

    def _dispatch(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/healthz":
            self._health()
            return
        if not self._authorized():
            self._challenge()
            return
        if self._local_api():
            return
        connection = self.headers.get("Connection", "").lower()
        upgrade = self.headers.get("Upgrade", "").lower()
        if "upgrade" in connection and upgrade == "websocket":
            try:
                self._proxy_websocket()
            except OSError as exc:
                self.send_error(502, f"WebSocket upstream unavailable: {exc}")
            return
        self._proxy_http()

    do_GET = _dispatch
    do_HEAD = _dispatch
    do_POST = _dispatch
    do_OPTIONS = _dispatch

    def log_message(self, fmt: str, *args: object) -> None:
        print(
            json.dumps(
                {
                    "component": "qikvrt-terminal-proxy",
                    "remote": self.client_address[0],
                    "message": fmt % args,
                },
                sort_keys=True,
            ),
            flush=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--host", default=os.environ.get("QIKVRT_PROXY_HOST", "127.0.0.1")
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("QIKVRT_PROXY_PORT", os.environ.get("PORT", "8080"))),
    )
    parser.add_argument("--novnc-host", default="127.0.0.1")
    parser.add_argument(
        "--novnc-port",
        type=int,
        default=int(os.environ.get("QIKVRT_NOVNC_PORT", "6080")),
    )
    parser.add_argument("--effect-host", default="127.0.0.1")
    parser.add_argument(
        "--effect-port",
        type=int,
        default=int(os.environ.get("QIKVRT_HTTP_PORT", "8771")),
    )
    args = parser.parse_args()

    password = load_password()
    username = os.environ.get("QIKVRT_PROXY_USERNAME", "qikvrt")
    if args.host not in LOOPBACK_NAMES and not password:
        raise SystemExit(
            "BLOCK: non-loopback terminal proxy requires Basic-auth secret"
        )
    if not username:
        raise SystemExit("BLOCK: terminal proxy username must be non-empty")

    server = ProxyServer(
        (args.host, args.port),
        username=username,
        password=password,
        novnc_host=args.novnc_host,
        novnc_port=args.novnc_port,
        effect_host=args.effect_host,
        effect_port=args.effect_port,
    )
    print(
        json.dumps(
            {
                "schema": "qikvrt_terminal_proxy_start_v1",
                "state": "READY",
                "bind_host": args.host,
                "port": args.port,
                "authentication_required": bool(password),
                "external_effect_claimed": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
