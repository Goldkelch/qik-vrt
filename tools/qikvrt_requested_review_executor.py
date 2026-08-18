#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed decision core for requested-review execution.

The module is deliberately GitHub-write-free. A workflow supplies one live,
exact-head-bound snapshot; this core returns WAIT, APPROVE, REQUEST_CHANGES,
or COMMENT_WITH_BLOCKER. The workflow persists the disposition and an
exact-head commit status without impersonating a requested GitHub identity.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any

SUCCESS = {"success"}
NON_ADVERSE = {"success", "skipped"}
SELF_WORKFLOW = "QIKVRT requested review executor"


class ReviewSnapshotError(ValueError):
    pass


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise ReviewSnapshotError(f"{label} is not a Git SHA-1")
    if any(ch not in "0123456789abcdef" for ch in value):
        raise ReviewSnapshotError(f"{label} is not lowercase hexadecimal")
    return value


def _run_number(run: Mapping[str, Any]) -> int:
    value = run.get("run_number", -1)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReviewSnapshotError("workflow run_number must be an integer")
    return value


def collapse_latest(runs: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    latest: dict[str, Mapping[str, Any]] = {}
    for run in runs:
        name = run.get("name")
        if not isinstance(name, str) or not name:
            raise ReviewSnapshotError("workflow run name is missing")
        if name == SELF_WORKFLOW:
            continue
        current = latest.get(name)
        if current is None or _run_number(run) > _run_number(current):
            latest[name] = run
    return latest


def _result(snapshot: Mapping[str, Any], state: str, blocker: str | None, detail: str) -> dict[str, Any]:
    return {
        "schema": "qikvrt_requested_review_decision_v1",
        "state": state,
        "first_blocker": blocker,
        "detail": detail,
        "repository": snapshot.get("repository"),
        "pr_number": snapshot.get("pr_number"),
        "base_ref": snapshot.get("base_ref"),
        "base_sha": snapshot.get("base_sha"),
        "head_sha": snapshot.get("head_sha"),
        "tree_sha": snapshot.get("tree_sha"),
        "reviewed_scope": snapshot.get("changed_paths", []),
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "INDEPENDENT_CODE_OWNER_APPROVAL": False,
        },
    }


def evaluate(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise ReviewSnapshotError("snapshot must be an object")

    current_base_value = snapshot.get("current_base_sha", snapshot.get("current_main_sha"))
    current_base = _sha(current_base_value, "current_base_sha")
    base = _sha(snapshot.get("base_sha"), "base_sha")
    head = _sha(snapshot.get("head_sha"), "head_sha")
    observed_head = _sha(snapshot.get("observed_head_sha"), "observed_head_sha")
    _sha(snapshot.get("tree_sha"), "tree_sha")

    if base != current_base:
        base_ref = snapshot.get("base_ref") or "<unknown>"
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "BASE_DRIFT", f"base {base} != current {base_ref} {current_base}")
    if observed_head != head:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "HEAD_DRIFT", f"observed head {observed_head} != bound head {head}")
    if snapshot.get("draft") is True:
        return _result(snapshot, "WAIT", "DRAFT", "requested candidate is still draft")

    requested = snapshot.get("requested_reviewers", [])
    requested_teams = snapshot.get("requested_team_reviewers", [])
    if not isinstance(requested, list) or not isinstance(requested_teams, list):
        raise ReviewSnapshotError("requested reviewer collections must be lists")
    if not requested and not requested_teams:
        return _result(snapshot, "WAIT", "NO_ACTIVE_REVIEW_REQUEST", "no requested reviewer remains")

    changed_paths = snapshot.get("changed_paths")
    if not isinstance(changed_paths, list) or not all(isinstance(path, str) and path for path in changed_paths):
        raise ReviewSnapshotError("changed_paths must be a list of non-empty strings")
    if not changed_paths:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "EMPTY_SCOPE", "requested review has no changed paths")

    unresolved = snapshot.get("unresolved_review_threads", 0)
    if isinstance(unresolved, bool) or not isinstance(unresolved, int) or unresolved < 0:
        raise ReviewSnapshotError("unresolved_review_threads must be a non-negative integer")
    if unresolved:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "UNRESOLVED_REVIEW_THREADS", f"{unresolved} unresolved review thread(s)")

    required = snapshot.get("required_gates")
    runs = snapshot.get("workflow_runs")
    if not isinstance(required, list) or not required or not all(isinstance(name, str) and name for name in required):
        raise ReviewSnapshotError("required_gates must be a non-empty list")
    if not isinstance(runs, list):
        raise ReviewSnapshotError("workflow_runs must be a list")
    latest = collapse_latest(runs)

    for gate in required:
        run = latest.get(gate)
        if run is None:
            return _result(snapshot, "WAIT", "REQUIRED_GATE_MISSING", f"required exact-head gate is absent: {gate}")
        if run.get("status") != "completed":
            return _result(snapshot, "WAIT", "REQUIRED_GATE_NOT_TERMINAL", f"required exact-head gate is not terminal: {gate}")
        if run.get("conclusion") not in SUCCESS:
            return _result(snapshot, "REQUEST_CHANGES", "REQUIRED_GATE_FAILED", f"required exact-head gate failed: {gate}={run.get('conclusion')}")

    for name, run in sorted(latest.items()):
        if name in required:
            continue
        if run.get("status") != "completed":
            return _result(snapshot, "WAIT", "APPLICABLE_GATE_NOT_TERMINAL", f"applicable exact-head gate is not terminal: {name}")
        if run.get("conclusion") not in NON_ADVERSE:
            return _result(snapshot, "REQUEST_CHANGES", "APPLICABLE_GATE_FAILED", f"applicable exact-head gate is adverse: {name}={run.get('conclusion')}")

    return _result(snapshot, "APPROVE", None, "exact-head scope inspected; all observed applicable gates are terminal non-adverse and no unresolved review thread remains")


def _load(path: str) -> Mapping[str, Any]:
    value = json.load(sys.stdin) if path == "-" else json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ReviewSnapshotError("snapshot JSON must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate",))
    parser.add_argument("--input", default="-")
    args = parser.parse_args(argv)
    try:
        result = evaluate(_load(args.input))
    except (OSError, ValueError, json.JSONDecodeError, ReviewSnapshotError) as exc:
        result = {
            "schema": "qikvrt_requested_review_decision_v1",
            "state": "COMMENT_WITH_BLOCKER",
            "first_blocker": "INVALID_REVIEW_SNAPSHOT",
            "detail": str(exc),
            "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False},
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") in {"WAIT", "APPROVE"} else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
