#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Read-only SSE over an append-only JSONL journal; Linux inotify is the clock.

Regular files support independent replay/live cursors for every subscriber.
A destructive FIFO cannot implement broadcast or durable resume and is rejected.
No timer, GitHub query, fabricated receipt or repository mutation drives follow.
An explicit bootstrap option creates only an empty private runtime journal.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import select
import stat
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

MAX_LINE = 65536


def valid_event(obj: dict) -> bool:
    required = {"schema", "event_id", "observed_at", "repository", "subject", "phase", "verb", "causal_state", "source", "productive_effect", "effect_ack", "payload"}
    if not isinstance(obj, dict) or obj.get("schema") != "qikvrt_live_event_v1" or not required.issubset(obj):
        return False
    eid = obj["event_id"]
    return (isinstance(eid, str) and 0 < len(eid) <= 512
            and not any(c in eid for c in "\r\n\0")
            and isinstance(obj["repository"], str)
            and isinstance(obj["subject"], dict)
            and isinstance(obj["source"], dict)
            and isinstance(obj["payload"], dict)
            and type(obj["productive_effect"]) is bool
            and all(isinstance(obj[k], str) for k in ("observed_at", "phase", "verb", "causal_state", "effect_ack"))
            and isinstance(obj["subject"].get("head_sha"), str)
            and re.fullmatch(r"[0-9a-f]{40}", obj["subject"]["head_sha"]) is not None)


def decode_event(raw: str):
    try:
        obj = json.loads(raw)
    except (ValueError, TypeError):
        return None
    return obj if valid_event(obj) else None


class CursorMissing(ValueError):
    pass


def seek_after(fh, after: str | None) -> None:
    """Resolve an exact cursor. An absent cursor is a conflict, never silent EOF."""
    fh.seek(0)
    if after is None:
        return
    if len(after) > 512 or any(c in after for c in "\r\n\0"):
        raise CursorMissing("invalid cursor")
    while True:
        raw = fh.readline(MAX_LINE + 1)
        if not raw:
            raise CursorMissing("resume cursor not retained in journal")
        if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
            raise CursorMissing("resume cursor not present in complete journal")
        event = decode_event(raw)
        if event is None:
            raise ValueError("invalid receipt before cursor")
        if event["event_id"] == after:
            return


class JournalReader:
    """One consumer with bounded readline() and notification armed before replay.

    The byte bound prevents a malformed unterminated record from exhausting RAM;
    incomplete records stay at their original offset until an append completes.
    """
    def __init__(self, path, after=None, live=False):
        self.path = Path(path)
        self.notify = -1
        self.fh = None
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
            self.fh = os.fdopen(fd, "rb", buffering=0)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("durable regular journal required; FIFO is not broadcast")
            self.identity = (info.st_dev, info.st_ino)
            if live:
                libc = ctypes.CDLL(None, use_errno=True)
                init = libc.inotify_init1
                init.argtypes = [ctypes.c_int]; init.restype = ctypes.c_int
                add = libc.inotify_add_watch
                add.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
                add.restype = ctypes.c_int
                self.notify = init(os.O_CLOEXEC)
                if self.notify < 0:
                    raise OSError(ctypes.get_errno(), "inotify initialization failed")
                # IN_MODIFY | IN_ATTRIB | IN_CLOSE_WRITE | IN_DELETE_SELF | IN_MOVE_SELF
                if add(self.notify, os.fsencode(self.path), 0x00000C0E) < 0:
                    raise OSError(ctypes.get_errno(), "journal notification unavailable")
            seek_after(self.fh, after)
        except BaseException:
            self.close()
            raise

    def close(self):
        if self.fh is not None:
            self.fh.close(); self.fh = None
        if self.notify >= 0:
            os.close(self.notify); self.notify = -1

    def events(self, client=None):
        while True:
            info = self.path.stat(follow_symlinks=False)
            offset = self.fh.tell()
            if (info.st_dev, info.st_ino) != self.identity or info.st_size < offset:
                raise ValueError("append-only journal replaced or truncated")
            raw = self.fh.readline(MAX_LINE + 1)
            if len(raw) > MAX_LINE:
                raise ValueError("receipt exceeds stream bound")
            if raw.endswith(b"\n"):
                event = decode_event(raw)
                if event is None:
                    raise ValueError("invalid journal receipt")
                yield event
                continue
            # Do not consume an incomplete record. Wait for its append event.
            self.fh.seek(offset)
            if self.notify < 0:
                return
            waiting = [self.notify] + ([client] if client is not None else [])
            ready, _, _ = select.select(waiting, [], [])
            if client is not None and client in ready:
                # EOF or unexpected pipelining ends this streaming connection.
                return
            os.read(self.notify, 65536)


def follow_events(path: Path, after: str | None = None, *, live=False, client=None):
    """Finite replay by default; live=True waits on OS append notifications."""
    reader = JournalReader(path, after, live)
    try:
        yield from reader.events(client)
    finally:
        reader.close()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    events_path: Path

    def failure(self, status, reason):
        body = json.dumps({"state": "HOLD", "reason": reason, "ordinary_release": False}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path not in ("/events", "/events/"):
            self.failure(404, "unknown endpoint"); return
        query = parse_qs(url.query, keep_blank_values=True)
        if set(query) - {"since"} or len(query.get("since", [])) > 1:
            self.failure(400, "invalid cursor query"); return
        # EventSource sends a newer Last-Event-ID on reconnect; it takes precedence
        # over the persisted startup cursor still present in the original URL.
        after = self.headers.get("Last-Event-ID") or query.get("since", [None])[0] or None
        try:
            reader = JournalReader(self.events_path, after, live=True)
        except CursorMissing as error:
            self.failure(409, str(error)); return
        except (OSError, ValueError, AttributeError):
            self.failure(503, "append-only journal or OS notification unavailable"); return
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.flush()
            for event in reader.events(self.connection):
                payload = json.dumps(event, separators=(",", ":"), ensure_ascii=False)
                frame = f"id: {event['event_id']}\nevent: qikvrt\ndata: {payload}\n\n".encode()
                self.wfile.write(frame)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except (OSError, ValueError):
            try:
                self.wfile.write(b'event: qikvrt_stream_error\ndata: {"state":"HOLD","reason":"journal invalidated"}\n\n')
                self.wfile.flush()
            except OSError:
                pass
        finally:
            reader.close()
            self.close_connection = True

    def log_message(self, fmt, *args):
        return


def prepare_journal(path: Path) -> None:
    """Create a private empty runtime journal without truncating existing bytes.

    This is storage initialization, not an observed event or source subscription.
    Symlinks, FIFOs and device nodes cannot become journal carriers.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC
    fd = os.open(path, flags, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("durable regular journal required for initialization")
    finally:
        os.close(fd)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--events", default="state/live/QIKVRT_LIVE_EVENTS.jsonl")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8787)
    p.add_argument("--initialize-journal", action="store_true", help="create an empty private journal only when missing; never truncate")
    a = p.parse_args()
    Handler.events_path = Path(a.events)
    if a.initialize_journal:
        prepare_journal(Handler.events_path)
    server = ThreadingHTTPServer((a.host, a.port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
