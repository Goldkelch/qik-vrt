import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "policy" / "METAGRAMMAR_OF_UNDERSTANDING_V1.json"
CONTRACT_PATH = ROOT / "docs" / "METAGRAMMAR_OF_UNDERSTANDING.md"
ADAPTERS_PATH = ROOT / "AI_ADAPTERS.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_metagrammar_policy_is_reflexive_and_fail_closed() -> None:
    policy = load_json(POLICY_PATH)

    assert policy["canonical_entrypoint"] == "AI"
    assert policy["universality"]["kind"] == "structural"
    assert policy["universality"]["empirical_omniscience_claimed"] is False

    required = set(policy["required_bindings"])
    assert {
        "claim",
        "referent",
        "source",
        "authority",
        "evidence",
        "epistemic_class",
        "state",
        "causal_order",
        "effect",
        "witness",
        "uncertainty",
        "next_allowed_transition",
    } <= required

    assert policy["reflexive_chain"][0] == "input"
    assert policy["reflexive_chain"][-1] == "updated_state"
    assert policy["fail_closed"]["forbid_similarity_as_identity"] is True
    assert policy["fail_closed"]["forbid_sequence_as_causality"] is True
    assert policy["fail_closed"]["forbid_claim_as_effect"] is True


def test_audio_examples_preserve_epistemic_boundaries() -> None:
    policy = load_json(POLICY_PATH)
    audio = policy["audio_fragment_classification"]

    assert audio["distinct_fragments"] == 5
    assert audio["supplied_files"] == 10
    assert audio["duplicate_pairs"] == 5
    assert audio["examples"]["ping_piep_pi"] == "wordplay_not_protocol_derivation"
    assert audio["examples"]["transistor_converter"] == "technical_relation_not_identity"


def test_ai_adapter_registry_exposes_generic_reflexive_contract() -> None:
    adapters = load_json(ADAPTERS_PATH)
    generic = [
        adapter
        for adapter in adapters["adapters"]
        if adapter["system"] == "Generic cognitive system"
    ]

    assert generic == [
        {
            "system": "Generic cognitive system",
            "path": "policy/METAGRAMMAR_OF_UNDERSTANDING_V1.json",
            "mode": "reflexive-contract",
        }
    ]
    assert CONTRACT_PATH.is_file()
