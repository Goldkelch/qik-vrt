import json
from pathlib import Path


def test_rollout_covers_required_layers_and_forbids_observed_only_terminal():
    data = json.loads(Path('policy/TERMINAL_CONTINUATION_ROLLOUT_V1.json').read_text(encoding='utf-8'))
    layers = {x['layer'] for x in data['rollout']}
    assert {'monitor','watchdog','self_heal','review','materialization','stack','issue_agent','temdd','publication','authority_mirror'} <= layers
    assert 'OBSERVED_ONLY' in data['completion_criterion']
