import importlib.util
from pathlib import Path

PATH = Path('tools/qikvrt_terminal_continuation.py')
spec = importlib.util.spec_from_file_location('selector', PATH)
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)

BASE = {
    'context_bound': True,
    'authority_bound': True,
    'meaning_bound': True,
    'evidence_current': True,
    'next_action_uniquely_determined': True,
    'external_effect_required': False,
    'external_effect_authorized': False,
    'fixpoint_verified': False,
    'stale_binding': False,
    'ambiguous_next_action': False,
}


def test_green_stable_state_continues():
    assert selector.decide(dict(BASE)) == 'CONTINUE'


def test_verified_fixpoint_noops():
    s = dict(BASE, fixpoint_verified=True)
    assert selector.decide(s) == 'NOOP'


def test_stale_binding_reobserves():
    s = dict(BASE, stale_binding=True)
    assert selector.decide(s) == 'REOBSERVE'


def test_missing_authority_requests_authority():
    s = dict(BASE, authority_bound=False)
    assert selector.decide(s) == 'REQUEST_AUTHORITY'


def test_unauthorized_external_effect_holds():
    s = dict(BASE, external_effect_required=True, external_effect_authorized=False)
    assert selector.decide(s) == 'HOLD'
