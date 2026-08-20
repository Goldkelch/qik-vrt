import json
from pathlib import Path

POLICY = Path('policy/UNIVERSAL_TERMINAL_CONTINUATION_V1.json')
DOC = Path('docs/UNIVERSAL_TERMINAL_CONTINUATION.md')


def test_policy_requires_reentry_and_fail_closed_stops():
    data = json.loads(POLICY.read_text(encoding='utf-8'))
    assert data['loop'][-1] == 'REENTER'
    assert data['fail_closed']['verified_fixpoint'] == 'NOOP'
    assert data['fail_closed']['ambiguous_next_action'] == 'HOLD'
    assert data['fail_closed']['stale_binding'] == 'REOBSERVE'
    assert data['fail_closed']['missing_authority'] == 'REQUEST_AUTHORITY'


def test_monitor_only_stall_class_is_explicit():
    data = json.loads(POLICY.read_text(encoding='utf-8'))
    cls = data['monitor_only_is_defect_when']
    assert all(cls.values())
    text = DOC.read_text(encoding='utf-8')
    assert 'MONITOR_ONLY_STALL' in text
    assert 'CI success without continuation is not completion' in text


def test_truth_boundaries_are_preserved():
    data = json.loads(POLICY.read_text(encoding='utf-8'))
    joined = '\n'.join(data['exclusions'])
    assert 'independent review authority' in joined
    assert 'EFFECT_ACK_DONE' in joined
