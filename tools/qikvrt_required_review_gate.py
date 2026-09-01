#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Evaluate the live native Code Owner review prerequisite without mutation."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import urllib.parse
import zipfile
from collections.abc import Mapping, Sequence
from typing import Any, Callable

SCHEMA = "qikvrt_required_code_owner_review_gate_v1"
DEFAULT_CODE_OWNERS = ("Goldkelch", "ingolf-lohmann")
SUCCESS = "success"
PENDING = "pending"
FAILURE = "failure"
STATUS_PUBLICATION_NOOP = "NOOP"
STATUS_PUBLICATION_WRITE = "WRITE"
STATUS_EFFECT_PLAN_SCHEMA = "qikvrt_required_code_owner_status_effect_plan_v1"
DECISIVE_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
SELECTION_SCHEMA = "qikvrt_required_code_owner_review_selection_v1"
REQUIRED_NATIVE_STATUS_CHECKS = {
    ("test", 15368),
    ("QIKVRT required code-owner review", 15368),
}
TRUSTED_EXECUTOR_WORKFLOW_PATH = (
    ".github/workflows/qikvrt_requested_review_executor.yml"
)
TRUSTED_DISPATCH_AUTHORITY_LANES = frozenset(
    {
        "exact-review-dispatch",
        "requested-review-dispatch",
        "mesh-review-successor-dispatch",
    }
)


def _complete_object_pages(
    pages: Sequence[Any], *, values_key: str, label: str
) -> list[Mapping[str, Any]]:
    if not isinstance(pages, Sequence) or isinstance(pages, (str, bytes)) or not pages:
        raise ReviewGateInputError(f"{label} pages are missing")
    values: list[Mapping[str, Any]] = []
    counts: set[int] = set()
    identifiers: set[int] = set()
    for page in pages:
        if not isinstance(page, Mapping):
            raise ReviewGateInputError(f"{label} page is malformed")
        total = page.get("total_count")
        raw = page.get(values_key)
        if (
            isinstance(total, bool)
            or not isinstance(total, int)
            or total < 0
            or not isinstance(raw, Sequence)
            or isinstance(raw, (str, bytes))
        ):
            raise ReviewGateInputError(f"{label} page is malformed")
        counts.add(total)
        for item in raw:
            if not isinstance(item, Mapping):
                raise ReviewGateInputError(f"{label} entry is malformed")
            identifier = item.get("id")
            if (
                isinstance(identifier, bool)
                or not isinstance(identifier, int)
                or identifier < 1
                or identifier in identifiers
            ):
                raise ReviewGateInputError(f"{label} identity is ambiguous")
            identifiers.add(identifier)
            values.append(item)
    if counts != {len(values)}:
        raise ReviewGateInputError(f"{label} pagination is incomplete")
    return values


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
    workflow_run_display_title: str = "",
    trusted_evaluator_sha: str = "",
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

    if workflow_event == "schedule":
        return _selection(
            "INELIGIBLE_EVENT_TARGET",
            source="WORKFLOW_RUN",
            first_blocker="SCHEDULED_OR_MANUAL_WORKFLOW_RUN_FORBIDDEN",
            workflow_run_head=run_head or None,
        )
    if workflow_event == "workflow_dispatch":
        from tools.qikvrt_requested_review_executor import (
            parse_requested_review_run_title,
        )

        locator = parse_requested_review_run_title(workflow_run_display_title)
        expected_evaluator = trusted_evaluator_sha.strip()
        if expected_evaluator and _selector_sha(expected_evaluator) is None:
            raise ReviewGateInputError("selector trusted evaluator SHA is invalid")
        if locator is None:
            return _selection(
                "INELIGIBLE_EVENT_TARGET",
                source="WORKFLOW_DISPATCH_LOCATOR",
                first_blocker="WORKFLOW_DISPATCH_LOCATOR_INVALID",
                workflow_run_head=run_head or None,
            )
        if (
            locator["evaluator_sha"] != run_head
            or (expected_evaluator and locator["evaluator_sha"] != expected_evaluator)
        ):
            return _selection(
                "REOBSERVE_EXACT_EVENT_TARGET",
                source="WORKFLOW_DISPATCH_LOCATOR",
                first_blocker="WORKFLOW_DISPATCH_EVALUATOR_SUPERSEDED",
                workflow_run_head=run_head or None,
            )
        return _selection(
            "CANDIDATE",
            source="WORKFLOW_DISPATCH_LOCATOR",
            pr_numbers=[locator["pr_number"]],
            expected_head=locator["head_sha"],
            workflow_run_head=run_head,
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


def verify_upstream_executor_dispatch_authority(
    *,
    repository: str,
    evaluator_sha: str,
    executor_workflow_id: int,
    run: Mapping[str, Any],
    core_lookups: Sequence[Mapping[str, Any]] = (),
    core_lookups_complete: bool = True,
) -> dict[str, Any]:
    """Require an independent durable producer for an executor dispatch run.

    A canonical title is only a locator.  A manual caller can reproduce every
    workflow input, so escalation into this Required Gate is admitted only
    when one exact protected Shared-Core outbox acceptance binds the same child
    run.  A human-review wake-up ledger record is a fact/intent/ACK locator
    only; it is deliberately not a second transport authority.
    """
    from tools.qikvrt_requested_review_executor import (
        parse_requested_review_run_title,
    )

    if not isinstance(repository, str) or repository.count("/") != 1:
        raise ReviewGateInputError("dispatch authority repository is invalid")
    evaluator = _sha(evaluator_sha, "dispatch authority evaluator")
    if (
        isinstance(executor_workflow_id, bool)
        or not isinstance(executor_workflow_id, int)
        or executor_workflow_id < 1
    ):
        raise ReviewGateInputError("dispatch authority workflow id is invalid")
    if not isinstance(run, Mapping):
        raise ReviewGateInputError("dispatch authority run is malformed")
    run_repository = run.get("repository")
    raw_path = run.get("path")
    canonical_path = (
        raw_path.split("@", 1)[0]
        if isinstance(raw_path, str) and raw_path.count("@") <= 1
        else None
    )
    locator = parse_requested_review_run_title(run.get("display_title"))
    run_id = run.get("id")
    run_attempt = run.get("run_attempt")
    if (
        locator is None
        or isinstance(run_id, bool)
        or not isinstance(run_id, int)
        or run_id < 1
        or isinstance(run_attempt, bool)
        or not isinstance(run_attempt, int)
        or run_attempt < 1
        or run.get("workflow_id") != executor_workflow_id
        or canonical_path != TRUSTED_EXECUTOR_WORKFLOW_PATH
        or run.get("event") != "workflow_dispatch"
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
        or run.get("head_branch") != "main"
        or run.get("head_sha") != evaluator
        or not isinstance(run_repository, Mapping)
        or run_repository.get("full_name") != repository
        or locator["evaluator_sha"] != evaluator
    ):
        return {
            "schema": "qikvrt_required_gate_upstream_dispatch_authority_v1",
            "state": "INELIGIBLE",
            "admitted": False,
            "first_blocker": "UPSTREAM_EXECUTOR_DISPATCH_RUN_INVALID",
            "source": None,
        }

    expected_inputs = {
        "pr": str(locator["pr_number"]),
        "head": locator["head_sha"],
        "fingerprint": locator["fingerprint"],
        "evaluator_sha": locator["evaluator_sha"],
        "transport_intent_sha256": locator["transport_intent_sha256"],
        "transport_attempt": str(locator["transport_attempt"]),
    }

    if core_lookups_complete is not True:
        return {
            "schema": "qikvrt_required_gate_upstream_dispatch_authority_v1",
            "state": "INELIGIBLE",
            "admitted": False,
            "first_blocker": "UPSTREAM_EXECUTOR_DISPATCH_AUTHORITY_READBACK_INCOMPLETE",
            "source": None,
        }

    def child_matches(child: Any) -> bool:
        if not isinstance(child, Mapping):
            return False
        child_path = child.get("workflow_path")
        if isinstance(child_path, str):
            child_path = child_path.split("@", 1)[0]
        return (
            child.get("run_id") == run_id
            and child.get("run_attempt") == run_attempt
            and child.get("workflow_id") == executor_workflow_id
            and child_path == TRUSTED_EXECUTOR_WORKFLOW_PATH
            and child.get("event") == "workflow_dispatch"
            and child.get("repository") == repository
            and child.get("head_sha") == evaluator
            and child.get("display_title") == run.get("display_title")
        )

    matches: list[dict[str, Any]] = []
    if not isinstance(core_lookups, Sequence) or isinstance(
        core_lookups, (str, bytes)
    ):
        raise ReviewGateInputError("dispatch authority lookups are malformed")
    for lookup in core_lookups:
        if not isinstance(lookup, Mapping):
            raise ReviewGateInputError("dispatch authority lookup is malformed")
        lane = lookup.get("lane")
        intent = lookup.get("intent")
        if lane not in TRUSTED_DISPATCH_AUTHORITY_LANES or not isinstance(
            intent, Mapping
        ):
            continue
        payload = intent.get("payload")
        request = payload.get("request") if isinstance(payload, Mapping) else None
        target = payload.get("target") if isinstance(payload, Mapping) else None
        inputs = request.get("inputs") if isinstance(request, Mapping) else None
        if (
            intent.get("fingerprint") != locator["transport_intent_sha256"]
            or not isinstance(payload, Mapping)
            or payload.get("repository") != repository
            or payload.get("main_head_sha") != evaluator
            or not isinstance(request, Mapping)
            or request.get("ref") != "main"
            or request.get("return_run_details") is not True
            or inputs != expected_inputs
            or not isinstance(target, Mapping)
            or target.get("workflow_id") != executor_workflow_id
            or target.get("workflow_path") != TRUSTED_EXECUTOR_WORKFLOW_PATH
            or target.get("event") != "workflow_dispatch"
        ):
            continue
        attempt = str(locator["transport_attempt"])
        acceptance = lookup.get("acceptance")
        direct = acceptance.get(attempt) if isinstance(acceptance, Mapping) else None
        direct_child = direct.get("child") if isinstance(direct, Mapping) else None
        recovery = lookup.get("child_recovery")
        recovered = recovery.get(attempt) if isinstance(recovery, Mapping) else None
        recovered_acceptance = (
            recovered.get("acceptance") if isinstance(recovered, Mapping) else None
        )
        recovered_child = (
            recovered_acceptance.get("child")
            if isinstance(recovered_acceptance, Mapping)
            else None
        )
        if child_matches(direct_child) or child_matches(recovered_child):
            matches.append(
                {
                    "kind": "PROTECTED_SHARED_OUTBOX_ACCEPTANCE",
                    "lane": lane,
                    "sequence": intent.get("sequence"),
                    "fingerprint": intent.get("fingerprint"),
                    "transport_attempt": locator["transport_attempt"],
                    "child_run_id": run_id,
                    "child_run_attempt": run_attempt,
                }
            )

    if len(matches) != 1:
        return {
            "schema": "qikvrt_required_gate_upstream_dispatch_authority_v1",
            "state": "INELIGIBLE",
            "admitted": False,
            "first_blocker": (
                "UPSTREAM_EXECUTOR_DISPATCH_AUTHORITY_MISSING"
                if not matches
                else "UPSTREAM_EXECUTOR_DISPATCH_AUTHORITY_AMBIGUOUS"
            ),
            "source": None,
        }
    return {
        "schema": "qikvrt_required_gate_upstream_dispatch_authority_v1",
        "state": "ADMITTED",
        "admitted": True,
        "first_blocker": None,
        "source": matches[0],
    }


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


def observe_automated_signer_receipts(
    *,
    repository: str,
    evaluator_sha: str,
    pr: Mapping[str, Any],
    reviews: Sequence[Mapping[str, Any]],
    required_code_owners: Sequence[str],
    api_json: Callable[[str], Any],
    api_pages: Callable[[str], Sequence[Any]],
    api_bytes: Callable[[str], bytes],
) -> tuple[dict[int, Mapping[str, Any]], dict[int, str]]:
    """Verify immutable receipts for current-head automation-marked reviews.

    The callbacks keep this policy module network-free.  A caller must provide
    complete REST pagination and raw artifact bytes from trusted-main code.
    Receipt verification is audit evidence only; a marked review can never
    satisfy the required human Code Owner gate.
    """
    from tools.qikvrt_native_account_review import (
        MARKER,
        NativeAccountReviewError,
        SIGNER_RECEIPT_ARTIFACT_PATTERN,
        TRUSTED_SIGNER_WORKFLOW_PATH,
        parse_delegated_review_locator,
        validate_signer_receipt,
    )

    if not isinstance(pr, Mapping):
        raise ReviewGateInputError("signer receipt pull request is malformed")
    if not isinstance(reviews, Sequence) or isinstance(reviews, (str, bytes)):
        raise ReviewGateInputError("signer receipt reviews are malformed")
    evaluator_sha = _sha(evaluator_sha, "signer receipt evaluator")
    author = pr.get("user")
    head = pr.get("head")
    if not isinstance(author, Mapping) or not isinstance(head, Mapping):
        raise ReviewGateInputError("signer receipt subject is malformed")
    author_login = _login(author.get("login"), "signer receipt author")
    owners = _code_owners(required_code_owners)
    eligible = {
        owner.casefold() for owner in owners if owner.casefold() != author_login.casefold()
    }
    head_sha = _sha(head.get("sha"), "signer receipt subject head")
    marked_reviews = [
        review
        for review in reviews
        if isinstance(review, Mapping)
        and isinstance(review.get("user"), Mapping)
        and isinstance(review["user"].get("login"), str)
        and review["user"]["login"].casefold() in eligible
        and review.get("commit_id") == head_sha
        and isinstance(review.get("body"), str)
        and MARKER in review["body"]
    ]
    verified: dict[int, Mapping[str, Any]] = {}
    blockers: dict[int, str] = {}
    for latest in sorted(marked_reviews, key=_review_sort_key):
        review_id = latest.get("id")
        if isinstance(review_id, bool) or not isinstance(review_id, int) or review_id < 1:
            raise ReviewGateInputError("latest decisive review id is invalid")
        body = latest.get("body")
        locator = parse_delegated_review_locator(body)
        if locator is None:
            blockers[review_id] = "SIGNER_REVIEW_LOCATOR_INVALID"
            continue
        if (
            locator["head_sha"] != head_sha
            or locator["signer_evaluator_sha"] != evaluator_sha
        ):
            blockers[review_id] = "SIGNER_REVIEW_EVALUATOR_OR_HEAD_DRIFT"
            continue
        try:
            run_id = locator["signer_run_id"]
            workflow = api_json(
                f"repos/{repository}/actions/workflows/"
                "qikvrt_required_review_gate.yml"
            )
            artifacts = _complete_object_pages(
                api_pages(
                    f"repos/{repository}/actions/runs/{run_id}/artifacts?per_page=100"
                ),
                values_key="artifacts",
                label="signer run artifacts",
            )
            reviewer = latest["user"]["login"]
            matches_by_attempt: dict[int, list[Mapping[str, Any]]] = {}
            for artifact in artifacts:
                name = artifact.get("name")
                match = (
                    SIGNER_RECEIPT_ARTIFACT_PATTERN.fullmatch(name)
                    if isinstance(name, str)
                    else None
                )
                if (
                    match is not None
                    and match.group(1).casefold() == reviewer.casefold()
                    and int(match.group(2)) == pr.get("number")
                    and match.group(3) == head_sha
                    and int(match.group(4)) == run_id
                    and int(match.group(5)) >= locator["signer_run_attempt"]
                    and artifact.get("expired") is not True
                ):
                    matches_by_attempt.setdefault(int(match.group(5)), []).append(
                        artifact
                    )
            if not matches_by_attempt or any(
                len(values) != 1 for values in matches_by_attempt.values()
            ):
                raise ReviewGateInputError(
                    "SIGNER_RECEIPT_ARTIFACT_MISSING_OR_AMBIGUOUS"
                )
            attempt_errors: list[str] = []
            for run_attempt in sorted(matches_by_attempt, reverse=True):
                try:
                    artifact = matches_by_attempt[run_attempt][0]
                    run = api_json(
                        f"repos/{repository}/actions/runs/{run_id}/attempts/"
                        f"{run_attempt}"
                    )
                    jobs = _complete_object_pages(
                        api_pages(
                            f"repos/{repository}/actions/runs/{run_id}/attempts/"
                            f"{run_attempt}/jobs?per_page=100"
                        ),
                        values_key="jobs",
                        label="signer attempt jobs",
                    )
                    artifact_name = artifact.get("name")
                    digest = artifact.get("digest")
                    url = artifact.get("archive_download_url")
                    if (
                        not isinstance(artifact_name, str)
                        or not isinstance(digest, str)
                        or len(digest) != 71
                        or not digest.startswith("sha256:")
                        or any(
                            character not in "0123456789abcdef"
                            for character in digest[7:]
                        )
                        or not isinstance(url, str)
                        or not url.startswith(
                            f"https://api.github.com/repos/{repository}/actions/artifacts/"
                        )
                    ):
                        raise ReviewGateInputError(
                            "SIGNER_RECEIPT_ARTIFACT_METADATA_INVALID"
                        )
                    archive = api_bytes(url)
                    if (
                        not isinstance(archive, bytes)
                        or hashlib.sha256(archive).hexdigest() != digest[7:]
                    ):
                        raise ReviewGateInputError(
                            "SIGNER_RECEIPT_ARTIFACT_DIGEST_DRIFT"
                        )
                    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
                        names = [
                            name for name in zipped.namelist() if not name.endswith("/")
                        ]
                        if names != ["signer-receipt.json"]:
                            raise ReviewGateInputError(
                                "SIGNER_RECEIPT_ARTIFACT_FILESET_INVALID"
                            )
                        raw_receipt = zipped.read("signer-receipt.json")
                    receipt = json.loads(raw_receipt.decode("utf-8"))
                    validated = validate_signer_receipt(
                        receipt,
                        review=latest,
                        current_reviews=reviews,
                        repository=repository,
                        evaluator_sha=evaluator_sha,
                        run=run,
                        workflow=workflow,
                        jobs=jobs,
                        artifact_name=artifact_name,
                    )
                    if validated.get("workflow_path") != TRUSTED_SIGNER_WORKFLOW_PATH:
                        raise ReviewGateInputError(
                            "SIGNER_RECEIPT_WORKFLOW_PATH_DRIFT"
                        )
                    verified[review_id] = validated
                    break
                except (
                    NativeAccountReviewError,
                    ReviewGateInputError,
                    KeyError,
                    TypeError,
                    ValueError,
                    UnicodeDecodeError,
                    zipfile.BadZipFile,
                    subprocess.SubprocessError,
                ) as exc:
                    attempt_errors.append(f"attempt-{run_attempt}:{exc}")
            if review_id not in verified:
                raise ReviewGateInputError(
                    "SIGNER_RECEIPT_NO_SUCCESSFUL_BOUND_ATTEMPT:"
                    + "|".join(attempt_errors)
                )
        except (
            NativeAccountReviewError,
            ReviewGateInputError,
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            zipfile.BadZipFile,
            subprocess.SubprocessError,
        ) as exc:
            blockers[review_id] = str(exc)
    return verified, blockers


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


def _canonical_sha256(value: Mapping[str, Any] | Sequence[Any]) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _status_effect_subject(
    pr: Mapping[str, Any], commit: Mapping[str, Any]
) -> dict[str, Any]:
    """Canonicalize the exact PR/head/tree/base tuple bound by a status plan."""
    if not isinstance(pr, Mapping) or not isinstance(commit, Mapping):
        raise ReviewGateInputError("status-plan subject observation is malformed")
    if pr.get("state") != "open" or pr.get("base", {}).get("ref") != "main":
        raise ReviewGateInputError("status-plan pull request is not open and main-based")
    number = _positive_pr_number(pr.get("number"))
    if number is None:
        raise ReviewGateInputError("status-plan pull request number is invalid")
    head = _sha(pr.get("head", {}).get("sha"), "status-plan head")
    base = _sha(pr.get("base", {}).get("sha"), "status-plan base")
    if _sha(commit.get("sha"), "status-plan commit") != head:
        raise ReviewGateInputError("status-plan commit differs from pull request head")
    tree = _sha(commit.get("tree", {}).get("sha"), "status-plan tree")
    if not isinstance(pr.get("head", {}).get("repo"), Mapping):
        raise ReviewGateInputError("status-plan head repository is missing")
    if not isinstance(pr.get("base", {}).get("repo"), Mapping):
        raise ReviewGateInputError("status-plan base repository is missing")
    return {
        "pr_number": number,
        "state": pr.get("state"),
        "draft": pr.get("draft"),
        "author": pr.get("user", {}).get("login"),
        "head_repository": pr.get("head", {}).get("repo", {}).get("full_name"),
        "head_ref": pr.get("head", {}).get("ref"),
        "head_sha": head,
        "head_tree_sha": tree,
        "base_repository": pr.get("base", {}).get("repo", {}).get("full_name"),
        "base_ref": pr.get("base", {}).get("ref"),
        "base_sha": base,
    }


def build_status_effect_plan(
    pr: Mapping[str, Any],
    commit: Mapping[str, Any],
    rules: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    statuses: Sequence[Mapping[str, Any]],
    *,
    context: str,
    required_code_owners: Sequence[str] = DEFAULT_CODE_OWNERS,
    verified_automated_reviews: Mapping[int, Mapping[str, Any]] | None = None,
    automated_review_receipt_blockers: Mapping[int, str] | None = None,
) -> dict[str, Any]:
    """Seal one exact read-only status decision for a narrow effect job."""
    subject = _status_effect_subject(pr, commit)
    verified_receipts = dict(verified_automated_reviews or {})
    receipt_blockers = dict(automated_review_receipt_blockers or {})
    decision = evaluate_required_review(
        pr,
        rules,
        reviews,
        required_code_owners=required_code_owners,
        verified_automated_review_ids=tuple(verified_receipts),
        automated_review_receipt_blockers=receipt_blockers,
    )
    description = status_description(decision)
    publication = decide_status_publication(
        statuses,
        context=context,
        state=decision["gate_state"],
        description=description,
    )
    value = {
        "schema": STATUS_EFFECT_PLAN_SCHEMA,
        "subject": subject,
        "observation_sha256": {
            "rules": _canonical_sha256(rules),
            "reviews": _canonical_sha256(reviews),
            "statuses": _canonical_sha256(statuses),
            "verified_automated_reviews": _canonical_sha256(verified_receipts),
            "automated_review_receipt_blockers": _canonical_sha256(
                receipt_blockers
            ),
        },
        "decision": decision,
        "publication": publication,
        "status_effect_authorized": publication["status_publication"]
        == STATUS_PUBLICATION_WRITE,
        "review_effect_authorized": False,
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }
    value["plan_sha256"] = _canonical_sha256(value)
    return value


def status_post_effect_drift_blocker(
    sealed_plan: Mapping[str, Any],
    *,
    expected_main_sha: str,
    observed_main: Mapping[str, Any],
    observed_pr: Mapping[str, Any],
    observed_commit: Mapping[str, Any],
    observed_rules: Sequence[Mapping[str, Any]],
    observed_reviews: Sequence[Mapping[str, Any]],
) -> str | None:
    """Classify drift after a required-status POST without authorizing success.

    A status write cannot be made atomically conditional on GitHub's PR,
    ruleset, review, and default-branch state.  The effect job therefore
    repeats the complete subject/Authority observation after the write.  Any
    difference from the sealed pre-effect snapshot requires a newer pending
    correction on the same status context.
    """
    sealed = validate_status_effect_plan(sealed_plan)
    expected_main = _sha(expected_main_sha, "post-effect expected main")
    if not isinstance(observed_main, Mapping):
        return "POST_EFFECT_MAIN_DRIFT"
    try:
        live_main = _sha(observed_main.get("sha"), "post-effect main")
    except ReviewGateInputError:
        return "POST_EFFECT_MAIN_DRIFT"
    if live_main != expected_main:
        return "POST_EFFECT_MAIN_DRIFT"
    try:
        subject = _status_effect_subject(observed_pr, observed_commit)
    except ReviewGateInputError:
        return "POST_EFFECT_SUBJECT_DRIFT"
    if subject != sealed.get("subject"):
        return "POST_EFFECT_SUBJECT_DRIFT"
    observation = sealed.get("observation_sha256")
    if not isinstance(observation, Mapping):
        raise ReviewGateInputError("status effect plan observation is missing")
    if _canonical_sha256(observed_rules) != observation.get("rules"):
        return "POST_EFFECT_RULES_DRIFT"
    if _canonical_sha256(observed_reviews) != observation.get("reviews"):
        return "POST_EFFECT_REVIEW_DRIFT"
    return None


def validate_status_effect_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(plan, Mapping):
        raise ReviewGateInputError("status effect plan must be an object")
    value = dict(plan)
    claimed = value.pop("plan_sha256", None)
    if claimed != _canonical_sha256(value):
        raise ReviewGateInputError("status effect plan digest differs")
    if (
        value.get("schema") != STATUS_EFFECT_PLAN_SCHEMA
        or value.get("review_effect_authorized") is not False
        or value.get("completion_claims")
        != {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        }
    ):
        raise ReviewGateInputError("status effect plan boundary differs")
    publication = value.get("publication")
    if not isinstance(publication, Mapping):
        raise ReviewGateInputError("status effect plan publication is missing")
    expected_authorized = (
        publication.get("status_publication") == STATUS_PUBLICATION_WRITE
    )
    if value.get("status_effect_authorized") is not expected_authorized:
        raise ReviewGateInputError("status effect authorization differs")
    return dict(plan)


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


def evaluate_required_review(
    pr: Mapping[str, Any],
    rules: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    *,
    required_code_owners: Sequence[str] = DEFAULT_CODE_OWNERS,
    verified_automated_review_ids: Sequence[int] = (),
    automated_review_receipt_blockers: Mapping[int, str] | None = None,
) -> dict[str, Any]:
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
    from tools.qikvrt_native_account_review import canonical_review_inventory

    try:
        reviews = canonical_review_inventory(reviews, "required-gate reviews")
    except ValueError as exc:
        raise ReviewGateInputError(str(exc)) from exc
    verified_ids = set(verified_automated_review_ids)
    if any(
        isinstance(identifier, bool)
        or not isinstance(identifier, int)
        or identifier < 1
        for identifier in verified_ids
    ):
        raise ReviewGateInputError("verified automated review id is invalid")
    receipt_blockers = dict(automated_review_receipt_blockers or {})
    if any(
        isinstance(identifier, bool)
        or not isinstance(identifier, int)
        or identifier < 1
        or not isinstance(blocker, str)
        or not blocker
        for identifier, blocker in receipt_blockers.items()
    ):
        raise ReviewGateInputError("automated review receipt blocker is invalid")

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

    from tools.qikvrt_native_account_review import (
        parse_delegated_review_locator,
    )

    def marked(review: Mapping[str, Any]) -> bool:
        return parse_delegated_review_locator(review.get("body")) is not None

    decisive = [
        review for review in exact_head_reviews
        if isinstance(review.get("state"), str)
        and review["state"].upper() in DECISIVE_REVIEW_STATES
    ]
    # An automation marker is always technical evidence, never Code Owner
    # approval Authority.  Keep those reviews visible for a precise HOLD, but
    # compute the native gate exclusively from unmarked human review facts.
    human_decisive = [review for review in decisive if not marked(review)]
    latest_by_reviewer: dict[str, Mapping[str, Any]] = {}
    for review in human_decisive:
        reviewer_key = review["user"]["login"].casefold()
        prior = latest_by_reviewer.get(reviewer_key)
        if prior is None or _review_sort_key(review) > _review_sort_key(prior):
            latest_by_reviewer[reviewer_key] = review
    latest_states = list(latest_by_reviewer.values())

    changes_requested = [
        review
        for review in latest_states
        if str(review.get("state") or "").upper() == "CHANGES_REQUESTED"
    ]
    if changes_requested:
        latest_change = max(changes_requested, key=_review_sort_key)
        reviewer_login = _login(
            latest_change["user"].get("login"), "review user.login"
        )
        return _block(
            gate_state=FAILURE,
            blocker="CODE_OWNER_REVIEW_CHANGES_REQUESTED",
            detail=f"@{reviewer_login} requested changes on current head {head_sha}",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owners=owner_logins,
            eligible_code_owners=eligible_owners,
        )

    approvals = [
        review
        for review in latest_states
        if str(review.get("state") or "").upper() == "APPROVED"
    ]
    if approvals:
        latest = max(approvals, key=_review_sort_key)
        reviewer_login = _login(
            latest["user"].get("login"), "review user.login"
        )
    elif latest_states:
        dismissed = max(latest_states, key=_review_sort_key)
        reviewer_login = _login(
            dismissed["user"].get("login"), "review user.login"
        )
        return _block(
            gate_state=PENDING,
            blocker="CODE_OWNER_REVIEW_DISMISSED",
            detail=f"@{reviewer_login}'s current-head review was dismissed",
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owners=owner_logins,
            eligible_code_owners=eligible_owners,
        )
    else:
        marked_current = [review for review in exact_head_reviews if marked(review)]
        if marked_current:
            latest_marked = max(marked_current, key=_review_sort_key)
            reviewer_login = _login(
                latest_marked["user"].get("login"), "review user.login"
            )
            return _block(
                gate_state=PENDING,
                blocker="AUTOMATED_REVIEW_NOT_CODE_OWNER_AUTHORITY",
                detail=(
                    f"@{reviewer_login}'s automation-marked current-head review "
                    "is technical evidence only; an unmarked human counterpart "
                    "approval remains required"
                ),
                pr_number=pr_number,
                head_sha=head_sha,
                required_code_owners=owner_logins,
                eligible_code_owners=eligible_owners,
            )
        return _block(
            gate_state=PENDING,
            blocker="CODE_OWNER_REVIEW_NOT_APPROVED",
            detail=(
                "no eligible repository Code Owner has an unmarked human "
                "approval bound to the current head"
            ),
            pr_number=pr_number,
            head_sha=head_sha,
            required_code_owners=owner_logins,
            eligible_code_owners=eligible_owners,
        )
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
