#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Synchronous TEMDD ledger; socket/SSE transport lives outside the kernel.

No scheduler, repository polling, review, promotion, or DoD inference. The
owner-only Unix socket is a local native-producer trust boundary, not a GitHub
webhook authenticator. A successful append means durable ledger readback only.
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import socket
import socketserver
import sqlite3
import stat
import subprocess
import sys
import threading
from urllib.parse import parse_qs, urlsplit
import uuid

# Also supports loading as src.qikvrt_temdd_event_ledger in repository tests.
try:
    from . import qikvrt_effect_ack_http_terminal as terminal
except ImportError:
    import qikvrt_effect_ack_http_terminal as terminal

MAX_EVENT = 65536
KINDS = frozenset({'OBSERVE', 'CLASSIFY', 'ACTION', 'EFFECT', 'READBACK',
                   'SUCCESSOR', 'HOLD'})
SCHEMA = 'qikvrt_temdd_native_event_v1'
HEX40 = re.compile(r'[0-9a-f]{40}\Z')
CURSOR = re.compile(r'([0-9a-f]{32}):([1-9][0-9]{0,18})\Z')


class Hold(ValueError):
    """Fail-closed observation/ingress failure; never repository NOOP."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def subject(root, repository, pr=None, ref=None):
    """Observe one clean immutable checkout, without a floating tree lookup."""
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args],
            stderr=subprocess.DEVNULL, timeout=5, text=True).strip()
    try:
        head = git('rev-parse', '--verify', 'HEAD^{commit}')
        tree = git('rev-parse', '--verify', head + '^{tree}')
        if not HEX40.fullmatch(head) or not HEX40.fullmatch(tree):
            raise Hold('EXACT_SUBJECT_UNOBSERVABLE')
        git('diff', '--quiet', head, '--')
        if git('rev-parse', '--verify', 'HEAD^{commit}') != head:
            raise Hold('EXACT_SUBJECT_CHANGED')
    except (OSError, subprocess.SubprocessError) as exc:
        raise Hold('EXACT_SUBJECT_UNOBSERVABLE_OR_DIRTY') from exc
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository):
        raise Hold('REPOSITORY_REQUIRED')
    if pr is not None and ref is not None:
        raise Hold('SUBJECT_LOCATOR_AMBIGUOUS')
    if pr is not None:
        if type(pr) is not int or pr < 1:
            raise Hold('PR_REQUIRED')
        locator = {'pr': pr}
    elif ref is not None:
        if (not isinstance(ref, str)
                or re.fullmatch(r'refs/(?:heads|tags)/[A-Za-z0-9._/-]{1,240}', ref) is None
                or '..' in ref or ref.endswith('/') or ref.startswith('refs/heads/-')):
            raise Hold('REF_REQUIRED')
        locator = {'ref': ref}
    else:
        raise Hold('SUBJECT_LOCATOR_REQUIRED')
    return {'repository': repository, **locator, 'head': head, 'tree': tree}


class Ledger:
    """One process owns the durable store; append is a finite transaction."""
    def __init__(self, state_dir, exact_subject):
        self.subject = dict(exact_subject)
        self.binding = digest(self.subject)
        self.condition = threading.Condition(threading.RLock())
        self.stopped = False
        self.reason = ''
        self.listeners = set()
        self.directory = Path(state_dir) / 'temdd'
        if self.directory.is_symlink():
            raise Hold('UNSAFE_LEDGER_DIRECTORY')
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        info = self.directory.stat()
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise Hold('LEDGER_DIRECTORY_MUST_BE_OWNER_ONLY')
        self.lock_fd = os.open(self.directory / 'owner.lock',
            os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            for name in ('events.sqlite3', 'events.sqlite3-wal', 'events.sqlite3-shm'):
                if (self.directory / name).is_symlink():
                    raise Hold('UNSAFE_LEDGER_FILE')
            self.db = sqlite3.connect(self.directory / 'events.sqlite3',
                                      check_same_thread=False, timeout=5)
            self.db.execute('PRAGMA journal_mode=WAL')
            self.db.execute('PRAGMA synchronous=FULL')
            with self.db:
                self.db.execute('CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
                self.db.execute('CREATE TABLE IF NOT EXISTS events ('
                    'seq INTEGER PRIMARY KEY AUTOINCREMENT, binding TEXT NOT NULL, '
                    'source TEXT NOT NULL, native_id TEXT NOT NULL, native_digest TEXT NOT NULL, '
                    'body TEXT NOT NULL, body_digest TEXT NOT NULL, UNIQUE(source,native_id))')
                self.db.execute('CREATE INDEX IF NOT EXISTS events_binding ON events(binding,seq)')
                self.db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('schema', '1'))
                self.db.execute('INSERT OR IGNORE INTO meta VALUES (?,?)', ('epoch', uuid.uuid4().hex))
            meta = dict(self.db.execute('SELECT key,value FROM meta'))
            if meta.get('schema') != '1' or not re.fullmatch(r'[0-9a-f]{32}', meta.get('epoch', '')):
                raise Hold('UNKNOWN_LEDGER_SCHEMA')
            self.epoch = meta['epoch']
            if self.db.execute('PRAGMA quick_check').fetchone() != ('ok',):
                raise Hold('CORRUPT_LEDGER')
        except BaseException:
            if hasattr(self, 'db'):
                self.db.close()
            os.close(self.lock_fd)
            raise

    def _validate(self, event):
        required = {'schema', 'kind', 'subject', 'provenance', 'observed_at', 'message', 'payload'}
        if not isinstance(event, dict) or set(event) != required or event['schema'] != SCHEMA:
            raise Hold('INVALID_NATIVE_EVENT')
        if canonical(event['subject']) != canonical(self.subject):
            raise Hold('EXACT_SUBJECT_MISMATCH')
        if not isinstance(event['kind'], str) or event['kind'] not in KINDS:
            raise Hold('INVALID_EVENT_KIND')
        provenance = event['provenance']
        if not isinstance(provenance, dict) or set(provenance) != {'source', 'native_event_id'}:
            raise Hold('NATIVE_PROVENANCE_REQUIRED')
        if provenance['source'] not in ('repository', 'transputer'):
            raise Hold('UNADMITTED_PRODUCER')
        native_id = provenance['native_event_id']
        if not isinstance(native_id, str) or not re.fullmatch(r'[^\x00-\x20\x7f]{1,256}', native_id):
            raise Hold('INVALID_NATIVE_EVENT_ID')
        if not isinstance(event['message'], str) or len(event['message']) > 4096:
            raise Hold('INVALID_EVENT_MESSAGE')
        if not isinstance(event['payload'], dict):
            raise Hold('PAYLOAD_OBJECT_REQUIRED')
        observed = event['observed_at']
        try:
            if not isinstance(observed, str) or not observed.endswith('Z'):
                raise ValueError()
            datetime.fromisoformat(observed[:-1] + '+00:00')
        except ValueError as exc:
            raise Hold('UTC_OBSERVATION_REQUIRED') from exc
        if len(canonical(event)) > MAX_EVENT:
            raise Hold('EVENT_TOO_LARGE')

    def _decode(self, row):
        seq, binding, text, expected = row
        body = json.loads(text)
        if binding != self.binding or body.get('subject') != self.subject or digest(body) != expected:
            raise Hold('LEDGER_READBACK_MISMATCH')
        return dict(body, id=f'{self.epoch}:{seq}', ledger_digest=expected)

    def append(self, event):
        # Freeze caller-owned objects before validation / hashing / persistence.
        event = json.loads(canonical(event))
        self._validate(event)
        native = digest(event)
        provenance = event['provenance']
        with self.condition:
            if self.stopped:
                raise Hold(self.reason or 'LEDGER_STOPPED')
            old = self.db.execute('SELECT seq,native_digest FROM events WHERE source=? AND native_id=?',
                (provenance['source'], provenance['native_event_id'])).fetchone()
            if old is not None:
                if old[1] != native:
                    raise Hold('NATIVE_EVENT_ID_CONFLICT')
                row = self.db.execute('SELECT seq,binding,body,body_digest FROM events WHERE seq=?', (old[0],)).fetchone()
                return self._decode(row)
            body = dict(event, schema='qikvrt_temdd_event_v1', recorded_at=utc(),
                        payload_digest=digest(event['payload']), evidence_transfer='DENY', dod=False)
            text = canonical(body).decode('utf-8')
            with self.db:
                result = self.db.execute('INSERT INTO events(binding,source,native_id,native_digest,body,body_digest) '
                    'VALUES (?,?,?,?,?,?)', (self.binding, provenance['source'], provenance['native_event_id'], native, text, digest(body)))
                seq = result.lastrowid
            # No publish before COMMIT and exact durable readback.
            row = self.db.execute('SELECT seq,binding,body,body_digest FROM events WHERE seq=?', (seq,)).fetchone()
            readback = self._decode(row)
            self._notify()
            return readback

    def cursor(self, value):
        if not value:
            return 0
        if not isinstance(value, str):
            raise Hold('INVALID_REPLAY_CURSOR')
        match = CURSOR.fullmatch(value)
        if not match or match[1] != self.epoch or int(match[2]) > 9223372036854775807:
            raise Hold('INVALID_REPLAY_CURSOR')
        seq = int(match[2])
        with self.condition:
            row = self.db.execute('SELECT seq,binding,body,body_digest FROM events WHERE seq=?', (seq,)).fetchone()
            if row is None or row[1] != self.binding:
                raise Hold('STALE_OR_UNKNOWN_REPLAY_CURSOR')
            self._decode(row)
        return seq

    def replay(self, after):
        with self.condition:
            rows = self.db.execute('SELECT seq,binding,body,body_digest FROM events '
                'WHERE binding=? AND seq>? ORDER BY seq LIMIT 128', (self.binding, after)).fetchall()
            return [self._decode(row) for row in rows]

    def _notify(self):
        self.condition.notify_all()
        for writer in tuple(self.listeners):
            with contextlib.suppress(BlockingIOError, OSError):
                writer.send(b'1')  # coalesced, nonblocking, at most 32 observers

    def subscribe(self):
        with self.condition:
            reader, writer = socket.socketpair()
            reader.setblocking(False)
            writer.setblocking(False)
            self.listeners.add(writer)
            writer.send(b'1')  # closes the replay/subscribe race
            return reader, writer

    def unsubscribe(self, reader, writer):
        with self.condition:
            self.listeners.discard(writer)
            reader.close()
            writer.close()
            self.condition.notify_all()

    def stop(self, reason='PRODUCER_STOPPED'):
        with self.condition:
            self.stopped = True
            self.reason = reason
            self._notify()

    def close(self):
        self.stop()
        with self.condition:
            self.db.close()
            os.close(self.lock_fd)


class Runtime:
    def __init__(self, root, state_dir, repository, pr=None, ref=None):
        self.root = Path(root).resolve()
        self.repository, self.pr, self.ref = repository, pr, ref
        self.subject = subject(self.root, repository, pr, ref)
        self.ledger = Ledger(state_dir, self.subject)
        self.subscribers = threading.BoundedSemaphore(32)

    def ensure_subject(self):
        try:
            if subject(self.root, self.repository, self.pr, self.ref) != self.subject:
                raise Hold('EXACT_SUBJECT_CHANGED_RESTART_REQUIRED')
            if self.ledger.stopped:
                raise Hold(self.ledger.reason)
        except Hold as exc:
            self.ledger.stop(str(exc))
            raise
        return self.subject

    def append(self, event):
        self.ensure_subject()
        return self.ledger.append(event)


def make_handler(runtime):
    class Handler(terminal.Handler):
        protocol_version = 'HTTP/1.1'

        def _hold(self, reason, code=503):
            self._json(code, {'state': 'HOLD', 'reason': reason, 'dod': False,
                             'ordinary_release': False, 'evidence_transfer': 'DENY'})

        def _frame(self, value, name=None, event_id=None):
            frame = (f'event: {name}\n' if name else '')
            frame += (f'id: {event_id}\n' if event_id else '')
            self.wfile.write((frame + 'data: ' + canonical(value).decode('utf-8') + '\n\n').encode('utf-8'))
            self.wfile.flush()

        def do_GET(self):
            path = urlsplit(self.path).path
            if path not in ('/AI', '/AI/', '/api/temdd/subject', '/api/temdd/events'):
                return super().do_GET()
            host = self.headers.get('Host', '')
            allowed_hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if host not in allowed_hosts:
                return self._hold('LOOPBACK_HOST_REQUIRED', 403)
            if self.headers.get('Origin') not in (None, 'http://' + host):
                return self._hold('SAME_ORIGIN_REQUIRED', 403)
            try:
                exact = runtime.ensure_subject()
                if path in ('/AI', '/AI/'):
                    data = (runtime.root / 'docs/terminal/temdd/index.html').read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.end_headers()
                    self.wfile.write(data)
                    return
                if path == '/api/temdd/subject':
                    return self._json(200, {'subject': exact, 'ledger_id': runtime.ledger.epoch,
                        'state': 'HOLD_UNVERIFIED', 'dod': False, 'evidence_transfer': 'DENY'})
                query = parse_qs(urlsplit(self.path).query, keep_blank_values=True)
                if set(query) - {'after'} or len(query.get('after', [''])) != 1:
                    raise Hold('INVALID_REPLAY_QUERY')
                # Native reconnect headers supersede the original URL's cursor.
                after = runtime.ledger.cursor(self.headers.get('Last-Event-ID') or query.get('after', [''])[0])
                if not runtime.subscribers.acquire(blocking=False):
                    return self._hold('SUBSCRIBER_LIMIT')
            except (ValueError, OSError, sqlite3.Error) as exc:
                return self._hold(str(exc), 409 if isinstance(exc, Hold) else 503)
            reader, writer = runtime.ledger.subscribe()
            try:
                self.connection.settimeout(5)  # bounded writes, not a polling timer
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Accel-Buffering', 'no')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                self._frame({'subject': exact, 'ledger_id': runtime.ledger.epoch,
                    'dod': False, 'evidence_transfer': 'DENY'}, name='subject')
                with selectors.DefaultSelector() as ready:
                    ready.register(reader, selectors.EVENT_READ)
                    ready.register(self.connection, selectors.EVENT_READ)
                    while True:  # outer I/O adapter; no timed status queries
                        for key, _ in ready.select():
                            if key.fileobj is self.connection:
                                return  # disconnect or unsupported pipelined input
                        with contextlib.suppress(BlockingIOError):
                            reader.recv(65536)
                        while True:
                            with runtime.ledger.condition:
                                if runtime.ledger.stopped:
                                    self._frame({'state': 'HOLD', 'reason': runtime.ledger.reason, 'dod': False}, name='hold')
                                    return
                                batch = runtime.ledger.replay(after)
                            runtime.ensure_subject()
                            for event in batch:
                                self._frame(event, event_id=event['id'])
                                after = int(event['id'].split(':')[1])
                            if len(batch) < 128:
                                break
            except (OSError, ValueError, sqlite3.Error):
                # Observer disconnect never changes repository execution state.
                with contextlib.suppress(OSError):
                    self._frame({'state': 'HOLD', 'reason': 'STREAM_READBACK_UNAVAILABLE', 'dod': False}, name='hold')
            finally:
                self.close_connection = True
                runtime.ledger.unsubscribe(reader, writer)
                runtime.subscribers.release()

        def do_POST(self):
            if urlsplit(self.path).path.startswith('/api/temdd/'):
                return self._hold('NATIVE_UNIX_INGRESS_REQUIRED', 405)
            return super().do_POST()
    return Handler


def make_ingress(runtime):
    class Ingress(socketserver.StreamRequestHandler):
        def handle(self):
            self.connection.settimeout(5)
            try:
                raw = self.rfile.readline(MAX_EVENT + 2)
                if len(raw) > MAX_EVENT + 1 or not raw.endswith(b'\n'):
                    raise Hold('BOUNDED_EVENT_LINE_REQUIRED')
                event = runtime.append(json.loads(raw))
                result = {'state': 'PERSISTED', 'event': event, 'authority_effect': False, 'dod': False}
            except (OSError, ValueError, sqlite3.Error, RecursionError) as exc:
                result = {'state': 'HOLD', 'reason': str(exc), 'dod': False}
            with contextlib.suppress(OSError):
                self.wfile.write(canonical(result) + b'\n')
    path = runtime.ledger.directory / 'ingress.sock'
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not stat.S_ISSOCK(path.stat().st_mode):
            raise Hold('UNSAFE_INGRESS_PATH')
        path.unlink()  # store-owner lock excludes a live competing producer
    server = socketserver.UnixStreamServer(str(path), Ingress)
    os.chmod(path, 0o600)
    return server


def submit(state_dir, event):
    raw = canonical(event)
    if len(raw) > MAX_EVENT:
        raise Hold('EVENT_TOO_LARGE')
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(10)
        client.connect(str(Path(state_dir) / 'temdd/ingress.sock'))
        client.sendall(raw + b'\n')
        with client.makefile('rb') as response:
            result = json.loads(response.readline(MAX_EVENT * 2))
    if result.get('state') != 'PERSISTED':
        raise Hold(result.get('reason', 'LEDGER_READBACK_UNAVAILABLE'))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('serve', 'append'))
    parser.add_argument('--state-dir', required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8771)
    parser.add_argument('--root', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--repository', default='Goldkelch/qik-vrt')
    parser.add_argument('--pr', type=int)
    parser.add_argument('--ref')
    args = parser.parse_args()
    try:
        if args.operation == 'append':
            raw = sys.stdin.buffer.read(MAX_EVENT + 1)
            if len(raw) > MAX_EVENT:
                raise Hold('EVENT_TOO_LARGE')
            print(canonical(submit(args.state_dir, json.loads(raw))).decode('utf-8'))
            return 0
        if args.host != '127.0.0.1':
            raise Hold('LOOPBACK_ONLY')
        runtime = Runtime(args.root, args.state_dir, args.repository, args.pr, args.ref)
        http = terminal.ThreadingHTTPServer((args.host, args.port), make_handler(runtime))
        ingress = make_ingress(runtime)
        thread = threading.Thread(target=ingress.serve_forever, daemon=True)
        thread.start()  # outer I/O adapter, not a repository job scheduler
        try:
            runtime.append({'schema': SCHEMA, 'kind': 'OBSERVE', 'subject': runtime.subject,
                'provenance': {'source': 'transputer', 'native_event_id': 'listener-bound:' + uuid.uuid4().hex},
                'observed_at': utc(), 'message': 'Local TEMDD listeners bound; no DoD inference',
                'payload': {'pid': os.getpid(), 'http_address': list(http.server_address)}})
            print(canonical({'state': 'LISTENING', 'subject': runtime.subject, 'dod': False}).decode(), flush=True)
            http.serve_forever()
        finally:
            runtime.ledger.stop()
            ingress.shutdown()
            ingress.server_close()
            http.server_close()
            thread.join(timeout=6)
            runtime.ledger.close()
        return 0
    except (OSError, ValueError, sqlite3.Error, RecursionError) as exc:
        print(canonical({'state': 'HOLD', 'reason': str(exc), 'dod': False}).decode(), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
