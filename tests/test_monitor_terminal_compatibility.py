import json
from pathlib import Path


def test_monitor_green_routes_continue():
    data = json.loads(Path('policy/MONITOR_TERMINAL_COMPATIBILITY_V1.json').read_text(encoding='utf-8'))
    c = data['compatibility']
    assert c['monitor_may_stop_on_green'] is False
    assert c['monitor_must_route_continue'] is True
    assert c['monitor_may_stop_on_fixpoint'] is True
    assert c['monitor_may_stop_on_hold'] is True
