#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Evaluate the live native Code Owner review prerequisite without mutation.

The workflow that calls this module is deliberately limited to observation and
commit-status publication.  It cannot request, submit, dismiss, or fabricate a
GitHub review.  GitHub's branch ruleset remains the merge authority; this
module makes the same prerequisite independently visible to CI and to the
expected-head promotion decision before it can call a merge endpoint.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA = "qikvrt_required_code_owner_review_gate_v1"
DEFAULT_CODE_OWNER = "Goldkelch"
SUCCESS = "success"
PENDING = "pending"
FAILURE = "failure"
DECISIVE_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}


class ReviewGateInputError(ValueError):
    """Raised for malformed live GitHub observation payloads."""


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 40:
        raise ReviewGateInputError(f"{label} is not a Git SHA-1")
    if any(character not in "0123456789abcdef" for character in value):
        raise ReviewGateInputError(f"{label} is not a lowercase hexadecimal Git SHA-1")
    return value


def _login(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReviewGateInputError(f"{label} is missing")
    return value.strip()


def _review_sort_key(review: Mapping[str, Any]) -> tuple[str, int]:
    submitted_at = review.get("submitted_at")
    if not isinstance(submitted_at, str):
        submitted_at = ""
    identifier = review.get("id", -1)
    if isinstance(identifier, bool) or not isinstance(identifier, int):
        identifier = -1
    return submitted_at, identifier


def _block(
    *,
    gate_state: str,
    blocker: str,
    detail: str,
    pr_number: Any,
    head_sha: str | None,
    required_code_owner: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "gate_state": gate_state,
        "first_blocker": blocker,
        "detail": detail,
        "pr_number": pr_number,
        "head_sha": head_sha,
        "required_code_owner": required_code_owner,
        "external_effect": "NONE",
        "review_mutation": "FORBIDDEN",
    }


def native_code_owner_rule_is_enforced(rules: Sequence[Mapping[str, Any]]) -> bool:
    """Return whether a live GitHub ruleset enforces a fresh Code Owner review."""
    for rule in rules:
        if rule.get("type") != "pull_request":
            continue
        parameters = rule.get("parameters")
        if not isinstance(parameters, Mapping):
            continue
        count = parameters.get("required_approving_review_count")
        if isinstance(count, bool) or not isinstance(count, int):
            continue
        if (
            count >= 1
            and parameters.get("require_code_owner_review") is True
            and parameters.get("dismiss_stale_reviews_on_push") is True
            and parameters.get("require_last_push_approval") is True
        ):
            return True
    return False


def evaluate_required_review(
    pr: Mapping[str, Any],
    rules: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    *,
    required_code_owner: str = DEFAULT_CODE_OWNER,
) -> dict[str, Any]:
    """Evaluate one exact-head observation of GitHub rules and reviews.

    A non-success result is deliberately not an approval substitute.  ``pending``
    means a normal review action is still required; ``failure`` means an active
    native rule or observed review disposition is adverse.
    """
    if not isinstance(pr, Mapping):
        raise ReviewGateInputError("pull request observation must be an object")
    if not isinstance(rules, Sequence) or isinstance(rules, (str, bytes)):
        raise ReviewGateInputError("rules observation must be a list")
    if not isinstance(reviews, Sequence) or isinstance(reviews, (str, bytes)):
        raise ReviewGateInputError("reviews observation must be a list")
    if not all(isinstance(rule, Mapping) for rule in rules):
        raise ReviewGateInputError("rules observation contains a non-object")
    if not all(isinstance(review, Mapping) for review in reviews):
        raise ReviewGateInputError("reviews observation contains a non-object")

    head = pr.get("head")
    author = pr.get("user")
    if not isinstance(head, Mapping) or not isinstance(author, Mapping):
        raise ReviewGateInputError("pull request must contain head and user objects")
    head_sha = _sha(head.get("sha"), "pull request head.sha")
    author_login = _login(author.get("login"), "pull request user.login")
    owner_login = _login(required_code_owner, "required code owner")
    pr_number = pr.get("number")

    if not native_code_owner_rule_is_enforced(rules):
        return _block(
            gate_state=FAILURE,
            blocker="CODE_OWNER_RULE_NOT_ENFORCED",
            detail=(
                "main must require one approval, Code Owner review, stale-review dismissal, "
                "and last-push approval"
            ),
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owner=owner_login,
        )

    owner_reviews = [
        review
        for review in reviews
        if isinstance(review.get("user"), Mapping)
        and isinstance(review["user"].get("login"), str)
        and review["user"]["login"].casefold() == owner_login.casefold()
    ]
    if not owner_reviews:
        return _block(
            gate_state=PENDING,
            blocker="CODE_OWNER_REVIEW_MISSING",
            detail=f"no review from @{owner_login} is present",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owner=owner_login,
        )

    exact_head_reviews = [
        review for review in owner_reviews if review.get("commit_id") == head_sha
    ]
    if not exact_head_reviews:
        return _block(
            gate_state=PENDING,
            blocker="CODE_OWNER_REVIEW_STALE",
            detail=f"@{owner_login} has no review bound to current head {head_sha}",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owner=owner_login,
        )

    decisive = [
        review
        for review in exact_head_reviews
        if isinstance(review.get("state"), str)
        and review["state"].upper() in DECISIVE_REVIEW_STATES
    ]
    if not decisive:
        return _block(
            gate_state=PENDING,
            blocker="CODE_OWNER_REVIEW_NOT_APPROVED",
            detail=f"@{owner_login} has no decisive current-head review",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owner=owner_login,
        )

    latest = max(decisive, key=_review_sort_key)
    latest_state = latest["state"].upper()
    if latest_state == "CHANGES_REQUESTED":
        return _block(
            gate_state=FAILURE,
            blocker="CODE_OWNER_REVIEW_CHANGES_REQUESTED",
            detail=f"@{owner_login} requested changes on current head {head_sha}",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owner=owner_login,
        )
    if latest_state == "DISMISSED":
        return _block(
            gate_state=PENDING,
            blocker="CODE_OWNER_REVIEW_DISMISSED",
            detail=f"@{owner_login}'s current-head review was dismissed",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owner=owner_login,
        )
    if latest_state != "APPROVED":
        raise ReviewGateInputError(f"unsupported decisive review state: {latest_state}")
    if author_login.casefold() == owner_login.casefold():
        return _block(
            gate_state=FAILURE,
            blocker="CODE_OWNER_REVIEW_SELF_APPROVAL",
            detail="the pull-request author cannot satisfy the independent Code Owner review gate",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owner=owner_login,
        )

    return {
        "schema": SCHEMA,
        "gate_state": SUCCESS,
        "first_blocker": None,
        "detail": f"@{owner_login} approved the current head",
        "pr_number": pr_number,
        "head_sha": head_sha,
        "required_code_owner": owner_login,
        "review_id": latest.get("id"),
        "external_effect": "NONE",
        "review_mutation": "FORBIDDEN",
    }


def _load_json(path: str) -> Any:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluate", nargs="?", default="evaluate")
    parser.add_argument("--pr", required=True, help="current GitHub pull-request JSON")
    parser.add_argument("--rules", required=True, help="live GitHub rules JSON for main")
    parser.add_argument("--reviews", required=True, help="paginated GitHub reviews JSON")
    parser.add_argument("--required-code-owner", default=DEFAULT_CODE_OWNER)
    args = parser.parse_args(argv)
    try:
        result = evaluate_required_review(
            _load_json(args.pr),
            _load_json(args.rules),
            _load_json(args.reviews),
            required_code_owner=args.required_code_owner,
        )
    except (OSError, ValueError, json.JSONDecodeError, ReviewGateInputError) as exc:
        result = _block(
            gate_state=FAILURE,
            blocker="INVALID_REVIEW_GATE_SNAPSHOT",
            detail=str(exc),
            pr_number=None,
            head_sha=None,
            required_code_owner=args.required_code_owner,
        )
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["gate_state"] == SUCCESS else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
