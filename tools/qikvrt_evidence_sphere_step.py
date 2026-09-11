#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""One finite, explicitly authorized Git-observation growth step; no network.

Reuses the real Mesh ledger and canonical encoding. The graph records observed
bytes, never truth of their contents. This is not an approval/publication engine.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.qikvrt_real_mesh import (  # noqa: E402
    AppendOnlyNodeLedger, MeshRuntimeError, canonical_json_bytes, canonical_sha256,
)

SCHEMA = 'qikvrt_evidence_sphere_git_observation_v1'
NODE_ID = 'evidence-sphere-v1'
CONTRACT = {
    'schema': 'qikvrt_evidence_sphere_contract_v1',
    'scope': 'LOCAL_GIT_OBJECT_BYTES_AND_ORIGIN_CONFIGURATION',
    'relation': 'CONTAINS_OBSERVED_BLOB',
    'claims_about_contents': False,
    'predecessor_evidence_transfer': False,
    'external_effects': False,
}
CONTRACT_ID = canonical_sha256(CONTRACT)
IMPLEMENTATION_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
EVENT_KEYS = {'schema', 'repository', 'head', 'tree', 'path', 'blob', 'sha256', 'bytes'}


class SphereError(MeshRuntimeError):
    """An incomplete, stale, conflicting or malformed observation."""


def git(root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ['git', '-C', str(root), *args], capture_output=True, timeout=15, check=False,
        env={**os.environ, 'GIT_NO_REPLACE_OBJECTS': '1'},
    )
    if completed.returncode:
        raise SphereError('GIT_OBSERVATION_UNAVAILABLE: ' + completed.stderr.decode('utf-8', 'replace')[:200])
    return completed.stdout


def normalize(event: Any) -> dict[str, Any]:
    if not isinstance(event, dict) or set(event) != EVENT_KEYS:
        raise SphereError('EXACT_EVENT_FIELDS_REQUIRED')
    if event['schema'] != SCHEMA:
        raise SphereError('UNSUPPORTED_EVENT_SCHEMA')
    if not isinstance(event['repository'], str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', event['repository']):
        raise SphereError('INVALID_REPOSITORY')
    for key, length in [('head', 40), ('tree', 40), ('blob', 40), ('sha256', 64)]:
        if not isinstance(event[key], str) or not re.fullmatch('[0-9a-f]{' + str(length) + '}', event[key]):
            raise SphereError('INVALID_' + key.upper())
    path = event['path']
    if (not isinstance(path, str) or not path or len(path) > 1024
            or PurePosixPath(path).is_absolute() or '..' in path.split('/')
            or str(PurePosixPath(path)) != path or '\\' in path
            or any(ord(char) < 32 for char in path)):
        raise SphereError('INVALID_LITERAL_PATH')
    if type(event['bytes']) is not int or not 0 <= event['bytes'] <= 16 * 1024 * 1024:
        raise SphereError('INVALID_BOUNDED_BYTE_COUNT')
    return dict(event)


def observe(root: Path, repository: str, head: str, path: str) -> dict[str, Any]:
    """Read exact local Git objects; origin configuration is not remote attestation."""
    normalize(dict(schema=SCHEMA, repository=repository, head=head, tree='0'*40,
                   path=path, blob='0'*40, sha256='0'*64, bytes=0))
    if git(root, 'rev-parse', 'HEAD').decode().strip() != head:
        raise SphereError('HEAD_DRIFT')
    origin = git(root, 'remote', 'get-url', 'origin').decode().strip()
    if origin not in {f'https://github.com/{repository}', f'https://github.com/{repository}.git',
                      f'git@github.com:{repository}.git'}:
        raise SphereError('ORIGIN_CONFIGURATION_MISMATCH')
    tree = git(root, 'rev-parse', head + '^{tree}').decode().strip()
    entries = git(root, '--literal-pathspecs', 'ls-tree', '-z', head, '--', path).split(b'\0')
    entries = [entry for entry in entries if entry]
    if len(entries) != 1 or b'\t' not in entries[0]:
        raise SphereError('EXACT_BLOB_UNAVAILABLE')
    metadata, observed_path = entries[0].split(b'\t', 1)
    mode, kind, blob = metadata.decode('ascii').split()
    if observed_path != path.encode('utf-8') or mode not in {'100644', '100755'} or kind != 'blob':
        raise SphereError('REGULAR_EXACT_BLOB_REQUIRED')
    size = int(git(root, 'cat-file', '-s', blob).strip())
    if size > 16 * 1024 * 1024:
        raise SphereError('BLOB_TOO_LARGE')
    raw = git(root, 'cat-file', 'blob', blob)
    # Bind both Git object identity and actual read bytes, not supplied flags.
    actual_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if len(raw) != size or actual_blob != blob:
        raise SphereError('BLOB_READBACK_MISMATCH')
    if git(root, 'rev-parse', 'HEAD').decode().strip() != head:
        raise SphereError('HEAD_DRIFT')
    return normalize(dict(schema=SCHEMA, repository=repository, head=head, tree=tree,
                          path=path, blob=blob, sha256=hashlib.sha256(raw).hexdigest(), bytes=size))


def empty_graph() -> dict[str, dict[str, Any]]:
    return {'nodes': {}, 'relations': {}}


def graph_root(graph: dict[str, Any]) -> str:
    return canonical_sha256({'contract': CONTRACT_ID, **graph})


def plan(graph: dict[str, Any], event: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Pure deterministic projection. Validation of source bytes precedes mutation."""
    event = normalize(event)
    subject = {'kind': 'git_subject', 'repository': event['repository'], 'head': event['head'], 'tree': event['tree']}
    artifact = {'kind': 'observed_bytes', 'blob': event['blob'], 'sha256': event['sha256'], 'bytes': event['bytes']}
    contract = {'kind': 'contract', 'value': CONTRACT}
    sid, aid, cid = [canonical_sha256(item) for item in (subject, artifact, contract)]
    event_id = canonical_sha256(event)
    relation = {'kind': CONTRACT['relation'], 'subject': sid, 'artifact': aid,
                'contract': cid, 'path': event['path'], 'observation': event_id,
                'epistemic_class': 'BYTE_OBSERVATION_NOT_CONTENT_TRUTH'}
    rid = canonical_sha256(relation)
    delta = {
        'nodes': {key: value for key, value in [(sid, subject), (aid, artifact), (cid, contract)] if key not in graph['nodes']},
        'relations': {} if rid in graph['relations'] else {rid: relation},
    }
    after = {key: {**graph[key], **delta[key]} for key in ('nodes', 'relations')}
    changed = bool(delta['relations'])
    receipt = {
        'schema': 'qikvrt_evidence_sphere_growth_receipt_v1',
        'contract': CONTRACT_ID, 'observation': event_id,
        'implementation_sha256': IMPLEMENTATION_SHA256,
        'old_root': graph_root(graph), 'delta_digest': canonical_sha256(delta), 'new_root': graph_root(after),
        'nodes_added': len(delta['nodes']), 'relations_added': len(delta['relations']),
        'new_content_objects': int(aid in delta['nodes']),
        'growth_kind': ('NEW_CONTENT_OBSERVATION' if aid in delta['nodes'] else 'NEW_SUBJECT_OR_PATH_BINDING') if changed else 'NONE',
        'decision': 'APPEND' if changed else 'NOOP',
        'ordinary_release': False, 'external_effect': 'NONE',
    }
    return after, {'event': event, 'delta': delta, 'receipt': receipt}


class SphereLedger(AppendOnlyNodeLedger):
    """Semantic replay on the existing Mesh hash-chain format; not a second format."""

    def __init__(self, path: Path) -> None:
        self.graph = empty_graph()
        if path.is_symlink():
            raise SphereError('LEDGER_SYMLINK')
        super().__init__(path, NODE_ID)

    def _apply_record(self, record: dict[str, Any]) -> None:
        if record.get('event') != 'COMPLETED' or not isinstance(record.get('response'), dict):
            raise SphereError('UNSUPPORTED_LEDGER_RECORD')
        response = record['response']
        after, expected = plan(self.graph, response.get('event'))
        if (response != expected or expected['receipt']['decision'] != 'APPEND'
                or record.get('message_id') != expected['receipt']['observation']):
            raise SphereError('SEMANTIC_LEDGER_REPLAY_MISMATCH')
        super()._apply_record(record)
        self.graph = after


@contextmanager
def locked(path: Path) -> Iterator[None]:
    """Cooperating POSIX writers only; never wait/poll or delete a competing lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(str(path) + '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SphereError('COMPETING_WRITER_ACTIVE') from exc
        yield
    finally:
        os.close(descriptor)


def inspect(path: Path) -> dict[str, Any]:
    with locked(path):
        ledger = SphereLedger(path)
        return {'root': graph_root(ledger.graph), 'nodes': len(ledger.graph['nodes']),
                'relations': len(ledger.graph['relations']), 'records': ledger.sequence,
                'ledger_tip': ledger.previous_record_sha256, 'graph': ledger.graph}


def step(root: Path, ledger_path: Path, event: dict[str, Any], expected_root: str, *, apply: bool = False) -> dict[str, Any]:
    """One event, one optional append, then independent reopen and semantic replay."""
    try:
        with locked(ledger_path):
            ledger = SphereLedger(ledger_path)
            before = graph_root(ledger.graph)
            if expected_root != before:
                raise SphereError('STALE_EXPECTED_ROOT')
            normalized = normalize(event)
            witnessed = observe(root, normalized['repository'], normalized['head'], normalized['path'])
            if witnessed != normalized:
                raise SphereError('EVENT_WITNESS_MISMATCH')
            _, response = plan(ledger.graph, normalized)
            receipt = response['receipt']
            if receipt['decision'] == 'NOOP':
                return {**receipt, 'reobserved': True, 'next_action': 'AWAIT_NEW_EVENT'}
            if not apply:
                return {'decision': 'REQUEST_AUTHORITY', 'root': before,
                        'proposed_delta_digest': receipt['delta_digest'], 'ordinary_release': False}
            # The caller must own the working copy as well as this ledger.
            if observe(root, normalized['repository'], normalized['head'], normalized['path']) != normalized:
                raise SphereError('PRE_APPEND_SUBJECT_DRIFT')
            record = ledger.append('COMPLETED', receipt['observation'], response=response)
            fresh = SphereLedger(ledger_path)
            if (graph_root(fresh.graph) != receipt['new_root']
                    or fresh.previous_record_sha256 != record['record_sha256']
                    or fresh.completed.get(receipt['observation']) != response):
                raise SphereError('LEDGER_READBACK_MISMATCH')
            return {**receipt, 'reobserved': True, 'ledger_tip': fresh.previous_record_sha256,
                    'next_action': 'AWAIT_NEW_EVENT'}
    except (MeshRuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        return {'decision': 'HOLD', 'reason': str(exc), 'ordinary_release': False,
                'external_effect': 'NONE', 'reobserved': False, 'next_action': 'REOBSERVE'}


def demo(root: Path, path: Path, repository: str) -> dict[str, Any]:
    """Finite real-byte witness: three observations, one replay, one negative event."""
    if path.exists():
        raise SphereError('DEMO_REQUIRES_NEW_LEDGER')
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    receipts = []
    events = [observe(root, repository, head, name) for name in (
        'AI', 'src/effect_ack_core.c',
        'docs/publications/2026-08-05-qik-vrt-quantum-causal-emergence/QCE_KERNEL_RECEIPT.json',
    )]
    initial = inspect(path)
    for event in events:
        value = step(root, path, event, inspect(path)['root'], apply=True)
        if value['decision'] != 'APPEND' or value.get('reobserved') is not True:
            raise SphereError('DEMO_APPEND_FAILED: ' + json.dumps(value))
        receipts.append(value)
    previous = path.read_bytes()
    replay = step(root, path, events[-1], inspect(path)['root'], apply=True)
    rejected = step(root, path, {**events[-1], 'sha256': '0'*64}, inspect(path)['root'], apply=True)
    if replay['decision'] != 'NOOP' or rejected['decision'] != 'HOLD' or path.read_bytes() != previous:
        raise SphereError('DEMO_NON_GROWTH_FAILED')
    return {'schema': 'qikvrt_evidence_sphere_demo_v1', 'repository': repository,
            'head': head, 'tree': events[0]['tree'], 'before': initial, 'growth': receipts,
            'duplicate': replay, 'unwitnessed': rejected, 'after': inspect(path),
            'scope': CONTRACT['scope'], 'deployment': False, 'publication': False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['observe', 'step', 'inspect', 'demo'])
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--repository', default='Goldkelch/qik-vrt')
    parser.add_argument('--head')
    parser.add_argument('--path')
    parser.add_argument('--event', type=Path)
    parser.add_argument('--expected-root')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        if args.operation == 'inspect':
            value = inspect(args.ledger)
        elif args.operation == 'observe':
            value = observe(args.root, args.repository, args.head or '', args.path or '')
        elif args.operation == 'demo':
            if not args.apply:
                parser.error('demo requires explicit --apply for its new local ledger')
            value = demo(args.root, args.ledger, args.repository)
        else:
            if args.event is None or args.expected_root is None:
                parser.error('step requires --event and --expected-root')
            value = step(args.root, args.ledger, json.loads(args.event.read_text(encoding='utf-8')),
                         args.expected_root, apply=args.apply)
    except (MeshRuntimeError, OSError, ValueError, subprocess.SubprocessError) as exc:
        value = {'decision': 'HOLD', 'reason': str(exc), 'ordinary_release': False}
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if value.get('decision') in {'HOLD', 'REQUEST_AUTHORITY'} else 0


if __name__ == '__main__':
    raise SystemExit(main())
