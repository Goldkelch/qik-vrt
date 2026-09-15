#!/usr/bin/env python3
"""Read-only SSE receipt relay; Linux file notifications, never periodic scans.

Control frames report transport boundaries/gaps, not native repository events.
An unsupported notification backend fails closed; it never falls back to polling.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import select
import struct
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class ReplayGap(ValueError):
    """The journal cannot establish the requested contiguous replay."""


def valid_event(obj: dict) -> bool:
    required = {"schema", "event_id", "observed_at", "repository", "subject", "phase", "verb", "causal_state", "source", "productive_effect", "effect_ack", "payload"}
    return (isinstance(obj, dict) and obj.get("schema") == "qikvrt_live_event_v1"
            and required.issubset(obj) and isinstance(obj["event_id"], str)
            and 0 < len(obj["event_id"]) <= 512
            and not any(c in obj["event_id"] for c in "\r\n\0"))


def iter_events(path: Path, after: str | None = None):
    # Parse the whole stable read before yielding: malformed history must not
    # release a partial apparently successful replay. Ignore an unfinished tail.
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw_lines = fh.readlines()
    except FileNotFoundError:
        if after is not None:
            raise ReplayGap("JOURNAL_MISSING")
        return
    records, identities = [], {}
    for raw in raw_lines:
        if not raw.endswith("\n"):
            break
        if not raw.strip():
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ReplayGap("INVALID_JSONL") from exc
        if not valid_event(obj):
            raise ReplayGap("INVALID_EVENT")
        canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False)
        eid = obj["event_id"]
        if eid in identities:
            if identities[eid] != canonical:
                raise ReplayGap("EVENT_ID_CONFLICT")
            continue
        identities[eid] = canonical
        records.append(obj)
    if after is not None and after not in identities:
        raise ReplayGap("CURSOR_NOT_FOUND")
    start = 0 if after is None else next(i + 1 for i, e in enumerate(records) if e["event_id"] == after)
    yield from records[start:]


class JournalWatch:
    """Watch the parent before the initial read, including atomic replacement."""
    # inotify(7): data writes/close, creation/removal/rename, parent invalidation.
    MASK = 0x00000002 | 0x00000008 | 0x00000040 | 0x00000080 | 0x00000100 | 0x00000200 | 0x00000400 | 0x00000800
    INVALID = 0x00000400 | 0x00000800 | 0x00004000 | 0x00008000

    def __init__(self, path: Path):
        if not sys.platform.startswith("linux"):
            raise OSError("EVENT_NOTIFICATION_BACKEND_UNAVAILABLE")
        libc = ctypes.CDLL(None, use_errno=True)
        libc.inotify_init1.argtypes = [ctypes.c_int]
        libc.inotify_init1.restype = ctypes.c_int
        libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        libc.inotify_add_watch.restype = ctypes.c_int
        self.fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), "inotify_init1")
        self.name = os.fsencode(path.name)
        if libc.inotify_add_watch(self.fd, os.fsencode(path.parent), self.MASK) < 0:
            err = ctypes.get_errno()
            self.close()
            raise OSError(err, "inotify_add_watch")

    def wait(self, timeout: float = 15.0) -> bool:
        # A timeout emits only a transport keepalive, never a journal/API read.
        if not select.select([self.fd], [], [], timeout)[0]:
            return False
        changed = False
        while True:
            try:
                data = os.read(self.fd, 65536)
            except BlockingIOError:
                return changed
            offset = 0
            while offset < len(data):
                _, mask, _, size = struct.unpack_from("iIII", data, offset)
                name = data[offset + 16:offset + 16 + size].split(b"\0", 1)[0]
                offset += 16 + size
                if mask & self.INVALID:
                    raise ReplayGap("NOTIFICATION_GAP")
                changed = changed or name == self.name

    def close(self):
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    events_path: Path

    def control(self, kind: str, **payload):
        self.wfile.write((f"event: {kind}\ndata: " + json.dumps(payload, separators=(",", ":")) + "\n\n").encode())
        self.wfile.flush()

    def do_GET(self):
        if self.path not in ("/events", "/events/"):
            self.send_error(404)
            return
        cursor = self.headers.get("Last-Event-ID") or None
        if cursor and (len(cursor) > 512 or any(c in cursor for c in "\r\n\0")):
            self.send_error(400, "INVALID_CURSOR")
            return
        try:
            watcher = JournalWatch(self.events_path)
        except (OSError, AttributeError):
            self.send_error(503, "EVENT_NOTIFICATION_BACKEND_UNAVAILABLE")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            while True:
                for item in iter_events(self.events_path, cursor):
                    payload = json.dumps(item, separators=(",", ":"), ensure_ascii=False)
                    self.wfile.write(f"id: {item['event_id']}\nevent: qikvrt\ndata: {payload}\n\n".encode())
                    cursor = item["event_id"]
                self.control("qikvrt-ready", schema="qikvrt_stream_boundary_v1", last_event_id=cursor)
                while not watcher.wait():
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (ReplayGap, OSError, UnicodeError) as exc:
            try:
                self.control("qikvrt-gap", reason=str(exc), effect_ack="PENDING")
            except OSError:
                pass
        finally:
            watcher.close()
            self.close_connection = True

    def log_message(self, fmt, *args):
        return


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--events", default="state/live/QIKVRT_LIVE_EVENTS.jsonl")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    a = p.parse_args()
    Handler.events_path = Path(a.events).resolve()
    server = ThreadingHTTPServer((a.host, a.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
