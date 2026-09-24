#!/usr/bin/env python3
from __future__ import annotations
import json
import re
import sys

KEY = re.compile(r"^[A-Za-z0-9_.:-]+$")
MAX_SAFE_INTEGER = 9007199254740991
DECISIONS = {"ACCEPT", "REJECT", "HOLD_UNVERIFIED"}

def fail(code: str):
    raise ValueError(code)

def validate_scalar_domain(value):
    if value is None or isinstance(value, bool) or isinstance(value, str):
        if isinstance(value, str) and any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
            fail("UNPAIRED_SURROGATE")
        return
    if isinstance(value, int) and not isinstance(value, bool):
        if abs(value) > MAX_SAFE_INTEGER:
            fail("INTEGER_OUT_OF_RANGE")
        return
    if isinstance(value, float):
        fail("FLOAT_NOT_ALLOWED")
    if isinstance(value, list):
        for item in value:
            validate_scalar_domain(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or KEY.fullmatch(key) is None:
                fail("NON_CANONICAL_OBJECT_KEY")
            validate_scalar_domain(item)
        return
    fail("UNSUPPORTED_JSON_VALUE")

def canonicalize(value) -> str:
    validate_scalar_domain(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def evaluate(inp: dict) -> str:
    if not isinstance(inp, dict):
        fail("INPUT_OBJECT_REQUIRED")
    if inp.get("canonicalization") != "temdd_canonical_json_v1":
        fail("CANONICAL_PROFILE_MISMATCH")
    data = inp.get("data")
    policy = inp.get("policy")
    subject = inp.get("subject")
    evidence = inp.get("evidence")
    if not isinstance(data, dict) or not isinstance(policy, dict) or not isinstance(subject, dict) or not isinstance(evidence, list):
        fail("INPUT_MODEL_INVALID")
    if policy.get("evaluation_semantics") != "temdd_decision_v1":
        fail("EVALUATION_SEMANTICS_MISMATCH")
    data_equals = policy.get("data_equals")
    required = policy.get("required_evidence_types")
    if not isinstance(data_equals, dict) or not isinstance(required, list) or not all(isinstance(x, str) for x in required):
        fail("POLICY_MODEL_INVALID")
    if len(set(required)) != len(required):
        fail("DUPLICATE_REQUIRED_EVIDENCE_TYPE")
    for key, expected in data_equals.items():
        if key not in data or data[key] != expected:
            return "REJECT"
    for evidence_type in required:
        candidates = [item for item in evidence if isinstance(item, dict) and item.get("type") == evidence_type]
        if len(candidates) != 1:
            return "HOLD_UNVERIFIED"
        item = candidates[0]
        if item.get("fresh") is not True or item.get("subject") != subject:
            return "HOLD_UNVERIFIED"
        assertion = item.get("assertion")
        if assertion is not True:
            if assertion is False:
                return "REJECT"
            return "HOLD_UNVERIFIED"
    return "ACCEPT"

def main() -> int:
    try:
        inp = json.load(sys.stdin)
        canonical_value = canonicalize(inp)
        decision = evaluate(inp)
        if decision not in DECISIONS:
            fail("DECISION_DOMAIN_VIOLATION")
        json.dump({"canonical": canonical_value, "decision": decision}, sys.stdout, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        sys.stdout.write("\n")
        return 0
    except Exception as exc:
        print("HOLD_UNVERIFIED " + str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
