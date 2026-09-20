#!/usr/bin/env python3
"""Cross-check six carriers against the frozen language-neutral finite contract.

Logs/markers are trusted-workflow receipts, not authentication of a proof.
Author and reviewer independence cannot be established by this comparator.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import pathlib
import re
import sys

STATE_CODE = {'EFFECT_NACK': 0, 'EFFECT_ACK_CONTINUE': 1, 'EFFECT_ACK_DONE': 2,
              'EFFECT_ACK_ISOLATE': 3, 'EFFECT_ACK_BLOCK': 4}
INPUTS = ('transport_ack', 'block_required', 'isolate_required', 'release_ready')
DOMAIN = tuple(itertools.product((0, 1), repeat=4))
BACKENDS = frozenset(('c90', 'm68000', 'smalltalk', 'ada_spark', 'lean'))
CONTRACT_SHA256 = 'e44b421ef862629b1f24ec02a8ddbc8dc0b763548ac0aa17f1c52f84e63182bc'


def digest(path):
    raw = path.read_bytes()
    return {'path': path.as_posix(), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def expected_rows(contract):
    if contract.get('schema') != 'qikvrt_core_invariant_vectors_v1':
        raise ValueError('wrong contract schema')
    if contract.get('state_order') != list(STATE_CODE):
        raise ValueError('wrong contract state encoding')
    result = []
    for row in contract['vectors']:
        if set(row) != set(INPUTS) | {'state', 'ordinary_release'}:
            raise ValueError('wrong vector fields')
        if any(type(row[key]) is not bool for key in (*INPUTS, 'ordinary_release')):
            raise ValueError('vector predicates must be JSON booleans')
        result.append([*(int(row[key]) for key in INPUTS),
                       STATE_CODE[row['state']], int(row['ordinary_release'])])
    if tuple(tuple(row[:4]) for row in result) != DOMAIN:
        raise ValueError('contract must enumerate each Boolean assignment once in order')
    if {row[4] for row in result} != set(STATE_CODE.values()):
        raise ValueError('contract must exercise all five states')
    if any(row[5] != int(row[4] == STATE_CODE['EFFECT_ACK_DONE']) for row in result):
        raise ValueError('contract release rule inconsistent')
    return result


def rows(path):
    result = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if not re.fullmatch(r'\s*[01] [01] [01] [01] [0-4] [01]\s*', line):
            raise ValueError(f'{path}: malformed row {line!r}')
        result.append([int(value) for value in line.split()])
    return result


def temdd_rows(ir):
    """Evaluate TEMDD's finite decision and release relations, without an oracle.

    The existing adapter parses TEMDD. This bounded lookup semantics interprets
    maps_to and permits_ordinary_release; it is not the full event/effect runtime.
    """
    if ir.get('schema') != 'temdd_ir_v1' or ir.get('ir_version') != '1':
        raise ValueError('wrong TEMDD IR schema')
    if ir.get('request', {}).get('target') != 'CORE_INVARIANT_V1':
        raise ValueError('wrong TEMDD proof target')
    maps, releases, names = {}, {}, set()
    for relation in ir['relations']:
        if relation['name'] in names:
            raise ValueError('duplicate TEMDD relation name')
        names.add(relation['name'])
        if relation['epistemic'] != 'TRUE' or relation['freshness'] != 'FRESH':
            raise ValueError('TEMDD relation is not TRUE and FRESH')
        predicate = relation['predicate']
        if predicate not in ('maps_to', 'permits_ordinary_release'):
            raise ValueError('unexpected TEMDD relation predicate')
        target_map = maps if predicate == 'maps_to' else releases
        if relation['source'] in target_map:
            raise ValueError('duplicate or conflicting TEMDD relation source')
        target_map[relation['source']] = relation['target']
    keys = [f't{t}_b{b}_i{i}_r{r}' for t, b, i, r in DOMAIN]
    if set(maps) != set(keys) or set(releases) != set(STATE_CODE):
        raise ValueError('TEMDD decision/release domain is incomplete')
    if not set(maps.values()) <= set(STATE_CODE):
        raise ValueError('unknown TEMDD decision state')
    if not set(releases.values()) <= {'false', 'true'}:
        raise ValueError('invalid TEMDD release value')
    return [[*bits, STATE_CODE[maps[key]], int(releases[maps[key]] == 'true')]
            for bits, key in zip(DOMAIN, keys)]


def compare(args):
    if not all(re.fullmatch(r'[0-9a-f]{40}', sha) for sha in (args.head, args.tree)):
        raise ValueError('invalid exact subject')
    contract_digest = digest(args.contract)
    if contract_digest['sha256'] != CONTRACT_SHA256:
        raise ValueError('frozen neutral contract digest changed')
    expected = expected_rows(json.loads(args.contract.read_text(encoding='utf-8')))
    names = [path.stem for path in args.backend]
    if len(names) != len(BACKENDS) or set(names) != BACKENDS:
        raise ValueError('require exactly c90, m68000, smalltalk, ada_spark and lean outputs')
    backends = {}
    for path in args.backend:
        if rows(path) != expected:
            raise ValueError(f'backend divergence: {path}')
        backends[path.stem] = {'result': 'PASS', 'vectors': 16, 'evidence': digest(path)}
    ir = json.loads(args.temdd_ir.read_text(encoding='utf-8'))
    if temdd_rows(ir) != expected:
        raise ValueError('TEMDD decision/release divergence')
    for marker, token in ((args.lean_marker, 'QIKVRT_CORE_INVARIANT_LEAN_PASS'),
                          (args.spark_marker, 'QIKVRT_CORE_INVARIANT_SPARK_PASS')):
        if marker.read_text(encoding='utf-8').strip() != token:
            raise ValueError(f'proof step marker missing: {marker}')
    for log in (args.lean_log, args.spark_log):
        if not log.read_text(encoding='utf-8').strip():
            raise ValueError(f'proof log is empty: {log}')
    return {
        'schema': 'qikvrt_core_invariant_cross_conformance_v2',
        'subject': {'head': args.head, 'tree': args.tree},
        'contract': contract_digest,
        'finite_domain': {'boolean_inputs': 4, 'vectors': 16, 'exhaustive': True},
        'backends': backends,
        'temdd': {'result': 'PASS', 'vectors': 16, 'evidence': digest(args.temdd_ir),
                  'semantics': 'finite decision and release relation lookup'},
        'lean': {'result': 'PASS', 'evidence': digest(args.lean_log)},
        'ada_spark': {'result': 'PASS', 'evidence': digest(args.spark_log)},
        'proof_receipts_require_trusted_workflow': True,
        'independent_reproduction': 'NOT_ESTABLISHED_BY_THIS_COMPARATOR',
        'oracle': 'language-neutral declarative vector contract',
        'implementation_authority': None, 'predecessor_evidence_transfer': False,
        'ordinary_release_only_at_effect_ack_done': True,
        'transport_ack_implies_done': False, 'overall': 'PASS', 'effect_ack_done': False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('contract', 'temdd-ir', 'lean-marker', 'spark-marker', 'lean-log', 'spark-log'):
        parser.add_argument('--' + name, type=pathlib.Path, required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--tree', required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('backend', nargs='+', type=pathlib.Path)
    args = parser.parse_args(argv)
    inputs = [args.contract, args.temdd_ir, args.lean_marker, args.spark_marker,
              args.lean_log, args.spark_log, *args.backend]
    if args.output.resolve() in {path.resolve() for path in inputs}:
        parser.error('output must not overwrite an input')
    try:
        report = compare(args)
        code = 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # A failed rerun must not leave a stale successful report at --output.
        report = {'schema': 'qikvrt_core_invariant_cross_conformance_v2',
                  'subject': {'head': args.head, 'tree': args.tree},
                  'overall': 'FAIL', 'error': str(exc), 'effect_ack_done': False}
        code = 1
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(report, sort_keys=True, separators=(',', ':')),
          file=sys.stdout if code == 0 else sys.stderr)
    return code


if __name__ == '__main__':
    raise SystemExit(main())
