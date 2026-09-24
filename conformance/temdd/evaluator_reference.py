#!/usr/bin/env python3
"""Independent process evaluator for the TEMDD machine-verifiable decision profile."""
from __future__ import annotations

import json
import sys


def decision(result: str, code: str) -> dict:
    return {"code": code, "result": result}


def evaluate(bound: object) -> dict:
    if not isinstance(bound, dict):
        return decision("FAIL", "MALFORMED_INPUT")
    required = {
        "data", "policy", "subject", "evidence",
        "model_version", "policy_version", "evaluator_version",
    }
    if set(bound) != required:
        return decision("FAIL", "MALFORMED_INPUT")
    data = bound.get("data")
    policy = bound.get("policy")
    subject = bound.get("subject")
    evidence = bound.get("evidence")
    if not all(isinstance(value, dict) for value in (data, policy, subject, evidence)):
        return decision("FAIL", "MALFORMED_INPUT")
    if (
        bound.get("model_version") != "1"
        or bound.get("policy_version") != "1"
        or bound.get("evaluator_version") != "1"
    ):
        return decision("HOLD_UNVERIFIED", "VERSION_MISMATCH")
    if data.get("valid") is not True:
        return decision("FAIL", "INVALID")
    if evidence.get("subject_digest") != subject.get("digest"):
        return decision("HOLD_UNVERIFIED", "SUBJECT_MISMATCH")
    if evidence.get("fresh") is not True:
        return decision("HOLD_UNVERIFIED", "INSUFFICIENT_EVIDENCE")
    if evidence.get("replay") is True:
        return decision("FAIL", "REPLAY")
    if evidence.get("duplicate") is True:
        return decision("FAIL", "DUPLICATE")
    if policy.get("allow") is not True:
        return decision("FAIL", "POLICY_VIOLATION")
    return decision("PASS", "ACCEPT")


def main() -> int:
    raw = sys.stdin.read()
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = None
    sys.stdout.write(json.dumps(evaluate(value), sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
