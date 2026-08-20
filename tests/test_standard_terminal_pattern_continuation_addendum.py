from pathlib import Path


def test_addendum_forbids_success_as_stop_condition():
    text = Path('docs/STANDARD_TERMINAL_PATTERN_CONTINUATION_ADDENDUM.md').read_text(encoding='utf-8')
    assert 'MUST NOT terminate merely because observation, CI, materialization, or review preparation is successful' in text
    assert 'MUST route the bound action to a capable executor' in text
    assert '`CONTINUE`' in text
    assert '`NOOP`' in text
    assert '`HOLD`' in text
