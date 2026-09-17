from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/chat_runtime_external_trigger_v1.json"
FILES = {
    "python": ROOT / "reference/chat_trigger/python/chat_trigger.py",
    "c90": ROOT / "reference/chat_trigger/c90/chat_trigger.c",
    "m68000": ROOT / "reference/chat_trigger/m68000/chat_trigger.s",
    "smalltalk": ROOT / "reference/chat_trigger/smalltalk/ChatTriggerState.st",
}


def test_contract_remains_fail_closed_until_real_chat_trigger_witness():
    c = json.loads(CONTRACT.read_text())
    assert c["d0"] == "CHAT_RUNTIME_EXTERNAL_TRIGGER_NOT_BOUND"
    assert c["technical_fixpoint"] is False
    assert c["state"] == "HOLD_UNVERIFIED"
    assert c["predecessor_evidence_transfer"] is False
    assert c["current"]["autonomous_chat_execution_trigger"] is False


def test_four_language_mapping_is_complete():
    c = json.loads(CONTRACT.read_text())
    assert c["required_isomorphic_implementations"] == list(FILES)
    assert all(p.is_file() for p in FILES.values())


def test_each_mapping_contains_all_six_closure_edges():
    needles = {
        "python": ["repository_processing", "durable_readback", "chat_trigger", "observation", "continuation", "fresh_validation"],
        "c90": ["repository_processing", "durable_readback", "chat_trigger", "observation", "continuation", "fresh_validation"],
        "m68000": ["repository_processing", "durable_readback", "autonomous chat trigger", "observation", "continuation", "fresh E2E validation"],
        "smalltalk": ["repositoryProcessing", "durableReadback", "chatTrigger", "observation", "continuation", "freshValidation"],
    }
    for language, path in FILES.items():
        text = path.read_text()
        for needle in needles[language]:
            assert needle in text, (language, needle)
