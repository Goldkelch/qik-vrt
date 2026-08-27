#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Plan and verify a delegated native-account pull-request review.

This module is deliberately network- and secret-free.  Trusted-main workflow
code performs every GitHub read, hands the resulting snapshots to this module,
and supplies a narrowly scoped account credential only in the final signer
job.  The module never receives, serializes, or logs a credential.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA = "qikvrt_delegated_native_account_review_plan_v1"
MARKER = "qikvrt-delegated-native-account-review:v1"
RECEIPT_SCHEMA = "qikvrt_mesh_repository_review_receipt_v1"
DELEGATION_SCHEMA = "qikvrt_owner_native_account_review_automation_v1"
DELEGATION_ID = "OWNER-NATIVE-ACCOUNT-REVIEW-AUTOMATION-V1"
DELEGATION_ACTIVE = "ACTIVE"
REPOSITORIES = ("Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt")
ACCOUNTS = ("Goldkelch", "ingolf-lohmann")
ALLOWED_PERMISSIONS = {"write", "maintain", "admin"}
NO_EFFECT = "NO_EFFECT"
DECISIVE_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
RETRACTION_EVENT_ACTIONS = {
    "pull_request_target": frozenset(
        {
        "opened",
        "edited",
        "converted_to_draft",
        "review_requested",
        "review_request_removed",
        "labeled",
        "unlabeled",
        "synchronize",
        "ready_for_review",
        "reopened",
        }
    ),
    "issue_comment": frozenset({"created", "edited", "deleted"}),
    "workflow_run": frozenset({"completed"}),
}


class NativeAccountReviewError(ValueError):
    """Raised for malformed, incomplete, or non-canonical review evidence."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha1(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise NativeAccountReviewError(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise NativeAccountReviewError(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


def _sha256_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise NativeAccountReviewError(f"{label} is not a SHA-256")
    if any(character not in "0123456789abcdef" for character in value):
        raise NativeAccountReviewError(f"{label} is not lowercase hexadecimal")
    return value


def _login(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise NativeAccountReviewError(f"{label} is missing")
    return value.strip()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise NativeAccountReviewError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise NativeAccountReviewError(f"{label} must be a list")
    return value


def _counterpart(author: str) -> str:
    matches = [account for account in ACCOUNTS if account.casefold() == author.casefold()]
    if len(matches) != 1:
        raise NativeAccountReviewError("PULL_REQUEST_AUTHOR_NOT_CONFIGURED_REPOSITORY_ACCOUNT")
    candidates = [account for account in ACCOUNTS if account.casefold() != author.casefold()]
    if len(candidates) != 1:
        raise NativeAccountReviewError("REPOSITORY_REVIEWER_COUNTERPART_AMBIGUOUS")
    return candidates[0]


def _review_event(disposition: str) -> str:
    return {
        "APPROVE": "APPROVE",
        "REQUEST_CHANGES": "REQUEST_CHANGES",
        # A mere COMMENT leaves a prior same-head APPROVED review decisive in
        # GitHub's native review state.  A fresh technical blocker must instead
        # supersede it with the negative native state, never transfer it.
        "COMMENT_WITH_BLOCKER": "REQUEST_CHANGES",
        "WAIT": NO_EFFECT,
    }.get(disposition, NO_EFFECT)


def _base_plan(
    *,
    repository: str,
    pr_number: int | None,
    expected_base: str | None,
    expected_head: str | None,
    expected_tree: str | None,
    fingerprint: str | None,
    first_blocker: str | None,
    detail: str,
    delegation_state: str | None = None,
    delegation_sha256: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "repository": repository,
        "pr_number": pr_number,
        "base_sha": expected_base,
        "head_sha": expected_head,
        "tree_sha": expected_tree,
        "evidence_fingerprint": fingerprint,
        "reviewer": None,
        "event": NO_EFFECT,
        "effect_permitted": False,
        "first_blocker": first_blocker,
        "detail": detail,
        "review_body": None,
        "manual_review_preserved": True,
        "stale_approval_retraction": False,
        "retraction_only": False,
        "active_requested_counterpart_required": False,
        "delegation": "DELEGATED_NATIVE_ACCOUNT_AUTOMATION",
        "delegation_state": delegation_state,
        "delegation_sha256": delegation_sha256,
        "independent_natural_person_review": False,
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }


def _delegation_info(delegation: Mapping[str, Any], repository: str) -> dict[str, str]:
    """Validate the trusted-main owner delegation without accepting a secret."""
    value = _mapping(delegation, "owner delegation")
    if value.get("schema") != DELEGATION_SCHEMA or value.get("delegation_id") != DELEGATION_ID:
        raise NativeAccountReviewError("DELEGATION_SCHEMA_OR_ID_INVALID")
    state = value.get("state")
    if state != DELEGATION_ACTIVE:
        raise NativeAccountReviewError("DELEGATION_REVOKED_OR_INACTIVE")
    repositories = _list(value.get("repositories"), "owner delegation repositories")
    if not all(isinstance(item, str) for item in repositories):
        raise NativeAccountReviewError("DELEGATION_REPOSITORY_SCOPE_INVALID")
    if sorted(repositories) != sorted(REPOSITORIES) or repository not in repositories:
        raise NativeAccountReviewError("DELEGATION_REPOSITORY_SCOPE_INVALID")
    accounts = _list(value.get("configured_platform_accounts"), "owner delegation accounts")
    if not all(isinstance(item, str) for item in accounts):
        raise NativeAccountReviewError("DELEGATION_ACCOUNT_SCOPE_INVALID")
    if sorted(accounts) != sorted(ACCOUNTS):
        raise NativeAccountReviewError("DELEGATION_ACCOUNT_SCOPE_INVALID")
    selection = _mapping(value.get("selection"), "owner delegation selection")
    if (
        selection.get("pull_request_author_is_eligible") is not False
        or selection.get("same_account_self_review") is not False
        or selection.get("chatgpt_native_signing") is not False
        or selection.get("bot_or_app_identity_substitution") is not False
    ):
        raise NativeAccountReviewError("DELEGATION_IDENTITY_BOUNDARY_INVALID")
    return {"state": state, "sha256": _sha256(value)}


def _sealed(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop("plan_sha256", None)
    result["plan_sha256"] = _sha256(result)
    return result


def validate_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a plan artifact before a signer job consumes it."""
    candidate = dict(_mapping(plan, "review plan"))
    if candidate.get("schema") != SCHEMA:
        raise NativeAccountReviewError("native account review plan schema is invalid")
    claimed = _sha256_text(candidate.get("plan_sha256"), "plan_sha256")
    payload = dict(candidate)
    payload.pop("plan_sha256", None)
    if claimed != _sha256(payload):
        raise NativeAccountReviewError("native account review plan seal is invalid")
    repository = candidate.get("repository")
    if repository not in REPOSITORIES:
        raise NativeAccountReviewError("native account review repository is invalid")
    event = candidate.get("event")
    if event not in {NO_EFFECT, "APPROVE", "REQUEST_CHANGES", "COMMENT"}:
        raise NativeAccountReviewError("native account review event is invalid")
    permitted = candidate.get("effect_permitted")
    if not isinstance(permitted, bool) or permitted != (event != NO_EFFECT):
        raise NativeAccountReviewError("native account review effect permission is invalid")
    stale_retraction = candidate.get("stale_approval_retraction")
    retraction_only = candidate.get("retraction_only")
    if not isinstance(stale_retraction, bool) or not isinstance(retraction_only, bool):
        raise NativeAccountReviewError("native account review retraction state is invalid")
    if retraction_only and (event != "REQUEST_CHANGES" or not stale_retraction):
        raise NativeAccountReviewError("native account review retraction-only state is invalid")
    active_request_required = candidate.get("active_requested_counterpart_required")
    if not isinstance(active_request_required, bool) or (
        active_request_required and event != "APPROVE"
    ):
        raise NativeAccountReviewError("native account review active-request state is invalid")
    if event == NO_EFFECT:
        if candidate.get("reviewer") is not None or candidate.get("review_body") is not None:
            raise NativeAccountReviewError("no-effect plan must not select a reviewer or body")
    else:
        if candidate.get("reviewer") not in ACCOUNTS:
            raise NativeAccountReviewError("native account review plan reviewer is invalid")
        _sha1(candidate.get("base_sha"), "plan base_sha")
        _sha1(candidate.get("head_sha"), "plan head_sha")
        _sha1(candidate.get("tree_sha"), "plan tree_sha")
        _sha256_text(candidate.get("evidence_fingerprint"), "plan evidence_fingerprint")
        if not isinstance(candidate.get("review_body"), str) or MARKER not in candidate["review_body"]:
            raise NativeAccountReviewError("native account review body is invalid")
        if candidate.get("delegation_state") != DELEGATION_ACTIVE:
            raise NativeAccountReviewError("native account review delegation is not active")
        _sha256_text(candidate.get("delegation_sha256"), "plan delegation_sha256")
    if candidate.get("delegation") != "DELEGATED_NATIVE_ACCOUNT_AUTOMATION":
        raise NativeAccountReviewError("native account review delegation is invalid")
    if candidate.get("independent_natural_person_review") is not False:
        raise NativeAccountReviewError("native account review must not claim a natural-person review")
    return candidate


def _first_snapshot_error(
    repository: str,
    pr: Mapping[str, Any],
    commit: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    ledger_transport_exact: bool,
    reobservation_exact: bool,
) -> tuple[str | None, dict[str, str | int | None]]:
    values: dict[str, str | int | None] = {
        "base_sha": None,
        "head_sha": None,
        "tree_sha": None,
        "fingerprint": None,
        "pr_number": None,
    }
    if repository not in REPOSITORIES:
        return "FOREIGN_REPOSITORY", values
    if receipt.get("schema") != RECEIPT_SCHEMA:
        return "RECEIPT_SCHEMA_INVALID", values
    try:
        number = receipt.get("pr_number")
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            return "RECEIPT_PR_NUMBER_INVALID", values
        values["pr_number"] = number
        base = _sha1(receipt.get("base_sha"), "receipt base_sha")
        head = _sha1(receipt.get("head_sha"), "receipt head_sha")
        tree = _sha1(receipt.get("tree_sha"), "receipt tree_sha")
        fingerprint = _sha256_text(receipt.get("evidence_fingerprint"), "receipt evidence_fingerprint")
        values.update(base_sha=base, head_sha=head, tree_sha=tree, fingerprint=fingerprint)
    except NativeAccountReviewError:
        return "RECEIPT_BINDING_INVALID", values
    if receipt.get("repository") != repository:
        return "RECEIPT_REPOSITORY_DRIFT", values
    if not ledger_transport_exact:
        return "LEDGER_TRANSPORT_READBACK_MISMATCH", values
    if not reobservation_exact:
        return "CAUSAL_REVIEW_EVIDENCE_DRIFT", values
    if pr.get("state") != "open":
        return "PULL_REQUEST_NOT_OPEN", values
    if pr.get("number") != values["pr_number"]:
        return "PULL_REQUEST_NUMBER_DRIFT", values
    if pr.get("draft") is True:
        return "PULL_REQUEST_DRAFT", values
    base = _mapping(pr.get("base"), "pull request base")
    head = _mapping(pr.get("head"), "pull request head")
    if base.get("ref") != "main":
        return "PULL_REQUEST_BASE_NOT_MAIN", values
    if base.get("sha") != values["base_sha"]:
        return "PULL_REQUEST_BASE_DRIFT", values
    if head.get("sha") != values["head_sha"]:
        return "PULL_REQUEST_HEAD_DRIFT", values
    head_repo = _mapping(head.get("repo"), "pull request head repository")
    if head_repo.get("full_name") != repository:
        return "PULL_REQUEST_HEAD_NOT_ROLE_LOCAL", values
    if commit.get("sha") != values["head_sha"]:
        return "PULL_REQUEST_COMMIT_DRIFT", values
    tree = _mapping(commit.get("tree"), "candidate commit tree")
    if tree.get("sha") != values["tree_sha"]:
        return "PULL_REQUEST_TREE_DRIFT", values
    return None, values


def _automated_review_present(
    reviews: Sequence[Mapping[str, Any]], reviewer: str, head: str, fingerprint: str
) -> bool:
    marker = f"fingerprint={fingerprint}"
    for review in reviews:
        if not isinstance(review, Mapping):
            raise NativeAccountReviewError("review observation contains a non-object")
        user = review.get("user")
        if not isinstance(user, Mapping) or not isinstance(user.get("login"), str):
            continue
        if user["login"].casefold() != reviewer.casefold() or review.get("commit_id") != head:
            continue
        body = review.get("body")
        if (
            isinstance(body, str)
            and MARKER in body
            and marker in body
        ):
            return True
    return False


def _manual_target_review_present(
    reviews: Sequence[Mapping[str, Any]], reviewer: str, head: str
) -> bool:
    for review in reviews:
        if not isinstance(review, Mapping):
            raise NativeAccountReviewError("review observation contains a non-object")
        user = review.get("user")
        if not isinstance(user, Mapping) or not isinstance(user.get("login"), str):
            continue
        if user["login"].casefold() != reviewer.casefold() or review.get("commit_id") != head:
            continue
        body = review.get("body")
        if not (isinstance(body, str) and MARKER in body):
            return True
    return False


def _manual_target_decisive_review_present(
    reviews: Sequence[Mapping[str, Any]], reviewer: str, head: str
) -> bool:
    """Only a current unmarked decisive review can supersede a stale auto state."""
    latest = _latest_decisive_target_review(reviews, reviewer, head)
    if latest is None:
        return False
    body = latest.get("body")
    return not (isinstance(body, str) and MARKER in body)


def _latest_decisive_target_review(
    reviews: Sequence[Mapping[str, Any]], reviewer: str, head: str
) -> Mapping[str, Any] | None:
    """Mirror GitHub's current decisive exact-head review state for one user."""
    selected: list[tuple[str, int, Mapping[str, Any]]] = []
    for review in reviews:
        if not isinstance(review, Mapping):
            raise NativeAccountReviewError("review observation contains a non-object")
        user = review.get("user")
        if not isinstance(user, Mapping) or not isinstance(user.get("login"), str):
            continue
        if user["login"].casefold() != reviewer.casefold() or review.get("commit_id") != head:
            continue
        if str(review.get("state") or "").upper() not in DECISIVE_REVIEW_STATES:
            continue
        review_id = review.get("id")
        if isinstance(review_id, bool) or not isinstance(review_id, int) or review_id < 1:
            raise NativeAccountReviewError("decisive target review lacks a valid review id")
        submitted_at = review.get("submitted_at")
        if not isinstance(submitted_at, str):
            submitted_at = ""
        selected.append((submitted_at, review_id, review))
    return max(selected, default=("", 0, None), key=lambda item: item[:2])[2]


def _latest_delegated_review(
    reviews: Sequence[Mapping[str, Any]], reviewer: str, head: str
) -> Mapping[str, Any] | None:
    """Return the latest decisive state only when it is a marked delegation."""
    latest = _latest_decisive_target_review(reviews, reviewer, head)
    if latest is None:
        return None
    body = latest.get("body")
    return latest if isinstance(body, str) and MARKER in body else None


def _stale_delegated_approval_present(
    reviews: Sequence[Mapping[str, Any]], reviewer: str, head: str, fingerprint: str
) -> bool:
    """A retraction needs the currently decisive marked state to be old APPROVED."""
    latest = _latest_delegated_review(reviews, reviewer, head)
    if latest is None:
        return False
    body = latest.get("body")
    return (
        isinstance(body, str)
        and f"fingerprint={fingerprint}" not in body
        and str(latest.get("state") or "").upper() == "APPROVED"
    )


def _exact_retraction_event(intake: Mapping[str, Any]) -> bool:
    """Allow only a pinned native event to retract a stale auto-approval."""
    event_name = intake.get("event_name")
    event_action = intake.get("event_action")
    return (
        isinstance(event_name, str)
        and isinstance(event_action, str)
        and event_action in RETRACTION_EVENT_ACTIONS.get(event_name, ())
    )


def _exact_followup_event(intake: Mapping[str, Any]) -> bool:
    """Accept one trusted exact event that can close a still-live request."""
    event_name = intake.get("event_name")
    event_action = intake.get("event_action")
    if event_name == "workflow_dispatch":
        return event_action == ""
    if event_name == "pull_request_target" and event_action == "review_requested":
        return False
    return _exact_retraction_event(intake)


def plan_native_account_review(
    *,
    repository: str,
    pr: Mapping[str, Any],
    commit: Mapping[str, Any],
    receipt: Mapping[str, Any],
    reviews: Sequence[Mapping[str, Any]],
    delegation: Mapping[str, Any],
    native_rule_enforced: bool,
    ledger_transport_exact: bool,
    reobservation_exact: bool,
) -> dict[str, Any]:
    """Derive one sealed no-effect or exact-account review projection.

    The caller must have retrieved all snapshots using trusted-main code.  A
    false verification bit is intentionally terminal for this projection.
    """
    pr_object = _mapping(pr, "pull request")
    commit_object = _mapping(commit, "candidate commit")
    receipt_object = _mapping(receipt, "review receipt")
    review_list = _list(reviews, "reviews")
    blocker, binding = _first_snapshot_error(
        repository,
        pr_object,
        commit_object,
        receipt_object,
        ledger_transport_exact=ledger_transport_exact,
        reobservation_exact=reobservation_exact,
    )
    if blocker is not None:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"] if isinstance(binding["pr_number"], int) else None,
                expected_base=binding["base_sha"] if isinstance(binding["base_sha"], str) else None,
                expected_head=binding["head_sha"] if isinstance(binding["head_sha"], str) else None,
                expected_tree=binding["tree_sha"] if isinstance(binding["tree_sha"], str) else None,
                fingerprint=binding["fingerprint"] if isinstance(binding["fingerprint"], str) else None,
                first_blocker=blocker,
                detail="native account review remains fail-closed until the exact receipt binding is restored",
            )
        )
    assert isinstance(binding["pr_number"], int)
    assert isinstance(binding["base_sha"], str)
    assert isinstance(binding["head_sha"], str)
    assert isinstance(binding["tree_sha"], str)
    assert isinstance(binding["fingerprint"], str)
    author = _login(_mapping(pr_object.get("user"), "pull request author").get("login"), "pull request author login")
    try:
        reviewer = _counterpart(author)
    except NativeAccountReviewError as exc:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker=str(exc),
                detail="the native-account counterpart is not uniquely determined",
            )
        )

    try:
        delegation_info = _delegation_info(delegation, repository)
    except NativeAccountReviewError as exc:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker=str(exc),
                detail="the owner delegation does not currently permit a native-account projection",
            )
        )

    intake = receipt_object.get("review_intake")
    disposition = receipt_object.get("state")
    event = _review_event(disposition) if isinstance(disposition, str) else NO_EFFECT
    if not isinstance(intake, Mapping):
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="REVIEW_INTAKE_INVALID",
                detail="a delegated native-account projection requires a receipt-bound review intake",
            )
        )
    target = intake.get("requested_reviewer")
    exact_requested_event = (
        intake.get("event_name") == "pull_request_target"
        and intake.get("event_action") == "review_requested"
        and intake.get("requested_target_observed") is True
        and isinstance(target, str)
        and target.casefold() == reviewer.casefold()
    )
    requested_reviewers = pr_object.get("requested_reviewers")
    live_requested_counterpart = (
        isinstance(requested_reviewers, list)
        and any(
            isinstance(item, Mapping)
            and isinstance(item.get("login"), str)
            and item["login"].casefold() == reviewer.casefold()
            for item in requested_reviewers
        )
    )
    exact_active_request = exact_requested_event or (
        live_requested_counterpart and _exact_followup_event(intake)
    )
    stale_delegated_approval = _stale_delegated_approval_present(
        review_list, reviewer, binding["head_sha"], binding["fingerprint"]
    )
    retraction_only = False
    if (
        stale_delegated_approval
        and _exact_retraction_event(intake)
        and not exact_active_request
    ):
        # Once the counterpart is no longer actively requested, a later exact
        # receipt cannot renew an approval.  Its only native-account effect is
        # to neutralize the marked old approval that would otherwise persist.
        event = "REQUEST_CHANGES"
        retraction_only = True
    elif event == NO_EFFECT and stale_delegated_approval and _exact_retraction_event(intake):
        # Even an otherwise non-decisive current receipt must not leave the
        # old approval decisive while evidence is being reobserved.
        event = "REQUEST_CHANGES"
        retraction_only = True
    if event == "APPROVE" and not exact_active_request:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker=(
                    "REQUESTED_REVIEWER_NOT_COUNTERPART"
                    if intake.get("event_action") == "review_requested" and isinstance(target, str)
                    else "REVIEW_REQUEST_EVENT_NOT_EXACT"
                ),
                detail="a delegated native approval requires either the exact request event or a trusted exact follow-up while the counterpart remains requested",
            )
        )
    if event == "REQUEST_CHANGES" and not exact_active_request and not retraction_only:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="RETRACTION_EVENT_NOT_EXACT",
                detail="a non-requested negative projection is allowed only to retract a stale delegated approval after an exact trusted native event",
            )
        )
    if event == NO_EFFECT:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="MESH_DISPOSITION_NOT_DECISIVE",
                detail="a WAIT or unknown technical disposition cannot create a native account review",
            )
        )
    if event == "APPROVE" and native_rule_enforced is not True:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="CODE_OWNER_RULE_NOT_ENFORCED",
                detail="native approval is forbidden until the platform requires a fresh Code Owner approval",
            )
        )
    if _automated_review_present(
        review_list, reviewer, binding["head_sha"], binding["fingerprint"]
    ):
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="IDENTICAL_DELEGATED_ACCOUNT_REVIEW_ALREADY_PRESENT",
                detail="the exact delegated account projection is already present",
            )
        )
    if not stale_delegated_approval and _manual_target_review_present(
        review_list, reviewer, binding["head_sha"]
    ):
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="MANUAL_TARGET_REVIEW_PRESENT",
                detail="an existing unmarked exact-head review by the target account is preserved",
            )
        )

    body = "\n".join(
        [
            f"<!-- {MARKER} fingerprint={binding['fingerprint']} head={binding['head_sha']} tree={binding['tree_sha']} event={event} -->",
            "QIKVRT delegated native-account review.",
            "",
            f"- exact base: `{binding['base_sha']}`",
            f"- exact head: `{binding['head_sha']}`",
            f"- exact tree: `{binding['tree_sha']}`",
            f"- evidence fingerprint: `{binding['fingerprint']}`",
            f"- technical disposition: `{disposition}`",
            f"- platform signer requested: `{reviewer}`",
            "- signer mode: `DELEGATED_NATIVE_ACCOUNT_AUTOMATION`",
            f"- stale delegated approval observed at plan: `{str(stale_delegated_approval).lower()}`",
            f"- retraction-only projection: `{str(retraction_only).lower()}`",
            "",
            "This is a transparently delegated platform-account action, not an independent natural-person review. It does not authorize merge, deployment, publication, PASS, FINAL_PASS, or EFFECT_ACK_DONE.",
        ]
    )
    return _sealed(
        {
            **_base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker=None,
                detail=(
                    "a later exact receipt retracts a stale delegated same-head approval"
                    if stale_delegated_approval
                    else "all trusted-main exact evidence permits one delegated counterpart review projection"
                ),
            ),
            "reviewer": reviewer,
            "event": event,
            "effect_permitted": True,
            "review_body": body,
            "stale_approval_retraction": stale_delegated_approval,
            "retraction_only": retraction_only,
            "active_requested_counterpart_required": event == "APPROVE",
            "delegation_state": delegation_info["state"],
            "delegation_sha256": delegation_info["sha256"],
        }
    )


def signer_preflight(
    *,
    plan: Mapping[str, Any],
    expected_signer: str,
    pr: Mapping[str, Any],
    commit: Mapping[str, Any],
    reviews: Sequence[Mapping[str, Any]],
    delegation: Mapping[str, Any],
    token_user: Mapping[str, Any],
    collaborator_permission: str | None,
    native_rule_enforced: bool,
    reobservation_exact: bool,
) -> dict[str, Any]:
    """Revalidate an effect plan immediately before the only review mutation."""
    value = validate_plan(plan)
    if expected_signer not in ACCOUNTS:
        raise NativeAccountReviewError("expected signer is not configured")
    if value["event"] == NO_EFFECT:
        return {"action": NO_EFFECT, "first_blocker": value.get("first_blocker"), "plan_sha256": value["plan_sha256"]}
    if value["reviewer"] != expected_signer:
        return {"action": NO_EFFECT, "first_blocker": "SIGNER_JOB_TARGET_MISMATCH", "plan_sha256": value["plan_sha256"]}
    try:
        delegation_info = _delegation_info(delegation, value["repository"])
    except NativeAccountReviewError as exc:
        return {"action": NO_EFFECT, "first_blocker": str(exc), "plan_sha256": value["plan_sha256"]}
    if delegation_info["sha256"] != value.get("delegation_sha256"):
        return {"action": NO_EFFECT, "first_blocker": "PRE_EFFECT_DELEGATION_DRIFT", "plan_sha256": value["plan_sha256"]}
    if reobservation_exact is not True:
        return {"action": NO_EFFECT, "first_blocker": "PRE_EFFECT_CAUSAL_REOBSERVATION_DRIFT", "plan_sha256": value["plan_sha256"]}
    if value["event"] == "APPROVE" and native_rule_enforced is not True:
        return {"action": NO_EFFECT, "first_blocker": "CODE_OWNER_RULE_NOT_ENFORCED", "plan_sha256": value["plan_sha256"]}
    user = _mapping(token_user, "token user")
    login = user.get("login")
    if not isinstance(login, str) or login != expected_signer or user.get("type") != "User":
        return {"action": NO_EFFECT, "first_blocker": "DELEGATED_ACCOUNT_TOKEN_IDENTITY_MISMATCH", "plan_sha256": value["plan_sha256"]}
    if collaborator_permission not in ALLOWED_PERMISSIONS:
        return {"action": NO_EFFECT, "first_blocker": "DELEGATED_ACCOUNT_PERMISSION_INSUFFICIENT", "plan_sha256": value["plan_sha256"]}
    pr_object = _mapping(pr, "pull request")
    commit_object = _mapping(commit, "candidate commit")
    if (
        pr_object.get("state") != "open"
        or pr_object.get("draft") is True
        or pr_object.get("number") != value["pr_number"]
        or _mapping(pr_object.get("base"), "pull request base").get("ref") != "main"
        or _mapping(pr_object.get("base"), "pull request base").get("sha") != value["base_sha"]
        or _mapping(pr_object.get("head"), "pull request head").get("sha") != value["head_sha"]
        or _mapping(_mapping(pr_object.get("head"), "pull request head").get("repo"), "pull request head repository").get("full_name") != value["repository"]
        or commit_object.get("sha") != value["head_sha"]
        or _mapping(commit_object.get("tree"), "candidate commit tree").get("sha") != value["tree_sha"]
    ):
        return {"action": NO_EFFECT, "first_blocker": "PRE_EFFECT_EXACT_BINDING_DRIFT", "plan_sha256": value["plan_sha256"]}
    author = _login(_mapping(pr_object.get("user"), "pull request author").get("login"), "pull request author login")
    if author.casefold() == expected_signer.casefold() or _counterpart(author) != expected_signer:
        return {"action": NO_EFFECT, "first_blocker": "PRE_EFFECT_SELF_REVIEW_OR_COUNTERPART_DRIFT", "plan_sha256": value["plan_sha256"]}
    if value["active_requested_counterpart_required"]:
        requested_reviewers = pr_object.get("requested_reviewers")
        if not isinstance(requested_reviewers, list) or not any(
            isinstance(item, Mapping)
            and isinstance(item.get("login"), str)
            and item["login"].casefold() == expected_signer.casefold()
            for item in requested_reviewers
        ):
            return {
                "action": NO_EFFECT,
                "first_blocker": "PRE_EFFECT_REQUESTED_REVIEWER_DRIFT",
                "plan_sha256": value["plan_sha256"],
            }
    review_list = _list(reviews, "reviews")
    if value["stale_approval_retraction"] and _manual_target_decisive_review_present(
        review_list, expected_signer, value["head_sha"]
    ):
        return {
            "action": NO_EFFECT,
            "first_blocker": "MANUAL_TARGET_DECISIVE_REVIEW_PRESENT",
            "plan_sha256": value["plan_sha256"],
        }
    if value["retraction_only"] and not _stale_delegated_approval_present(
        review_list, expected_signer, value["head_sha"], value["evidence_fingerprint"]
    ):
        return {
            "action": NO_EFFECT,
            "first_blocker": "STALE_DELEGATED_APPROVAL_NO_LONGER_DECISIVE",
            "plan_sha256": value["plan_sha256"],
        }
    if _automated_review_present(
        review_list, expected_signer, value["head_sha"], value["evidence_fingerprint"]
    ):
        return {"action": NO_EFFECT, "first_blocker": "IDENTICAL_DELEGATED_ACCOUNT_REVIEW_ALREADY_PRESENT", "plan_sha256": value["plan_sha256"]}
    if not value["stale_approval_retraction"] and _manual_target_review_present(
        review_list, expected_signer, value["head_sha"]
    ):
        return {"action": NO_EFFECT, "first_blocker": "MANUAL_TARGET_REVIEW_PRESENT", "plan_sha256": value["plan_sha256"]}
    return {
        "action": "POST",
        "event": value["event"],
        "reviewer": expected_signer,
        "commit_id": value["head_sha"],
        "body": value["review_body"],
        "plan_sha256": value["plan_sha256"],
    }


def verify_review_readback(
    *, plan: Mapping[str, Any], review: Mapping[str, Any], expected_signer: str
) -> dict[str, Any]:
    """Verify the API response before it is treated as a projection receipt."""
    value = validate_plan(plan)
    observed = _mapping(review, "submitted review")
    if value["event"] == NO_EFFECT or expected_signer != value.get("reviewer"):
        return {"exact": False, "first_blocker": "READBACK_PLAN_NOT_EFFECTFUL"}
    user = _mapping(observed.get("user"), "submitted review user")
    state = observed.get("state")
    expected_state = {
        "COMMENT": "COMMENTED",
        "APPROVE": "APPROVED",
        "REQUEST_CHANGES": "CHANGES_REQUESTED",
    }[value["event"]]
    exact = (
        user.get("login") == expected_signer
        and user.get("type") == "User"
        and observed.get("commit_id") == value["head_sha"]
        and state == expected_state
        and isinstance(observed.get("body"), str)
        and MARKER in observed["body"]
        and f"fingerprint={value['evidence_fingerprint']}" in observed["body"]
    )
    return {
        "exact": exact,
        "first_blocker": None if exact else "DELEGATED_ACCOUNT_REVIEW_READBACK_MISMATCH",
        "review_id": observed.get("id"),
        "reviewer": user.get("login"),
        "commit_id": observed.get("commit_id"),
        "state": state,
        "plan_sha256": value["plan_sha256"],
    }


def _load(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    plan_parser = commands.add_parser("plan")
    plan_parser.add_argument("--repository", required=True)
    plan_parser.add_argument("--pr", required=True)
    plan_parser.add_argument("--commit", required=True)
    plan_parser.add_argument("--receipt", required=True)
    plan_parser.add_argument("--reviews", required=True)
    plan_parser.add_argument("--delegation", required=True)
    plan_parser.add_argument("--native-rule-enforced", choices=("true", "false"), required=True)
    plan_parser.add_argument("--ledger-transport-exact", choices=("true", "false"), required=True)
    plan_parser.add_argument("--reobservation-exact", choices=("true", "false"), required=True)
    signer_parser = commands.add_parser("signer-preflight")
    signer_parser.add_argument("--plan", required=True)
    signer_parser.add_argument("--expected-signer", required=True)
    signer_parser.add_argument("--pr", required=True)
    signer_parser.add_argument("--commit", required=True)
    signer_parser.add_argument("--reviews", required=True)
    signer_parser.add_argument("--delegation", required=True)
    signer_parser.add_argument("--token-user", required=True)
    signer_parser.add_argument("--collaborator-permission", default="")
    signer_parser.add_argument("--native-rule-enforced", choices=("true", "false"), required=True)
    signer_parser.add_argument("--reobservation-exact", choices=("true", "false"), required=True)
    readback_parser = commands.add_parser("verify-readback")
    readback_parser.add_argument("--plan", required=True)
    readback_parser.add_argument("--review", required=True)
    readback_parser.add_argument("--expected-signer", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            result = plan_native_account_review(
                repository=args.repository,
                pr=_load(args.pr),
                commit=_load(args.commit),
                receipt=_load(args.receipt),
                reviews=_load(args.reviews),
                delegation=_load(args.delegation),
                native_rule_enforced=args.native_rule_enforced == "true",
                ledger_transport_exact=args.ledger_transport_exact == "true",
                reobservation_exact=args.reobservation_exact == "true",
            )
        elif args.command == "signer-preflight":
            result = signer_preflight(
                plan=_load(args.plan),
                expected_signer=args.expected_signer,
                pr=_load(args.pr),
                commit=_load(args.commit),
                reviews=_load(args.reviews),
                delegation=_load(args.delegation),
                token_user=_load(args.token_user),
                collaborator_permission=args.collaborator_permission or None,
                native_rule_enforced=args.native_rule_enforced == "true",
                reobservation_exact=args.reobservation_exact == "true",
            )
        else:
            result = verify_review_readback(
                plan=_load(args.plan),
                review=_load(args.review),
                expected_signer=args.expected_signer,
            )
    except (OSError, TypeError, ValueError, json.JSONDecodeError, NativeAccountReviewError) as exc:
        result = {"schema": SCHEMA, "state": "HOLD_UNVERIFIED", "first_blocker": str(exc)}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
