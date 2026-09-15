#!/usr/bin/env python3
"""Dependency-free append-driven SSE relay for QIK-VRT JSONL receipts.

Observational transport only: it never creates repository effects. The relay
blocks on the append stream; it does not poll repository state to manufacture
progress.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def valid_event(obj: dict) -> bool:
    required = {"schema", "event_id", "observed_at", "repository", "subject", "phase", "verb", "causal_state", "source", "productive_effect", "effect_ack", "payload"}
    return obj.get("schema") == "qikvrt_live_event_v1" and required.issubset(obj)


def decode_event(raw: str):
    raw = raw.strip()
    if not raw:
        return None
    obj = json.loads(raw)
    return obj if valid_event(obj) else None


def seek_after(fh, after: str | None) -> None:
    """Position immediately after the requested event, or at EOF if absent."""
    fh.seek(0)
    if after is None:
        return
    while True:
        raw = fh.readline()
        if not raw:
            return
        event = decode_event(raw)
        if event and event["event_id"] == after:
            return


def follow_events(path: Path, after: str | None = None):
    """Yield existing receipts then block for append notification from the pipe/file.

    Production deployment supplies the event stream as a FIFO/pipe from the
    repository-native monitor. Regular files are accepted for deterministic
    replay tests and terminate at EOF rather than polling for later changes.
    """
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fh:
        seek_after(fh, after)
        while True:
            raw = fh.readline()
            if not raw:
                return
            event = decode_event(raw)
            if event:
                yield event


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    events_path: Path

    def do_GET(self):
        if self.path not in ("/events", "/events/"):
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        last = self.headers.get("Last-Event-ID") or None
        try:
            for event in follow_events(self.events_path, last):
                payload = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
                frame = f"id: {event['event_id']}\nevent: qikvrt\ndata: {payload}\n\n".encode()
                self.wfile.write(frame)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, fmt, *args):
        return


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--events", default="state/live/QIKVRT_LIVE_EVENTS.jsonl")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    a = p.parse_args()
    Handler.events_path = Path(a.events)
    server = ThreadingHTTPServer((a.host, a.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
