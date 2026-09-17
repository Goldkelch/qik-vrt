from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/cidetemdd_manifestation_guard_v1.json"


def test_manifestation_guard_is_fail_closed():
    c = json.loads(CONTRACT.read_text())
    assert c["predecessor_evidence_transfer"] is False
    assert c["release_candidate_allowed"] is False
    assert c["public_release_allowed"] is False
    assert c["effect_ack_done"] is False
    assert c["observed_current_blocker"] == "REFLEXIVE_SUCCESSOR_LOSES_EXECUTION_ADMISSION_BY_ACTOR_PROVENANCE"


def test_all_delivery_dimensions_are_explicit():
    c = json.loads(CONTRACT.read_text())
    assert set(c["dimensions"]) == {
        "continuous_integration",
        "continuous_delivery",
        "continuous_execution",
        "tested_event_model_driven_development",
        "manifestation",
    }
    for name, spec in c["dimensions"].items():
        assert spec["requires"], name
        assert spec["state"] in {"HOLD_UNVERIFIED", "PARTIAL", "PASS"}


def test_manifestation_requires_fresh_successor_execution():
    c = json.loads(CONTRACT.read_text())
    req = set(c["dimensions"]["manifestation"]["requires"])
    assert "canonical_integrity_persisted" in req
    assert "exact_successor_readback" in req
    assert "fresh_successor_validation" in req
    assert "no_action_required_on_required_current_subject_gates" in req
