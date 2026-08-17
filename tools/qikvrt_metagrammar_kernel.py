#!/usr/bin/env python3
"""Deterministic fail-closed validator for QIK-VRT metagrammar messages."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SECTIONS = [
    "AUTHORITY",
    "SUCCESSOR_BINDING",
    "MATERIALIZATION",
    "EXACT_HEAD_GATES",
    "INWARD_REFLEXIVITY",
    "OUTWARD_REFLECTION",
    "FIRST_DETERMINISTIC_BLOCKER",
    "NEXT_ACTION",
]

BLOCKERS = [
    "AUTHORITY_CONFLICT",
    "EXACT_HEAD_MISMATCH",
    "SCOPE_OR_PROVENANCE_DRIFT",
    "INTEGRITY_FAILURE",
    "PLATFORM_PRE_JOB_BARRIER",
    "EXECUTED_WORKFLOW_FAILURE",
    "NONTERMINAL_APPLICABLE_GATE",
    "REQUIRED_REVIEW_MISSING",
    "REQUIRED_AUTHORIZATION_MISSING",
    "REQUIRED_EFFECT_RECEIPT_MISSING",
    "SEMANTIC_HOLD",
    "NONE",
]


def _require(condition: bool, code: str, errors: list[str]) -> None:
    if not condition:
        errors.append(code)


def validate(message: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    _require(message.get("protocol") == "QMV/1.0", "QMV-E000", errors)
    for section in SECTIONS:
        _require(section in message, f"QMV-E-MISSING-{section}", errors)

    authority = message.get("AUTHORITY", {})
    for key in ("repository", "ref", "head", "tree"):
        _require(bool(authority.get(key)), f"QMV-E-AUTHORITY-{key.upper()}", errors)

    outward = message.get("OUTWARD_REFLECTION", {})
    completion = outward.get("completion", {})
    for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
        _require(completion.get(key) in (True, False, None), f"QMV-E-COMPLETION-{key}", errors)

    if completion.get("EFFECT_ACK_DONE") is True:
        _require(completion.get("FINAL_PASS") is True, "QMV-E012", errors)
    if completion.get("FINAL_PASS") is True:
        _require(completion.get("PASS") is True, "QMV-E011", errors)

    gates = message.get("EXACT_HEAD_GATES", {})
    if completion.get("PASS") is True:
        _require(gates.get("all_applicable_executed_terminal_success") is True, "QMV-E010", errors)
        _require(gates.get("head") == authority.get("candidate_head", gates.get("head")), "QMV-E004", errors)

    blocker = message.get("FIRST_DETERMINISTIC_BLOCKER")
    _require(blocker in BLOCKERS, "QMV-E-BLOCKER", errors)
    inward = message.get("INWARD_REFLEXIVITY", {})
    if blocker != "NONE":
        _require(inward.get("productive_writer_admitted") is False, "QMV-E-FAIL-CLOSED", errors)

    if gates.get("action_required") is True or gates.get("zero_job") is True:
        _require(gates.get("all_applicable_executed_terminal_success") is not True, "QMV-E007", errors)

    effects = message.get("effects", {})
    if effects.get("transport_ack") is True and effects.get("effect_ack") is not True:
        _require(completion.get("EFFECT_ACK_DONE") is not True, "QMV-E009", errors)

    return sorted(set(errors))


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: qikvrt_metagrammar_kernel.py MESSAGE.json", file=sys.stderr)
        return 2
    payload = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    errors = validate(payload)
    print(json.dumps({"valid": not errors, "errors": errors}, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
