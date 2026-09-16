import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "QIKVRT_THREE_PHASE_MESH_SEED_MVP_V1.json"


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_three_distinct_phases_form_closed_seed_cycle():
    c = load_contract()
    phases = c["phases"]
    assert set(phases) == {"terminal", "transputer", "router"}
    nodes = {v["node"] for v in phases.values()}
    assert len(nodes) == 3
    edges = {(e["from"], e["to"]) for e in c["seed_edges"]}
    assert edges == {
        ("universal-terminal", "universal-cloud-transputer"),
        ("universal-cloud-transputer", "evidence-router"),
        ("evidence-router", "universal-terminal"),
    }


def test_fail_closed_evidence_semantics_are_explicit():
    inv = load_contract()["invariants"]
    assert inv["predecessor_evidence_transfer"] is False
    assert inv["reachable_is_not_valid"] is True
    assert inv["valid_is_not_proved"] is True
    assert inv["proved_is_not_effect"] is True
    assert inv["transport_ack_is_not_effect_ack"] is True
    assert inv["evidence_history"] == "append-only"
    assert inv["assertion_validity"] == "non-monotonic"
    assert inv["current_admissibility"] == "fresh-validation-required"


def test_each_phase_requires_independent_readback_or_fresh_validation():
    phases = load_contract()["phases"]
    assert "independent_readback" in phases["terminal"]["done_requires"]
    assert "independent_readback" in phases["transputer"]["done_requires"]
    assert "fresh_validation" in phases["router"]["done_requires"]


def test_mvp_requires_all_three_phases_and_edges():
    required = set(load_contract()["effect_ack_done_requires"])
    assert required == {
        "terminal_phase_done",
        "transputer_phase_done",
        "router_phase_done",
        "three_seed_edges_freshly_validated",
        "end_to_end_effect_readback",
    }
