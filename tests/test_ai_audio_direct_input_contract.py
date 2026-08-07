import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = (ROOT / "AI").read_text(encoding="utf-8")
POLICY = json.loads((ROOT / "policy/AI_AUDIO_DIRECT_INPUT_CONTRACT_V1.json").read_text(encoding="utf-8"))


def test_ai_entrypoint_references_audio_contract():
    assert "DIRECT AUDIO INPUT CONTRACT" in AI
    assert "policy/AI_AUDIO_DIRECT_INPUT_CONTRACT_V1.json" in AI


def test_audio_is_direct_user_instruction_surface():
    rules = POLICY["rules"]
    assert rules["audio_is_first_class_user_instruction_surface"] is True
    assert rules["transcribe_without_confirmation_when_technically_readable"] is True
    assert rules["execute_transcribed_instruction_without_modality_reconfirmation_when_otherwise_authorized"] is True


def test_fail_closed_transcription_semantics():
    rules = POLICY["rules"]
    assert rules["preserve_transcription_uncertainty"] is True
    assert rules["fabricate_unreadable_transcript"] is False
    assert POLICY["failure_semantics"]["audio_unreadable_or_transcription_runtime_unavailable"] == "DISCLOSE_TECHNICAL_LIMITATION_AND_DO_NOT_INVENT_CONTENT"


def test_existing_effect_boundaries_remain_explicit():
    boundaries = set(POLICY["unchanged_boundaries"])
    required = {
        "SAFETY",
        "AUTHORIZATION",
        "EXTERNAL_EFFECTS",
        "ZENODO",
        "IETF",
        "PASS",
        "FINAL_PASS",
        "EFFECT_ACK_DONE",
    }
    assert required <= boundaries


def test_no_modality_reconfirmation():
    interaction = POLICY["human_interaction_policy"]
    assert interaction["ask_whether_to_transcribe"] is False
    assert interaction["ask_again_because_input_was_audio"] is False
