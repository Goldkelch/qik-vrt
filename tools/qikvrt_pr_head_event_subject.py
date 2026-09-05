# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Bind one exact PR-head subject from a repository interrupt.

The autonomous PR-head controller must consume an exact event subject before it
falls back to a repository-wide scan.  This module is deliberately pure: it
validates only the GitHub event envelope and the already observed current main
SHA.  Live head/run/status reobservation remains in the controller.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
from collections.abc import Mapping
from typing import Any

_SHA40 = re.compile(r"^[0-9a-f]{40}$")


class EventSubjectBindingError(ValueError):
    """An event claimed an exact subject but could not bind it safely."""


def _object(value: Any) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None


def _subject_from_pull_request(event: Mapping[str, Any]) -> dict[str, Any] | None:
    pull = _object(event.get("pull_request"))
    if pull is None:
        return None
    head = _object(pull.get("head"))
    base = _object(pull.get("base"))
    head_repo = _object((head or {}).get("repo"))
    return {
        "number": pull.get("number"),
        "head_ref": (head or {}).get("ref"),
        "head_sha": (head or {}).get("sha"),
        "base_sha": (base or {}).get("sha"),
        "head_repository": (head_repo or {}).get("full_name"),
        "selection_basis": "EXACT_PULL_REQUEST_TARGET_EVENT",
    }


def _subject_from_workflow_run(event: Mapping[str, Any]) -> dict[str, Any] | None:
    workflow_run = _object(event.get("workflow_run"))
    if workflow_run is None:
        return None
    pulls = workflow_run.get("pull_requests")
    if not isinstance(pulls, list) or len(pulls) != 1:
        return None
    pull = _object(pulls[0])
    if pull is None:
        raise EventSubjectBindingError("workflow_run pull request is not an object")
    head = _object(pull.get("head"))
    base = _object(pull.get("base"))
    head_repository = _object(workflow_run.get("head_repository"))
    head_repo = _object((head or {}).get("repo"))
    repository = (head_repository or {}).get("full_name")
    if repository is None:
        repository = (head_repo or {}).get("full_name")
    return {
        "number": pull.get("number"),
        "head_ref": (head or {}).get("ref"),
        "head_sha": (head or {}).get("sha"),
        "base_sha": (base or {}).get("sha"),
        "head_repository": repository,
        "selection_basis": "EXACT_WORKFLOW_RUN_EVENT",
    }


def bind_event_subject(
    event: Mapping[str, Any],
    repository: str,
    current_main_sha: str,
) -> dict[str, Any]:
    """Return a deterministic exact-event binding receipt."""
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise EventSubjectBindingError("repository identity is invalid")
    if not isinstance(current_main_sha, str) or _SHA40.fullmatch(current_main_sha) is None:
        raise EventSubjectBindingError("current main SHA is invalid")

    raw = _subject_from_pull_request(event)
    if raw is None:
        raw = _subject_from_workflow_run(event)
    if raw is None:
        return {
            "schema": "qikvrt_pr_head_event_subject_v1",
            "state": "UNBOUND",
            "d0": 0,
            "selection_basis": "GLOBAL_BOUNDED_DISCOVERY",
            "reason": "NO_SINGLE_EXACT_EVENT_SUBJECT",
            "first_causal_blocker": None,
            "next_action": "RUN_BOUNDED_GLOBAL_DISCOVERY",
            "subject": None,
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
        }

    if raw.get("head_repository") != repository:
        return {
            "schema": "qikvrt_pr_head_event_subject_v1",
            "state": "UNBOUND",
            "d0": 0,
            "selection_basis": "GLOBAL_BOUNDED_DISCOVERY",
            "reason": "EVENT_SUBJECT_NOT_INTERNAL_TO_REPOSITORY",
            "first_causal_blocker": None,
            "next_action": "RUN_BOUNDED_GLOBAL_DISCOVERY",
            "subject": None,
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
        }

    number = raw.get("number")
    head_ref = raw.get("head_ref")
    head_sha = raw.get("head_sha")
    base_sha = raw.get("base_sha")
    if (
        isinstance(number, bool)
        or not isinstance(number, int)
        or number < 1
        or not isinstance(head_ref, str)
        or not head_ref
        or head_ref.startswith("refs/")
        or "\x00" in head_ref
        or not isinstance(head_sha, str)
        or _SHA40.fullmatch(head_sha) is None
        or not isinstance(base_sha, str)
        or _SHA40.fullmatch(base_sha) is None
    ):
        return {
            "schema": "qikvrt_pr_head_event_subject_v1",
            "state": "HOLD_UNVERIFIED",
            "d0": 1,
            "selection_basis": raw.get("selection_basis"),
            "reason": "EVENT_SUBJECT_BINDING_INVALID",
            "first_causal_blocker": "EVENT_SUBJECT_BINDING_INVALID",
            "next_action": "PRESERVE_FAIL_CLOSED_WITHOUT_GLOBAL_SUBSTITUTION",
            "subject": None,
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
        }

    subject = {
        "number": number,
        "head": {
            "ref": head_ref,
            "sha": head_sha,
            "repo": {"full_name": repository},
        },
        "base": {"sha": base_sha},
    }
    if base_sha != current_main_sha:
        return {
            "schema": "qikvrt_pr_head_event_subject_v1",
            "state": "HOLD",
            "d0": 1,
            "selection_basis": raw.get("selection_basis"),
            "reason": "BASE_DRIFT",
            "first_causal_blocker": "BASE_DRIFT",
            "next_action": "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN",
            "subject": subject,
            "current_main_sha": current_main_sha,
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
        }

    return {
        "schema": "qikvrt_pr_head_event_subject_v1",
        "state": "BOUND",
        "d0": 0,
        "selection_basis": raw.get("selection_basis"),
        "reason": "EXACT_EVENT_SUBJECT_BOUND",
        "first_causal_blocker": None,
        "next_action": "CLASSIFY_EXACT_EVENT_SUBJECT_FIRST",
        "subject": subject,
        "current_main_sha": current_main_sha,
        "productive_effect": False,
        "effect_ack": "NOT_REQUIRED",
    }


def _write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True, type=pathlib.Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--current-main", required=True)
    parser.add_argument("--receipt-output", required=True, type=pathlib.Path)
    parser.add_argument("--subjects-output", required=True, type=pathlib.Path)
    args = parser.parse_args()

    value = json.loads(args.event.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise EventSubjectBindingError("GitHub event payload is not an object")
    receipt = bind_event_subject(value, args.repository, args.current_main)
    subjects = [receipt["subject"]] if receipt.get("state") == "BOUND" else []
    _write_json(args.receipt_output, receipt)
    _write_json(args.subjects_output, subjects)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
