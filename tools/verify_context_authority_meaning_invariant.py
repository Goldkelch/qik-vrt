#!/usr/bin/env python3
"""Validate the context-authority-meaning repository invariant."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "policy" / "CONTEXT_AUTHORITY_MEANING_INVARIANT_V1.json"
DOC = ROOT / "docs" / "KAUSAL_EPISTEMISCHE_HOCHAUFLOESUNG.md"

REQUIRED_INVARIANTS = {
    "CONTEXT_REQUIRED_FOR_INTERPRETATION",
    "AUTHORITY_REQUIRED_FOR_PRODUCTIVE_EFFECT",
    "MEANING_BOUND_TO_EXACT_SUBJECT_AND_STATE",
    "EVIDENCE_BOUND_TO_CLAIM",
    "CAUSALITY_NOT_SEQUENCE",
    "REQUESTED_NOT_EXECUTED",
    "EXECUTED_NOT_OBSERVED",
    "OBSERVED_NOT_ACKNOWLEDGED",
    "TRANSPORT_ACK_NOT_EFFECT_ACK",
}

REQUIRED_BINDINGS = {
    "subject",
    "context",
    "exact_state",
    "meaning",
    "authority",
    "evidence",
    "causal_order",
    "intended_effect",
    "observed_effect",
    "proof",
}

REQUIRED_DOC_MARKERS = (
    "Kontext, Autorität und Bedeutung gehören zusammen.",
    "KAUSALITÄT    ≠ SEQUENZ",
    "REQUESTED     ≠ EXECUTED",
    "TRANSPORT_ACK ≠ EFFECT_ACK",
    "history-preserving",
    "PASS",
    "FINAL_PASS",
    "EFFECT_ACK_DONE",
)


def load_policy() -> dict[str, object]:
    return json.loads(POLICY.read_text(encoding="utf-8"))


def validate() -> None:
    policy = load_policy()
    assert policy["id"] == "CONTEXT_AUTHORITY_MEANING_INVARIANT_V1"
    assert policy["version"] == 1
    assert set(policy["invariants"]) >= REQUIRED_INVARIANTS
    assert set(policy["required_binding_fields"]) >= REQUIRED_BINDINGS

    actions = set(policy["decision_rule"]["fail_closed_actions"])
    assert actions == {"NOOP", "HOLD", "REOBSERVE", "REQUEST_AUTHORITY"}

    non_claims = "\n".join(policy["non_claims"])
    for marker in ("independent review authority", "PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
        assert marker in non_claims

    doc = DOC.read_text(encoding="utf-8")
    for marker in REQUIRED_DOC_MARKERS:
        assert marker in doc, marker


if __name__ == "__main__":
    validate()
    print("CONTEXT_AUTHORITY_MEANING_INVARIANT_V1: structurally valid")
