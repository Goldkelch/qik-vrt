#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Classify HOLD admissibility from exact repository-native carriers."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Sequence
from typing import Any


SCHEMA = "qikvrt_hold_admissibility_v1"
CONTINUATION_STATES = {
    "ACTION",
    "CONTINUE",
    "REOBSERVE",
    "REQUEST_AUTHORITY",
    "SUCCESSOR",
}


class CarrierBindingError(ValueError):
    """Raised when a supplied carrier binding is not canonical."""


def _canonical(values: Sequence[str], label: str) -> list[str]:
    result: list[str] = []
    for raw in values:
        if not isinstance(raw, str):
            raise CarrierBindingError(f"{label} carrier must be a string")
        value = raw.strip()
        if not value:
            raise CarrierBindingError(f"{label} carrier must not be empty")
        result.append(value)
    if len(result) != len(set(result)):
        raise CarrierBindingError(f"{label} carriers must be unique")
    return sorted(result)


def classify(
    *,
    issue_carriers: Sequence[str] = (),
    pull_request_carriers: Sequence[str] = (),
    branch_carriers: Sequence[str] = (),
    continuation_state: str = "CONTINUE",
    first_blocker: str | None = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    """Return HOLD only when every repository-native carrier set is empty."""
    if continuation_state not in CONTINUATION_STATES:
        raise CarrierBindingError(
            f"continuation_state must be one of {sorted(CONTINUATION_STATES)}"
        )

    issues = _canonical(issue_carriers, "issue")
    pulls = _canonical(pull_request_carriers, "pull_request")
    branches = _canonical(branch_carriers, "branch")
    carrier_count = len(issues) + len(pulls) + len(branches)
    carriers = {
        "open_issues": issues,
        "open_pull_requests": pulls,
        "work_branches": branches,
    }

    if carrier_count:
        return {
            "schema": SCHEMA,
            "state": continuation_state,
            "hold_admissible": False,
            "first_blocker": first_blocker,
            "next_action": next_action or "USE_ACTIVE_REPOSITORY_CARRIER",
            "carrier_count": carrier_count,
            "carriers": carriers,
        }

    return {
        "schema": SCHEMA,
        "state": "HOLD",
        "hold_admissible": True,
        "first_blocker": first_blocker,
        "next_action": None,
        "carrier_count": 0,
        "carriers": carriers,
    }


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--issue-carrier", action="append", default=[])
    parser.add_argument("--pull-request-carrier", action="append", default=[])
    parser.add_argument("--branch-carrier", action="append", default=[])
    parser.add_argument(
        "--continuation-state",
        default="CONTINUE",
        choices=sorted(CONTINUATION_STATES),
    )
    parser.add_argument("--first-blocker")
    parser.add_argument("--next-action")
    parser.add_argument("--receipt", type=pathlib.Path)
    args = parser.parse_args(argv)

    try:
        result = classify(
            issue_carriers=args.issue_carrier,
            pull_request_carriers=args.pull_request_carrier,
            branch_carriers=args.branch_carrier,
            continuation_state=args.continuation_state,
            first_blocker=args.first_blocker,
            next_action=args.next_action,
        )
    except CarrierBindingError as exc:
        parser.error(str(exc))

    raw = canonical_bytes(result)
    if args.receipt is not None:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_bytes(raw)
    sys.stdout.buffer.write(raw)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
