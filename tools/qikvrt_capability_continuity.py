# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann. Implementation: OpenAI Codex.
"""Read-only RCP migration inventory; never infer operation from source presence."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plan(root=ROOT):
    source = root / 'runtime/capabilities/SESSION_SURFACE_20260926.json'
    mapping = root / 'runtime/capabilities/CONTINUITY_MAP.json'
    inventory = json.loads(source.read_text())
    policy = json.loads(mapping.read_text())
    names = inventory['tools'] + inventory['native_interfaces']
    if len(names) != len(set(names)):
        raise ValueError('duplicate capability identity')
    rows = []
    for name in sorted(names):
        matches = [r for r in policy['routes'] if name.startswith(r['prefix'])]
        matches.sort(key=lambda r: len(r['prefix']), reverse=True)
        route = matches[0] if matches else policy['fallback']
        locations = []
        for location in route['reuse_locations']:
            path = root / location
            if not path.resolve().is_relative_to(root.resolve()):
                raise ValueError('unconfined implementation location')
            locations.append({'path': location, 'present': path.is_file(),
                              'sha256': digest(path) if path.is_file() else None})
        rows.append({'capability_id': name, 'source_observed': True,
                     'destination_state': 'UNVERIFIED',
                     'reuse_locations': locations,
                     'next_effect': route['next_effect'],
                     'blockers': route['blockers'],
                     'safe_to_retire_source': False})
    return {'schema': 'qikvrt-capability-continuity-plan/1',
            'scope': inventory['scope'], 'inventory_sha256': digest(source),
            'mapping_sha256': digest(mapping), 'capabilities': rows,
            'coverage': {'observed': len(names), 'accounted_for': len(rows),
                         'operationally_migrated': 0},
            'all_runtime_capabilities_restored': False,
            'chatgpt_tasks_allowed': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check inventory integrity, not migration completion')
    args = parser.parse_args()
    result = plan()
    if args.check:
        print(json.dumps({'inventory_accounting': 'PASS', 'coverage': result['coverage'],
                          'migration_complete': False}))
    else:
        result['observed_head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        result['observed_tree'] = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip()
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
