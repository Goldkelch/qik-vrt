#!/usr/bin/env python3
"""Fail-closed evaluator for known-defect and requirement closure inventories."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any

CLOSED = {"CLOSED_VERIFIED", "SUPERSEDED_WITH_TRACE", "NOT_APPLICABLE_WITH_EVIDENCE"}
NONCLOSED = {"ACTIVE_REMAINDER", "BLOCKED_EXTERNAL"}
ALLOWED = CLOSED | NONCLOSED
REQUIRED_NONCLOSED = {
    "stable_id",
    "class",
    "source_ref",
    "current_state",
    "first_deterministic_blocker",
    "next_history_preserving_action",
    "evidence_refs",
}


class ClosureError(ValueError):
    pass


def evaluate(inventory: Mapping[str, Any]) -> dict[str, Any]:
    items = inventory.get("items")
    if not isinstance(items, list):
        raise ClosureError("items must be a list")

    seen: set[str] = set()
    remainders: list[dict[str, Any]] = []
    violations: list[dict[str, str]] = []

    for index, raw in enumerate(items):
        if not isinstance(raw, Mapping):
            raise ClosureError(f"item[{index}] must be an object")
        stable_id = raw.get("stable_id")
        state = raw.get("current_state")
        if not isinstance(stable_id, str) or not stable_id:
            raise ClosureError(f"item[{index}] stable_id missing")
        if stable_id in seen:
            violations.append({"stable_id": stable_id, "violation": "DUPLICATE_STABLE_ID"})
            continue
        seen.add(stable_id)
        if state not in ALLOWED:
            violations.append({"stable_id": stable_id, "violation": "UNKNOWN_OR_FORBIDDEN_DISPOSITION"})
            continue

        if state in NONCLOSED:
            missing = [field for field in sorted(REQUIRED_NONCLOSED) if field not in raw]
            if missing:
                violations.append({"stable_id": stable_id, "violation": "INCOMPLETE_ACTIVE_REMAINDER:" + ",".join(missing)})
            else:
                blocker = raw.get("first_deterministic_blocker")
                next_action = raw.get("next_history_preserving_action")
                evidence_refs = raw.get("evidence_refs")
                if not isinstance(blocker, str) or not blocker:
                    violations.append({"stable_id": stable_id, "violation": "MISSING_FIRST_DETERMINISTIC_BLOCKER"})
                if not isinstance(next_action, str) or not next_action:
                    violations.append({"stable_id": stable_id, "violation": "MISSING_NEXT_ACTION"})
                if not isinstance(evidence_refs, list) or not evidence_refs:
                    violations.append({"stable_id": stable_id, "violation": "MISSING_EVIDENCE_REFS"})
            remainders.append(dict(raw))

        if raw.get("class") == "REPAIR_CANDIDATE" and state == "CLOSED_VERIFIED":
            if raw.get("effective_target_observed") is not True:
                violations.append({"stable_id": stable_id, "violation": "REPAIR_CLOSED_WITHOUT_EFFECTIVE_TARGET_OBSERVATION"})

    status = "CLOSED" if not remainders and not violations else "OPEN"
    return {
        "schema": "qikvrt_requirement_closure_evaluation_v1",
        "status": status,
        "item_count": len(items),
        "active_remainder_count": len(remainders),
        "violation_count": len(violations),
        "first_deterministic_blocker": violations[0]["violation"] if violations else (remainders[0].get("first_deterministic_blocker") if remainders else None),
        "active_remainders": remainders,
        "violations": violations,
        "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
    }


def _load(path: str) -> Mapping[str, Any]:
    value = json.load(sys.stdin) if path == "-" else json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ClosureError("inventory must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluate", nargs="?")
    parser.add_argument("--input", default="-")
    args = parser.parse_args(argv)
    try:
        result = evaluate(_load(args.input))
    except (OSError, ValueError, json.JSONDecodeError, ClosureError) as exc:
        result = {
            "schema": "qikvrt_requirement_closure_evaluation_v1",
            "status": "OPEN",
            "first_deterministic_blocker": "INVALID_CLOSURE_INVENTORY",
            "detail": str(exc),
            "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "CLOSED" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
