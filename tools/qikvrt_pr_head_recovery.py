#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pure, fail-closed classification for stalled pull-request heads.

The classifier deliberately has no GitHub client and performs no effect.  It turns
already collected run observations into the existing four-state D0 decision.  The
workflow remains responsible for exact-head reobservation and any bounded dispatch.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_ALLOWED_EXACT_HEAD_STATUSES = frozenset(
    {"missing", "pending", "success", "failure", "error"}
)
_ADVERSE_CONCLUSIONS = frozenset(
    {"action_required", "cancelled", "failure", "startup_failure", "timed_out"}
)


@dataclass(frozen=True)
class RecoveryDecision:
    """One bounded D0 result for an exact pull-request head."""

    d0: int
    state: str
    reason: str
    active_workflows: int
    executed_failures: int
    zero_job_action_required: int

    def to_mapping(self) -> dict[str, object]:
        value: dict[str, object] = asdict(self)
        value["productive_effect"] = False
        value["effect_ack"] = "NOT_REQUIRED"
        return value


@dataclass(frozen=True)
class _Observation:
    run_id: int
    name: str
    status: str
    conclusion: str | None
    jobs_total: int
    created_at: datetime


def _require_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _parse_created_at(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("created_at must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("created_at must include a timezone")
    return parsed


def _normalize(raw: Mapping[str, object]) -> _Observation:
    run_id = _require_integer(raw.get("id"), "id")
    if run_id < 0:
        raise ValueError("id must be non-negative")

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")

    status = raw.get("status")
    if not isinstance(status, str) or not status:
        raise ValueError("status must be a non-empty string")

    conclusion = raw.get("conclusion")
    if conclusion is not None and not isinstance(conclusion, str):
        raise ValueError("conclusion must be a string or null")

    jobs_total = _require_integer(raw.get("jobs_total"), "jobs_total")
    if jobs_total < 0:
        raise ValueError("jobs_total must be non-negative")

    return _Observation(
        run_id=run_id,
        name=name.strip(),
        status=status,
        conclusion=conclusion,
        jobs_total=jobs_total,
        created_at=_parse_created_at(raw.get("created_at")),
    )


def _latest_by_workflow(
    observations: Iterable[Mapping[str, object]],
) -> tuple[_Observation, ...]:
    """Return only the latest run per workflow using timestamp and run_id."""

    latest: dict[str, _Observation] = {}
    for raw in observations:
        if not isinstance(raw, Mapping):
            raise ValueError("each observation must be an object")
        current = _normalize(raw)
        previous = latest.get(current.name)
        if previous is None or (current.created_at, current.run_id) > (
            previous.created_at,
            previous.run_id,
        ):
            latest[current.name] = current
    return tuple(latest[name] for name in sorted(latest))


def classify_observations(
    observations: Iterable[Mapping[str, object]],
    *,
    exact_head_status: str | None = None,
) -> RecoveryDecision:
    """Classify one exact head without fabricating productive authority.

    Precedence is fail-closed: active work and executed failures HOLD; a trusted
    exact-head status makes dispatch idempotent; only the characteristic latest
    zero-job ``action_required`` state selects REOBSERVE.
    """

    normalized_status = "missing" if exact_head_status is None else exact_head_status
    if normalized_status not in _ALLOWED_EXACT_HEAD_STATUSES:
        raise ValueError(
            "exact_head_status must be one of missing, pending, success, failure, error"
        )

    latest = _latest_by_workflow(observations)
    active_workflows = sum(item.status != "completed" for item in latest)
    executed_failures = sum(
        item.status == "completed"
        and item.conclusion in _ADVERSE_CONCLUSIONS
        and item.jobs_total > 0
        for item in latest
    )
    zero_job_action_required = sum(
        item.status == "completed"
        and item.conclusion == "action_required"
        and item.jobs_total == 0
        for item in latest
    )

    def decision(d0: int, state: str, reason: str) -> RecoveryDecision:
        return RecoveryDecision(
            d0=d0,
            state=state,
            reason=reason,
            active_workflows=active_workflows,
            executed_failures=executed_failures,
            zero_job_action_required=zero_job_action_required,
        )

    if active_workflows:
        return decision(1, "HOLD", "ACTIVE_WORKFLOW")
    if normalized_status == "pending":
        return decision(1, "HOLD", "TRUSTED_EXACT_HEAD_VERIFICATION_PENDING")
    if normalized_status in {"failure", "error"}:
        return decision(1, "HOLD", "TRUSTED_EXACT_HEAD_VERIFICATION_FAILED")
    if normalized_status == "success":
        return decision(0, "NOOP", "TRUSTED_EXACT_HEAD_VERIFIED")
    if executed_failures:
        return decision(1, "HOLD", "EXECUTED_FAILURE_PRESENT")
    if zero_job_action_required:
        return decision(2, "REOBSERVE", "ZERO_JOB_ACTION_REQUIRED")
    return decision(0, "NOOP", "CONSISTENT_OR_ALREADY_TERMINAL")


def _read_payload(path: str) -> Sequence[Mapping[str, object]]:
    stream = sys.stdin if path == "-" else Path(path).open(encoding="utf-8")
    try:
        value: Any = json.load(stream)
    finally:
        if stream is not sys.stdin:
            stream.close()
    if isinstance(value, dict):
        value = value.get("observations")
    if not isinstance(value, list):
        raise ValueError("input must be a JSON array or an object with observations")
    return value


def _write_payload(path: str, value: Mapping[str, object]) -> None:
    text = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    if path == "-":
        sys.stdout.write(text)
        return
    Path(path).write_text(text, encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    classify = commands.add_parser("classify", help="classify collected run observations")
    classify.add_argument("--input", required=True, help="JSON input path or -")
    classify.add_argument("--output", default="-", help="JSON output path or -")
    classify.add_argument(
        "--exact-head-status",
        default="missing",
        choices=sorted(_ALLOWED_EXACT_HEAD_STATUSES),
        help="latest target-commit status for trusted exact-head verification",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command != "classify":
            raise ValueError(f"unsupported command: {args.command}")
        result = classify_observations(
            _read_payload(args.input),
            exact_head_status=args.exact_head_status,
        )
        _write_payload(args.output, result.to_mapping())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
