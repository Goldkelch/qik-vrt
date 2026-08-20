import json
from pathlib import Path


def test_temdd_cycle_reenters():
    data = json.loads(Path('policy/TEMDD_AUTONOMOUS_CONTINUATION_V1.json').read_text(encoding='utf-8'))
    assert data['event_cycle'][-1] == 'REENTER'
    assert data['next_event_examples']['verified_M68000_request_capsule'] == 'build deterministic MLP.TOS artifact'
    assert data['next_event_examples']['verified_semantic_register_model'] == 'bind Lean/Lake theorem and prove lowering preservation'


def test_candidate_and_effect_boundaries_remain_explicit():
    data = json.loads(Path('policy/TEMDD_AUTONOMOUS_CONTINUATION_V1.json').read_text(encoding='utf-8'))
    joined = '\n'.join(data['safety'])
    assert 'candidate success is canonical main state' in joined
    assert 'browser launch is an Effect Ack' in joined
