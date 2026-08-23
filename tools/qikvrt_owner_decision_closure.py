#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Classify one exact-bound Product-Owner continuation without performing effects.

The trusted-main workflow owns GitHub observation and mutation.  This module is
the pure, deterministic decision core: it validates the owner receipt and the
live pull-request binding, invalidates exact-head evidence on drift, and emits
one of AUTO_RESOLVABLE, WAITING, TRUE_BLOCKER, or CONTINUE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "qikvrt_owner_decision_closure_v1"
CLASSES = {"AUTO_RESOLVABLE", "WAITING", "TRUE_BLOCKER", "CONTINUE"}
SUCCESS = {"success"}
ADVERSE = {"failure", "cancelled", "timed_out", "startup_failure", "stale"}
ACTIVE = {"queued", "in_progress", "waiting", "pending", "requested"}
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
DEFAULT_REQUIRED_WORKFLOWS = (
    "QIKVRT CI",
    "QIKVRT repository evidence materialization",
    "QIKVRT Collective Proposal Review",
)
REVIEW_STATUS_CONTEXT = "QIKVRT required code-owner review"


class ClosureInputError(ValueError):
    """The observation envelope is incomplete or contradictory."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA_RE.fullmatch(value) is None:
        raise ClosureInputError(f"{label} is not a lowercase Git SHA-1")
    return value


def _scope(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ClosureInputError(f"{label} must be a non-empty path list")
    if any(not isinstance(path, str) or not path or path.startswith("/") for path in value):
        raise ClosureInputError(f"{label} contains an invalid path")
    if value != sorted(set(value)):
        raise ClosureInputError(f"{label} must be sorted and unique")
    return value


def binding(value: Mapping[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ClosureInputError(f"{label} is not an object")
    projected = {
        "base_sha": _sha(value.get("base_sha"), f"{label}.base_sha"),
        "head_sha": _sha(value.get("head_sha"), f"{label}.head_sha"),
        "tree_sha": _sha(value.get("tree_sha"), f"{label}.tree_sha"),
        "scope": _scope(value.get("scope"), f"{label}.scope"),
    }
    projected["scope_sha256"] = fingerprint(projected["scope"])
    return projected


def _latest_status(statuses: Sequence[Mapping[str, Any]], context: str) -> Mapping[str, Any] | None:
    matching = [item for item in statuses if item.get("context") == context]
    return max(
        matching,
        key=lambda item: (str(item.get("updated_at") or item.get("created_at") or ""), int(item.get("id") or -1)),
        default=None,
    )


def _latest_workflows(workflows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    latest: dict[str, Mapping[str, Any]] = {}
    for item in workflows:
        name = item.get("name")
        if not isinstance(name, str) or not name:
            raise ClosureInputError("workflow name is missing")
        if item.get("head_sha") is not None:
            _sha(item.get("head_sha"), f"workflow {name}.head_sha")
        key = (int(item.get("run_number") or -1), int(item.get("run_attempt") or 1), int(item.get("id") or -1))
        current = latest.get(name)
        current_key = (
            int(current.get("run_number") or -1),
            int(current.get("run_attempt") or 1),
            int(current.get("id") or -1),
        ) if current else (-1, -1, -1)
        if key > current_key:
            latest[name] = item
    return latest


def _result(
    *,
    current: Mapping[str, Any],
    decision_binding: Mapping[str, Any],
    classification: str,
    phase: str,
    blocker: str | None,
    detail: str,
    next_action: str,
    stale_evidence: bool,
    dispatch_workflows: Sequence[str] = (),
    request_reviewer: bool = False,
) -> dict[str, Any]:
    if classification not in CLASSES:
        raise AssertionError(classification)
    result = {
        "schema": SCHEMA,
        "classification": classification,
        "phase": phase,
        "first_blocker": blocker,
        "detail": detail,
        "next_action": next_action,
        "decision_binding": dict(decision_binding),
        "current_binding": dict(current),
        "binding_fingerprint": fingerprint(current),
        "stale_exact_head_evidence": stale_evidence,
        "dispatch_workflows": list(dispatch_workflows),
        "request_reviewer": request_reviewer,
        "review_authority": "INDEPENDENT_NATIVE_GITHUB_REVIEW_REQUIRED",
        "external_effect": "NONE_BY_CLASSIFIER",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
            "PUBLICATION": False,
        },
    }
    result["receipt_fingerprint"] = fingerprint(result)
    return result


def classify(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise ClosureInputError("snapshot is not an object")
    decision = snapshot.get("owner_decision")
    if not isinstance(decision, Mapping):
        raise ClosureInputError("owner_decision is missing")
    if decision.get("state") != "APPROVED":
        raise ClosureInputError("owner_decision.state must be APPROVED")
    if decision.get("author_login") != snapshot.get("product_owner_login"):
        raise ClosureInputError("owner decision author is not the configured Product Owner")
    source_id = decision.get("source_id")
    if not isinstance(source_id, int) or isinstance(source_id, bool) or source_id < 1:
        raise ClosureInputError("owner_decision.source_id must be positive")

    decided = binding(decision.get("binding", {}), "owner_decision.binding")
    current = binding(snapshot.get("current_binding", {}), "current_binding")
    if snapshot.get("pr_state") != "open":
        return _result(current=current, decision_binding=decided, classification="TRUE_BLOCKER", phase="RESOLVE", blocker="PULL_REQUEST_NOT_OPEN", detail="the bound pull request is not open", next_action="Reobserve the intended open review candidate.", stale_evidence=decided != current)
    if snapshot.get("draft") is True:
        return _result(current=current, decision_binding=decided, classification="TRUE_BLOCKER", phase="RESOLVE", blocker="CANDIDATE_NOT_REVIEW_READY", detail="the bound pull request is still draft", next_action="Make the candidate review-ready without changing its approved semantic scope, then reobserve.", stale_evidence=decided != current)

    if decided != current:
        same_scope = decided["scope_sha256"] == current["scope_sha256"]
        descendant = snapshot.get("head_is_descendant") is True
        changed_since_decision = snapshot.get("paths_changed_since_decision")
        materialization = snapshot.get("materialization_paths", [])
        if not isinstance(changed_since_decision, list) or not isinstance(materialization, list):
            raise ClosureInputError("drift path observations must be lists")
        projection_only = set(changed_since_decision).issubset(set(materialization))
        if same_scope and descendant and projection_only:
            return _result(current=current, decision_binding=decided, classification="AUTO_RESOLVABLE", phase="RESOLVE", blocker=None, detail="exact binding drifted only through declared materialization paths on a descendant", next_action="Persist a replacement exact binding and restart fresh-head verification; transfer no former-head evidence.", stale_evidence=True)
        return _result(current=current, decision_binding=decided, classification="TRUE_BLOCKER", phase="RESOLVE", blocker="OWNER_DECISION_BINDING_DRIFT", detail="base, head, tree, or semantic scope drift is not a projection-only descendant transition", next_action="Present the drift delta and obtain one new owner decision for the changed semantic candidate.", stale_evidence=True)

    head = current["head_sha"]
    statuses = snapshot.get("statuses", [])
    workflows = snapshot.get("workflows", [])
    reviews = snapshot.get("reviews", [])
    if not all(isinstance(value, list) for value in (statuses, workflows, reviews)):
        raise ClosureInputError("statuses, workflows, and reviews must be lists")
    if any(not isinstance(item, Mapping) for seq in (statuses, workflows, reviews) for item in seq):
        raise ClosureInputError("an observed evidence item is not an object")

    required = snapshot.get("required_workflows", list(DEFAULT_REQUIRED_WORKFLOWS))
    if not isinstance(required, list) or not required or any(not isinstance(name, str) or not name for name in required):
        raise ClosureInputError("required_workflows is invalid")
    latest = _latest_workflows(workflows)
    missing = [name for name in required if name not in latest]
    if missing:
        return _result(current=current, decision_binding=decided, classification="AUTO_RESOLVABLE", phase="VERIFY", blocker=None, detail="fresh exact-head workflow evidence is absent", next_action="Dispatch only the missing trusted-main verification workflows.", stale_evidence=False, dispatch_workflows=missing)

    active: list[str] = []
    adverse: list[str] = []
    for name in required:
        run = latest[name]
        if run.get("head_sha") != head:
            adverse.append(f"{name}:STALE_HEAD")
        elif run.get("status") in ACTIVE or run.get("status") != "completed":
            active.append(name)
        elif run.get("conclusion") in ADVERSE or run.get("conclusion") not in SUCCESS:
            adverse.append(f"{name}:{run.get('conclusion') or 'missing'}")
    if adverse:
        return _result(current=current, decision_binding=decided, classification="TRUE_BLOCKER", phase="VERIFY", blocker="EXACT_HEAD_WORKFLOW_ADVERSE", detail=", ".join(adverse), next_action="Repair the first adverse exact-head gate as a descendant and re-resolve the owner binding.", stale_evidence=False)
    if active:
        return _result(current=current, decision_binding=decided, classification="WAITING", phase="VERIFY", blocker=None, detail="fresh exact-head workflows are still active", next_action="Observe the already-started workflows to terminal state.", stale_evidence=False)

    reviewer = snapshot.get("required_code_owner")
    if not isinstance(reviewer, str) or not reviewer:
        raise ClosureInputError("required_code_owner is missing")
    decisive = [
        review for review in reviews
        if str((review.get("user") or {}).get("login", "")).casefold() == reviewer.casefold()
        and review.get("commit_id") == head
        and str(review.get("state", "")).upper() in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
    ]
    decisive.sort(key=lambda item: (str(item.get("submitted_at") or ""), int(item.get("id") or -1)))
    latest_review = decisive[-1] if decisive else None
    if latest_review and str(latest_review.get("state")).upper() == "CHANGES_REQUESTED":
        return _result(current=current, decision_binding=decided, classification="TRUE_BLOCKER", phase="AUTHORIZE", blocker="INDEPENDENT_REVIEW_CHANGES_REQUESTED", detail=f"@{reviewer} requested changes on the exact head", next_action="Address the independent review findings in a descendant and re-resolve the binding.", stale_evidence=False)
    if not latest_review or str(latest_review.get("state")).upper() != "APPROVED":
        requested = {str(item).casefold() for item in snapshot.get("requested_reviewers", [])}
        should_request = reviewer.casefold() not in requested
        return _result(current=current, decision_binding=decided, classification="AUTO_RESOLVABLE" if should_request else "WAITING", phase="AUTHORIZE", blocker=None, detail="no independent current-head Code Owner approval is recorded", next_action="Request the configured Code Owner once." if should_request else "Observe the already-requested independent review.", stale_evidence=False, request_reviewer=should_request)

    gate = _latest_status(statuses, REVIEW_STATUS_CONTEXT)
    if gate is None or gate.get("state") == "pending":
        return _result(current=current, decision_binding=decided, classification="AUTO_RESOLVABLE", phase="AUTHORIZE", blocker=None, detail="the independent review exists but its native exact-head gate is not terminal", next_action="Dispatch the trusted required-review gate for this PR.", stale_evidence=False, dispatch_workflows=("QIKVRT required code-owner review",))
    if gate.get("state") != "success":
        return _result(current=current, decision_binding=decided, classification="TRUE_BLOCKER", phase="AUTHORIZE", blocker="CODE_OWNER_GATE_ADVERSE", detail=str(gate.get("description") or gate.get("state")), next_action="Repair native review enforcement or the exact-head review state, then reobserve.", stale_evidence=False)

    return _result(current=current, decision_binding=decided, classification="CONTINUE", phase="CONTINUE", blocker=None, detail="owner decision, exact-head workflows, independent review, and native review status are current", next_action="Hand the exact-bound receipt to the separately authorized executor/observer path; no merge or publication is inferred.", stale_evidence=False)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("classify", nargs="?", default="classify")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        result = classify(json.loads(pathlib.Path(args.input).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ClosureInputError, ValueError) as exc:
        result = {"schema": SCHEMA, "classification": "TRUE_BLOCKER", "phase": "RESOLVE", "first_blocker": "INVALID_CLOSURE_SNAPSHOT", "detail": str(exc), "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False, "MERGE": False, "PUBLICATION": False}}
    rendered = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output:
        pathlib.Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result["classification"] != "TRUE_BLOCKER" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
