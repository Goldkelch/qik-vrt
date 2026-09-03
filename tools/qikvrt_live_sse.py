#!/usr/bin/env python3
"""Minimal dependency-free SSE relay for QIK-VRT JSONL event receipts.

Observational transport only: it never creates repository effects.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def valid_event(obj: dict) -> bool:
    required = {"schema", "event_id", "observed_at", "repository", "subject", "phase", "verb", "causal_state", "source", "productive_effect", "effect_ack", "payload"}
    return obj.get("schema") == "qikvrt_live_event_v1" and required.issubset(obj)


def iter_events(path: Path, after: str | None = None):
    seen_after = after is None
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if not valid_event(obj):
                continue
            if not seen_after:
                if obj["event_id"] == after:
                    seen_after = True
                continue
            yield obj


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    events_path: Path
    poll_seconds: float

    def do_GET(self):
        if self.path not in ("/events", "/events/"):
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        last = self.headers.get("Last-Event-ID") or None
        sent = last
        try:
            while True:
                emitted = False
                for event in iter_events(self.events_path, sent):
                    payload = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
                    frame = f"id: {event['event_id']}\nevent: qikvrt\ndata: {payload}\n\n".encode()
                    self.wfile.write(frame); self.wfile.flush()
                    sent = event["event_id"]; emitted = True
                if not emitted:
                    self.wfile.write(b": keepalive\n\n"); self.wfile.flush()
                time.sleep(self.poll_seconds)
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, fmt, *args):
        return


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--events", default="state/live/QIKVRT_LIVE_EVENTS.jsonl")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--poll-seconds", type=float, default=0.5)
    a = p.parse_args()
    Handler.events_path = Path(a.events)
    Handler.poll_seconds = a.poll_seconds
    server = ThreadingHTTPServer((a.host, a.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
