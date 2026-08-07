import base64
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "qikvrt_io_round_trip", ROOT / "tools" / "qikvrt_io_round_trip.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def base_envelope():
    return {
        "event_id": "test-event",
        "direction": "input",
        "timestamp": "2026-08-07T13:43:00Z",
        "media_type": "text/plain",
        "payload_text": "new result",
        "provenance": {"human": "Ingolf Lohmann", "system": "test"},
        "knowledge_class": "NEW_FORMAL_RESULT",
        "proof_status": "FORMALLY_PROVED",
        "claim_scope": "test scope",
    }


def initialize_root(tmp_path):
    (tmp_path / "AI").write_text("entrypoint", encoding="utf-8")
    (tmp_path / "policy").mkdir()


def test_payload_is_content_addressed():
    digest, source = MODULE.payload_digest(base_envelope())
    assert source == "payload_text"
    assert digest == hashlib.sha256(b"new result").hexdigest()


def test_binary_payload_round_trips_exact_bytes(tmp_path):
    initialize_root(tmp_path)
    raw = b"\x00QIK-VRT\xff\n"
    envelope = base_envelope()
    envelope.pop("payload_text")
    envelope["payload_base64"] = base64.b64encode(raw).decode("ascii")
    path, receipt = MODULE.materialize(tmp_path, envelope)
    stored = tmp_path / receipt["payload_storage"]["repository_path"]
    assert path.exists()
    assert stored.read_bytes() == raw
    assert receipt["payload_sha256"] == hashlib.sha256(raw).hexdigest()


def test_digest_only_payload_requires_bound_reference(tmp_path):
    initialize_root(tmp_path)
    envelope = base_envelope()
    envelope.pop("payload_text")
    envelope["payload_sha256"] = "0" * 64
    with pytest.raises(SystemExit, match="payload_reference"):
        MODULE.materialize(tmp_path, envelope)
    envelope["payload_reference"] = {
        "scheme": "sealed-object",
        "locator": "object:test",
    }
    _, receipt = MODULE.materialize(tmp_path, envelope)
    assert receipt["payload_storage"]["persisted_bytes"] is False
    assert receipt["payload_storage"]["reference"]["locator"] == "object:test"


def test_unproved_claim_cannot_be_ready_for_zenodo():
    envelope = base_envelope()
    envelope.update({
        "proof_status": "UNPROVED_CLAIM",
        "stable_bytes": True,
        "rights_clear": True,
        "publication_granularity_suitable": True,
        "novelty_or_version_significance": True,
    })
    route = MODULE.publication_route(
        "NEW_CLAIM", envelope["proof_status"], False, envelope
    )
    assert route["zenodo"] == "HOLD"


def test_formal_result_can_route_to_zenodo_but_not_ietf():
    envelope = base_envelope()
    envelope.update({
        "stable_bytes": True,
        "rights_clear": True,
        "publication_granularity_suitable": True,
        "novelty_or_version_significance": True,
    })
    route = MODULE.publication_route(
        "NEW_FORMAL_RESULT", envelope["proof_status"], False, envelope
    )
    assert route["zenodo"] == "READY"
    assert route["ietf"] == "NOT_ELIGIBLE"


def test_protocol_result_requires_ietf_specific_gates():
    envelope = base_envelope()
    envelope.update({
        "knowledge_class": "NEW_PROTOCOL_RESULT",
        "proof_status": "MACHINE_VERIFIED_DERIVATION",
        "stable_bytes": True,
        "rights_clear": True,
        "publication_granularity_suitable": True,
        "novelty_or_version_significance": True,
        "protocol_or_interoperability_relevance": True,
        "ietf_format_valid": True,
        "ietf_submission_rationale": True,
    })
    route = MODULE.publication_route(
        "NEW_PROTOCOL_RESULT", envelope["proof_status"], False, envelope
    )
    assert route == {
        "zenodo": "READY",
        "ietf": "READY",
        "reason": "deterministic_policy_evaluation",
    }


def test_duplicate_never_creates_publication_noise():
    envelope = base_envelope()
    route = MODULE.publication_route(
        "DUPLICATE", "FORMALLY_PROVED", True, envelope
    )
    assert route["zenodo"] == "NOT_ELIGIBLE"
    assert route["ietf"] == "NOT_ELIGIBLE"


def test_materialize_is_append_only_and_reuses_exact_payload(tmp_path):
    initialize_root(tmp_path)
    envelope = base_envelope()
    first_path, first = MODULE.materialize(tmp_path, envelope)
    second_path, second = MODULE.materialize(tmp_path, envelope)
    assert first_path.exists()
    assert second_path.exists()
    assert first["receipt_sha256"] != second["receipt_sha256"]
    assert first["knowledge_class"] == "NEW_FORMAL_RESULT"
    assert second["knowledge_class"] == "DUPLICATE"
    payload_path = tmp_path / first["payload_storage"]["repository_path"]
    assert payload_path.read_bytes() == b"new result"
    assert first["payload_storage"] == second["payload_storage"]
    receipts = list(
        (tmp_path / "state" / "io_round_trip" / "receipts").glob("*.json")
    )
    payloads = list(
        (tmp_path / "state" / "io_round_trip" / "payloads").rglob("*.bin")
    )
    assert len(receipts) == 2
    assert len(payloads) == 1
    parsed = [json.loads(path.read_text(encoding="utf-8")) for path in receipts]
    assert {item["knowledge_class"] for item in parsed} == {
        "NEW_FORMAL_RESULT",
        "DUPLICATE",
    }
