#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic fail-closed disposition classifier for unattended pull requests.

This module is intentionally effect-free. It projects one exact-bound pull-request
observation to exactly one current disposition from the canonical Issue #929
state set. Repository workflows may consume the result, but review, merge, close,
publication and other effects remain separate authority-bearing operations.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

DISPOSITIONS = frozenset(
    {
        "ACTIVE_EXECUTION",
        "READY_FOR_INDEPENDENT_REVIEW",
        "HOLD_WITH_FIRST_CAUSAL_BLOCKER",
        "REBIND_REQUIRED",
        "MERGE_READY",
        "EXTERNAL_EFFECT_PENDING",
        "CLOSE_AS_SUPERSEDED",
        "MERGED",
        "CLOSED_NOT_PLANNED_WITH_CAUSE",
    }
)


@dataclass(frozen=True)
class Disposition:
    disposition: str
    first_causal_blocker: str | None
    next_action: str

    def to_mapping(self) -> dict[str, object]:
        value: dict[str, object] = asdict(self)
        value["PASS"] = False
        value["FINAL_PASS"] = False
        value["EFFECT_ACK_DONE"] = False
        return value


def _required_str(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _required_bool(value: object, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean")
    return value


def _required_nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def classify(observation: Mapping[str, object]) -> Disposition:
    """Return exactly one disposition for one exact-bound PR observation.

    Precedence is causal and fail-closed: terminal repository state first; then
    supersession and base drift; then active execution; then observed blockers;
    then independent-review and external-effect boundaries; finally merge-ready.
    Missing evidence cannot become MERGE_READY.
    """

    repository = _required_str(observation.get("repository"), "repository")
    del repository  # validation is the binding; no repository-specific behavior.
    _required_nonnegative_int(observation.get("pull_request"), "pull_request")
    head_sha = _required_str(observation.get("head_sha"), "head_sha")
    base_sha = _required_str(observation.get("base_sha"), "base_sha")
    current_main_sha = _required_str(
        observation.get("current_main_sha"), "current_main_sha"
    )
    if not all(len(value) == 40 for value in (head_sha, base_sha, current_main_sha)):
        raise ValueError("head_sha, base_sha and current_main_sha must be 40 characters")

    state = _required_str(observation.get("state"), "state")
    merged = _required_bool(observation.get("merged"), "merged")
    superseded = _required_bool(observation.get("superseded"), "superseded")
    active_workflows = _required_nonnegative_int(
        observation.get("active_workflows"), "active_workflows"
    )
    failed_workflows = _required_nonnegative_int(
        observation.get("failed_workflows"), "failed_workflows"
    )
    gates_complete = _required_bool(observation.get("gates_complete"), "gates_complete")
    review_required = _required_bool(
        observation.get("review_required"), "review_required"
    )
    review_satisfied = _required_bool(
        observation.get("review_satisfied"), "review_satisfied"
    )
    external_effect_pending = _required_bool(
        observation.get("external_effect_pending"), "external_effect_pending"
    )

    raw_blocker = observation.get("first_causal_blocker")
    if raw_blocker is not None and (
        not isinstance(raw_blocker, str) or not raw_blocker.strip()
    ):
        raise ValueError("first_causal_blocker must be null or a non-empty string")
    blocker = raw_blocker.strip() if isinstance(raw_blocker, str) else None

    if merged:
        if state != "closed":
            raise ValueError("merged pull request must be closed")
        return Disposition("MERGED", None, "NOOP")
    if state == "closed":
        return Disposition(
            "CLOSED_NOT_PLANNED_WITH_CAUSE",
            blocker or "CLOSED_WITHOUT_MERGE",
            "NOOP",
        )
    if state != "open":
        raise ValueError("state must be open or closed")
    if superseded:
        return Disposition("CLOSE_AS_SUPERSEDED", blocker or "SUPERSEDED", "CLOSE_PR")
    if base_sha != current_main_sha:
        return Disposition(
            "REBIND_REQUIRED",
            "BASE_DRIFT",
            "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN",
        )
    if active_workflows:
        return Disposition("ACTIVE_EXECUTION", None, "REOBSERVE_ON_TERMINAL_DELTA")
    if blocker is not None:
        return Disposition("HOLD_WITH_FIRST_CAUSAL_BLOCKER", blocker, "PRESERVE_HOLD")
    if failed_workflows:
        return Disposition(
            "HOLD_WITH_FIRST_CAUSAL_BLOCKER",
            "EXACT_HEAD_GATE_FAILURE",
            "CLASSIFY_FIRST_FAILED_GATE",
        )
    if not gates_complete:
        return Disposition(
            "HOLD_WITH_FIRST_CAUSAL_BLOCKER",
            "EXACT_HEAD_EVIDENCE_INCOMPLETE",
            "REOBSERVE_EXACT_HEAD_GATES",
        )
    if review_required and not review_satisfied:
        return Disposition(
            "READY_FOR_INDEPENDENT_REVIEW",
            None,
            "REQUEST_OR_REOBSERVE_INDEPENDENT_REVIEW",
        )
    if external_effect_pending:
        return Disposition(
            "EXTERNAL_EFFECT_PENDING",
            None,
            "PRESERVE_EXTERNAL_EFFECT_BOUNDARY",
        )
    return Disposition("MERGE_READY", None, "REQUEST_AUTHORIZED_PROMOTION")


def _read(path: str) -> Mapping[str, object]:
    stream = sys.stdin if path == "-" else Path(path).open(encoding="utf-8")
    try:
        value: Any = json.load(stream)
    finally:
        if stream is not sys.stdin:
            stream.close()
    if not isinstance(value, Mapping):
        raise ValueError("input must be a JSON object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="-")
    args = parser.parse_args(argv)
    try:
        value = classify(_read(args.input)).to_mapping()
        text = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
        if args.output == "-":
            sys.stdout.write(text)
        else:
            Path(args.output).write_text(text, encoding="utf-8")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
