#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Finalize one issue transaction without collapsing scoped blockers.

The deterministic work-unit planner always runs. A failed model blocks only the
first semantic cursor; it does not erase completed repository work. A required
platform publication keeps the issue in CONTINUE until the dedicated trusted
publisher has committed a PUBLIC_VERIFIED receipt.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWED_DISPOSITIONS = {
    "EXECUTE_NOW",
    "CLARIFICATION_REQUIRED",
    "BLOCKED_WITH_NEXT_ACTION",
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
}
CLOSURE_DISPOSITIONS = {
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
}


def section(markdown: str, title: str) -> str:
    match = re.search(
        rf"(?ms)^##\s+{re.escape(title)}\s*$\n(.*?)(?=^##\s+|\Z)",
        markdown,
    )
    return match.group(1).strip() if match else ""


def disposition_token(markdown: str) -> str | None:
    value = section(markdown, "Issue disposition")
    if not value:
        return None
    token = value.splitlines()[0].strip().strip("`")
    return token if token in ALLOWED_DISPOSITIONS else None


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_planner(
    directory: Path,
    *,
    model_available: bool,
) -> dict[str, Any]:
    resolved = directory.resolve()
    try:
        issue = int(resolved.name)
    except ValueError as exc:
        raise RuntimeError(
            f"issue directory name is not numeric: {resolved.name}"
        ) from exc
    root = resolved.parents[2]
    planner = root / "tools" / "issue_agent_work_units.py"
    if not planner.is_file():
        raise RuntimeError(f"deterministic planner missing: {planner}")
    command = [
        sys.executable,
        str(planner),
        "--root",
        str(root),
        "--issue",
        str(issue),
    ]
    if model_available:
        command.append("--model-available")
    subprocess.run(command, cwd=root, check=True)
    aggregate_path = directory / "STATUS.work-units.json"
    if not aggregate_path.is_file():
        raise RuntimeError("planner did not produce STATUS.work-units.json")
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    if not isinstance(aggregate, dict):
        raise RuntimeError("planner aggregate is not an object")
    return aggregate


def _fallback_answer(aggregate: dict[str, Any]) -> str:
    blocker = aggregate.get("first_blocker") or "UNCLASSIFIED_INTERNAL_BLOCKER"
    next_action = aggregate.get("next_action") or (
        "Resume the exact work-unit cursor without repeating completed units."
    )
    cursor = aggregate.get("next_cursor") or "NONE"
    return (
        "# Repository answer\n\n"
        "The autonomous semantic model step was unavailable or failed. "
        "Completed deterministic repository work was preserved and the "
        "transaction advanced to the first genuinely blocked cursor.\n\n"
        "## Evidence used\n\n"
        "Exact repository request, repository context and persisted deterministic "
        "work-unit receipts.\n\n"
        "## Formal status\n\nNOT_EVALUATED_BEYOND_EXISTING_EXACT_RECEIPTS\n\n"
        "## Empirical status\n\nNOT_EVALUATED\n\n"
        "## Issue disposition\n\nBLOCKED_WITH_NEXT_ACTION\n\n"
        f"## Disposition reason\n\n{blocker}\n\n"
        f"## Required next action\n\n{next_action}\n\n"
        "## Exact work-unit cursor\n\n"
        f"{cursor}\n\n"
        "## Gate result\n\nBLOCK\n"
    )


def _valid_answer_disposition(markdown: str) -> tuple[str | None, str, str]:
    disposition = disposition_token(markdown)
    reason = section(markdown, "Disposition reason")
    next_action = section(markdown, "Required next action")
    valid = (
        disposition is not None
        and bool(reason)
        and bool(next_action)
        and (
            disposition in CLOSURE_DISPOSITIONS
            or next_action.strip().upper() != "NONE"
        )
    )
    return (disposition if valid else None, reason, next_action)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True)
    parser.add_argument("--inference-outcome", required=True)
    args = parser.parse_args()

    directory = Path(args.directory)
    answer_path = directory / "ANSWER.md"
    inference_completed = (
        args.inference_outcome == "success"
        and answer_path.is_file()
        and answer_path.stat().st_size > 0
    )

    try:
        aggregate = run_planner(
            directory,
            model_available=inference_completed,
        )
    except (
        OSError,
        RuntimeError,
        subprocess.CalledProcessError,
        json.JSONDecodeError,
    ) as exc:
        now = datetime.now(timezone.utc).isoformat()
        if not answer_path.is_file():
            answer_path.write_text(
                "# Repository answer\n\n"
                "Deterministic work-unit planning failed before a trustworthy "
                "aggregate could be produced.\n\n"
                "## Issue disposition\n\nBLOCKED_WITH_NEXT_ACTION\n\n"
                "## Disposition reason\n\n"
                "DETERMINISTIC_WORK_UNIT_PLANNER_FAILED\n\n"
                "## Required next action\n\n"
                "Repair and rerun the trusted deterministic planner on the same "
                "exact issue branch.\n\n"
                "## Gate result\n\nBLOCK\n",
                encoding="utf-8",
            )
        write_json(
            directory / "STATUS.json",
            {
                "status": "BLOCK",
                "issue_materialized": True,
                "model_inference_completed": inference_completed,
                "issue_disposition": "BLOCKED_WITH_NEXT_ACTION",
                "disposition_reason": "DETERMINISTIC_WORK_UNIT_PLANNER_FAILED",
                "next_action": (
                    "Repair and rerun the trusted deterministic planner on the "
                    "same exact issue branch."
                ),
                "first_blocker": "DETERMINISTIC_WORK_UNIT_PLANNER_FAILED",
                "fallback_error": type(exc).__name__,
                "closure_recommended": False,
                "automatic_issue_close": False,
                "automatic_merge": False,
                "mirror_sync_required": False,
                "common_tag_required": False,
                "publication_required": False,
                "publication_state": "NOT_ASSESSED",
                "machine_owned_work_remaining": True,
                "owner_decision_required": False,
                "effect_ack_done": False,
                "generated_at": now,
                "no_false_pass": True,
            },
        )
        raise

    if not inference_completed:
        answer_path.write_text(
            _fallback_answer(aggregate),
            encoding="utf-8",
        )

    markdown = answer_path.read_text(encoding="utf-8")
    disposition, reason, next_action = _valid_answer_disposition(markdown)
    if disposition is None:
        disposition = "BLOCKED_WITH_NEXT_ACTION"
        reason = "ISSUE_DISPOSITION_MISSING_OR_INVALID"
        next_action = (
            "Regenerate one repository-grounded disposition with a reason and "
            "one concrete next action."
        )

    gate = aggregate.get("status")
    publication_required = aggregate.get("publication_required") is True
    publication_state = str(
        aggregate.get("publication_state", "NOT_REQUESTED")
    )
    pre_effect_ready = aggregate.get("pre_effect_ready") is True
    first_blocker = aggregate.get("first_blocker")

    if gate == "BLOCK":
        disposition = "BLOCKED_WITH_NEXT_ACTION"
        reason = str(first_blocker or reason or "SCOPED_WORK_UNIT_BLOCKER")
        next_action = str(
            aggregate.get("next_action")
            or next_action
            or "Resume the exact blocked work unit."
        )
        status_value = "BLOCK"
    elif (
        publication_required
        and pre_effect_ready
        and publication_state == "READY"
    ):
        disposition = "EXECUTE_NOW"
        reason = "PLATFORM_PUBLICATION_READY"
        next_action = (
            "Execute the exact manifest-bound platform publication, reobserve "
            "the public bytes and commit the effect receipt."
        )
        status_value = "CONTINUE"
    elif gate == "DONE" and disposition in CLOSURE_DISPOSITIONS:
        status_value = "DONE"
    else:
        if disposition in CLOSURE_DISPOSITIONS:
            disposition = "EXECUTE_NOW"
            reason = "MACHINE_OWNED_WORK_REMAINS"
            next_action = str(
                aggregate.get("next_action")
                or "Resume the next exact work-unit cursor."
            )
        status_value = "CONTINUE"

    closure = disposition in CLOSURE_DISPOSITIONS
    automatic = status_value == "DONE" and closure
    effect_ack_done = bool(
        automatic
        and publication_required
        and publication_state == "PUBLIC_VERIFIED"
    )
    status = {
        "status": status_value,
        "issue_materialized": True,
        "model_inference_completed": inference_completed,
        "issue_disposition": disposition,
        "disposition_reason": reason,
        "next_action": next_action,
        "first_blocker": first_blocker,
        "next_cursor": aggregate.get("next_cursor"),
        "work_unit_state": aggregate.get("work_unit_state"),
        "pre_effect_ready": pre_effect_ready,
        "publication_required": publication_required,
        "publication_state": publication_state,
        "machine_owned_work_remaining": status_value == "CONTINUE",
        "owner_decision_required": bool(
            aggregate.get("owner_decision_required", False)
        ),
        "closure_recommended": closure,
        "automatic_issue_close": automatic,
        "automatic_merge": automatic,
        "mirror_sync_required": automatic,
        "common_tag_required": automatic,
        "effect_ack_done": effect_ack_done,
        "effect_ack_state": aggregate.get(
            "effect_ack_state",
            "EFFECT_ACK_CONTINUE",
        ),
        "generated_at": None,
        "no_false_pass": True,
    }
    status_path = directory / "STATUS.json"
    previous: dict[str, Any] | None = None
    if status_path.is_file():
        try:
            loaded = json.loads(status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = None
        if isinstance(loaded, dict):
            previous = loaded
    comparable = dict(status)
    comparable.pop("generated_at", None)
    previous_comparable = dict(previous) if previous is not None else None
    if previous_comparable is not None:
        previous_comparable.pop("generated_at", None)
    status["generated_at"] = (
        previous.get("generated_at")
        if previous is not None
        and previous_comparable == comparable
        and isinstance(previous.get("generated_at"), str)
        else datetime.now(timezone.utc).isoformat()
    )
    write_json(status_path, status)


if __name__ == "__main__":
    main()
