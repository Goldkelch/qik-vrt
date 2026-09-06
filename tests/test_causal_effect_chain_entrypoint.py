import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_causal_effect_chain_is_closed_and_ordered():
    policy = load("policy/CAUSAL_EFFECT_CHAIN_V1.json")
    assert policy["schema"] == "qikvrt_causal_effect_chain_v1"
    assert policy["chain"] == [
        "OBSERVE",
        "BIND_EXACT_SUBJECT",
        "CLASSIFY_CLAIMS_AND_BOUNDARIES",
        "VERIFY_PRECONDITIONS",
        "RESOLVE_AUTHORITY",
        "EXECUTE_ONE_AUTHORIZED_EFFECT",
        "READBACK_EFFECT",
        "PERSIST_RECEIPT",
        "SUCCESSOR_OR_HOLD",
    ]
    invariants = policy["invariants"]
    assert invariants["one_mutating_move_per_cycle"] is True
    assert invariants["expected_readback_required_before_effect"] is True
    assert invariants["predecessor_evidence_transfer"] is False
    assert invariants["effect_without_readback_may_not_be_called_done"] is True


def test_ai_task_router_requires_causal_chain_before_effect():
    router = load("AI_TASK_ROUTER.json")
    assert router["causal_effect_chain"] == "policy/CAUSAL_EFFECT_CHAIN_V1.json"
    assert router["causal_chain_required"] is True
    route = router["routes"]["zenodo_publication"]
    assert route["primary_capability"] == "runtime/capabilities/ZENODO_PUBLICATION_CAPABILITY.json"
    assert route["production_policy"] == "policy/zenodo-machine-proof-policy-v2.json"
    assert "public DOI/record metadata" in route["resolution_sequence"][-1]


def test_every_declared_ai_adapter_exposes_router():
    adapters = load("AI_ADAPTERS.json")
    assert adapters["task_router"] == "AI_TASK_ROUTER.json"
    assert adapters["causal_effect_chain"] == "policy/CAUSAL_EFFECT_CHAIN_V1.json"
    assert "before any mutating task" in adapters["task_routing_rule"]
