#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Horizon-capable loopback wrapper for the QIK-VRT Effect-Ack terminal.

The wrapper changes only the browser-origin boundary. It keeps the existing
single-use Prepare -> Commit -> Readback implementation and remains bound to
127.0.0.1 with external_effect=NONE.
"""
from __future__ import annotations

import argparse
import json
import os
from http.server import ThreadingHTTPServer

import qikvrt_effect_ack_http_terminal as base

DEFAULT_ALLOWED_ORIGINS = {
    "https://github.com",
    "https://goldkelch.github.io",
    "https://horizon-by-qik-vrt.vercel.app",
}


def allowed_origins() -> set[str]:
    configured = {
        item.strip()
        for item in os.environ.get("QIKVRT_TERMINAL_ALLOWED_ORIGINS", "").split(",")
        if item.strip()
    }
    return DEFAULT_ALLOWED_ORIGINS | configured


class Handler(base.Handler):
    server_version = "QIKVRTMetatransistorTerminal/1.0"

    def _allowed_origin(self) -> str | None:
        origin = self.headers.get("Origin")
        if not origin:
            return "https://github.com"
        return origin if origin in allowed_origins() else None

    def send_header(self, keyword: str, value: str) -> None:
        if keyword.lower() == "access-control-allow-origin":
            origin = self._allowed_origin()
            if origin is None:
                return
            value = origin
        super().send_header(keyword, value)

    def end_headers(self) -> None:
        if self._allowed_origin() is not None:
            super().send_header("Vary", "Origin")
            if self.headers.get("Access-Control-Request-Private-Network") == "true":
                super().send_header("Access-Control-Allow-Private-Network", "true")
        super().end_headers()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=base.HOST)
    parser.add_argument("--port", type=int, default=base.DEFAULT_PORT)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("BLOCK: Metatransistor terminal bridge is loopback-only")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(
        json.dumps(
            {
                "state": "READY",
                "host": args.host,
                "port": args.port,
                "surface": "HORIZON_AND_FIREFOX",
                "external_effects": "NONE",
            },
            sort_keys=True,
        ),
        flush=True,
    )
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
