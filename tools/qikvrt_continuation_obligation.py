#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ACTIVE_STATUSES = frozenset({"queued", "in_progress", "requested", "waiting", "pending"})
ADVERSE_CONCLUSIONS = frozenset(
    {"failure", "cancelled", "timed_out", "startup_failure", "action_required"}
)
OBSERVER_WORKFLOW_NAMES = frozenset(
    {
        "QIKVRT continuation obligation watch",
        "QIKVRT live status watch",
        "QIKVRT reflexive repository watchdog",
        "QIKVRT workflow executor watchdog",
    }
)


@dataclass(frozen=True)
class Decision:
    d0: int
    state: str
    reason: str
    productive_effect: bool = False
    effect_ack: str = "NOT_REQUIRED"
    follow_up_required: bool = True
    causal_run_id: int | None = None
    causal_workflow: str | None = None
    causal_status: str | None = None
    causal_conclusion: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _run_key(run: dict[str, Any]) -> tuple[str, str]:
    workflow_id = run.get("workflow_id")
    if workflow_id is not None:
        return ("id", str(workflow_id))
    return ("name", str(run.get("name") or ""))


def _order_key(run: dict[str, Any]) -> tuple[str, int, int]:
    created = str(run.get("created_at") or run.get("updated_at") or "")
    try:
        attempt = int(run.get("run_attempt") or 0)
    except (TypeError, ValueError):
        attempt = 0
    try:
        run_id = int(run.get("id") or 0)
    except (TypeError, ValueError):
        run_id = 0
    return (created, attempt, run_id)


def latest_productive_runs(runs: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for run in runs:
        name = str(run.get("name") or "")
        if name in OBSERVER_WORKFLOW_NAMES:
            continue
        key = _run_key(run)
        previous = latest.get(key)
        if previous is None or _order_key(run) > _order_key(previous):
            latest[key] = run
    return sorted(latest.values(), key=_order_key)


def _causal(decision: Decision, run: dict[str, Any] | None) -> Decision:
    if run is None:
        return decision
    try:
        run_id = int(run.get("id")) if run.get("id") is not None else None
    except (TypeError, ValueError):
        run_id = None
    data = decision.to_dict()
    data.update(
        causal_run_id=run_id,
        causal_workflow=str(run.get("name") or "") or None,
        causal_status=str(run.get("status") or "") or None,
        causal_conclusion=str(run.get("conclusion") or "") or None,
    )
    return Decision(**data)


def classify_observations(
    subject: dict[str, Any], runs: Iterable[dict[str, Any]]
) -> Decision:
    if not bool(subject.get("open", True)):
        return Decision(
            d0=0,
            state="NOOP",
            reason="SUBJECT_CLOSED",
            follow_up_required=False,
        )
    if bool(subject.get("effect_ack_done", False)):
        return Decision(
            d0=0,
            state="NOOP",
            reason="EFFECT_ACK_DONE",
            follow_up_required=False,
        )

    latest = latest_productive_runs(runs)

    active = [
        run
        for run in latest
        if str(run.get("status") or "").lower() in ACTIVE_STATUSES
        or (
            not run.get("conclusion")
            and str(run.get("status") or "").lower() != "completed"
        )
    ]
    if active:
        return _causal(
            Decision(d0=1, state="HOLD", reason="ACTIVE_EXACT_HEAD_TRANSITION"),
            max(active, key=_order_key),
        )

    terminal_without_conclusion = [
        run
        for run in latest
        if str(run.get("status") or "").lower() == "completed"
        and not run.get("conclusion")
    ]
    if terminal_without_conclusion:
        return _causal(
            Decision(
                d0=2,
                state="REOBSERVE",
                reason="TERMINAL_RUN_WITHOUT_CONCLUSION",
            ),
            max(terminal_without_conclusion, key=_order_key),
        )

    adverse = [
        run
        for run in latest
        if str(run.get("conclusion") or "").lower() in ADVERSE_CONCLUSIONS
    ]
    if adverse:
        return _causal(
            Decision(
                d0=2,
                state="REOBSERVE",
                reason="TERMINAL_ADVERSE_RUN_WITHOUT_SUCCESSOR",
            ),
            max(adverse, key=_order_key),
        )

    if not latest:
        return Decision(
            d0=2,
            state="REOBSERVE",
            reason="NO_EXACT_HEAD_EXECUTION_EVIDENCE",
        )

    if bool(subject.get("draft", False)):
        return _causal(
            Decision(
                d0=2,
                state="REOBSERVE",
                reason="OPEN_DRAFT_QUIESCENT_AFTER_TERMINAL_RUNS",
            ),
            max(latest, key=_order_key),
        )

    requested = subject.get("requested_reviewers") or []
    if requested:
        return _causal(
            Decision(
                d0=3,
                state="REQUEST_AUTHORITY",
                reason="REQUESTED_REVIEW_PENDING_AFTER_TERMINAL_RUNS",
            ),
            max(latest, key=_order_key),
        )

    return _causal(
        Decision(
            d0=3,
            state="REQUEST_AUTHORITY",
            reason="OPEN_NONTERMINAL_SUBJECT_WITHOUT_ACTIVE_SUCCESSOR",
        ),
        max(latest, key=_order_key),
    )


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    classify = sub.add_parser("classify")
    classify.add_argument("--input", required=True)
    classify.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    decision = classify_observations(payload["subject"], payload.get("runs", []))
    output = json.dumps(decision.to_dict(), sort_keys=True, indent=2) + "\n"
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output, encoding="utf-8")
    if path.read_text(encoding="utf-8") != output:
        raise SystemExit("continuation decision persistence readback mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
