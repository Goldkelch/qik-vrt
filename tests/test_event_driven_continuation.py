import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/".github/workflows/qikvrt_event_driven_continuation.yml"
DOC=ROOT/"docs/EVENT_DRIVEN_CONTINUATION.md"
POLICY=ROOT/"policy/QIKVRT_EVENT_DRIVEN_CONTINUATION_V1.json"

def test_event_driven_continuation_contract():
    text=WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request:" in text and "pull_request_review:" in text and "workflow_run:" in text
    assert "schedule:" not in text
    assert "contents: read" in text and "contents: write" not in text
    assert "gh pr merge" not in text and "gh pr review" not in text
    assert 'head != expected' in text
    assert "HOLD_UNVERIFIED: subject mutated after triggering event" in text
    assert 'review.get("commit_id") != head' in text
    doc=DOC.read_text(encoding="utf-8")
    assert "predecessor evidence is never transferred" in doc
    assert "never from polling or a schedule" in doc
    policy=json.loads(POLICY.read_text(encoding="utf-8"))
    assert policy["mode"]=="EVENT_DRIVEN"
    assert policy["predecessor_evidence_transfer"] is False
    assert policy["authority_boundary"]["automation_may_synthesize_approval"] is False
    assert policy["continuation"]["merge_capability"] is False
    assert policy["completion_claims"]["EFFECT_ACK_DONE"] is False
