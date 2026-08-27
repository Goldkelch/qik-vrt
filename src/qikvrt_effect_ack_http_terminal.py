#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""CORS/PNA adapter for the loopback-only QIKVRT Effect-Ack backend.

The protocol core is byte-preserved in
``qikvrt_effect_ack_http_terminal_core``.  This adapter changes only the HTTP
response envelope needed by a real Firefox extension page: non-credentialed
cross-origin loopback requests receive explicit CORS and Private-Network
Access response fields.  The server remains bound to loopback, the protected
effect remains ``terminal_input``, and ``external_effect`` remains ``NONE``.
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

_CORE_PATH = Path(__file__).with_name("qikvrt_effect_ack_http_terminal_core.py")
_SPEC = importlib.util.spec_from_file_location(
    "qikvrt_effect_ack_http_terminal_core",
    _CORE_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("QIKVRT Effect-Ack backend core unavailable")
core = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = core
_SPEC.loader.exec_module(core)

# Preserve the public contract used by repository tests and callers.
MAX_BODY = core.MAX_BODY
TOKEN_TTL_SECONDS = core.TOKEN_TTL_SECONDS
HOST = core.HOST
DEFAULT_PORT = core.DEFAULT_PORT
SF_KEY = core.SF_KEY
canonical_json = core.canonical_json
sha256 = core.sha256
sf_bytes = core.sf_bytes
parse_sf_bytes = core.parse_sf_bytes
parse_effect_ack_request = core.parse_effect_ack_request
git_read = core.git_read
Prepared = core.Prepared
State = core.State
STATE = core.STATE


class Handler(core.Handler):
    """Core handler with an explicit non-credentialed loopback CORS envelope."""

    def _sync_state(self) -> None:
        # Unit tests replace module.STATE between cases.  Keep the byte-preserved
        # core's global state synchronized before inherited request processing.
        core.STATE = globals()["STATE"]

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header(
            "Vary",
            "Origin, Access-Control-Request-Private-Network",
        )

    def _json(
        self,
        code: int,
        body: dict[str, Any],
        *,
        state: str | None = None,
        record_hash: str | None = None,
        commit_token: str | None = None,
    ) -> None:
        payload = core.json.dumps(
            body,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self._cors()
        self.send_header("Access-Control-Expose-Headers", "Effect-Ack, Link")
        self.send_header(
            "Link",
            "</.well-known/effect-ack>; rel=\"effect-ack\"; "
            "type=\"application/json\"",
        )
        if state and record_hash:
            state_token = {
                "EFFECT_NACK": "nack",
                "EFFECT_ACK_CONTINUE": "continue",
                "EFFECT_ACK_DONE": "done",
                "EFFECT_ACK_ISOLATE": "isolate",
                "EFFECT_ACK_BLOCK": "block",
            }[state]
            value = (
                f"v=1, state={state_token}, "
                f"hash={core.sf_bytes(bytes.fromhex(record_hash))}"
            )
            if commit_token is not None:
                value += (
                    ", token="
                    + core.sf_bytes(commit_token.encode("ascii"))
                )
            self.send_header("Effect-Ack", value)
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors()
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Effect-Ack-Request",
        )
        self.send_header(
            "Access-Control-Allow-Methods",
            "GET, POST, OPTIONS",
        )
        self.send_header("Access-Control-Max-Age", "600")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        self._sync_state()
        super().do_GET()

    def do_POST(self) -> None:
        self._sync_state()
        super().do_POST()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("BLOCK: reference terminal bridge is loopback-only")
    server = core.ThreadingHTTPServer((args.host, args.port), Handler)
    print(
        core.json.dumps(
            {
                "state": "READY",
                "host": args.host,
                "port": args.port,
                "external_effects": "NONE",
                "cors": "NON_CREDENTIALED_LOOPBACK_ONLY",
                "private_network_access": "EXPLICIT_ALLOW_RESPONSE",
            },
            sort_keys=True,
        ),
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
