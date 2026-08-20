#!/usr/bin/env python3
import json
import sys


def decide(state):
    required = ('context_bound', 'authority_bound', 'meaning_bound', 'evidence_current')
    if state.get('stale_binding'):
        return 'REOBSERVE'
    if state.get('ambiguous_next_action'):
        return 'HOLD'
    if not state.get('authority_bound'):
        return 'REQUEST_AUTHORITY'
    if not state.get('evidence_current'):
        return 'HOLD'
    if state.get('external_effect_required') and not state.get('external_effect_authorized'):
        return 'HOLD'
    if state.get('fixpoint_verified'):
        return 'NOOP'
    if all(state.get(k) for k in required) and state.get('next_action_uniquely_determined'):
        return 'CONTINUE'
    return 'HOLD'


def main():
    data = json.load(sys.stdin)
    out = {'decision': decide(data)}
    json.dump(out, sys.stdout, sort_keys=True)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
