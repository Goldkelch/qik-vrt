import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "CONTEXT_AUTHORITY_MEANING_INVARIANT_V1.json"
VALIDATOR = ROOT / "tools" / "verify_context_authority_meaning_invariant.py"


def test_policy_preserves_required_distinctions() -> None:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    invariants = set(policy["invariants"])
    assert "CONTEXT_REQUIRED_FOR_INTERPRETATION" in invariants
    assert "AUTHORITY_REQUIRED_FOR_PRODUCTIVE_EFFECT" in invariants
    assert "MEANING_BOUND_TO_EXACT_SUBJECT_AND_STATE" in invariants
    assert "CAUSALITY_NOT_SEQUENCE" in invariants
    assert "TRANSPORT_ACK_NOT_EFFECT_ACK" in invariants


def test_validator_accepts_repository_candidate() -> None:
    completed = subprocess.run(
        [sys.executable, str(VALIDATOR)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert "structurally valid" in completed.stdout
