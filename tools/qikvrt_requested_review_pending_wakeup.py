# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed classification for orphaned requested-review pending work units."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any, Iterable

_EXACT_TITLE = re.compile(
    r"^QIKVRT requested review pr=(?P<pr>[0-9]+) "
    r"head=(?P<head>[0-9a-f]{40}) fp=(?P<fingerprint>\S+)$"
)
_ACTIVE = {"in_progress", "queued", "requested", "waiting"}


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def classify_pending_wakeup(
    *,
    pending_runs: Iterable[dict[str, Any]],
    active_runs: Iterable[dict[str, Any]],
    pull_requests: dict[int, dict[str, Any]],
    now: datetime | None = None,
    grace_seconds: int = 120,
) -> dict[str, Any]:
    """Select at most one exact live orphan pending work unit.

    No effect is authorized unless there is no active executor transport and
    exactly one sufficiently old, explicitly bound workflow_dispatch pending
    run whose PR/head remains live on main.
    """
    now = now or datetime.now(timezone.utc)
    active = [r for r in active_runs if str(r.get("status")) in _ACTIVE]
    if active:
        return {
            "state": "HOLD",
            "first_blocker": "REQUESTED_REVIEW_WRITER_ACTIVE",
            "selected": False,
            "active_run_ids": sorted(int(r["id"]) for r in active if r.get("id")),
        }

    candidates: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for run in pending_runs:
        if run.get("status") != "pending" or run.get("event") != "workflow_dispatch":
            continue
        title = str(run.get("display_title") or run.get("name") or "")
        match = _EXACT_TITLE.fullmatch(title)
        if not match:
            observations.append({
                "run_id": run.get("id"),
                "state": "HOLD_UNVERIFIED",
                "first_blocker": "PENDING_WORK_UNIT_NOT_EXACTLY_BOUND",
            })
            continue
        pr_number = int(match.group("pr"))
        expected_head = match.group("head")
        pr = pull_requests.get(pr_number) or {}
        live_head = ((pr.get("head") or {}).get("sha") or "")
        live_base = ((pr.get("base") or {}).get("ref") or "")
        created_at = str(run.get("created_at") or "")
        if not created_at:
            observations.append({
                "run_id": run.get("id"),
                "state": "HOLD_UNVERIFIED",
                "first_blocker": "PENDING_WORK_UNIT_AGE_UNBOUND",
            })
            continue
        age_seconds = max(0, int((now - _parse_time(created_at)).total_seconds()))
        if pr.get("state") != "open" or live_base != "main" or live_head != expected_head:
            observations.append({
                "run_id": int(run["id"]),
                "pr_number": pr_number,
                "expected_head": expected_head,
                "live_head": live_head,
                "state": "STALE",
                "first_blocker": "EXACT_SUBJECT_DRIFT",
                "age_seconds": age_seconds,
            })
            continue
        if age_seconds < grace_seconds:
            observations.append({
                "run_id": int(run["id"]),
                "pr_number": pr_number,
                "head_sha": expected_head,
                "state": "HOLD",
                "first_blocker": "PENDING_GRACE_PERIOD_ACTIVE",
                "age_seconds": age_seconds,
            })
            continue
        candidates.append({
            "run_id": int(run["id"]),
            "pr_number": pr_number,
            "head_sha": expected_head,
            "fingerprint": match.group("fingerprint"),
            "created_at": created_at,
            "age_seconds": age_seconds,
        })

    if not candidates:
        return {
            "state": "NOOP",
            "first_blocker": None,
            "selected": False,
            "observations": observations,
        }
    candidates.sort(key=lambda item: (item["created_at"], item["run_id"]))
    selected = candidates[0]
    return {
        "state": "WAKEUP_REQUIRED",
        "first_blocker": "SINGLE_PENDING_SLOT_WITHOUT_ACTIVE_WRITER",
        "selected": True,
        **selected,
        "candidate_count": len(candidates),
        "observations": observations,
    }
