#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Evaluate the live native Code Owner review prerequisite without mutation."""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import urllib.parse
from collections.abc import Mapping, Sequence
from typing import Any

SCHEMA = "qikvrt_required_code_owner_review_gate_v1"
DEFAULT_CODE_OWNERS = ("Goldkelch", "ingolf-lohmann")
SUCCESS = "success"
PENDING = "pending"
FAILURE = "failure"
STATUS_PUBLICATION_NOOP = "NOOP"
STATUS_PUBLICATION_WRITE = "WRITE"
DECISIVE_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
SELECTION_SCHEMA = "qikvrt_required_code_owner_review_selection_v1"
REQUIRED_NATIVE_STATUS_CHECKS = {
    ("test", 15368),
    ("QIKVRT required code-owner review", 15368),
}


class ReviewGateInputError(ValueError):
    pass


def _positive_pr_number(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdecimal():
            number = int(text)
            return number if number > 0 else None
    return None


def _selection(
    state: str,
    *,
    source: str,
    first_blocker: str | None = None,
    pr_numbers: Sequence[int] = (),
    expected_head: str | None = None,
    workflow_run_head: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": SELECTION_SCHEMA,
        "state": state,
        "source": source,
        "first_blocker": first_blocker,
        "pr_numbers": list(pr_numbers),
        "expected_head": expected_head,
        "workflow_run_head": workflow_run_head,
        "status_publication": "FORBIDDEN" if state != "CANDIDATE" else "PENDING_EXACT_REOBSERVATION",
    }


def _selector_sha(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) != 40:
        return None
    if any(character not in "0123456789abcdef" for character in value):
        return None
    return value


def _workflow_run_pr_subject(
    item: Mapping[str, Any], repository: str
) -> tuple[int | None, str | None, str | None]:
    number = _positive_pr_number(item.get("number"))
    if number is None:
        return None, None, "MALFORMED_WORKFLOW_RUN_PULL_REQUESTS"
    url = item.get("url")
    if not isinstance(url, str) or not url:
        return None, None, "MALFORMED_WORKFLOW_RUN_PULL_REQUESTS"
    parsed = urllib.parse.urlparse(url)
    expected_path = f"/repos/{repository}/pulls/{number}"
    if (
        parsed.scheme != "https"
        or parsed.netloc != "api.github.com"
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
    ):
        return None, None, "WORKFLOW_RUN_PULL_REQUEST_NOT_ROLE_LOCAL"
    head = item.get("head")
    if not isinstance(head, Mapping):
        return None, None, "MALFORMED_WORKFLOW_RUN_PULL_REQUESTS"
    head_value = head.get("sha")
    if not isinstance(head_value, str) or not head_value:
        return None, None, "WORKFLOW_RUN_PULL_REQUEST_HEAD_MISSING"
    candidate_head = _selector_sha(head_value)
    if candidate_head is None:
        return None, None, "WORKFLOW_RUN_PULL_REQUEST_HEAD_INVALID"
    return number, candidate_head, None


def select_required_review_targets(
    *,
    repository: str,
    requested_pr: str,
    workflow_event: str,
    workflow_run_head: str,
    event_prs: Any,
) -> dict[str, Any]:
    """Resolve exactly one status subject without a scheduled repository scan."""
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise ReviewGateInputError("selector repository is invalid")
    run_head = workflow_run_head.strip()
    if run_head and _selector_sha(run_head) is None:
        return _selection(
            "REOBSERVE_EXACT_EVENT_TARGET",
            source="WORKFLOW_RUN",
            first_blocker="INVALID_WORKFLOW_RUN_HEAD",
            workflow_run_head=run_head,
        )
    if requested_pr.strip():
        number = _positive_pr_number(requested_pr)
        if number is None:
            return _selection(
                "INELIGIBLE_EVENT_TARGET",
                source="WORKFLOW_DISPATCH_PR",
                first_blocker="INVALID_EXACT_PULL_REQUEST_NUMBER",
            )
        return _selection(
            "CANDIDATE", source="WORKFLOW_DISPATCH_PR", pr_numbers=[number]
        )

    if workflow_event in {"schedule", "workflow_dispatch"}:
        return _selection(
            "INELIGIBLE_EVENT_TARGET",
            source="WORKFLOW_RUN",
            first_blocker="SCHEDULED_OR_MANUAL_WORKFLOW_RUN_FORBIDDEN",
            workflow_run_head=run_head or None,
        )
    if not workflow_event:
        return _selection(
            "NO_EVENT_SUBJECT",
            source="NONE",
            first_blocker="NO_EXACT_WORKFLOW_RUN_PULL_REQUEST",
            workflow_run_head=run_head or None,
        )
    if workflow_event and not run_head:
        return _selection(
            "REOBSERVE_EXACT_EVENT_TARGET",
            source="WORKFLOW_RUN",
            first_blocker="WORKFLOW_RUN_HEAD_MISSING",
        )
    if not event_prs:
        return _selection(
            "NO_EVENT_SUBJECT",
            source="NONE",
            first_blocker="NO_EXACT_WORKFLOW_RUN_PULL_REQUEST",
            workflow_run_head=run_head or None,
        )
    if not isinstance(event_prs, Sequence) or isinstance(event_prs, (str, bytes)):
        return _selection(
            "INELIGIBLE_EVENT_TARGET",
            source="WORKFLOW_RUN_PULL_REQUESTS",
            first_blocker="MALFORMED_WORKFLOW_RUN_PULL_REQUESTS",
            workflow_run_head=run_head or None,
        )
    subjects: dict[int, str] = {}
    for item in event_prs:
        if not isinstance(item, Mapping):
            return _selection(
                "INELIGIBLE_EVENT_TARGET",
                source="WORKFLOW_RUN_PULL_REQUESTS",
                first_blocker="MALFORMED_WORKFLOW_RUN_PULL_REQUESTS",
                workflow_run_head=run_head or None,
            )
        number, candidate_head, blocker = _workflow_run_pr_subject(item, repository)
        if blocker is not None:
            return _selection(
                "INELIGIBLE_EVENT_TARGET",
                source="WORKFLOW_RUN_PULL_REQUESTS",
                first_blocker=blocker,
                workflow_run_head=run_head or None,
            )
        assert number is not None
        assert candidate_head is not None
        previous_head = subjects.get(number)
        if previous_head is not None and previous_head != candidate_head:
            return _selection(
                "AMBIGUOUS_EVENT_SUBJECT",
                source="WORKFLOW_RUN_PULL_REQUESTS",
                first_blocker="WORKFLOW_RUN_PULL_REQUEST_HEAD_CONFLICT",
                pr_numbers=[number],
                workflow_run_head=run_head or None,
            )
        subjects[number] = candidate_head
    if len(subjects) != 1:
        return _selection(
            "AMBIGUOUS_EVENT_SUBJECT",
            source="WORKFLOW_RUN_PULL_REQUESTS",
            first_blocker="WORKFLOW_RUN_MULTIPLE_PULL_REQUESTS",
            pr_numbers=sorted(subjects),
            workflow_run_head=run_head or None,
        )
    number, candidate_head = next(iter(subjects.items()))
    return _selection(
        "CANDIDATE",
        source="WORKFLOW_RUN_PULL_REQUESTS",
        pr_numbers=[number],
        expected_head=candidate_head,
        workflow_run_head=run_head or None,
    )


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


def _status_sort_key(status: Mapping[str, Any]) -> tuple[str, int]:
    updated_at = status.get("updated_at")
    if not isinstance(updated_at, str):
        updated_at = status.get("created_at")
    if not isinstance(updated_at, str):
        updated_at = ""
    identifier = status.get("id", -1)
    if isinstance(identifier, bool) or not isinstance(identifier, int):
        identifier = -1
    return updated_at, identifier


def status_description(decision: Mapping[str, Any]) -> str:
    state = decision.get("gate_state")
    if state not in {SUCCESS, PENDING, FAILURE}:
        raise ReviewGateInputError("decision gate_state is invalid")
    blocker = decision.get("first_blocker")
    if blocker is None:
        blocker = "CODE_OWNER_REVIEW_CURRENT"
    if not isinstance(blocker, str) or not blocker:
        raise ReviewGateInputError("decision first_blocker is invalid")
    return f"{state}: {blocker}"[:140]


def decide_status_publication(
    statuses: Sequence[Mapping[str, Any]],
    *,
    context: str,
    state: str,
    description: str,
) -> dict[str, Any]:
    if not isinstance(statuses, Sequence) or isinstance(statuses, (str, bytes)):
        raise ReviewGateInputError("commit statuses observation must be a list")
    if not all(isinstance(status, Mapping) for status in statuses):
        raise ReviewGateInputError("commit statuses observation contains a non-object")
    if not isinstance(context, str) or not context.strip():
        raise ReviewGateInputError("status context is missing")
    if state not in {SUCCESS, PENDING, FAILURE}:
        raise ReviewGateInputError("status state is invalid")
    if not isinstance(description, str) or not description:
        raise ReviewGateInputError("status description is missing")

    matching = [status for status in statuses if status.get("context") == context]
    latest = max(matching, key=_status_sort_key) if matching else None
    unchanged = (
        latest is not None
        and latest.get("state") == state
        and latest.get("description") == description
    )
    return {
        "status_publication": STATUS_PUBLICATION_NOOP if unchanged else STATUS_PUBLICATION_WRITE,
        "status_publication_reason": (
            "UNCHANGED_HEAD_CONTEXT_STATE" if unchanged else "MATERIAL_GATE_TRANSITION"
        ),
        "status_context": context,
        "status_state": state,
        "status_description": description,
        "previous_status_id": latest.get("id") if latest is not None else None,
    }


def _code_owners(values: Sequence[str]) -> tuple[str, ...]:
    owners: list[str] = []
    seen: set[str] = set()
    for value in values:
        owner = _login(value, "required code owner")
        folded = owner.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        owners.append(owner)
    if len(owners) < 2:
        raise ReviewGateInputError("at least two distinct repository code owners are required")
    return tuple(owners)


def _block(*, gate_state: str, blocker: str, detail: str, pr_number: Any, head_sha: str | None, required_code_owners: Sequence[str], eligible_code_owners: Sequence[str]) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "gate_state": gate_state,
        "first_blocker": blocker,
        "detail": detail,
        "pr_number": pr_number,
        "head_sha": head_sha,
        "required_code_owners": list(required_code_owners),
        "eligible_code_owners": list(eligible_code_owners),
        "external_effect": "NONE",
        "review_mutation": "FORBIDDEN",
    }


def native_code_owner_rule_is_enforced(rules: Sequence[Mapping[str, Any]]) -> bool:
    pull_request_enforced = False
    status_checks_enforced = False
    for rule in rules:
        rule_type = rule.get("type")
        parameters = rule.get("parameters")
        if not isinstance(parameters, Mapping):
            continue
        if rule_type == "pull_request":
            count = parameters.get("required_approving_review_count")
            if isinstance(count, bool) or not isinstance(count, int):
                continue
            pull_request_enforced = (
                count >= 1
                and parameters.get("require_code_owner_review") is True
                and parameters.get("dismiss_stale_reviews_on_push") is True
                and parameters.get("require_last_push_approval") is True
            )
        elif rule_type == "required_status_checks":
            raw_checks = parameters.get("required_status_checks")
            if not isinstance(raw_checks, Sequence) or isinstance(raw_checks, (str, bytes)):
                continue
            observed = {
                (check.get("context"), check.get("integration_id"))
                for check in raw_checks
                if isinstance(check, Mapping)
            }
            status_checks_enforced = REQUIRED_NATIVE_STATUS_CHECKS <= observed
    return pull_request_enforced and status_checks_enforced


def evaluate_required_review(pr: Mapping[str, Any], rules: Sequence[Mapping[str, Any]], reviews: Sequence[Mapping[str, Any]], *, required_code_owners: Sequence[str] = DEFAULT_CODE_OWNERS) -> dict[str, Any]:
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
    pr_number = pr.get("number")
    owner_logins = _code_owners(required_code_owners)
    eligible_owners = tuple(
        owner for owner in owner_logins if owner.casefold() != author_login.casefold()
    )
    if not eligible_owners:
        return _block(
            gate_state=FAILURE,
            blocker="CODE_OWNER_COUNTERPART_UNAVAILABLE",
            detail="the pull-request author excludes every configured repository code owner",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owners=owner_logins,
            eligible_code_owners=eligible_owners,
        )

    if not native_code_owner_rule_is_enforced(rules):
        return _block(
            gate_state=FAILURE,
            blocker="CODE_OWNER_RULE_NOT_ENFORCED",
            detail="main must require one approval, Code Owner review, stale-review dismissal, last-push approval, and the exact test and review-gate statuses",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owners=owner_logins,
            eligible_code_owners=eligible_owners,
        )

    owner_reviews = [
        review for review in reviews
        if isinstance(review.get("user"), Mapping)
        and isinstance(review["user"].get("login"), str)
        and review["user"]["login"].casefold() in {
            owner.casefold() for owner in eligible_owners
        }
    ]
    if not owner_reviews:
        self_reviews = [
            review for review in reviews
            if isinstance(review.get("user"), Mapping)
            and isinstance(review["user"].get("login"), str)
            and review["user"]["login"].casefold() == author_login.casefold()
            and author_login.casefold() in {owner.casefold() for owner in owner_logins}
        ]
        if self_reviews:
            return _block(gate_state=FAILURE, blocker="CODE_OWNER_REVIEW_SELF_APPROVAL", detail="the pull-request author cannot satisfy the repository Code Owner counterpart gate", pr_number=pr_number, head_sha=head_sha, required_code_owners=owner_logins, eligible_code_owners=eligible_owners)
        names = ", ".join(f"@{owner}" for owner in eligible_owners)
        return _block(gate_state=PENDING, blocker="CODE_OWNER_REVIEW_MISSING", detail=f"no review from eligible counterpart {names} is present", pr_number=pr_number, head_sha=head_sha, required_code_owners=owner_logins, eligible_code_owners=eligible_owners)

    exact_head_reviews = [review for review in owner_reviews if review.get("commit_id") == head_sha]
    if not exact_head_reviews:
        return _block(gate_state=PENDING, blocker="CODE_OWNER_REVIEW_STALE", detail=f"no eligible repository Code Owner has a review bound to current head {head_sha}", pr_number=pr_number, head_sha=head_sha, required_code_owners=owner_logins, eligible_code_owners=eligible_owners)

    decisive = [
        review for review in exact_head_reviews
        if isinstance(review.get("state"), str) and review["state"].upper() in DECISIVE_REVIEW_STATES
    ]
    if not decisive:
        return _block(gate_state=PENDING, blocker="CODE_OWNER_REVIEW_NOT_APPROVED", detail="no eligible repository Code Owner has a decisive current-head review", pr_number=pr_number, head_sha=head_sha, required_code_owners=owner_logins, eligible_code_owners=eligible_owners)

    latest = max(decisive, key=_review_sort_key)
    latest_state = latest["state"].upper()
    reviewer_login = _login(latest["user"].get("login"), "review user.login")
    if latest_state == "CHANGES_REQUESTED":
        return _block(gate_state=FAILURE, blocker="CODE_OWNER_REVIEW_CHANGES_REQUESTED", detail=f"@{reviewer_login} requested changes on current head {head_sha}", pr_number=pr_number, head_sha=head_sha, required_code_owners=owner_logins, eligible_code_owners=eligible_owners)
    if latest_state == "DISMISSED":
        return _block(gate_state=PENDING, blocker="CODE_OWNER_REVIEW_DISMISSED", detail=f"@{reviewer_login}'s current-head review was dismissed", pr_number=pr_number, head_sha=head_sha, required_code_owners=owner_logins, eligible_code_owners=eligible_owners)
    if latest_state != "APPROVED":
        raise ReviewGateInputError(f"unsupported decisive review state: {latest_state}")
    return {
        "schema": SCHEMA,
        "gate_state": SUCCESS,
        "first_blocker": None,
        "detail": f"@{reviewer_login} approved the current head as the non-author repository Code Owner",
        "pr_number": pr_number,
        "head_sha": head_sha,
        "required_code_owners": list(owner_logins),
        "eligible_code_owners": list(eligible_owners),
        "review_author": reviewer_login,
        "review_id": latest.get("id"),
        "external_effect": "NONE",
        "review_mutation": "FORBIDDEN",
    }


def _load_json(path: str) -> Any:
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluate", nargs="?", default="evaluate")
    parser.add_argument("--pr", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument("--reviews", required=True)
    parser.add_argument("--required-code-owner", action="append", dest="required_code_owners")
    args = parser.parse_args(argv)
    try:
        result = evaluate_required_review(_load_json(args.pr), _load_json(args.rules), _load_json(args.reviews), required_code_owners=args.required_code_owners or DEFAULT_CODE_OWNERS)
    except (OSError, ValueError, json.JSONDecodeError, ReviewGateInputError) as exc:
        owners = args.required_code_owners or DEFAULT_CODE_OWNERS
        result = _block(gate_state=FAILURE, blocker="INVALID_REVIEW_GATE_SNAPSHOT", detail=str(exc), pr_number=None, head_sha=None, required_code_owners=owners, eligible_code_owners=())
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0 if result["gate_state"] == SUCCESS else 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
