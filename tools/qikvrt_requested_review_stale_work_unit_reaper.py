# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed classifier for stale recursive requested-review workflow runs.

Only workflow_dispatch children emitted by the requested-review executor are
eligible for cancellation. Native pull_request_target observations are never
cancelled here: they remain responsible for observing and projecting BASE_DRIFT.
"""
from __future__ import annotations

import re
from typing import Any

_TITLE = re.compile(
    r"^QIKVRT requested review pr=(?P<pr>[1-9][0-9]*) "
    r"head=(?P<head>[0-9a-f]{40}) fp=(?P<fingerprint>[0-9a-f]{64})$"
)
_ACTIVE = {"pending", "queued", "requested", "waiting"}


def classify_run(run: dict[str, Any], pr: dict[str, Any], current_main_sha: str) -> dict[str, Any]:
    """Return a deterministic cancellation disposition for one queued child."""
    result: dict[str, Any] = {
        "state": "KEEP",
        "cancel": False,
        "first_blocker": None,
        "next_action": "NOOP",
    }
    if run.get("event") != "workflow_dispatch" or run.get("status") not in _ACTIVE:
        return result

    match = _TITLE.fullmatch(str(run.get("display_title") or ""))
    if match is None:
        return {
            **result,
            "state": "HOLD_UNVERIFIED",
            "first_blocker": "RECURSIVE_WORK_UNIT_TITLE_UNBOUND",
            "next_action": "PRESERVE_FAIL_CLOSED_WITHOUT_CANCELLATION",
        }

    queued_pr = int(match.group("pr"))
    queued_head = match.group("head")
    live_number = pr.get("number")
    live_state = pr.get("state")
    live_head = (pr.get("head") or {}).get("sha")
    live_base = (pr.get("base") or {}).get("sha")

    if live_number != queued_pr:
        return {
            **result,
            "state": "HOLD_UNVERIFIED",
            "first_blocker": "RECURSIVE_WORK_UNIT_PR_IDENTITY_MISMATCH",
            "next_action": "PRESERVE_FAIL_CLOSED_WITHOUT_CANCELLATION",
        }
    if live_state != "open" or live_head != queued_head:
        return {
            **result,
            "state": "STALE_WORK_UNIT",
            "cancel": True,
            "first_blocker": "STALE_HEAD",
            "next_action": "CANCEL_STALE_RECURSIVE_TRANSPORT_ONLY",
        }
    if live_base != current_main_sha:
        return {
            **result,
            "state": "STALE_WORK_UNIT",
            "cancel": True,
            "first_blocker": "BASE_DRIFT",
            "next_action": "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN",
        }
    return result
