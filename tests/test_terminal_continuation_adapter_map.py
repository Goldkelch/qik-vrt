import json
from pathlib import Path


def test_expected_orchestrators_are_covered():
    data = json.loads(Path('policy/TERMINAL_CONTINUATION_ADAPTER_MAP_V1.json').read_text(encoding='utf-8'))
    names = {item['component'] for item in data['adapters']}
    assert {'repository_monitor','reflexive_watchdog','phoenix_self_heal','requested_review_executor','code_owner_observer','integrity_materializer','stacked_successor_recovery','issue_agent','temdd_compiler','publication_preparation','authority_mirror_orchestrator'} <= names


def test_code_owner_adapter_preserves_identity_boundary():
    data = json.loads(Path('policy/TERMINAL_CONTINUATION_ADAPTER_MAP_V1.json').read_text(encoding='utf-8'))
    owner = next(item for item in data['adapters'] if item['component'] == 'code_owner_observer')
    assert 'never fabricate review identity' in owner['on_continue']
