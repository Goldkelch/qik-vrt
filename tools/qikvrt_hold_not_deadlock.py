#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Deterministic HOLD != DEADLOCK queue classifier.

This module never mutates GitHub. It classifies one bounded snapshot of
requested-review workflow runs and returns at most one stale, unbound queue
entry that may be cancelled by an event-driven caller.
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from typing import Any

ACTIVE = {"queued", "pending", "waiting", "requested"}
GENERIC_TITLE_TOKENS = ("pr=event", "head=event", "fp=event")


class LivenessSnapshotError(ValueError):
    pass


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise LivenessSnapshotError(f"{label} must be a positive integer")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LivenessSnapshotError(f"{label} must be non-empty text")
    return value.strip()


def is_exact_bound(run: Mapping[str, Any]) -> bool:
    title = _text(run.get("display_title") or run.get("name"), "run title")
    if any(token not in title for token in GENERIC_TITLE_TOKENS):
        return True
    prs = run.get("pull_requests", [])
    if not isinstance(prs, list):
        raise LivenessSnapshotError("pull_requests must be a list")
    return bool(prs)


def classify_queue(runs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(runs, Sequence) or isinstance(runs, (str, bytes)):
        raise LivenessSnapshotError("runs must be a sequence")
    stale: list[dict[str, Any]] = []
    protected: list[int] = []
    for raw in runs:
        if not isinstance(raw, Mapping):
            raise LivenessSnapshotError("run must be an object")
        run_id = _positive_int(raw.get("id"), "run id")
        status = _text(raw.get("status"), "run status")
        if status not in ACTIVE:
            continue
        if is_exact_bound(raw):
            protected.append(run_id)
            continue
        stale.append({
            "id": run_id,
            "run_number": raw.get("run_number"),
            "status": status,
            "display_title": raw.get("display_title") or raw.get("name"),
        })
    stale.sort(key=lambda item: (item["run_number"] if isinstance(item["run_number"], int) else -1, item["id"]))
    return {
        "schema": "qikvrt_hold_not_deadlock_queue_v1",
        "state": "CANCEL_ONE_STALE_GENERIC" if stale else "NOOP",
        "cancel_run_id": stale[0]["id"] if stale else None,
        "stale_generic_count": len(stale),
        "protected_exact_run_ids": sorted(protected),
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "MERGE": False,
            "PUBLICATION": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot")
    args = parser.parse_args()
    with open(args.snapshot, encoding="utf-8") as handle:
        payload = json.load(handle)
    runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
    result = classify_queue(runs)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
