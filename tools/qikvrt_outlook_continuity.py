# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Private adapter transaction kernel. No network, send, copy or delete operation.

The adapter must return fresh, complete snapshots and a semantic disposition
bound to the snapshot digest. Presence of this kernel is not a live mail service.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import os
import stat
from datetime import datetime, timezone

TARGETS = frozenset(('AbNan – Jamshed', 'ChatGPT', 'QIK-VRT', 'QIK-VRT/Privat'))
PRESERVED = ('body', 'subject', 'from', 'to', 'cc', 'bcc', 'attachments', 'isRead', 'isDraft', 'internetMessageId')


def binding(message):
    return hashlib.sha256(json.dumps(message, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def destination(message, decision, managed, inbox):
    """Unknown attention stays visible. Semantic decisions are trusted adapter inputs."""
    if decision.get('snapshot_sha256') != binding(message):
        raise ValueError('stale semantic disposition')
    if message['folder_kind'] == 'deleted':
        return None
    if message['folder_kind'] == 'junk' and not decision.get('proven_outreach_bounce'):
        return None
    received = message['kind'] == 'received'
    needs_attention = decision.get('attention') != 'routine' or decision.get('control_cc') is True
    if received and needs_attention:
        # Restore only items with proven automatic placement, never user filing.
        if message['parentFolderId'] in managed and decision.get('placement') == 'managed':
            return inbox
        return None
    if decision.get('classification_complete') is not True or not decision.get('evidence'):
        return None
    target = decision.get('project')
    if target not in TARGETS:
        return None
    if message['kind'] == 'draft' and message['isDraft'] is not True:
        raise ValueError('draft identity mismatch')
    return target


class Journal:
    """Existing private SQLite store, with durable pre-effect intent.

    Operator provisions private directory/permissions. Initialize is explicit:
    missing state during restart must not silently create an empty checkpoint.
    """
    def __init__(self, path, initialize=False):
        from pathlib import Path
        p = Path(path)
        if p.is_symlink() or (not p.exists() and not initialize):
            raise ValueError('private journal missing or symlinked')
        if not p.exists():
            fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(fd)
        if stat.S_IMODE(p.stat().st_mode) & 0o077:
            raise ValueError('journal must have private file permissions')
        self.db = sqlite3.connect(str(p), timeout=0, isolation_level=None)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY, time TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL)')

    def append(self, kind, payload):
        self.db.execute('INSERT INTO events(time,kind,payload) VALUES(?,?,?)',
                        (datetime.now(timezone.utc).isoformat(), kind, json.dumps(payload, sort_keys=True)))

    def events(self):
        return [(kind, json.loads(payload)) for kind, payload in self.db.execute('SELECT kind,payload FROM events ORDER BY seq')]

    def pending(self):
        pending = {}
        for kind, payload in self.events():
            if kind == 'intent':
                pending[payload['operation']] = payload
            elif kind == 'verified':
                pending.pop(payload['operation'], None)
        return pending


def verify_preservation(before, after):
    if any(key not in before or key not in after for key in PRESERVED):
        raise ValueError('incomplete preservation snapshot')
    if any(before[key] != after[key] for key in PRESERVED):
        raise ValueError('message preservation mismatch')


def move_one(adapter, journal, message_id, decision):
    """Caller holds an exclusive mailbox lease for the whole run.

    Adapter resolves folder paths recursively, rejects ambiguous IDs, and must
    serialize reads/moves. move has no automatic POST retry. Recovery is read-only.
    """
    if journal.pending():
        raise ValueError('unresolved prior intent: reconcile before any next move')
    folders = adapter.folders()  # Fresh path-to-ID mapping, including inbox.
    if set(folders) != TARGETS | {'inbox'} or len(set(folders.values())) != 5:
        raise ValueError('folder mapping incomplete or ambiguous')
    before = adapter.snapshot(message_id)
    verify_preservation(before, before)
    dest = destination(before, decision, set(folders.values()) - {folders['inbox']}, folders['inbox'])
    if dest is None:
        return 'kept'
    target = folders[dest] if dest in TARGETS else dest
    if before['parentFolderId'] == target:
        return 'already_present'
    operation = binding({'before': before, 'destination': target})
    intent = {'operation': operation, 'old_id': before['id'], 'source': before['parentFolderId'],
              'destination': target, 'before': before, 'reason': decision}
    journal.append('intent', intent)
    moved = adapter.move(before['id'], target)
    # Persist actual new ID before subsequent network reads.
    journal.append('response', {'operation': operation, 'new_id': moved['id']})
    after = adapter.snapshot(moved['id'])
    verify_preservation(before, after)
    if after['parentFolderId'] != target or not adapter.member(target, after['id']):
        raise ValueError('target membership unverified')
    if adapter.member(before['parentFolderId'], before['id']):
        raise ValueError('source still contains original')
    journal.append('verified', {'operation': operation, 'old_id': before['id'], 'new_id': after['id'],
                               'source': before['parentFolderId'], 'destination': target})
    return 'moved'


def reconcile(adapter, journal):
    """Never repeat an uncertain move. Exact returned-ID readback only.

    If a response was lost, adapter/operator must resolve the precise copy;
    internetMessageId alone cannot distinguish sent and received CC copies.
    """
    responses = {p['operation']: p['new_id'] for k, p in journal.events() if k == 'response'}
    for operation, intent in journal.pending().items():
        if operation not in responses:
            raise ValueError('move outcome unknown: exact-copy reconciliation required')
        after = adapter.snapshot(responses[operation])
        verify_preservation(intent['before'], after)
        if not adapter.member(intent['destination'], after['id']) or after['parentFolderId'] != intent['destination']:
            raise ValueError('recovery destination unverified')
        if adapter.member(intent['source'], intent['old_id']):
            raise ValueError('recovery source still present')
        journal.append('verified', {'operation': operation, 'old_id': intent['old_id'],
                                   'new_id': after['id'], 'source': intent['source'],
                                   'destination': intent['destination']})


def close_window(journal, through, *, pagination_complete, drafts_complete):
    if journal.pending() or pagination_complete is not True or drafts_complete is not True:
        raise ValueError('incomplete window cannot advance checkpoint')
    parsed = datetime.fromisoformat(through.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('checkpoint must include timezone')
    previous = [p['through'] for k, p in journal.events() if k == 'checkpoint']
    if previous and parsed <= datetime.fromisoformat(previous[-1].replace('Z', '+00:00')):
        raise ValueError('checkpoint must advance monotonically')
    journal.append('checkpoint', {'through': through})
