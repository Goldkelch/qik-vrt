#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pure planner for bounded repository-native deterministic repair.

The planner performs no network or repository mutation.  It converts exact-head
observations and ancestry facts into one fail-closed action.  The workflow is
responsible for exact-ref reobservation, scope guards, tests, and any bounded
effect.
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
_INTEGRITY_FAILURE = "REPOSITORY_INTEGRITY_PROJECTION_DRIFT"


@dataclass(frozen=True)
class RepairPlan:
    d0: int
    state: str
    reason: str
    action: str
    productive_effect: bool
    requires_exact_head_revalidation: bool
    active_workflows: int
    executed_failures: int
    zero_job_action_required: int
    behind_by: int

    def to_mapping(self) -> dict[str, object]:
        value = asdict(self)
        value["effect_ack"] = "NOT_REQUIRED"
        value["independent_review_authority"] = False
        value["merge_authority"] = False
        value["external_effect"] = "NONE"
        return value


@dataclass(frozen=True)
class Observation:
    run_id: int
    name: str
    status: str
    conclusion: str | None
    jobs_total: int
    created_at: datetime


def _integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("created_at must be a non-empty ISO-8601 string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be a valid ISO-8601 timestamp") from exc
    if result.tzinfo is None:
        raise ValueError("created_at must include a timezone")
    return result


def _observation(raw: Mapping[str, object]) -> Observation:
    name = raw.get("name")
    status = raw.get("status")
    conclusion = raw.get("conclusion")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")
    if not isinstance(status, str) or not status:
        raise ValueError("status must be a non-empty string")
    if conclusion is not None and not isinstance(conclusion, str):
        raise ValueError("conclusion must be a string or null")
    return Observation(
        run_id=_integer(raw.get("id"), "id"),
        name=name.strip(),
        status=status,
        conclusion=conclusion,
        jobs_total=_integer(raw.get("jobs_total"), "jobs_total"),
        created_at=_timestamp(raw.get("created_at")),
    )


def latest_by_workflow(
    observations: Iterable[Mapping[str, object]],
) -> tuple[Observation, ...]:
    latest: dict[str, Observation] = {}
    for raw in observations:
        if not isinstance(raw, Mapping):
            raise ValueError("each observation must be an object")
        item = _observation(raw)
        prior = latest.get(item.name)
        if prior is None or (item.created_at, item.run_id) > (
            prior.created_at,
            prior.run_id,
        ):
            latest[item.name] = item
    return tuple(latest[name] for name in sorted(latest))


def plan_repair(
    observations: Iterable[Mapping[str, object]],
    *,
    exact_head_status: str = "missing",
    dispatch_error_is_recoverable: bool = False,
    behind_by: int = 0,
    mergeable: bool | None = None,
    first_failure_class: str | None = None,
) -> RepairPlan:
    """Return one bounded action with fail-closed precedence.

    D0 values retain the repository ABI:
      0 NOOP
      1 HOLD
      2 REOBSERVE
      3 REQUEST_AUTHORITY

    Productive repository mutation is represented by ``state=REPAIR`` while
    preserving D0=2: the workflow may reobserve and create a history-preserving
    successor, but it never merges main or manufactures review authority.
    """

    if exact_head_status not in _ALLOWED_EXACT_HEAD_STATUSES:
        raise ValueError("invalid exact_head_status")
    if behind_by < 0:
        raise ValueError("behind_by must be non-negative")
    if mergeable is not None and not isinstance(mergeable, bool):
        raise ValueError("mergeable must be true, false, or null")
    if first_failure_class is not None and not isinstance(first_failure_class, str):
        raise ValueError("first_failure_class must be a string or null")

    latest = latest_by_workflow(observations)
    active = sum(item.status != "completed" for item in latest)
    executed_failures = sum(
        item.status == "completed"
        and item.conclusion in _ADVERSE_CONCLUSIONS
        and item.jobs_total > 0
        for item in latest
    )
    zero_job = sum(
        item.status == "completed"
        and item.conclusion == "action_required"
        and item.jobs_total == 0
        for item in latest
    )

    def make(
        d0: int,
        state: str,
        reason: str,
        action: str,
        *,
        productive: bool = False,
        revalidate: bool = False,
    ) -> RepairPlan:
        return RepairPlan(
            d0=d0,
            state=state,
            reason=reason,
            action=action,
            productive_effect=productive,
            requires_exact_head_revalidation=revalidate,
            active_workflows=active,
            executed_failures=executed_failures,
            zero_job_action_required=zero_job,
            behind_by=behind_by,
        )

    if active:
        return make(1, "HOLD", "ACTIVE_WORKFLOW", "NONE")
    if exact_head_status == "pending":
        return make(
            1,
            "HOLD",
            "TRUSTED_EXACT_HEAD_VERIFICATION_PENDING",
            "NONE",
        )
    if exact_head_status == "success":
        return make(0, "NOOP", "TRUSTED_EXACT_HEAD_VERIFIED", "NONE")
    if exact_head_status in {"failure", "error"} and not dispatch_error_is_recoverable:
        return make(
            1,
            "HOLD",
            "EXECUTED_OR_UNCLASSIFIED_EXACT_HEAD_FAILURE",
            "NONE",
        )

    if behind_by:
        if mergeable is True:
            return make(
                2,
                "REPAIR",
                "STALE_BASE_CONFLICT_FREE",
                "REBIND_CURRENT_MAIN",
                productive=True,
                revalidate=True,
            )
        return make(
            3,
            "REQUEST_AUTHORITY",
            "STALE_BASE_NOT_SAFELY_REBINDABLE",
            "NONE",
        )

    if first_failure_class == _INTEGRITY_FAILURE:
        return make(
            2,
            "REPAIR",
            _INTEGRITY_FAILURE,
            "DISPATCH_INTEGRITY_MATERIALIZER",
            revalidate=True,
        )

    if dispatch_error_is_recoverable:
        return make(
            2,
            "REOBSERVE",
            "RECOVERABLE_DISPATCH_ERROR",
            "DISPATCH_EXACT_HEAD",
            revalidate=True,
        )

    if zero_job:
        return make(
            2,
            "REOBSERVE",
            "ZERO_JOB_ACTION_REQUIRED",
            "DISPATCH_EXACT_HEAD",
            revalidate=True,
        )

    if executed_failures:
        return make(
            1,
            "HOLD",
            "EXECUTED_FAILURE_REQUIRES_REPAIR_RECIPE",
            "NONE",
        )

    if not latest:
        return make(
            2,
            "REOBSERVE",
            "NO_EXACT_HEAD_OBSERVATION",
            "DISPATCH_EXACT_HEAD",
            revalidate=True,
        )

    return make(0, "NOOP", "CONSISTENT_OR_ALREADY_TERMINAL", "NONE")


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


def _write(path: str, value: Mapping[str, object]) -> None:
    text = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    if path == "-":
        sys.stdout.write(text)
    else:
        Path(path).write_text(text, encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="-")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payload = _read(args.input)
        observations = payload.get("observations", [])
        if not isinstance(observations, list):
            raise ValueError("observations must be a JSON array")
        plan = plan_repair(
            observations,
            exact_head_status=str(payload.get("exact_head_status", "missing")),
            dispatch_error_is_recoverable=bool(
                payload.get("dispatch_error_is_recoverable", False)
            ),
            behind_by=_integer(payload.get("behind_by", 0), "behind_by"),
            mergeable=payload.get("mergeable"),
            first_failure_class=payload.get("first_failure_class"),
        )
        _write(args.output, plan.to_mapping())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
