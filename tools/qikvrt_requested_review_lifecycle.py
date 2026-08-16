#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright (c) 2026 Ingolf Lohmann.
"""Fail-closed exact-binding decision core for requested GitHub reviews.

The core is deliberately read-only. Its trusted workflow wrapper may persist
one exact-binding ``COMMENT_WITH_BLOCKER`` review, but it must never manufacture
an ``APPROVED`` review or merge a pull request. A requested reviewer can cease
to appear in GitHub's *active* request list after submitting a review, so the
snapshot includes the repository-observed request history as well.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import pathlib
import re
import sys
from typing import Any, Mapping, Sequence


class ReviewLifecycleBlock(ValueError):
    """Raised for an invalid machine snapshot."""


# A lifecycle marker is evidence of a prior automated/product-owner blocker
# disposition only when GitHub attributes it to one of these fixed, repository
# governed identities.  Treating a copied HTML comment from an arbitrary review
# as a marker would let a PR author suppress the required lifecycle event.
LIFECYCLE_MARKER_ACTORS = frozenset({"github-actions[bot]", "ingolf-lohmann"})

# The executor's own signer can leave a COMMENTED lifecycle record, but that
# automated record must never satisfy a requested human/code-owner review.
AUTOMATION_REVIEW_ACTORS = frozenset({"github-actions[bot]"})
COMMENT_WITH_BLOCKER_TOKEN = "<!-- qikvrt-review-disposition:COMMENT_WITH_BLOCKER -->"


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise ReviewLifecycleBlock(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise ReviewLifecycleBlock(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ReviewLifecycleBlock(f"{label} is not a SHA-256")
    if any(character not in "0123456789abcdef" for character in value):
        raise ReviewLifecycleBlock(f"{label} is not a lowercase hexadecimal SHA-256")
    return value


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ReviewLifecycleBlock(f"{label} must be a list of non-empty strings")
    return value


def _optional_sha(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _sha(value, label)


def _timestamp(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ReviewLifecycleBlock(f"{label} must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewLifecycleBlock(f"{label} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ReviewLifecycleBlock(f"{label} must include a timezone")
    return parsed


def _request_times(value: Any, label: str) -> dict[str, tuple[str, datetime]]:
    if not isinstance(value, Mapping):
        raise ReviewLifecycleBlock(f"{label} must be an object")
    normalized: dict[str, tuple[str, datetime]] = {}
    for login, timestamp in value.items():
        if not isinstance(login, str) or not login:
            raise ReviewLifecycleBlock(f"{label} has an invalid requested-reviewer key")
        parsed = _timestamp(timestamp, f"{label}[{login!r}]")
        key = login.casefold()
        if key in normalized:
            raise ReviewLifecycleBlock(f"{label} repeats requested reviewer {login!r}")
        normalized[key] = (timestamp, parsed)
    return normalized


def _request_event_ids(value: Any, label: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ReviewLifecycleBlock(f"{label} must be an object")
    normalized: dict[str, int] = {}
    for login, event_id in value.items():
        if not isinstance(login, str) or not login:
            raise ReviewLifecycleBlock(f"{label} has an invalid requested-reviewer key")
        if isinstance(event_id, bool) or not isinstance(event_id, int) or event_id < 1:
            raise ReviewLifecycleBlock(f"{label}[{login!r}] is not a positive event id")
        key = login.casefold()
        if key in normalized:
            raise ReviewLifecycleBlock(f"{label} repeats requested reviewer {login!r}")
        normalized[key] = event_id
    return normalized


def _review_login(review: Mapping[str, Any]) -> str:
    actor = review.get("user")
    if isinstance(actor, Mapping):
        actor = actor.get("login")
    if not isinstance(actor, str) or not actor:
        raise ReviewLifecycleBlock("review user login is missing")
    return actor


def _review_disposition(review: Mapping[str, Any]) -> str | None:
    state = review.get("state")
    if state == "APPROVED":
        return "APPROVE"
    if state == "CHANGES_REQUESTED":
        return "REQUEST_CHANGES"
    body = review.get("body")
    if (
        state == "COMMENTED"
        and isinstance(body, str)
        and re.match(r"\A<!-- qikvrt-review-disposition:COMMENT_WITH_BLOCKER -->(?:\r?\n|\Z)", body)
    ):
        return "COMMENT_WITH_BLOCKER"
    return None


def _marker(snapshot: Mapping[str, Any]) -> str:
    binding = {
        "repository": snapshot["repository"],
        "pull_request": snapshot["pull_request"],
        "base_ref": snapshot["base_ref"],
        "base_sha": snapshot["base_sha"],
        "head_sha": snapshot["head_sha"],
        "tree_sha": snapshot["tree_sha"],
        "merge_commit_sha": snapshot["merge_commit_sha"],
        "reviewed_scope": snapshot["changed_paths"],
        "requested_reviewers": snapshot["requested_reviewers"],
        "requested_reviewer_requested_at": snapshot["requested_reviewer_requested_at"],
        "requested_reviewer_request_event_ids": snapshot["requested_reviewer_request_event_ids"],
        "requested_teams": snapshot["requested_teams"],
        "requested_team_requested_at": snapshot["requested_team_requested_at"],
        "requested_team_request_event_ids": snapshot["requested_team_request_event_ids"],
        "diff_sha256": snapshot["diff_sha256"],
    }
    encoded = json.dumps(binding, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "<!-- qikvrt-requested-review-lifecycle:" + hashlib.sha256(encoded).hexdigest() + " -->"


def _binding(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "repository": snapshot["repository"],
        "pull_request": snapshot["pull_request"],
        "base_ref": snapshot["base_ref"],
        "base_sha": snapshot["base_sha"],
        "head_sha": snapshot["head_sha"],
        "tree_sha": snapshot["tree_sha"],
        "merge_commit_sha": snapshot["merge_commit_sha"],
        "reviewed_scope": snapshot["changed_paths"],
        "diff_sha256": snapshot["diff_sha256"],
        "diff_bytes": snapshot["diff_bytes"],
        "comment_count": len(snapshot["comments"]),
        "requested_reviewers": snapshot["requested_reviewers"],
        "requested_reviewer_requested_at": snapshot["requested_reviewer_requested_at"],
        "requested_reviewer_request_event_ids": snapshot["requested_reviewer_request_event_ids"],
        "active_requested_reviewers": snapshot["active_requested_reviewers"],
        "requested_teams": snapshot["requested_teams"],
        "requested_team_requested_at": snapshot["requested_team_requested_at"],
        "requested_team_request_event_ids": snapshot["requested_team_request_event_ids"],
        "active_requested_teams": snapshot["active_requested_teams"],
    }


def _recorded_lifecycle_marker(snapshot: Mapping[str, Any], marker: str) -> bool:
    """Return whether an authenticated exact-head lifecycle marker exists."""
    for review in snapshot["existing_lifecycle_reviews"]:
        state = review.get("state")
        commit_id = review.get("commit_id")
        body = review.get("body")
        if state != "COMMENTED" or commit_id != snapshot["head_sha"] or not isinstance(body, str):
            continue
        try:
            login = _review_login(review)
        except ReviewLifecycleBlock:
            continue
        if login.casefold() in LIFECYCLE_MARKER_ACTORS and marker in body:
            return True
    return False


def _observed_exact_head_review_states(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expose raw platform review states without inventing one aggregate state."""
    eligible = {reviewer.casefold() for reviewer in snapshot["requested_reviewers"]}
    observed: list[dict[str, Any]] = []
    for review in snapshot["reviews"]:
        if review.get("commit_id") != snapshot["head_sha"]:
            continue
        try:
            reviewer = _review_login(review)
        except ReviewLifecycleBlock:
            continue
        if reviewer.casefold() not in eligible:
            continue
        state = review.get("state")
        if not isinstance(state, str) or not state:
            continue
        value: dict[str, Any] = {"reviewer": reviewer, "state": state}
        review_id = review.get("id")
        if isinstance(review_id, int) and not isinstance(review_id, bool):
            value["id"] = review_id
        submitted_at = review.get("submitted_at")
        if isinstance(submitted_at, str) and submitted_at:
            value["submitted_at"] = submitted_at
        observed.append(value)
    return sorted(
        observed,
        key=lambda item: (
            item["reviewer"].casefold(),
            str(item.get("submitted_at", "")),
            int(item.get("id", 0)),
        ),
    )


def _next_action(failure_class: str) -> str:
    if failure_class in {
        "BASE_DRIFT",
        "BASE_REF_DRIFT",
        "BASE_REF_RESOLUTION_DRIFT",
        "HEAD_DRIFT",
        "TREE_DRIFT",
        "MERGE_CONTEXT_DRIFT",
        "PR_ACTIVITY_DRIFT",
        "PULL_REQUEST_NOT_OPEN",
    }:
        return "Reobserve the current open pull request before any lifecycle write."
    if failure_class == "OBSERVED_CANDIDATE_GATE_PENDING_OR_ADVERSE":
        return "Wait for or repair the first observed non-green candidate gate, then reobserve."
    if failure_class == "UNSUPPORTED_REQUESTED_TEAM_REVIEWER":
        return "Define and verify a repository member-to-account mapping for the requested team."
    if failure_class == "REQUESTED_REVIEW_REQUEST_TIME_UNAVAILABLE":
        return "Reobserve complete requested-review event history before accepting a disposition."
    if failure_class == "UNSUPPORTED_AUTOMATION_REQUESTED_REVIEWER":
        return "Request a human or governed account reviewer; an automation signer cannot satisfy review."
    if failure_class == "MERGE_CONTEXT_UNAVAILABLE":
        return "Wait for GitHub to expose a current test-merge context, then reobserve exact gates."
    return "A requested eligible GitHub reviewer must record an exact-head substantive disposition."


def _block(
    snapshot: Mapping[str, Any],
    failure_class: str,
    detail: str,
    *,
    persistable: bool = True,
    first_non_green_gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    marker = _marker(snapshot)
    return {
        "schema": "qikvrt_requested_review_lifecycle_decision_v1",
        "state": "BLOCK",
        "persistable": persistable,
        "disposition": "COMMENT_WITH_BLOCKER",
        "first_blocker": failure_class,
        "detail": detail,
        **_binding(snapshot),
        "findings": [{"class": failure_class, "detail": detail}],
        "lifecycle_review_state": "BLOCKED",
        "observed_exact_head_review_states": _observed_exact_head_review_states(snapshot),
        "review_marker": marker,
        "binding_sha256": marker.removeprefix("<!-- qikvrt-requested-review-lifecycle:").removesuffix(" -->"),
        "review_already_recorded": _recorded_lifecycle_marker(snapshot, marker),
        "next_action": _next_action(failure_class),
        "first_non_green_gate": dict(first_non_green_gate) if first_non_green_gate else None,
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def _not_applicable(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "qikvrt_requested_review_lifecycle_decision_v1",
        "state": "NOT_APPLICABLE",
        "persistable": False,
        "disposition": None,
        "first_blocker": None,
        "detail": "no active or historically observed requested reviewer is bound to this pull request",
        **_binding(snapshot),
        "findings": [],
        "lifecycle_review_state": "NOT_REQUESTED",
        "observed_exact_head_review_states": _observed_exact_head_review_states(snapshot),
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def _recorded(snapshot: Mapping[str, Any], review: Mapping[str, Any], disposition: str) -> dict[str, Any]:
    reviewer = _review_login(review)
    platform_state = str(review["state"])
    detail = f"requested reviewer {reviewer} recorded {disposition} on the exact candidate head"
    return {
        "schema": "qikvrt_requested_review_lifecycle_decision_v1",
        "state": "REVIEW_RECORDED",
        "persistable": False,
        "disposition": disposition,
        "first_blocker": None,
        "detail": detail,
        **_binding(snapshot),
        "findings": [{"class": "REVIEW_DISPOSITION_RECORDED", "detail": detail}],
        "lifecycle_review_state": "REVIEW_RECORDED",
        "platform_review_state": platform_state,
        "observed_exact_head_review_states": _observed_exact_head_review_states(snapshot),
        "reviewer": reviewer,
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def _latest_review_per_reviewer(
    reviews: Sequence[Mapping[str, Any]],
    head: str,
    eligible: set[str],
    requested_at: Mapping[str, tuple[str, datetime]],
) -> list[Mapping[str, Any]]:
    """Return each reviewer's latest still-valid substantive disposition.

    An ordinary later ``COMMENTED`` review is not a GitHub dismissal of an
    earlier approval or request for changes.  It must not silently erase a
    substantive disposition.  A later ``DISMISSED`` review, however, is an
    explicit invalidation signal and blocks the older disposition until a new
    substantive exact-head review follows it.
    """
    latest_substantive: dict[str, tuple[tuple[datetime, int], Mapping[str, Any]]] = {}
    latest_dismissal: dict[str, tuple[tuple[datetime, int], Mapping[str, Any]]] = {}
    for review in reviews:
        if review.get("commit_id") != head:
            continue
        login = _review_login(review)
        normalized_login = login.casefold()
        if normalized_login not in eligible or normalized_login in AUTOMATION_REVIEW_ACTORS:
            continue
        try:
            submitted_at = _timestamp(review.get("submitted_at"), "review submitted_at")
        except ReviewLifecycleBlock:
            continue
        if submitted_at <= requested_at[normalized_login][1]:
            # GitHub timestamps have finite precision. A review at the same
            # timestamp cannot prove that it followed the current/re-requested
            # request, so it is fail-closed evidence about an older or
            # indeterminate lifecycle only.
            continue
        review_id = review.get("id")
        if isinstance(review_id, bool) or not isinstance(review_id, int):
            review_id = 0
        # Compare timezone-aware datetimes, not their rendered strings: lexical
        # offset ordering can invert real chronology (for example +02:00).
        order = (submitted_at, review_id)
        if _review_disposition(review) is not None:
            if (
                normalized_login not in latest_substantive
                or order > latest_substantive[normalized_login][0]
            ):
                latest_substantive[normalized_login] = (order, review)
        elif review.get("state") == "DISMISSED":
            if (
                normalized_login not in latest_dismissal
                or order > latest_dismissal[normalized_login][0]
            ):
                latest_dismissal[normalized_login] = (order, review)

    valid: list[tuple[tuple[datetime, int], Mapping[str, Any]]] = []
    for login, substantive in latest_substantive.items():
        dismissal = latest_dismissal.get(login)
        if dismissal is not None and dismissal[0] >= substantive[0]:
            continue
        valid.append(substantive)
    return [entry[1] for entry in sorted(valid, key=lambda entry: entry[0], reverse=True)]


def _gate_observations(
    value: Any,
    *,
    head: str,
    test_merge: str | None,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, Mapping) for item in value):
        raise ReviewLifecycleBlock("gate_observations must be a list of objects")
    normalized: list[dict[str, Any]] = []
    for item in value:
        kind = item.get("kind")
        context = item.get("context")
        name = item.get("name")
        if kind not in {"check_run", "legacy_status"}:
            raise ReviewLifecycleBlock("gate observation kind is unsupported")
        if context not in {"head", "test_merge"}:
            raise ReviewLifecycleBlock("gate observation context is unsupported")
        observed_sha = _sha(item.get("sha"), "gate observation sha")
        expected_sha = head if context == "head" else test_merge
        if expected_sha is None:
            raise ReviewLifecycleBlock(
                "test-merge gate observation exists while the candidate test-merge SHA is unavailable"
            )
        if observed_sha != expected_sha:
            raise ReviewLifecycleBlock(
                f"{context} gate observation sha does not match the bound candidate context"
            )
        if not isinstance(name, str) or not name:
            raise ReviewLifecycleBlock("gate observation name is missing")
        observed = dict(item)
        if kind == "check_run":
            if not isinstance(item.get("status"), str) or not item["status"]:
                raise ReviewLifecycleBlock("check-run gate status is missing")
            conclusion = item.get("conclusion")
            if conclusion is not None and not isinstance(conclusion, str):
                raise ReviewLifecycleBlock("check-run gate conclusion is malformed")
        else:
            if not isinstance(item.get("state"), str) or not item["state"]:
                raise ReviewLifecycleBlock("legacy-status gate state is missing")
        for url_field in ("details_url", "target_url"):
            if url_field in item and item[url_field] is not None and not isinstance(item[url_field], str):
                raise ReviewLifecycleBlock(f"gate observation {url_field} is malformed")
        normalized.append(observed)
    return sorted(
        normalized,
        key=lambda item: (
            item["context"],
            item["kind"],
            item["name"].casefold(),
            str(item.get("id", "")),
        ),
    )


def _gate_is_green(gate: Mapping[str, Any]) -> bool:
    if gate["kind"] == "check_run":
        return gate.get("status") == "completed" and gate.get("conclusion") in {"success", "skipped"}
    return gate.get("state") == "success"


def _gate_detail(gate: Mapping[str, Any] | None) -> str:
    if gate is None:
        return "no check run or legacy status was observed on either exact candidate gate context"
    if gate["kind"] == "check_run":
        outcome = f"status={gate.get('status')!r}, conclusion={gate.get('conclusion')!r}"
        url = gate.get("details_url")
    else:
        outcome = f"state={gate.get('state')!r}"
        url = gate.get("target_url")
    suffix = f", url={url}" if isinstance(url, str) and url else ""
    return (
        f"first non-green {gate['context']} {gate['kind']} {gate['name']!r} "
        f"on {gate['sha']}: {outcome}{suffix}"
    )


def evaluate_review_lifecycle(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Return one exact, non-impersonating requested-review disposition."""
    if not isinstance(snapshot, Mapping):
        raise ReviewLifecycleBlock("snapshot must be an object")
    repository = snapshot.get("repository")
    if not isinstance(repository, str) or "/" not in repository:
        raise ReviewLifecycleBlock("repository must be owner/name")
    pull_request = snapshot.get("pull_request")
    if isinstance(pull_request, bool) or not isinstance(pull_request, int) or pull_request < 1:
        raise ReviewLifecycleBlock("pull_request must be a positive integer")
    state = snapshot.get("state")
    current_state = snapshot.get("current_state")
    if not isinstance(state, str) or not state:
        raise ReviewLifecycleBlock("state must be a non-empty string")
    if not isinstance(current_state, str) or not current_state:
        raise ReviewLifecycleBlock("current_state must be a non-empty string")
    base_ref = snapshot.get("base_ref")
    if not isinstance(base_ref, str) or not base_ref:
        raise ReviewLifecycleBlock("base_ref must be a non-empty string")
    current_base_ref = snapshot.get("current_base_ref")
    if not isinstance(current_base_ref, str) or not current_base_ref:
        raise ReviewLifecycleBlock("current_base_ref must be a non-empty string")

    base = _sha(snapshot.get("base_sha"), "base_sha")
    current_base = _sha(snapshot.get("current_base_sha"), "current_base_sha")
    current_pull_request_base = _sha(
        snapshot.get("current_pull_request_base_sha"), "current_pull_request_base_sha"
    )
    head = _sha(snapshot.get("head_sha"), "head_sha")
    current_head = _sha(snapshot.get("current_head_sha"), "current_head_sha")
    tree = _sha(snapshot.get("tree_sha"), "tree_sha")
    current_tree = _sha(snapshot.get("current_tree_sha"), "current_tree_sha")
    merge_commit = _optional_sha(snapshot.get("merge_commit_sha"), "merge_commit_sha")
    current_merge_commit = _optional_sha(
        snapshot.get("current_merge_commit_sha"), "current_merge_commit_sha"
    )
    updated_at = _timestamp(snapshot.get("updated_at"), "updated_at")
    current_updated_at = _timestamp(snapshot.get("current_updated_at"), "current_updated_at")
    active_requested = _strings(snapshot.get("active_requested_reviewers"), "active_requested_reviewers")
    requested_history = _strings(snapshot.get("requested_reviewer_history"), "requested_reviewer_history")
    requested_time_history = _request_times(
        snapshot.get("requested_reviewer_requested_at"), "requested_reviewer_requested_at"
    )
    requested_event_id_history = _request_event_ids(
        snapshot.get("requested_reviewer_request_event_ids"),
        "requested_reviewer_request_event_ids",
    )
    active_teams = _strings(snapshot.get("active_requested_teams"), "active_requested_teams")
    requested_team_history = _strings(
        snapshot.get("requested_team_history"), "requested_team_history"
    )
    requested_team_time_history = _request_times(
        snapshot.get("requested_team_requested_at"), "requested_team_requested_at"
    )
    requested_team_event_id_history = _request_event_ids(
        snapshot.get("requested_team_request_event_ids"),
        "requested_team_request_event_ids",
    )
    changed_paths = _strings(snapshot.get("changed_paths"), "changed_paths")
    diff_sha256 = _sha256(snapshot.get("diff_sha256"), "diff_sha256")
    diff_bytes = snapshot.get("diff_bytes")
    if isinstance(diff_bytes, bool) or not isinstance(diff_bytes, int) or diff_bytes < 0:
        raise ReviewLifecycleBlock("diff_bytes must be a non-negative integer")
    comments = snapshot.get("comments")
    if not isinstance(comments, list) or not all(isinstance(comment, Mapping) for comment in comments):
        raise ReviewLifecycleBlock("comments must be a list of objects")
    reviews = snapshot.get("reviews")
    if not isinstance(reviews, list) or not all(isinstance(review, Mapping) for review in reviews):
        raise ReviewLifecycleBlock("reviews must be a list of objects")
    unresolved_threads = snapshot.get("unresolved_threads")
    if isinstance(unresolved_threads, bool) or not isinstance(unresolved_threads, int) or unresolved_threads < 0:
        raise ReviewLifecycleBlock("unresolved_threads must be a non-negative integer")
    gate_coverage = snapshot.get("gate_coverage")
    if gate_coverage != "OBSERVED_ACTIONS_AND_LEGACY_ONLY":
        raise ReviewLifecycleBlock("gate_coverage is not the supported observed-only value")
    all_observed_gates_green = snapshot.get("all_observed_candidate_gates_terminal_green")
    if not isinstance(all_observed_gates_green, bool):
        raise ReviewLifecycleBlock("all_observed_candidate_gates_terminal_green must be boolean")
    gate_observations = _gate_observations(
        snapshot.get("gate_observations"), head=head, test_merge=merge_commit
    )
    derived_gates_green = bool(gate_observations) and all(
        _gate_is_green(gate) for gate in gate_observations
    )
    if all_observed_gates_green != derived_gates_green:
        raise ReviewLifecycleBlock(
            "all_observed_candidate_gates_terminal_green contradicts gate_observations"
        )
    competing_writer_or_supersession = snapshot.get("competing_writer_or_supersession")
    if not isinstance(competing_writer_or_supersession, bool):
        raise ReviewLifecycleBlock("competing_writer_or_supersession must be boolean")
    lifecycle_reviews = snapshot.get("existing_lifecycle_reviews")
    if not isinstance(lifecycle_reviews, list) or not all(
        isinstance(item, Mapping) for item in lifecycle_reviews
    ):
        raise ReviewLifecycleBlock("existing_lifecycle_reviews must be a list of objects")
    competing_writer_detail = snapshot.get("competing_writer_detail")
    if not isinstance(competing_writer_detail, str) or not competing_writer_detail:
        raise ReviewLifecycleBlock("competing_writer_detail must be a non-empty string")

    requested_by_login: dict[str, str] = {}
    for login in [*active_requested, *requested_history]:
        requested_by_login.setdefault(login.casefold(), login)
    requested_by_team: dict[str, str] = {}
    for team in [*active_teams, *requested_team_history]:
        requested_by_team.setdefault(team.casefold(), team)
    reviewer_times: dict[str, str] = {}
    reviewer_time_values: dict[str, tuple[str, datetime]] = {}
    reviewer_event_ids: dict[str, int] = {}
    missing_request_times: list[str] = []
    for login in requested_by_login.values():
        entry = requested_time_history.get(login.casefold())
        event_id = requested_event_id_history.get(login.casefold())
        if entry is None or event_id is None:
            missing_request_times.append(f"@{login}")
            continue
        reviewer_times[login] = entry[0]
        reviewer_time_values[login.casefold()] = entry
        reviewer_event_ids[login] = event_id
    team_times: dict[str, str] = {}
    team_event_ids: dict[str, int] = {}
    for team in requested_by_team.values():
        entry = requested_team_time_history.get(team.casefold())
        event_id = requested_team_event_id_history.get(team.casefold())
        if entry is None or event_id is None:
            missing_request_times.append(f"@{team}")
            continue
        team_times[team] = entry[0]
        team_event_ids[team] = event_id
    normalized = dict(snapshot)
    normalized.update(
        {
            "repository": repository,
            "pull_request": pull_request,
            "base_ref": base_ref,
            "base_sha": base,
            "head_sha": head,
            "tree_sha": tree,
            "merge_commit_sha": merge_commit,
            "active_requested_reviewers": sorted(set(active_requested), key=str.casefold),
            "requested_reviewers": sorted(requested_by_login.values(), key=str.casefold),
            "requested_reviewer_requested_at": dict(
                sorted(reviewer_times.items(), key=lambda item: item[0].casefold())
            ),
            "requested_reviewer_request_event_ids": dict(
                sorted(reviewer_event_ids.items(), key=lambda item: item[0].casefold())
            ),
            "active_requested_teams": sorted(set(active_teams), key=str.casefold),
            "requested_teams": sorted(requested_by_team.values(), key=str.casefold),
            "requested_team_requested_at": dict(
                sorted(team_times.items(), key=lambda item: item[0].casefold())
            ),
            "requested_team_request_event_ids": dict(
                sorted(team_event_ids.items(), key=lambda item: item[0].casefold())
            ),
            "changed_paths": sorted(set(changed_paths)),
            "diff_sha256": diff_sha256,
            "diff_bytes": diff_bytes,
            "comments": comments,
            "existing_lifecycle_reviews": lifecycle_reviews,
            "competing_writer_detail": competing_writer_detail,
            "gate_observations": gate_observations,
            "gate_coverage": gate_coverage,
        }
    )

    if state != "open" or current_state != "open":
        return _block(
            normalized,
            "PULL_REQUEST_NOT_OPEN",
            f"candidate state={state!r}, current state={current_state!r}; lifecycle writes require an open PR",
            persistable=False,
        )
    if current_pull_request_base != base:
        return _block(
            normalized,
            "BASE_DRIFT",
            f"final pull-request base {current_pull_request_base} != candidate base {base}",
            persistable=False,
        )
    if current_base != current_pull_request_base:
        return _block(
            normalized,
            "BASE_REF_RESOLUTION_DRIFT",
            f"resolved current {base_ref} {current_base} != final pull-request base {current_pull_request_base}",
            persistable=False,
        )
    if current_base_ref != base_ref:
        return _block(
            normalized,
            "BASE_REF_DRIFT",
            f"current base ref {current_base_ref} != candidate base ref {base_ref}",
            persistable=False,
        )
    if current_head != head:
        return _block(
            normalized,
            "HEAD_DRIFT",
            f"current head {current_head} != expected head {head}",
            persistable=False,
        )
    if current_tree != tree:
        return _block(
            normalized,
            "TREE_DRIFT",
            f"current tree {current_tree} != expected tree {tree}",
            persistable=False,
        )
    if updated_at != current_updated_at:
        return _block(
            normalized,
            "PR_ACTIVITY_DRIFT",
            "pull request updated_at changed while snapshot observations were in flight",
            persistable=False,
        )
    if not requested_by_login and not requested_by_team:
        return _not_applicable(normalized)
    if requested_by_team:
        return _block(
            normalized,
            "UNSUPPORTED_REQUESTED_TEAM_REVIEWER",
            "requested GitHub team(s) require a repository-defined member-to-account mapping: "
            + ", ".join(f"@{team}" for team in normalized["requested_teams"]),
        )
    if missing_request_times:
        return _block(
            normalized,
            "REQUESTED_REVIEW_REQUEST_TIME_UNAVAILABLE",
            "no active request-event timestamp is available for " + ", ".join(sorted(missing_request_times)),
        )
    automation_requesters = sorted(
        login for login in requested_by_login.values() if login.casefold() in AUTOMATION_REVIEW_ACTORS
    )
    if automation_requesters:
        return _block(
            normalized,
            "UNSUPPORTED_AUTOMATION_REQUESTED_REVIEWER",
            "automation account(s) cannot satisfy substantive requested review: "
            + ", ".join(f"@{login}" for login in automation_requesters),
        )
    if merge_commit is None or current_merge_commit is None:
        return _block(
            normalized,
            "MERGE_CONTEXT_UNAVAILABLE",
            "GitHub did not expose a stable current test-merge SHA for exact gate observation",
        )
    if current_merge_commit != merge_commit:
        return _block(
            normalized,
            "MERGE_CONTEXT_DRIFT",
            f"current test-merge SHA {current_merge_commit} != observed {merge_commit}",
            persistable=False,
        )
    if competing_writer_or_supersession:
        return _block(
            normalized,
            "COMPETING_WRITER_OR_SUPERSESSION",
            competing_writer_detail,
        )
    if not all_observed_gates_green:
        first_non_green = next(
            (gate for gate in gate_observations if not _gate_is_green(gate)), None
        )
        return _block(
            normalized,
            "OBSERVED_CANDIDATE_GATE_PENDING_OR_ADVERSE",
            _gate_detail(first_non_green),
            first_non_green_gate=first_non_green,
        )
    if unresolved_threads:
        return _block(normalized, "UNRESOLVED_REVIEW_THREADS", f"{unresolved_threads} review thread(s) remain unresolved")

    for review in _latest_review_per_reviewer(
        reviews, head, set(requested_by_login), reviewer_time_values
    ):
        disposition = _review_disposition(review)
        if disposition is not None:
            return _recorded(normalized, review, disposition)

    return _block(
        normalized,
        "REQUESTED_REVIEW_NOT_RECORDED",
        "no requested reviewer has recorded an exact-head substantive disposition",
    )


def _load_snapshot(path: str) -> Mapping[str, Any]:
    if path == "-":
        value = json.load(sys.stdin)
    else:
        value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ReviewLifecycleBlock("snapshot JSON must be an object")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate",))
    parser.add_argument("--input", default="-", help="snapshot JSON file or - for stdin")
    args = parser.parse_args(argv)
    try:
        result = evaluate_review_lifecycle(_load_snapshot(args.input))
    except (OSError, ValueError, json.JSONDecodeError, ReviewLifecycleBlock) as exc:
        result = {
            "schema": "qikvrt_requested_review_lifecycle_decision_v1",
            "state": "BLOCK",
            "persistable": False,
            "disposition": "COMMENT_WITH_BLOCKER",
            "first_blocker": "INVALID_REVIEW_SNAPSHOT",
            "detail": str(exc),
            "findings": [{"class": "INVALID_REVIEW_SNAPSHOT", "detail": str(exc)}],
            "external_effect": "NONE",
            "completion_claims": {
                "PASS": False,
                "FINAL_PASS": False,
                "EFFECT_ACK_DONE": False,
            },
        }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result.get("state") in {"REVIEW_RECORDED", "NOT_APPLICABLE"} else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
