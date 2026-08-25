#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed decision core for expected-head-bound QIK-VRT promotion.

Promotion is phase-qualified:
- REQUEST_READY_RECLASSIFICATION_AUTHORITY: a marked draft has all
  repository-internal exact-head gates, but no automatic draft mutation follows
  because GitHub offers no expected-base-and-head compare-and-swap for it.
- REQUEST_EXACT_BASE_CAS_AUTHORITY: a non-draft candidate may be reobserved,
  but no merge mutation follows because GitHub's head precondition does not
  compare-and-swap the checked base as immediate first parent.

Bot review execution and Code-Owner authority are distinct inputs. Integrity
projection overlap is not treated as semantic competing-writer overlap.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any, Iterable, Mapping, Sequence

PROMOTION_MARKER = "<!-- qikvrt-expected-head-promotion:enabled external_effect=NONE -->"
REVIEW_GATE = "QIKVRT requested review execution"
INTEGRITY_PROJECTION_PATHS = frozenset(
    {
        "REPOSITORY_FILE_MANIFEST.json",
        "REPOSITORY_FILE_MANIFEST.json.sha256",
        "SHA256SUMS.txt",
    }
)
SUCCESS_CONCLUSIONS = {"success"}
NON_ADVERSE_CONCLUSIONS = {"success", "skipped"}


class PromotionBlock(ValueError):
    """Raised when a snapshot is structurally invalid rather than merely blocked."""


def mesh_review_status_projection(
    statuses: Iterable[Mapping[str, Any]], context: str
) -> dict[str, Any]:
    """Return the exact latest Mesh status identity used by a promotion fence."""
    if not isinstance(context, str) or not context:
        raise PromotionBlock("Mesh review status context is missing")
    matching: list[Mapping[str, Any]] = []
    for status in statuses:
        if not isinstance(status, Mapping):
            raise PromotionBlock("commit status must be an object")
        if status.get("context") == context:
            matching.append(status)
    if not matching:
        raise PromotionBlock("requested-review execution status is missing")

    def key(status: Mapping[str, Any]) -> tuple[str, int]:
        identifier = status.get("id")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier < 1:
            raise PromotionBlock("requested-review status id is invalid")
        timestamp = status.get("updated_at") or status.get("created_at")
        if not isinstance(timestamp, str) or not timestamp:
            raise PromotionBlock("requested-review status timestamp is missing")
        return timestamp, identifier

    latest = max(matching, key=key)
    state = latest.get("state")
    if not isinstance(state, str) or not state:
        raise PromotionBlock("requested-review status state is missing")
    match = re.search(r"\bfp=([0-9a-f]{64})\b", latest.get("description") or "")
    if match is None:
        raise PromotionBlock("requested-review status lacks a full evidence fingerprint")
    return {
        "context": context,
        "id": latest["id"],
        "state": state,
        "evidence_fingerprint": match.group(1),
    }


def require_unchanged_mesh_review_status(
    expected: Mapping[str, Any],
    statuses: Iterable[Mapping[str, Any]],
    context: str,
) -> dict[str, Any]:
    """Fail unless the current latest success status is the exact fenced status."""
    observed = mesh_review_status_projection(statuses, context)
    if observed.get("state") != "success":
        raise PromotionBlock(
            f"requested-review execution is {observed.get('state')!r} at final fence"
        )
    if dict(expected) != observed:
        raise PromotionBlock("requested-review status changed after Mesh reobservation")
    return observed


def trusted_promotion_marker(
    pull_request: Mapping[str, Any],
    repository: str,
    marker: str = PROMOTION_MARKER,
) -> dict[str, str]:
    """Bind promotion opt-in to the repository's own self-heal PR body."""
    if not isinstance(pull_request, Mapping):
        raise PromotionBlock("promotion marker subject is not a pull request")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise PromotionBlock("promotion marker repository is invalid")
    if not isinstance(marker, str) or not marker:
        raise PromotionBlock("promotion marker is missing")
    head = pull_request.get("head")
    base = pull_request.get("base")
    if not isinstance(head, Mapping) or not isinstance(base, Mapping):
        raise PromotionBlock("promotion marker subject lacks Git bindings")
    head_repository = head.get("repo")
    if not isinstance(head_repository, Mapping) or head_repository.get("full_name") != repository:
        raise PromotionBlock("promotion marker is not role-local")
    head_ref = head.get("ref")
    if not isinstance(head_ref, str) or not head_ref.startswith("automation/self-heal-"):
        raise PromotionBlock("promotion marker is not bound to a self-heal branch")
    if pull_request.get("state") != "open" or base.get("ref") != "main":
        raise PromotionBlock("promotion marker subject is not an open main pull request")
    author = pull_request.get("user")
    if not isinstance(author, Mapping) or author.get("login") != "github-actions[bot]":
        raise PromotionBlock("promotion marker author is not the repository workflow identity")
    body = pull_request.get("body")
    if not isinstance(body, str) or marker not in body:
        raise PromotionBlock("trusted pull-request body has no promotion marker")
    return {
        "source": "TRUSTED_AUTONOMOUS_SELF_HEAL_PR_BODY",
        "author": "github-actions[bot]",
        "head_ref": head_ref,
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }


def require_unchanged_promotion_marker(
    expected_body_sha256: str,
    pull_request: Mapping[str, Any],
    repository: str,
    marker: str = PROMOTION_MARKER,
) -> dict[str, str]:
    """Fail if the trusted marker body changed before a repository mutation."""
    if (
        not isinstance(expected_body_sha256, str)
        or len(expected_body_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_body_sha256)
    ):
        raise PromotionBlock("expected promotion marker digest is invalid")
    observed = trusted_promotion_marker(pull_request, repository, marker)
    if observed["body_sha256"] != expected_body_sha256:
        raise PromotionBlock("promotion marker body changed before mutation")
    return observed


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise PromotionBlock(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise PromotionBlock(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


def _run_number(run: Mapping[str, Any]) -> int:
    value = run.get("run_number", -1)
    if isinstance(value, bool) or not isinstance(value, int):
        raise PromotionBlock("workflow run_number must be an integer")
    return value


def collapse_latest_runs(runs: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    latest: dict[str, Mapping[str, Any]] = {}
    for run in runs:
        if not isinstance(run, Mapping):
            raise PromotionBlock("workflow run must be an object")
        name = run.get("name")
        if not isinstance(name, str) or not name:
            raise PromotionBlock("workflow run name is missing")
        current = latest.get(name)
        if current is None or _run_number(run) > _run_number(current):
            latest[name] = run
    return latest


def _decision(
    snapshot: Mapping[str, Any],
    state: str,
    failure_class: str | None,
    detail: str,
    *,
    phase: str | None = None,
    latest: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "qikvrt_expected_head_promotion_decision_v3",
        "state": state,
        "phase": phase,
        "first_blocker": failure_class,
        "detail": detail,
        "pr_number": snapshot.get("pr_number"),
        "expected_head_sha": snapshot.get("expected_head_sha"),
        "current_main_sha": snapshot.get("current_main_sha"),
        "external_effect": "NONE",
        "verification_state": "HOLD_UNVERIFIED",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "AUTHORITY_MIRROR_EQUALITY": False,
            "INDEPENDENT_REVIEW": False,
            "MERGE": False,
        },
    }
    if latest is not None:
        result["latest_workflows"] = {
            name: {
                "run_number": _run_number(run),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
            }
            for name, run in sorted(latest.items())
        }
    return result


def _blocked(snapshot: Mapping[str, Any], failure_class: str, detail: str) -> dict[str, Any]:
    return _decision(snapshot, "BLOCK", failure_class, detail)


def _code_owner_review_blocker(
    snapshot: Mapping[str, Any], expected_head: str
) -> tuple[str, str] | None:
    observed = snapshot.get("code_owner_review_gate")
    if not isinstance(observed, Mapping):
        return (
            "CODE_OWNER_REVIEW_GATE_MISSING",
            "promotion snapshot has no independent Code Owner review-gate observation",
        )
    observed_head = observed.get("head_sha")
    if observed_head != expected_head:
        return (
            "CODE_OWNER_REVIEW_STALE",
            f"review gate head {observed_head!r} != expected head {expected_head}",
        )
    state = observed.get("gate_state")
    if state == "success":
        return None
    first_blocker = observed.get("first_blocker")
    allowed = {
        "CODE_OWNER_RULE_NOT_ENFORCED",
        "CODE_OWNER_REVIEW_MISSING",
        "CODE_OWNER_REVIEW_STALE",
        "CODE_OWNER_REVIEW_NOT_APPROVED",
        "CODE_OWNER_REVIEW_DISMISSED",
        "CODE_OWNER_REVIEW_CHANGES_REQUESTED",
        "CODE_OWNER_REVIEW_SELF_APPROVAL",
    }
    if first_blocker in allowed:
        return first_blocker, str(observed.get("detail") or first_blocker)
    return (
        "CODE_OWNER_REVIEW_GATE_NOT_GREEN",
        f"Code Owner review gate is {state!r}",
    )


def _effective_overlaps(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise PromotionBlock("competing_writer_overlaps must be a list")
    effective: list[dict[str, Any]] = []
    for overlap in value:
        if not isinstance(overlap, Mapping):
            raise PromotionBlock("competing writer overlap must be an object")
        paths = overlap.get("paths")
        if not isinstance(paths, list) or not all(isinstance(path, str) and path for path in paths):
            raise PromotionBlock("competing writer overlap paths must be a non-empty string list")
        semantic_paths = sorted(set(paths) - INTEGRITY_PROJECTION_PATHS)
        if semantic_paths:
            effective.append(
                {
                    "pr_number": overlap.get("pr_number"),
                    "paths": semantic_paths,
                }
            )
    return effective


def evaluate_promotion(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(snapshot, Mapping):
        raise PromotionBlock("snapshot must be an object")

    current_main = _sha(snapshot.get("current_main_sha"), "current_main_sha")
    base = _sha(snapshot.get("base_sha"), "base_sha")
    expected_head = _sha(snapshot.get("expected_head_sha"), "expected_head_sha")
    current_head = _sha(snapshot.get("current_head_sha"), "current_head_sha")

    if current_main != base:
        return _blocked(snapshot, "BASE_DRIFT", f"current main {current_main} != candidate base {base}")
    if current_head != expected_head:
        return _blocked(snapshot, "HEAD_DRIFT", f"current head {current_head} != expected head {expected_head}")
    if snapshot.get("mergeable") is not True:
        return _blocked(snapshot, "NOT_MERGEABLE", "candidate is not currently mergeable")
    if snapshot.get("external_effect") != "NONE":
        return _blocked(snapshot, "EXTERNAL_EFFECT_BOUNDARY", "candidate crosses an external-effect boundary")

    overlaps = _effective_overlaps(snapshot.get("competing_writer_overlaps", []))
    if overlaps:
        return _blocked(
            snapshot,
            "COMPETING_WRITER_OVERLAP",
            f"overlapping semantic writer(s): {overlaps}",
        )

    required = snapshot.get("required_gates")
    if not isinstance(required, list) or not required or not all(
        isinstance(name, str) and name for name in required
    ):
        raise PromotionBlock("required_gates must be a non-empty list of names")
    if REVIEW_GATE not in required:
        raise PromotionBlock(f"required_gates must include {REVIEW_GATE!r}")

    runs = snapshot.get("workflow_runs")
    if not isinstance(runs, list):
        raise PromotionBlock("workflow_runs must be a list")
    latest = collapse_latest_runs(runs)
    draft = snapshot.get("draft") is True

    phase_required = [gate for gate in required if not (draft and gate == REVIEW_GATE)]
    for gate in phase_required:
        run = latest.get(gate)
        if run is None:
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_MISSING", f"required workflow is absent: {gate}")
        if run.get("status") != "completed":
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_NOT_TERMINAL", f"required workflow is not terminal: {gate}")
        if run.get("conclusion") not in SUCCESS_CONCLUSIONS:
            return _blocked(snapshot, "REQUIRED_EXACT_HEAD_GATE_NOT_GREEN", f"required workflow is not successful: {gate}={run.get('conclusion')}")

    for name, run in sorted(latest.items()):
        if name in phase_required or (draft and name == REVIEW_GATE):
            continue
        status = run.get("status")
        conclusion = run.get("conclusion")
        if status != "completed":
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_TERMINAL", f"workflow is not terminal: {name}")
        if conclusion not in NON_ADVERSE_CONCLUSIONS:
            return _blocked(snapshot, "APPLICABLE_EXACT_HEAD_GATE_NOT_GREEN", f"workflow is adverse: {name}={conclusion}")

    if draft:
        result = _decision(
            snapshot,
            "BLOCK",
            "READY_RECLASSIFICATION_CAS_UNAVAILABLE",
            "all pre-review exact-head conditions are satisfied, but automatic draft-to-ready is disabled because the mutation cannot atomically bind the reobserved base and head and its GITHUB_TOKEN event cannot establish the required follow-on gate cycle",
            phase="REQUEST_READY_RECLASSIFICATION_AUTHORITY",
            latest=latest,
        )
        result["next_action"] = (
            "REQUEST_HISTORY_PRESERVING_READY_RECLASSIFICATION_AUTHORITY"
        )
        return result

    review_blocker = _code_owner_review_blocker(snapshot, expected_head)
    if review_blocker is not None:
        return _blocked(snapshot, *review_blocker)

    result = _decision(
        snapshot,
        "BLOCK",
        "HEAD1_BASE_CAS_UNAVAILABLE",
        "technical and authority gates are favorable, but the GitHub pull-merge head precondition cannot bind the reobserved base as the immediate first parent; automated merge remains disabled",
        phase="REQUEST_EXACT_BASE_CAS_AUTHORITY",
        latest=latest,
    )
    result["next_action"] = "REQUEST_HISTORY_PRESERVING_EXACT_BASE_CAS_AUTHORITY"
    return result


def _load_snapshot(path: str) -> Mapping[str, Any]:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise PromotionBlock("snapshot JSON must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate",))
    parser.add_argument("--input", default="-", help="snapshot JSON file or - for stdin")
    args = parser.parse_args(argv)
    try:
        result = evaluate_promotion(_load_snapshot(args.input))
    except (OSError, ValueError, json.JSONDecodeError, PromotionBlock) as exc:
        result = {
            "schema": "qikvrt_expected_head_promotion_decision_v3",
            "state": "BLOCK",
            "phase": None,
            "first_blocker": "INVALID_PROMOTION_SNAPSHOT",
            "detail": str(exc),
            "external_effect": "NONE",
            "verification_state": "HOLD_UNVERIFIED",
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
                "AUTHORITY_MIRROR_EQUALITY": False,
                "INDEPENDENT_REVIEW": False,
                "MERGE": False,
            },
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") == "PROMOTABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
