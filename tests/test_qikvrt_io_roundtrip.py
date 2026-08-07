# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.

from tools import qikvrt_io_roundtrip as io


def test_normalize_accepts_multimodal_and_preserves_direction():
    value = io.normalize({"direction": "INPUT", "modality": "audio", "payload": "sha256:abc"})
    assert value["direction"] == "INPUT"
    assert value["modality"] == "audio"


def test_unknown_modality_fails_into_other_without_losing_payload():
    value = io.normalize({"modality": "future-modality", "payload": {"x": 1}})
    assert value["modality"] == "other"
    assert value["payload"] == {"x": 1}


def test_new_knowledge_requires_proof_granularity_connectability_and_artifact_binding():
    base = io.normalize({
        "direction": "OUTPUT",
        "modality": "structured_data",
        "payload": {"claim": "x"},
        "epistemic_status": "NEW_KNOWLEDGE",
        "granularity": "PUBLICATION_UNIT",
        "connectability": "CANONICAL",
        "metadata": {"artifact_sha256": "a" * 64},
        "machine_proof_receipt": {"sha256": "b" * 64},
    })
    state = io.publication_state(base)
    assert state["new_knowledge"] is True
    assert state["machine_proof_receipt"] is True
    assert state["eligible_granularity"] is True
    assert state["connectable"] is True
    assert state["exact_artifact_binding"] is True


def test_missing_machine_proof_is_not_publication_ready():
    value = io.normalize({
        "epistemic_status": "NEW_KNOWLEDGE",
        "granularity": "ELIGIBLE",
        "connectability": "CONNECTABLE",
        "metadata": {"artifact_sha256": "a" * 64},
    })
    assert io.publication_state(value)["machine_proof_receipt"] is False


def test_external_effect_authorization_is_exact_and_fail_closed(monkeypatch):
    monkeypatch.delenv("QIKVRT_EXTERNAL_EFFECT_AUTHORIZATION", raising=False)
    assert io.authorized("ZENODO") is False
    monkeypatch.setenv("QIKVRT_EXTERNAL_EFFECT_AUTHORIZATION", "ZENODO")
    assert io.authorized("ZENODO") is True
    assert io.authorized("IETF") is False
