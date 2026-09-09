#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Select one replayable required-review run for the ruleset bridge.

The scheduled watchdog may inspect one complete, bounded 100-run observation
per workflow.  That observation is evidence only when its declared count is
complete and its required-review and bridge runs bind the current Main SHA,
repository and workflow path.  The selector returns the least-recently-carried
exact upstream run whose bridge is not active.  The bridge subsequently
rebinds the artifact, PR tuple, head, status and Main before any dispatch.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


REQUIRED_REVIEW_NAME = "QIKVRT required code-owner review"
REQUIRED_REVIEW_PATH = ".github/workflows/qikvrt_required_review_gate.yml"
BRIDGE_NAME = "QIKVRT ruleset effect dispatch bridge"
BRIDGE_PATH = ".github/workflows/qikvrt_ruleset_effect_dispatch_bridge.yml"
BRIDGE_TITLE = re.compile(
    r"^QIKVRT ruleset bridge upstream=(?P<upstream>[1-9][0-9]*) carrier=.+$"
)
ACTIVE_STATUSES = frozenset({"requested", "pending", "queued", "in_progress", "waiting"})
TERMINAL_CONCLUSIONS = frozenset(
    {
        "action_required",
        "cancelled",
        "failure",
        "neutral",
        "skipped",
        "stale",
        "success",
        "timed_out",
        "startup_failure",
    }
)
MAX_WORKFLOW_RUNS = 100
SHA1 = re.compile(r"^[0-9a-f]{40}$")
REPOSITORY = re.compile(r"^[^/\s]+/[^/\s]+$")
SCHEMA = "qikvrt_ruleset_bridge_scheduled_carrier_selection_v2"


class CarrierSelectionError(ValueError):
    """The paginated external observation cannot support a safe replay."""


def _int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CarrierSelectionError(f"{field} must be a positive integer")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CarrierSelectionError(f"{field} must be a non-empty string")
    return value


def _sha(value: Any, field: str) -> str:
    text = _text(value, field)
    if SHA1.fullmatch(text) is None:
        raise CarrierSelectionError(f"{field} must be a lowercase 40-character SHA-1")
    return text


def _repository(value: Any, field: str) -> str:
    if not isinstance(value, Mapping):
        raise CarrierSelectionError(f"{field} must be an object")
    name = _text(value.get("full_name"), f"{field}.full_name")
    if REPOSITORY.fullmatch(name) is None:
        raise CarrierSelectionError(f"{field}.full_name must be an owner/name repository")
    return name


def _workflow_path_matches(value: Any, expected_path: str, field: str) -> bool:
    """Accept the exact workflow path in event or REST `path@main` form."""

    path = _text(value, field)
    return path in {expected_path, f"{expected_path}@main"}


def _one_page(value: Any, field: str) -> list[Mapping[str, Any]]:
    """Validate one complete GitHub `per_page=100` workflow-runs response."""

    if isinstance(value, Mapping):
        page = value
    elif isinstance(value, list) and len(value) == 1 and isinstance(value[0], Mapping):
        page = value[0]
    else:
        raise CarrierSelectionError(f"{field} must contain exactly one object page")
    total_count = page.get("total_count")
    if isinstance(total_count, bool) or not isinstance(total_count, int):
        raise CarrierSelectionError(f"{field}.total_count must be an integer")
    if total_count < 0 or total_count > MAX_WORKFLOW_RUNS:
        raise CarrierSelectionError(
            f"{field}.total_count must be within 0..{MAX_WORKFLOW_RUNS}"
        )
    runs = page.get("workflow_runs")
    if not isinstance(runs, list):
        raise CarrierSelectionError(f"{field}.workflow_runs must be an array")
    if len(runs) != total_count:
        raise CarrierSelectionError(
            f"{field}.workflow_runs must contain its complete total_count"
        )
    if len(runs) > MAX_WORKFLOW_RUNS:
        raise CarrierSelectionError(f"{field}.workflow_runs exceeds {MAX_WORKFLOW_RUNS}")
    items: list[Mapping[str, Any]] = []
    seen_ids: set[int] = set()
    for run_index, run in enumerate(runs):
        if not isinstance(run, Mapping):
            raise CarrierSelectionError(f"{field}.workflow_runs[{run_index}] must be an object")
        run_id = _int(run.get("id"), f"{field}.workflow_runs[{run_index}].id")
        if run_id in seen_ids:
            raise CarrierSelectionError(f"{field}.workflow_runs contains duplicate run id {run_id}")
        seen_ids.add(run_id)
        items.append(run)
    return items


def _status_and_conclusion(run: Mapping[str, Any], field: str) -> tuple[str, str | None]:
    status = _text(run.get("status"), f"{field}.status")
    if status in ACTIVE_STATUSES:
        conclusion = run.get("conclusion")
        if conclusion is not None:
            raise CarrierSelectionError(
                f"{field}.conclusion must be null while status is active"
            )
        return status, None
    if status != "completed":
        raise CarrierSelectionError(f"{field}.status is unknown: {status!r}")
    conclusion = _text(run.get("conclusion"), f"{field}.conclusion")
    if conclusion not in TERMINAL_CONCLUSIONS:
        raise CarrierSelectionError(f"{field}.conclusion is unknown: {conclusion!r}")
    return status, conclusion


def _run_provenance(
    run: Mapping[str, Any],
    *,
    field: str,
    expected_name: str,
    expected_path: str,
    expected_repository: str,
    expected_main_sha: str,
) -> bool:
    """Validate run shape and return whether it is bound to the exact Main."""

    _int(run.get("id"), f"{field}.id")
    _text(run.get("updated_at") or run.get("created_at"), f"{field}.timestamp")
    name = _text(run.get("name"), f"{field}.name")
    path_matches = _workflow_path_matches(
        run.get("path"), expected_path, f"{field}.path"
    )
    repository = _repository(run.get("repository"), f"{field}.repository")
    branch = _text(run.get("head_branch"), f"{field}.head_branch")
    head_sha = _sha(run.get("head_sha"), f"{field}.head_sha")
    return (
        name == expected_name
        and path_matches
        and repository == expected_repository
        and branch == "main"
        and head_sha == expected_main_sha
    )


def _run_sort_key(run: Mapping[str, Any]) -> tuple[str, int]:
    return (str(run.get("updated_at") or run.get("created_at") or ""), _int(run.get("id"), "run.id"))


def select_carrier(
    required_pages: Any,
    bridge_pages: Any,
    *,
    expected_main_sha: str,
    expected_repository: str,
) -> dict[str, Any]:
    """Return the next non-active exact upstream run, or an explicit NOOP."""

    expected_main_sha = _sha(expected_main_sha, "expected_main_sha")
    if REPOSITORY.fullmatch(_text(expected_repository, "expected_repository")) is None:
        raise CarrierSelectionError("expected_repository must be an owner/name repository")
    required_runs = _one_page(required_pages, "required review runs")
    bridge_runs = _one_page(bridge_pages, "bridge runs")

    latest_bridge_by_upstream: dict[int, Mapping[str, Any]] = {}
    for index, run in enumerate(bridge_runs):
        field = f"bridge runs.workflow_runs[{index}]"
        title = _text(run.get("display_title"), f"{field}.display_title")
        match = BRIDGE_TITLE.fullmatch(title)
        if match is None:
            raise CarrierSelectionError(f"{field}.display_title is not an exact bridge title")
        upstream = int(match.group("upstream"))
        _status_and_conclusion(run, field)
        if not _run_provenance(
            run,
            field=field,
            expected_name=BRIDGE_NAME,
            expected_path=BRIDGE_PATH,
            expected_repository=expected_repository,
            expected_main_sha=expected_main_sha,
        ):
            continue
        previous = latest_bridge_by_upstream.get(upstream)
        if previous is None or _run_sort_key(run) > _run_sort_key(previous):
            latest_bridge_by_upstream[upstream] = run

    eligible: list[tuple[tuple[str, int], Mapping[str, Any], Mapping[str, Any] | None]] = []
    for index, run in enumerate(required_runs):
        field = f"required review runs.workflow_runs[{index}]"
        run_id = _int(run.get("id"), f"{field}.id")
        status, conclusion = _status_and_conclusion(run, field)
        if not _run_provenance(
            run,
            field=field,
            expected_name=REQUIRED_REVIEW_NAME,
            expected_path=REQUIRED_REVIEW_PATH,
            expected_repository=expected_repository,
            expected_main_sha=expected_main_sha,
        ):
            continue
        if status != "completed" or conclusion != "success":
            continue
        latest = latest_bridge_by_upstream.get(run_id)
        if latest is not None and latest.get("status") in ACTIVE_STATUSES:
            continue
        last_carried = _run_sort_key(latest) if latest is not None else _run_sort_key(run)
        eligible.append((last_carried, run, latest))

    if not eligible:
        return {
            "schema": SCHEMA,
            "state": "NOOP",
            "first_blocker": "NO_REPLAYABLE_REQUIRED_REVIEW_RUN",
            "eligible_required_review_runs": 0,
            "expected_main_sha": expected_main_sha,
            "expected_repository": expected_repository,
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
        }

    _last_carried, selected, previous_bridge = min(
        eligible,
        key=lambda item: (item[0], _int(item[1].get("id"), "required review run.id")),
    )
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "state": "CANDIDATE",
        "upstream_run_id": _int(selected.get("id"), "required review run.id"),
        "eligible_required_review_runs": len(eligible),
        "expected_main_sha": expected_main_sha,
        "expected_repository": expected_repository,
        "previous_bridge_run_id": (
            _int(previous_bridge.get("id"), "bridge run.id") if previous_bridge is not None else None
        ),
        "productive_effect": False,
        "effect_ack": "NOT_REQUIRED",
    }
    return result


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--required-runs", type=Path, required=True)
    parser.add_argument("--bridge-runs", type=Path, required=True)
    parser.add_argument("--expected-main-sha", required=True)
    parser.add_argument("--expected-repository", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        value = select_carrier(
            _read(args.required_runs),
            _read(args.bridge_runs),
            expected_main_sha=args.expected_main_sha,
            expected_repository=args.expected_repository,
        )
        args.output.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except (CarrierSelectionError, OSError, json.JSONDecodeError) as exc:
        print(f"qikvrt scheduled bridge carrier error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
