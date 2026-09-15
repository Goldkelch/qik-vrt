#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Event-driven, append-only QIK-VRT JSONL ingress and SSE projection.

Linux inotify wakes one reader. Idle consumers block; there is no timer, file
rescan, HTTP status request, or polling fallback. Input is a trusted local
producer channel, not an authenticated public webhook or authority grant.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import select
import stat
import struct
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_EVENT_BYTES = 65536
MAX_EVENTS = 10000


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def valid_event(obj: dict) -> bool:
    required = {"schema", "event_id", "observed_at", "repository", "subject",
                "phase", "verb", "causal_state", "source", "productive_effect",
                "effect_ack", "payload", "d0", "predecessor_event_ids"}
    return (isinstance(obj, dict) and obj.get("schema") == "qikvrt_live_event_v1"
            and required.issubset(obj) and isinstance(obj["event_id"], str)
            and 0 < len(obj["event_id"]) <= 256
            and not any(ord(c) < 32 for c in obj["event_id"]))


class EventFile:
    """One bounded, incremental reader; register notifications before reading.

    Truncation, replacement and notification overflow stop the reader. Producers
    must append; this class does not claim to authenticate or prevent in-place
    tampering by another process with write access to the source file.
    """
    def __init__(self, path: Path):
        self.path = Path(path).absolute()
        libc = ctypes.CDLL(None, use_errno=True)
        init = libc.inotify_init1
        init.argtypes, init.restype = [ctypes.c_int], ctypes.c_int
        add = libc.inotify_add_watch
        add.argtypes, add.restype = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32], ctypes.c_int
        self.fd = init(os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), "inotify_init1")
        # MODIFY, ATTRIB, CLOSE_WRITE, MOVED_FROM/TO, CREATE, DELETE, DELETE_SELF, MOVE_SELF
        if add(self.fd, os.fsencode(self.path.parent), 0xFCE) < 0:
            os.close(self.fd)
            raise OSError(ctypes.get_errno(), "inotify_add_watch")
        self.stop_r, self.stop_w = os.pipe()
        self.offset, self.identity, self.count = 0, None, 0
        self.stopped = False
        self.closed = False
        self.lifecycle_lock = threading.Lock()

    def read_new(self):
        try:
            descriptor = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            if self.identity is not None:
                raise ValueError("event journal was removed")
            return []
        result = []
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            identity = (info.st_dev, info.st_ino)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("event journal is not a regular file")
            if self.identity not in (None, identity) or info.st_size < self.offset:
                raise ValueError("append-only event journal changed identity or shrank")
            self.identity = identity
            stream.seek(self.offset)
            while raw := stream.readline(MAX_EVENT_BYTES + 1):
                if len(raw) > MAX_EVENT_BYTES:
                    raise ValueError("event exceeds input bound")
                if not raw.endswith(b"\n"):
                    break  # Keep offset at the last complete record.
                obj = json.loads(raw, object_pairs_hook=unique_object)
                if not valid_event(obj):
                    raise ValueError("invalid live event envelope")
                self.count += 1
                if self.count > MAX_EVENTS:
                    raise ValueError("event journal capacity reached; explicit rollover required")
                result.append(obj)
                self.offset += len(raw)
        return result

    def follow(self):
        yield from self.read_new()
        while not self.stopped:
            ready, _, _ = select.select([self.fd, self.stop_r], [], [])
            if self.stop_r in ready:
                return
            notices = os.read(self.fd, 65536)
            offset, changed = 0, False
            while offset < len(notices):
                _wd, mask, _cookie, size = struct.unpack_from("iIII", notices, offset)
                name = notices[offset + 16:offset + 16 + size].split(b"\0", 1)[0]
                offset += 16 + size
                if mask & (0x4000 | 0x8000 | 0x400 | 0x800):
                    raise ValueError("event notification overflow or watched directory lost")
                changed |= name == os.fsencode(self.path.name)
            if changed:
                yield from self.read_new()

    def stop(self):
        with self.lifecycle_lock:
            if not self.stopped:
                self.stopped = True
                os.write(self.stop_w, b"x")

    def close(self):
        with self.lifecycle_lock:
            self.stopped = True
            if not self.closed:
                self.closed = True
                for fd in (self.fd, self.stop_r, self.stop_w):
                    os.close(fd)


class EventHub:
    def __init__(self, path):
        self.reader = EventFile(path)
        self.condition = threading.Condition()
        self.events, self.ids = [], {}
        self.error = None
        try:
            for event in self.reader.read_new():
                self.add(event)
        except BaseException:
            self.reader.close()
            raise

    def add(self, event):
        with self.condition:
            old = self.ids.get(event["event_id"])
            if old is not None:
                if self.events[old] != event:
                    raise ValueError("event ID rebound to different content")
                return
            self.ids[event["event_id"]] = len(self.events)
            self.events.append(event)
            self.condition.notify_all()

    def run(self):
        try:
            for event in self.reader.follow():
                self.add(event)
        except Exception as exc:
            with self.condition:
                self.error = str(exc)
                self.condition.notify_all()
        finally:
            self.reader.stopped = True
            self.reader.close()

    def stop(self):
        self.reader.stop()
        with self.condition:
            self.condition.notify_all()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    hub: EventHub

    def do_GET(self):
        if self.path not in ("/events", "/events/"):
            self.send_error(404)
            return
        last = self.headers.get("Last-Event-ID") or None
        with self.hub.condition:
            if self.hub.error:
                self.send_error(503, "event source unavailable")
                return
            if last is not None and last not in self.hub.ids:
                self.send_error(409, "unknown resume cursor")
                return
            cursor = self.hub.ids[last] + 1 if last is not None else 0
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.flush()
        try:
            while True:
                with self.hub.condition:
                    self.hub.condition.wait_for(lambda: cursor < len(self.hub.events)
                                                or self.hub.error or self.hub.reader.stopped)
                    if self.hub.error or self.hub.reader.stopped:
                        return
                    events = self.hub.events[cursor:]
                    cursor += len(events)
                for event in events:
                    payload = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
                    self.wfile.write(f"id: {event['event_id']}\nevent: qikvrt\ndata: {payload}\n\n".encode())
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, fmt, *args):
        return


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", default="state/live/QIKVRT_LIVE_EVENTS.jsonl")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    a = p.parse_args()
    Handler.hub = EventHub(Path(a.events))
    worker = threading.Thread(target=Handler.hub.run, daemon=True)
    worker.start()
    server = ThreadingHTTPServer((a.host, a.port), Handler)
    try:
        # handle_request blocks in accept; no serve_forever maintenance timer.
        while True:
            server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        Handler.hub.stop()
        worker.join()
        server.server_close()


if __name__ == "__main__":
    main()
