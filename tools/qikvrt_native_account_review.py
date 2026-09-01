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
import re
import sys
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA = "qikvrt_delegated_native_account_review_plan_v1"
MARKER = "qikvrt-delegated-native-account-review:v1"
SIGNER_RECEIPT_SCHEMA = "qikvrt_native_account_review_signer_receipt_v1"
SIGNER_POST_EFFECT_FENCE_SCHEMA = (
    "qikvrt_native_account_review_post_effect_authority_fence_v1"
)
TRUSTED_SIGNER_WORKFLOW_PATH = ".github/workflows/qikvrt_required_review_gate.yml"
RECEIPT_SCHEMA = "qikvrt_mesh_repository_review_receipt_v1"
TECHNICAL_CONTINUE = "TECHNICAL_CONTINUE"
DELEGATION_SCHEMA = "qikvrt_owner_native_account_review_automation_v1"
DELEGATION_ID = "OWNER-NATIVE-ACCOUNT-REVIEW-AUTOMATION-V1"
DELEGATION_ACTIVE = "ACTIVE"
SECRET_ENVIRONMENT = "qikvrt-native-review-authority"
SECRET_ENVIRONMENT_NAMES = (
    "QIKVRT_ENV_GOLDKELCH_REVIEW_TOKEN",
    "QIKVRT_ENV_INGOLF_LOHMANN_REVIEW_TOKEN",
    "QIKVRT_ENV_NATIVE_ACCOUNT_REVIEW_ACTIVATION",
)
FORBIDDEN_BROAD_SECRET_NAMES = SECRET_ENVIRONMENT_NAMES + (
    "QIKVRT_GOLDKELCH_REVIEW_TOKEN",
    "QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN",
    "QIKVRT_NATIVE_ACCOUNT_REVIEW_ACTIVATION",
)
REPOSITORIES = ("Goldkelch/qik-vrt", "ingolf-lohmann/qik-vrt")
ACCOUNTS = ("Goldkelch", "ingolf-lohmann")
ALLOWED_PERMISSIONS = {"write", "maintain", "admin"}
NO_EFFECT = "NO_EFFECT"
DECISIVE_REVIEW_STATES = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
MANUAL_REVIEW_GUARD = "PRE_EFFECT_ABSENCE_AND_POST_EFFECT_ORDERING_REQUIRED"
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
TRUSTED_EXECUTOR_PATH = ".github/workflows/qikvrt_requested_review_executor.yml"
TRUSTED_EXECUTOR_EVENTS = frozenset(
    {"pull_request_target", "issue_comment", "workflow_run", "workflow_dispatch"}
)
TRUSTED_EXECUTOR_ARTIFACT_PATTERN = re.compile(
    r"^qikvrt-mesh-review-pr-([1-9][0-9]*)-([0-9a-f]{40})-"
    r"([0-9a-f]{64})-run-([1-9][0-9]*)-attempt-([1-9][0-9]*)$"
)
PRODUCER_BINDING_SCHEMA = "qikvrt_mesh_review_producer_binding_v1"
PRODUCER_BINDING_FILES = frozenset(
    {"review.json", "review.diff", "ledger-write.json", "review-transport.json"}
)
DELEGATED_REVIEW_MARKER_PATTERN = re.compile(
    rf"^<!-- {re.escape(MARKER)} fingerprint=([0-9a-f]{{64}}) "
    r"head=([0-9a-f]{40}) tree=([0-9a-f]{40}) "
    r"event=(TECHNICAL_CONTINUE|REQUEST_CHANGES|COMMENT) "
    r"run=([1-9][0-9]*) attempt=([1-9][0-9]*) "
    r"evaluator=([0-9a-f]{40}) -->$"
)
SIGNER_RECEIPT_ARTIFACT_PATTERN = re.compile(
    r"^qikvrt-native-review-signer-receipt-(Goldkelch|ingolf-lohmann)-"
    r"pr-([1-9][0-9]*)-head-([0-9a-f]{40})-run-([1-9][0-9]*)-"
    r"attempt-([1-9][0-9]*)$"
)


class NativeAccountReviewError(ValueError):
    """Raised for malformed, incomplete, or non-canonical review evidence."""


def trusted_executor_run_is_valid(
    run: Mapping[str, Any],
    workflow: Mapping[str, Any],
    repository: str,
    trusted_main_sha: str,
    expected_run_id: int,
    expected_run_attempt: int,
) -> bool:
    """Bind an upstream executor run to the trusted workflow, not its run title.

    GitHub's custom ``run-name`` is presentation data and can differ from the
    workflow's stable ``name``.  Native-account planning therefore admits an
    upstream run only when its workflow id resolves to the exact trusted path
    in the role-local repository and its event and conclusion are eligible.
    """
    if not isinstance(run, Mapping) or not isinstance(workflow, Mapping):
        return False
    if not isinstance(repository, str) or repository.count("/") != 1:
        return False
    if (
        not isinstance(trusted_main_sha, str)
        or len(trusted_main_sha) != 40
        or any(character not in "0123456789abcdef" for character in trusted_main_sha)
    ):
        return False
    run_workflow_id = run.get("workflow_id")
    workflow_id = workflow.get("id")
    if (
        isinstance(expected_run_id, bool)
        or not isinstance(expected_run_id, int)
        or expected_run_id < 1
        or isinstance(expected_run_attempt, bool)
        or not isinstance(expected_run_attempt, int)
        or expected_run_attempt < 1
        or isinstance(run_workflow_id, bool)
        or not isinstance(run_workflow_id, int)
        or run_workflow_id < 1
        or isinstance(workflow_id, bool)
        or not isinstance(workflow_id, int)
        or workflow_id < 1
    ):
        return False
    run_repository = run.get("repository")
    return (
        run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and run.get("event") in TRUSTED_EXECUTOR_EVENTS
        and run.get("id") == expected_run_id
        and run.get("run_attempt") == expected_run_attempt
        and run_workflow_id == workflow_id
        and workflow.get("path") == TRUSTED_EXECUTOR_PATH
        and run.get("path") == TRUSTED_EXECUTOR_PATH
        and run.get("head_branch") == "main"
        and run.get("head_sha") == trusted_main_sha
        and isinstance(run_repository, Mapping)
        and run_repository.get("full_name") == repository
    )


def verify_current_trusted_executor_attempt(
    *,
    repository: str,
    trusted_main_sha: str,
    current_main: Mapping[str, Any],
    run: Mapping[str, Any],
    workflow: Mapping[str, Any],
    selection: Mapping[str, Any],
    artifact_pages: Sequence[Any],
    producer_binding: Mapping[str, Any],
    files: Mapping[str, bytes],
) -> dict[str, Any]:
    """Revalidate the selected producer attempt immediately before effect."""
    if not isinstance(current_main, Mapping) or current_main.get("sha") != trusted_main_sha:
        raise NativeAccountReviewError("CURRENT_TRUSTED_MAIN_DRIFT")
    if not isinstance(selection, Mapping):
        raise NativeAccountReviewError("UPSTREAM_EXECUTOR_SELECTION_INVALID")
    run_id = selection.get("upstream_run_id")
    run_attempt = selection.get("upstream_run_attempt")
    if not trusted_executor_run_is_valid(
        run,
        workflow,
        repository,
        trusted_main_sha,
        run_id,
        run_attempt,
    ):
        raise NativeAccountReviewError("UPSTREAM_EXECUTOR_ATTEMPT_NO_LONGER_CURRENT")
    if selection.get("upstream_event") != run.get("event"):
        raise NativeAccountReviewError("UPSTREAM_EXECUTOR_EVENT_DRIFT")
    artifact = select_trusted_executor_artifact(run, artifact_pages)
    bound_fields = (
        "artifact_id",
        "artifact_name",
        "artifact_digest",
        "artifact_pr_number",
        "artifact_head",
        "artifact_fingerprint",
        "producer_run_id",
        "producer_run_attempt",
        "artifact_total_count",
    )
    if any(selection.get(field) != artifact.get(field) for field in bound_fields):
        raise NativeAccountReviewError("UPSTREAM_EXECUTOR_ARTIFACT_ATTEMPT_DRIFT")
    if (
        selection.get("producer_run_id") != run_id
        or selection.get("producer_run_attempt") != run_attempt
    ):
        raise NativeAccountReviewError("UPSTREAM_EXECUTOR_SELECTION_ATTEMPT_DRIFT")
    verify_trusted_executor_producer_binding(
        producer_binding,
        repository=repository,
        run_id=run_id,
        run_attempt=run_attempt,
        artifact_name=selection.get("artifact_name"),
        pr_number=selection.get("artifact_pr_number"),
        head_sha=selection.get("artifact_head"),
        evidence_fingerprint=selection.get("artifact_fingerprint"),
        files=files,
    )
    return {
        "schema": "qikvrt_current_executor_attempt_reobservation_v1",
        "exact": True,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "artifact_id": artifact["artifact_id"],
        "artifact_name": artifact["artifact_name"],
        "trusted_main_sha": trusted_main_sha,
    }


def select_trusted_executor_artifact(
    run: Mapping[str, Any],
    pages: Sequence[Any],
) -> dict[str, Any]:
    """Select one complete exact-attempt executor evidence artifact.

    The run-scoped artifacts endpoint can retain artifacts from older rerun
    attempts.  Callers must therefore provide every paginated page and bind
    the artifact's immutable name to both the run id and current attempt.
    """
    if not isinstance(run, Mapping):
        raise NativeAccountReviewError("UPSTREAM_EXECUTOR_RUN_INVALID")
    run_id = run.get("id")
    run_attempt = run.get("run_attempt")
    if (
        isinstance(run_id, bool)
        or not isinstance(run_id, int)
        or run_id < 1
        or isinstance(run_attempt, bool)
        or not isinstance(run_attempt, int)
        or run_attempt < 1
    ):
        raise NativeAccountReviewError("UPSTREAM_EXECUTOR_ATTEMPT_INVALID")
    if not isinstance(pages, Sequence) or isinstance(pages, (str, bytes)) or not pages:
        raise NativeAccountReviewError("UPSTREAM_EXECUTOR_ARTIFACT_PAGES_INVALID")

    artifacts: list[Mapping[str, Any]] = []
    declared_counts: set[int] = set()
    artifact_ids: set[int] = set()
    for page in pages:
        if not isinstance(page, Mapping):
            raise NativeAccountReviewError("UPSTREAM_EXECUTOR_ARTIFACT_PAGE_INVALID")
        total_count = page.get("total_count")
        raw_artifacts = page.get("artifacts")
        if (
            isinstance(total_count, bool)
            or not isinstance(total_count, int)
            or total_count < 0
            or not isinstance(raw_artifacts, Sequence)
            or isinstance(raw_artifacts, (str, bytes))
        ):
            raise NativeAccountReviewError("UPSTREAM_EXECUTOR_ARTIFACT_PAGE_INVALID")
        declared_counts.add(total_count)
        for artifact in raw_artifacts:
            if not isinstance(artifact, Mapping):
                raise NativeAccountReviewError("UPSTREAM_EXECUTOR_ARTIFACT_INVALID")
            artifact_id = artifact.get("id")
            if (
                isinstance(artifact_id, bool)
                or not isinstance(artifact_id, int)
                or artifact_id < 1
                or artifact_id in artifact_ids
            ):
                raise NativeAccountReviewError(
                    "UPSTREAM_EXECUTOR_ARTIFACT_ID_MISSING_OR_AMBIGUOUS"
                )
            artifact_ids.add(artifact_id)
            artifacts.append(artifact)
    if len(declared_counts) != 1 or declared_counts != {len(artifacts)}:
        raise NativeAccountReviewError(
            "UPSTREAM_EXECUTOR_ARTIFACT_TOTAL_COUNT_INCOMPLETE"
        )

    matches: list[tuple[Mapping[str, Any], re.Match[str]]] = []
    for artifact in artifacts:
        if artifact.get("expired") is True:
            continue
        name = artifact.get("name")
        match = (
            TRUSTED_EXECUTOR_ARTIFACT_PATTERN.fullmatch(name)
            if isinstance(name, str)
            else None
        )
        if (
            match is not None
            and int(match.group(4)) == run_id
            and int(match.group(5)) == run_attempt
        ):
            matches.append((artifact, match))
    if len(matches) != 1:
        raise NativeAccountReviewError(
            "UPSTREAM_EXECUTOR_ARTIFACT_MISSING_OR_AMBIGUOUS"
        )
    artifact, match = matches[0]
    artifact_digest = artifact.get("digest")
    if (
        not isinstance(artifact_digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", artifact_digest) is None
    ):
        raise NativeAccountReviewError("UPSTREAM_EXECUTOR_ARTIFACT_DIGEST_INVALID")
    return {
        "artifact": dict(artifact),
        "artifact_id": artifact["id"],
        "artifact_name": artifact["name"],
        "artifact_digest": artifact_digest,
        "artifact_pr_number": int(match.group(1)),
        "artifact_head": match.group(2),
        "artifact_fingerprint": match.group(3),
        "producer_run_id": int(match.group(4)),
        "producer_run_attempt": int(match.group(5)),
        "artifact_total_count": len(artifacts),
    }


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


def build_trusted_executor_producer_binding(
    *,
    repository: str,
    run_id: int,
    run_attempt: int,
    artifact_name: str,
    pr_number: int,
    head_sha: str,
    evidence_fingerprint: str,
    files: Mapping[str, bytes],
) -> dict[str, Any]:
    """Seal one artifact-local transport envelope without changing receipt bytes."""
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise NativeAccountReviewError("producer binding repository is invalid")
    if (
        isinstance(run_id, bool)
        or not isinstance(run_id, int)
        or run_id < 1
        or isinstance(run_attempt, bool)
        or not isinstance(run_attempt, int)
        or run_attempt < 1
        or isinstance(pr_number, bool)
        or not isinstance(pr_number, int)
        or pr_number < 1
    ):
        raise NativeAccountReviewError("producer binding numeric identity is invalid")
    head_sha = _sha1(head_sha, "producer binding head")
    evidence_fingerprint = _sha256_text(
        evidence_fingerprint, "producer binding fingerprint"
    )
    match = (
        TRUSTED_EXECUTOR_ARTIFACT_PATTERN.fullmatch(artifact_name)
        if isinstance(artifact_name, str)
        else None
    )
    if (
        match is None
        or int(match.group(1)) != pr_number
        or match.group(2) != head_sha
        or match.group(3) != evidence_fingerprint
        or int(match.group(4)) != run_id
        or int(match.group(5)) != run_attempt
    ):
        raise NativeAccountReviewError(
            "producer binding artifact name differs from exact subject attempt"
        )
    if not isinstance(files, Mapping) or set(files) != PRODUCER_BINDING_FILES:
        raise NativeAccountReviewError("producer binding file set is incomplete")
    file_bindings: dict[str, dict[str, Any]] = {}
    for name in sorted(PRODUCER_BINDING_FILES):
        content = files.get(name)
        if not isinstance(content, bytes):
            raise NativeAccountReviewError(
                f"producer binding file bytes are invalid: {name}"
            )
        file_bindings[name] = {
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
    result: dict[str, Any] = {
        "schema": PRODUCER_BINDING_SCHEMA,
        "repository": repository,
        "workflow_path": TRUSTED_EXECUTOR_PATH,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "artifact_name": artifact_name,
        "pr_number": pr_number,
        "head_sha": head_sha,
        "evidence_fingerprint": evidence_fingerprint,
        "files": file_bindings,
    }
    result["binding_payload_sha256"] = _sha256(result)
    return result


def verify_trusted_executor_producer_binding(
    binding: Mapping[str, Any],
    **expected: Any,
) -> dict[str, Any]:
    if not isinstance(binding, Mapping):
        raise NativeAccountReviewError("producer binding must be an object")
    canonical = build_trusted_executor_producer_binding(**expected)
    if dict(binding) != canonical:
        raise NativeAccountReviewError(
            "producer binding differs from exact artifact bytes or attempt"
        )
    return canonical


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


def canonical_review_inventory(
    value: Any, label: str = "reviews"
) -> list[dict[str, Any]]:
    """Validate a complete caller-supplied review inventory."""
    values = _list(value, label)
    result: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in values:
        item = _mapping(raw, f"{label} item")
        identifier = item.get("id")
        if (
            isinstance(identifier, bool)
            or not isinstance(identifier, int)
            or identifier < 1
            or identifier in seen
        ):
            raise NativeAccountReviewError(
                f"{label} contains an invalid or duplicate review id"
            )
        seen.add(identifier)
        result.append(dict(item))
    return result


def flatten_review_pages(value: Any) -> list[dict[str, Any]]:
    """Flatten one exact ``gh api --paginate --slurp`` review response.

    The list-reviews endpoint has no declared total.  We therefore make no
    absence claim beyond the pages GitHub returned, but we do reject malformed
    pages and offset-shift duplicates before a signer or status effect can use
    the observation.
    """
    if not isinstance(value, list) or not value:
        raise NativeAccountReviewError(
            "review pagination must be a non-empty list of pages"
        )
    flattened: list[Mapping[str, Any]] = []
    for page in value:
        if not isinstance(page, list) or len(page) > 100:
            raise NativeAccountReviewError("review pagination page is malformed")
        for raw in page:
            if not isinstance(raw, Mapping):
                raise NativeAccountReviewError(
                    "review pagination item is not an object"
                )
            flattened.append(raw)
    return canonical_review_inventory(flattened, "review pagination")


def _counterpart(author: str) -> str:
    matches = [account for account in ACCOUNTS if account.casefold() == author.casefold()]
    if len(matches) != 1:
        raise NativeAccountReviewError("PULL_REQUEST_AUTHOR_NOT_CONFIGURED_REPOSITORY_ACCOUNT")
    candidates = [account for account in ACCOUNTS if account.casefold() != author.casefold()]
    if len(candidates) != 1:
        raise NativeAccountReviewError("REPOSITORY_REVIEWER_COUNTERPART_AMBIGUOUS")
    return candidates[0]


def _planned_review_effect(disposition: str) -> str:
    return {
        TECHNICAL_CONTINUE: TECHNICAL_CONTINUE,
        "REQUEST_CHANGES": "REQUEST_CHANGES",
        # A technical blocker may use GitHub's negative review state, but a
        # technical continuation is always a non-decisive COMMENT.
        "COMMENT_WITH_BLOCKER": "REQUEST_CHANGES",
        "WAIT": NO_EFFECT,
    }.get(disposition, NO_EFFECT)


def _native_review_event_after_preflight(effect: str) -> str:
    """Map technical evidence without manufacturing approval Authority."""
    try:
        return {
            TECHNICAL_CONTINUE: "COMMENT",
            "REQUEST_CHANGES": "REQUEST_CHANGES",
            "COMMENT": "COMMENT",
        }[effect]
    except KeyError as exc:
        raise NativeAccountReviewError(
            "technical review effect has no native event mapping"
        ) from exc


def _expected_platform_review_state(event: str) -> str:
    try:
        return {
            "APPROVE": "APPROVED",
            "REQUEST_CHANGES": "CHANGES_REQUESTED",
            "COMMENT": "COMMENTED",
        }[event]
    except KeyError as exc:
        raise NativeAccountReviewError("native account review event is not effectful") from exc


def _expected_platform_review_state_for_effect(effect: str) -> str:
    try:
        return {
            TECHNICAL_CONTINUE: "COMMENTED",
            "REQUEST_CHANGES": "CHANGES_REQUESTED",
            "COMMENT": "COMMENTED",
        }[effect]
    except KeyError as exc:
        raise NativeAccountReviewError(
            "technical review effect is not effectful"
        ) from exc


def _delegated_review_body(
    *,
    base_sha: str,
    head_sha: str,
    tree_sha: str,
    fingerprint: str,
    disposition: str,
    reviewer: str,
    event: str,
    stale_approval_retraction: bool,
    retraction_only: bool,
    signer_run_id: int,
    signer_run_attempt: int,
    signer_evaluator_sha: str,
) -> str:
    if (
        isinstance(signer_run_id, bool)
        or not isinstance(signer_run_id, int)
        or signer_run_id < 1
        or isinstance(signer_run_attempt, bool)
        or not isinstance(signer_run_attempt, int)
        or signer_run_attempt < 1
    ):
        raise NativeAccountReviewError("native signer run identity is invalid")
    signer_evaluator_sha = _sha1(
        signer_evaluator_sha, "native signer evaluator SHA"
    )
    return "\n".join(
        [
            f"<!-- {MARKER} fingerprint={fingerprint} head={head_sha} tree={tree_sha} "
            f"event={event} run={signer_run_id} attempt={signer_run_attempt} "
            f"evaluator={signer_evaluator_sha} -->",
            "QIKVRT delegated native-account review.",
            "",
            f"- exact base: `{base_sha}`",
            f"- exact head: `{head_sha}`",
            f"- exact tree: `{tree_sha}`",
            f"- evidence fingerprint: `{fingerprint}`",
            f"- Technical disposition: `{disposition}`",
            f"- platform signer requested: `{reviewer}`",
            "- signer mode: `DELEGATED_NATIVE_ACCOUNT_AUTOMATION`",
            "- stale delegated approval observed at plan: "
            f"`{str(stale_approval_retraction).lower()}`",
            f"- retraction-only projection: `{str(retraction_only).lower()}`",
            "",
            "This is a transparently delegated platform-account action, not an independent natural-person review. It does not authorize merge, deployment, publication, PASS, FINAL_PASS, or EFFECT_ACK_DONE.",
        ]
    )


def parse_delegated_review_locator(body: Any) -> dict[str, Any] | None:
    """Parse only the exact immutable signer locator from a canonical body."""
    if not isinstance(body, str):
        return None
    first_line = body.split("\n", 1)[0]
    match = DELEGATED_REVIEW_MARKER_PATTERN.fullmatch(first_line)
    if match is None:
        return None
    fingerprint, head, tree, event, run_id, run_attempt, evaluator = match.groups()
    return {
        "evidence_fingerprint": fingerprint,
        "head_sha": head,
        "tree_sha": tree,
        "event": event,
        "signer_run_id": int(run_id),
        "signer_run_attempt": int(run_attempt),
        "signer_evaluator_sha": evaluator,
    }


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
    signer_run_id: int | None = None,
    signer_run_attempt: int | None = None,
    signer_evaluator_sha: str | None = None,
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
        "manual_review_guard": MANUAL_REVIEW_GUARD,
        "stale_approval_retraction": False,
        "retraction_only": False,
        "active_requested_counterpart_required": False,
        "delegation": "DELEGATED_NATIVE_ACCOUNT_AUTOMATION",
        "delegation_state": delegation_state,
        "delegation_sha256": delegation_sha256,
        "signer_run_id": signer_run_id,
        "signer_run_attempt": signer_run_attempt,
        "signer_evaluator_sha": signer_evaluator_sha,
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
    activation = _mapping(
        value.get("activation_boundary"), "owner delegation activation"
    )
    receipt = activation.get("external_readback_receipt")
    owner = receipt.get("repository_owner") if isinstance(receipt, Mapping) else None
    owner_type = owner.get("type") if isinstance(owner, Mapping) else None
    organization_absent = (
        receipt.get("organization_scope_secret_names_absent")
        if isinstance(receipt, Mapping) else None
    )
    organization_scope = (
        receipt.get("organization_scope_readback")
        if isinstance(receipt, Mapping) else None
    )
    owner_valid = (
        isinstance(owner, Mapping)
        and owner.get("login") == repository.split("/", 1)[0]
        and isinstance(owner.get("id"), int)
        and not isinstance(owner.get("id"), bool)
        and owner.get("id") > 0
        and owner_type in {"User", "Organization"}
    )
    organization_scope_valid = (
        owner_type == "User"
        and organization_scope == "NOT_APPLICABLE_USER_OWNER"
        and organization_absent == []
    ) or (
        owner_type == "Organization"
        and organization_scope == "VERIFIED_ORGANIZATION_SECRET_INVENTORY"
        and sorted(organization_absent or [])
        == sorted(FORBIDDEN_BROAD_SECRET_NAMES)
    )
    if (
        activation.get("external_configuration_verified") is not True
        or not isinstance(receipt, Mapping)
        or receipt.get("schema")
        != "qikvrt_native_review_secret_environment_readback_v1"
        or receipt.get("environment") != SECRET_ENVIRONMENT
        or receipt.get("deployment_branch_policy")
        != "SELECTED_BRANCHES_ONLY"
        or receipt.get("selected_branch") != "main"
        or receipt.get("protected_branches") is not True
        or sorted(receipt.get("environment_secret_names") or [])
        != sorted(SECRET_ENVIRONMENT_NAMES)
        or sorted(receipt.get("repository_scope_secret_names_absent") or [])
        != sorted(FORBIDDEN_BROAD_SECRET_NAMES)
        or not owner_valid
        or not organization_scope_valid
        or receipt.get("settings_readback_complete") is not True
        or not isinstance(receipt.get("verified_at"), str)
        or not receipt.get("verified_at")
        or not isinstance(receipt.get("verifier_login"), str)
        or not receipt.get("verifier_login")
    ):
        raise NativeAccountReviewError(
            "AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED"
        )
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
    if event not in {
        NO_EFFECT,
        TECHNICAL_CONTINUE,
        "REQUEST_CHANGES",
        "COMMENT",
    }:
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
        active_request_required and event != TECHNICAL_CONTINUE
    ):
        raise NativeAccountReviewError("native account review active-request state is invalid")
    if event == NO_EFFECT:
        if (
            candidate.get("reviewer") is not None
            or candidate.get("review_body") is not None
            or candidate.get("signer_run_id") is not None
            or candidate.get("signer_run_attempt") is not None
            or candidate.get("signer_evaluator_sha") is not None
        ):
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
        run_id = candidate.get("signer_run_id")
        run_attempt = candidate.get("signer_run_attempt")
        if (
            isinstance(run_id, bool)
            or not isinstance(run_id, int)
            or run_id < 1
            or isinstance(run_attempt, bool)
            or not isinstance(run_attempt, int)
            or run_attempt < 1
        ):
            raise NativeAccountReviewError("native signer run identity is invalid")
        evaluator = _sha1(
            candidate.get("signer_evaluator_sha"), "native signer evaluator SHA"
        )
        locator = parse_delegated_review_locator(candidate["review_body"])
        if (
            locator is None
            or locator["evidence_fingerprint"]
            != candidate["evidence_fingerprint"]
            or locator["head_sha"] != candidate["head_sha"]
            or locator["tree_sha"] != candidate["tree_sha"]
            or locator["event"] != event
            or locator["signer_run_id"] != run_id
            or locator["signer_run_attempt"] != run_attempt
            or locator["signer_evaluator_sha"] != evaluator
        ):
            raise NativeAccountReviewError("native signer body locator differs from plan")
        if candidate.get("delegation_state") != DELEGATION_ACTIVE:
            raise NativeAccountReviewError("native account review delegation is not active")
        _sha256_text(candidate.get("delegation_sha256"), "plan delegation_sha256")
    if candidate.get("delegation") != "DELEGATED_NATIVE_ACCOUNT_AUTOMATION":
        raise NativeAccountReviewError("native account review delegation is invalid")
    if candidate.get("manual_review_guard") != MANUAL_REVIEW_GUARD:
        raise NativeAccountReviewError("native account manual review guard is invalid")
    if "manual_review_preserved" in candidate:
        raise NativeAccountReviewError("native account plan must not preclaim manual review preservation")
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
    state = receipt.get("state")
    if state == "APPROVE" or receipt.get("mesh_disposition") == "APPROVE":
        return "LEGACY_TECHNICAL_APPROVE_RECEIPT", values
    if (
        not isinstance(state, str)
        or state != receipt.get("mesh_disposition")
        or state not in {
            TECHNICAL_CONTINUE,
            "REQUEST_CHANGES",
            "COMMENT_WITH_BLOCKER",
            "WAIT",
        }
    ):
        return "RECEIPT_TECHNICAL_DISPOSITION_INVALID", values
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
    reviews: Sequence[Mapping[str, Any]],
    reviewer: str,
    head: str,
    expected_body: str,
    expected_state: str,
) -> bool:
    """Match the exact sealed projection, including non-decisive comments.

    TECHNICAL_CONTINUE is deliberately projected as COMMENTED.  Restricting
    idempotency to decisive reviews would therefore post the same technical
    observation again on every retry.
    """
    for raw in reviews:
        review = _mapping(raw, "review observation item")
        user = review.get("user")
        if (
            isinstance(user, Mapping)
            and isinstance(user.get("login"), str)
            and user["login"].casefold() == reviewer.casefold()
            and review.get("commit_id") == head
            and str(review.get("state") or "").upper() == expected_state
            and review.get("body") == expected_body
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


def _latest_target_review(
    reviews: Sequence[Mapping[str, Any]], reviewer: str, head: str
) -> Mapping[str, Any] | None:
    """Return the latest exact-head review of any state for one account."""
    selected: list[tuple[str, int, Mapping[str, Any]]] = []
    for raw in reviews:
        review = _mapping(raw, "review observation item")
        user = review.get("user")
        if (
            not isinstance(user, Mapping)
            or not isinstance(user.get("login"), str)
            or user["login"].casefold() != reviewer.casefold()
            or review.get("commit_id") != head
        ):
            continue
        review_id = review.get("id")
        submitted_at = review.get("submitted_at")
        if (
            isinstance(review_id, bool)
            or not isinstance(review_id, int)
            or review_id < 1
            or not isinstance(submitted_at, str)
            or not submitted_at
        ):
            raise NativeAccountReviewError(
                "target review ordering identity is ambiguous"
            )
        selected.append((submitted_at, review_id, review))
    return max(selected, default=("", 0, None), key=lambda item: item[:2])[2]


def _adoptable_unreceipted_review(
    reviews: Sequence[Mapping[str, Any]],
    *,
    plan: Mapping[str, Any],
    reviewer: str,
    current_signer_run_id: int,
    current_signer_run_attempt: int,
) -> tuple[Mapping[str, Any] | None, str | None]:
    """Find the sole exact review left by an earlier attempt of this run.

    This is deliberately narrower than ordinary idempotency.  It exists only
    for the POST -> runner-loss window: a later attempt of the *same* signer
    run may receipt the exact marked review without posting another review.
    """
    if (
        current_signer_run_id != plan.get("signer_run_id")
        or isinstance(current_signer_run_attempt, bool)
        or not isinstance(current_signer_run_attempt, int)
        or current_signer_run_attempt < plan.get("signer_run_attempt", 0)
    ):
        return None, None
    expected_state = _expected_platform_review_state_for_effect(plan["event"])
    planned_locator = parse_delegated_review_locator(plan.get("review_body"))
    if planned_locator is None:
        return None, "UNRECEIPTED_DELEGATED_REVIEW_PLAN_LOCATOR_INVALID"
    planned_tail = plan["review_body"].split("\n", 1)[1]
    exact: list[Mapping[str, Any]] = []
    for raw in reviews:
        review = _mapping(raw, "review observation item")
        user = review.get("user")
        if (
            isinstance(user, Mapping)
            and isinstance(user.get("login"), str)
            and user["login"].casefold() == reviewer.casefold()
            and user.get("type") == "User"
            and review.get("commit_id") == plan["head_sha"]
            and str(review.get("state") or "").upper() == expected_state
            and isinstance(review.get("body"), str)
        ):
            locator = parse_delegated_review_locator(review.get("body"))
            if (
                locator is not None
                and locator["signer_run_id"] == plan["signer_run_id"]
                and locator["signer_run_attempt"]
                <= plan["signer_run_attempt"]
                and locator["signer_run_attempt"] < current_signer_run_attempt
                and locator["signer_evaluator_sha"]
                == plan["signer_evaluator_sha"]
                and locator["evidence_fingerprint"]
                == planned_locator["evidence_fingerprint"]
                and locator["head_sha"] == planned_locator["head_sha"]
                and locator["tree_sha"] == planned_locator["tree_sha"]
                and locator["event"] == planned_locator["event"]
                and review["body"].split("\n", 1)[1] == planned_tail
            ):
                exact.append(review)
    if not exact:
        return None, None
    if len(exact) != 1:
        return None, "UNRECEIPTED_DELEGATED_REVIEW_AMBIGUOUS"
    candidate = exact[0]
    review_id = candidate.get("id")
    submitted_at = candidate.get("submitted_at")
    if (
        isinstance(review_id, bool)
        or not isinstance(review_id, int)
        or review_id < 1
        or not isinstance(submitted_at, str)
        or not submitted_at
    ):
        return None, "UNRECEIPTED_DELEGATED_REVIEW_IDENTITY_INVALID"
    if _manual_target_review_present(reviews, reviewer, plan["head_sha"]):
        return None, "MANUAL_TARGET_REVIEW_PRESENT"
    try:
        latest = _latest_target_review(reviews, reviewer, plan["head_sha"])
    except NativeAccountReviewError:
        return None, "UNRECEIPTED_DELEGATED_REVIEW_ORDER_DRIFT"
    if latest is None or latest.get("id") != review_id:
        return None, "UNRECEIPTED_DELEGATED_REVIEW_ORDER_DRIFT"
    return candidate, None


def _canonical_delegated_decisive_review(
    review: Mapping[str, Any],
    *,
    reviewer: str,
    base_sha: str,
    head_sha: str,
    tree_sha: str,
) -> bool:
    """Recognize only an exact body that this trusted planner can produce."""
    body = review.get("body")
    state = str(review.get("state") or "").upper()
    user = review.get("user")
    if (
        not isinstance(body, str)
        or not isinstance(user, Mapping)
        or not isinstance(user.get("login"), str)
        or user["login"].casefold() != reviewer.casefold()
        or review.get("commit_id") != head_sha
        or state not in {"COMMENTED", "APPROVED", "CHANGES_REQUESTED"}
    ):
        return False
    locator = parse_delegated_review_locator(body)
    if (
        locator is None
        or locator["head_sha"] != head_sha
        or locator["tree_sha"] != tree_sha
    ):
        return False
    fingerprint = locator["evidence_fingerprint"]
    event = locator["event"]
    expected_state = (
        _expected_platform_review_state_for_effect(event)
        if event == TECHNICAL_CONTINUE
        else _expected_platform_review_state(event)
    )
    if expected_state != state:
        return False
    if event == TECHNICAL_CONTINUE:
        dispositions = (TECHNICAL_CONTINUE,)
    elif event == "APPROVE":
        dispositions = ("APPROVE",)
    else:
        dispositions = (
            "REQUEST_CHANGES",
            "COMMENT_WITH_BLOCKER",
            TECHNICAL_CONTINUE,
            "APPROVE",
            "WAIT",
        )
    for disposition in dispositions:
        for stale in (False, True):
            for retraction_only in (False, True):
                if retraction_only and not stale:
                    continue
                if event in {TECHNICAL_CONTINUE, "APPROVE"} and retraction_only:
                    continue
                candidate = _delegated_review_body(
                    base_sha=base_sha,
                    head_sha=head_sha,
                    tree_sha=tree_sha,
                    fingerprint=fingerprint,
                    disposition=disposition,
                    reviewer=reviewer,
                    event=event,
                    stale_approval_retraction=stale,
                    retraction_only=retraction_only,
                    signer_run_id=locator["signer_run_id"],
                    signer_run_attempt=locator["signer_run_attempt"],
                    signer_evaluator_sha=locator["signer_evaluator_sha"],
                )
                if body == candidate:
                    return True
    return False


def _existing_delegated_review_blocker(
    reviews: Sequence[Mapping[str, Any]],
    *,
    reviewer: str,
    base_sha: str,
    head_sha: str,
    tree_sha: str,
    expected_body: str,
    expected_state: str,
) -> str | None:
    if _automated_review_present(
        reviews, reviewer, head_sha, expected_body, expected_state
    ):
        return "IDENTICAL_DELEGATED_ACCOUNT_REVIEW_ALREADY_PRESENT"
    if expected_state == "COMMENTED":
        marked_comments: list[tuple[str, int, Mapping[str, Any]]] = []
        for raw in reviews:
            candidate = _mapping(raw, "review observation item")
            user = candidate.get("user")
            body = candidate.get("body")
            if (
                isinstance(user, Mapping)
                and isinstance(user.get("login"), str)
                and user["login"].casefold() == reviewer.casefold()
                and candidate.get("commit_id") == head_sha
                and str(candidate.get("state") or "").upper() == "COMMENTED"
                and isinstance(body, str)
                and MARKER in body
            ):
                review_id = candidate.get("id")
                if (
                    isinstance(review_id, bool)
                    or not isinstance(review_id, int)
                    or review_id < 1
                ):
                    return "DELEGATED_ACCOUNT_REVIEW_BODY_OR_STATE_DRIFT"
                submitted_at = candidate.get("submitted_at")
                marked_comments.append(
                    (submitted_at if isinstance(submitted_at, str) else "", review_id, candidate)
                )
        if marked_comments:
            latest_comment = max(marked_comments, key=lambda item: item[:2])[2]
            body = latest_comment["body"]
            if not _canonical_delegated_decisive_review(
                latest_comment,
                reviewer=reviewer,
                base_sha=base_sha,
                head_sha=head_sha,
                tree_sha=tree_sha,
            ):
                return "DELEGATED_ACCOUNT_REVIEW_BODY_OR_STATE_DRIFT"
            prior_locator = parse_delegated_review_locator(body)
            expected_locator = parse_delegated_review_locator(expected_body)
            if (
                prior_locator is not None
                and expected_locator is not None
                and prior_locator["evidence_fingerprint"]
                != expected_locator["evidence_fingerprint"]
            ):
                return None
            if (
                prior_locator is not None
                and expected_locator is not None
                and prior_locator["evidence_fingerprint"]
                == expected_locator["evidence_fingerprint"]
                and prior_locator["head_sha"] == expected_locator["head_sha"]
                and prior_locator["tree_sha"] == expected_locator["tree_sha"]
                and prior_locator["event"] == expected_locator["event"]
                and body.split("\n", 1)[1] == expected_body.split("\n", 1)[1]
            ):
                return None
            return "DELEGATED_ACCOUNT_REVIEW_SAME_STATE_BODY_DRIFT"
    latest = _latest_decisive_target_review(reviews, reviewer, head_sha)
    if latest is None:
        return None
    state = str(latest.get("state") or "").upper()
    if state == "DISMISSED":
        return "DISMISSED_REVIEW_REQUIRES_AUTHORITY_REOBSERVATION"
    body = latest.get("body")
    if not (isinstance(body, str) and MARKER in body):
        return None
    locator = parse_delegated_review_locator(body)
    if (
        state == "APPROVED"
        and isinstance(locator, Mapping)
        and locator.get("event") in {TECHNICAL_CONTINUE, "APPROVE"}
    ):
        # Old automation-marked approvals are never current Authority.  They
        # neither satisfy the gate nor prevent a separately authorized current
        # technical observation.
        return None
    if not _canonical_delegated_decisive_review(
        latest,
        reviewer=reviewer,
        base_sha=base_sha,
        head_sha=head_sha,
        tree_sha=tree_sha,
    ):
        return "DELEGATED_ACCOUNT_REVIEW_BODY_OR_STATE_DRIFT"
    if state == expected_state:
        prior_fingerprint = re.search(r"fingerprint=([0-9a-f]{64})", body)
        expected_fingerprint = re.search(
            r"fingerprint=([0-9a-f]{64})", expected_body
        )
        if (
            prior_fingerprint is not None
            and expected_fingerprint is not None
            and prior_fingerprint.group(1) != expected_fingerprint.group(1)
        ):
            return None
        prior_locator = parse_delegated_review_locator(body)
        expected_locator = parse_delegated_review_locator(expected_body)
        if (
            prior_locator is not None
            and expected_locator is not None
            and prior_locator["evidence_fingerprint"]
            == expected_locator["evidence_fingerprint"]
            and prior_locator["head_sha"] == expected_locator["head_sha"]
            and prior_locator["tree_sha"] == expected_locator["tree_sha"]
            and prior_locator["event"] == expected_locator["event"]
            and body.split("\n", 1)[1] == expected_body.split("\n", 1)[1]
        ):
            # A new trusted evaluator/run may supersede only the transport
            # locator of an otherwise byte-identical canonical projection.
            # The separate manual-review guard still runs before any POST.
            return None
        return "DELEGATED_ACCOUNT_REVIEW_SAME_STATE_BODY_DRIFT"
    # A canonical opposite decisive state may be superseded only after the
    # current receipt has independently authorized the new exact projection.
    return None


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
    if event_name == "pull_request_target" and event_action in {
        "review_requested",
        "review_request_removed",
    }:
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
    signer_run_id: int,
    signer_run_attempt: int,
    signer_evaluator_sha: str,
) -> dict[str, Any]:
    """Derive one sealed no-effect or exact-account review projection.

    The caller must have retrieved all snapshots using trusted-main code.  A
    false verification bit is intentionally terminal for this projection.
    """
    pr_object = _mapping(pr, "pull request")
    commit_object = _mapping(commit, "candidate commit")
    receipt_object = _mapping(receipt, "review receipt")
    review_list = canonical_review_inventory(reviews)
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
    if (
        isinstance(signer_run_id, bool)
        or not isinstance(signer_run_id, int)
        or signer_run_id < 1
        or isinstance(signer_run_attempt, bool)
        or not isinstance(signer_run_attempt, int)
        or signer_run_attempt < 1
    ):
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="SIGNER_RUN_PROVENANCE_INVALID",
                detail="the future signer effect lacks an exact workflow run identity",
            )
        )
    try:
        signer_evaluator_sha = _sha1(
            signer_evaluator_sha, "native signer evaluator SHA"
        )
    except NativeAccountReviewError:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="SIGNER_RUN_PROVENANCE_INVALID",
                detail="the future signer effect lacks an exact trusted evaluator identity",
            )
        )
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
    event = (
        _planned_review_effect(disposition)
        if isinstance(disposition, str)
        else NO_EFFECT
    )
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
    if (
        intake.get("event_name") == "pull_request_target"
        and intake.get("event_action") == "review_request_removed"
        and live_requested_counterpart
    ):
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="STALE_REVIEW_REQUEST_REMOVAL_LIVE_TARGET_PRESENT",
                detail=(
                    "the removal delivery is older than the current live "
                    "requested-reviewer state; no prior negative projection "
                    "may override the later request"
                ),
            )
        )
    exact_active_request = exact_requested_event or (
        live_requested_counterpart and _exact_followup_event(intake)
    )
    # Historical automation-marked approvals are predecessor-only evidence.
    # They are ignored by the required gate and are never renewed, adopted or
    # retracted as part of a current TECHNICAL_CONTINUE observation.
    stale_delegated_approval = False
    retraction_only = False
    provisional_body = None
    recover_prior_attempt = False
    if event != NO_EFFECT:
        provisional_body = _delegated_review_body(
            base_sha=binding["base_sha"],
            head_sha=binding["head_sha"],
            tree_sha=binding["tree_sha"],
            fingerprint=binding["fingerprint"],
            disposition=str(disposition),
            reviewer=reviewer,
            event=event,
            stale_approval_retraction=False,
            retraction_only=False,
            signer_run_id=signer_run_id,
            signer_run_attempt=signer_run_attempt,
            signer_evaluator_sha=signer_evaluator_sha,
        )
    if event == TECHNICAL_CONTINUE and provisional_body is not None:
        candidate, _ = _adoptable_unreceipted_review(
            review_list,
            plan={
                "event": event,
                "head_sha": binding["head_sha"],
                "review_body": provisional_body,
                "signer_run_id": signer_run_id,
                "signer_run_attempt": signer_run_attempt,
                "signer_evaluator_sha": signer_evaluator_sha,
            },
            reviewer=reviewer,
            current_signer_run_id=signer_run_id,
            current_signer_run_attempt=signer_run_attempt,
        )
        recover_prior_attempt = candidate is not None
    if event == TECHNICAL_CONTINUE and not (
        exact_active_request or recover_prior_attempt
    ):
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
                detail=(
                    "a delegated technical comment requires the exact request "
                    "event, a trusted live follow-up, or adoption of the exact "
                    "same-run prior-attempt comment"
                ),
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
                detail=(
                    "a negative technical projection requires the exact active "
                    "request or trusted live follow-up; a legacy marked approval "
                    "is predecessor-only and grants no retraction authority"
                ),
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
    if event == TECHNICAL_CONTINUE and native_rule_enforced is not True:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker="CODE_OWNER_RULE_NOT_ENFORCED",
                detail=(
                    "the delegated technical comment remains fail-closed until "
                    "the independent human Code Owner rule is enforced"
                ),
            )
        )
    assert provisional_body is not None
    body = provisional_body
    delegated_blocker = _existing_delegated_review_blocker(
        review_list,
        reviewer=reviewer,
        base_sha=binding["base_sha"],
        head_sha=binding["head_sha"],
        tree_sha=binding["tree_sha"],
        expected_body=body,
        expected_state=_expected_platform_review_state_for_effect(event),
    )
    if delegated_blocker is not None:
        return _sealed(
            _base_plan(
                repository=repository,
                pr_number=binding["pr_number"],
                expected_base=binding["base_sha"],
                expected_head=binding["head_sha"],
                expected_tree=binding["tree_sha"],
                fingerprint=binding["fingerprint"],
                first_blocker=delegated_blocker,
                detail=(
                    "the exact delegated account projection is already present"
                    if delegated_blocker
                    == "IDENTICAL_DELEGATED_ACCOUNT_REVIEW_ALREADY_PRESENT"
                    else "an existing delegated or dismissed review requires Authority reobservation before another automated decisive state"
                ),
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
                    "all trusted-main exact evidence permits one non-decisive "
                    "delegated technical counterpart observation"
                ),
            ),
            "reviewer": reviewer,
            "event": event,
            "effect_permitted": True,
            "review_body": body,
            "stale_approval_retraction": stale_delegated_approval,
            "retraction_only": retraction_only,
            "active_requested_counterpart_required": event == TECHNICAL_CONTINUE,
            "delegation_state": delegation_info["state"],
            "delegation_sha256": delegation_info["sha256"],
            "signer_run_id": signer_run_id,
            "signer_run_attempt": signer_run_attempt,
            "signer_evaluator_sha": signer_evaluator_sha,
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
    current_signer_run_id: int | None = None,
    current_signer_run_attempt: int | None = None,
    current_signer_evaluator_sha: str | None = None,
) -> dict[str, Any]:
    """Revalidate an effect plan immediately before the only review mutation."""
    value = validate_plan(plan)
    if expected_signer not in ACCOUNTS:
        raise NativeAccountReviewError("expected signer is not configured")
    if value["event"] == NO_EFFECT:
        return {"action": NO_EFFECT, "first_blocker": value.get("first_blocker"), "plan_sha256": value["plan_sha256"]}
    if value["reviewer"] != expected_signer:
        return {"action": NO_EFFECT, "first_blocker": "SIGNER_JOB_TARGET_MISMATCH", "plan_sha256": value["plan_sha256"]}
    # Network-free callers may omit these and evaluate the plan's own sealed
    # provenance.  The effect workflow CLI makes all three actual run values
    # mandatory and passes them explicitly.
    if current_signer_run_id is None:
        current_signer_run_id = value["signer_run_id"]
    if current_signer_run_attempt is None:
        current_signer_run_attempt = value["signer_run_attempt"]
    if current_signer_evaluator_sha is None:
        current_signer_evaluator_sha = value["signer_evaluator_sha"]
    if (
        current_signer_run_id != value["signer_run_id"]
        or isinstance(current_signer_run_attempt, bool)
        or not isinstance(current_signer_run_attempt, int)
        or current_signer_run_attempt < value["signer_run_attempt"]
        or current_signer_evaluator_sha != value["signer_evaluator_sha"]
    ):
        return {
            "action": NO_EFFECT,
            "first_blocker": "SIGNER_EXECUTION_PROVENANCE_DRIFT",
            "plan_sha256": value["plan_sha256"],
        }
    try:
        delegation_info = _delegation_info(delegation, value["repository"])
    except NativeAccountReviewError as exc:
        return {"action": NO_EFFECT, "first_blocker": str(exc), "plan_sha256": value["plan_sha256"]}
    if delegation_info["sha256"] != value.get("delegation_sha256"):
        return {"action": NO_EFFECT, "first_blocker": "PRE_EFFECT_DELEGATION_DRIFT", "plan_sha256": value["plan_sha256"]}
    if reobservation_exact is not True:
        return {"action": NO_EFFECT, "first_blocker": "PRE_EFFECT_CAUSAL_REOBSERVATION_DRIFT", "plan_sha256": value["plan_sha256"]}
    if value["event"] == TECHNICAL_CONTINUE and native_rule_enforced is not True:
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
    review_list = canonical_review_inventory(reviews)
    adoptable, adoption_blocker = _adoptable_unreceipted_review(
        review_list,
        plan=value,
        reviewer=expected_signer,
        current_signer_run_id=current_signer_run_id,
        current_signer_run_attempt=current_signer_run_attempt,
    )
    if adoption_blocker is not None:
        return {
            "action": NO_EFFECT,
            "first_blocker": adoption_blocker,
            "plan_sha256": value["plan_sha256"],
        }
    if value["active_requested_counterpart_required"]:
        requested_reviewers = pr_object.get("requested_reviewers")
        still_requested = isinstance(requested_reviewers, list) and any(
            isinstance(item, Mapping)
            and isinstance(item.get("login"), str)
            and item["login"].casefold() == expected_signer.casefold()
            for item in requested_reviewers
        )
        if not still_requested and adoptable is None:
            return {
                "action": NO_EFFECT,
                "first_blocker": "PRE_EFFECT_REQUESTED_REVIEWER_DRIFT",
                "plan_sha256": value["plan_sha256"],
            }
    if adoptable is not None:
        return {
            "action": "ADOPT_UNRECEIPTED",
            "first_blocker": None,
            "review_id": adoptable["id"],
            "review": dict(adoptable),
            "reviewer": expected_signer,
            "commit_id": value["head_sha"],
            "body": value["review_body"],
            "plan_sha256": value["plan_sha256"],
        }
    delegated_blocker = _existing_delegated_review_blocker(
        review_list,
        reviewer=expected_signer,
        base_sha=value["base_sha"],
        head_sha=value["head_sha"],
        tree_sha=value["tree_sha"],
        expected_body=value["review_body"],
        expected_state=_expected_platform_review_state_for_effect(value["event"]),
    )
    if delegated_blocker is not None:
        return {
            "action": NO_EFFECT,
            "first_blocker": delegated_blocker,
            "plan_sha256": value["plan_sha256"],
        }
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
    if not value["stale_approval_retraction"] and _manual_target_review_present(
        review_list, expected_signer, value["head_sha"]
    ):
        return {"action": NO_EFFECT, "first_blocker": "MANUAL_TARGET_REVIEW_PRESENT", "plan_sha256": value["plan_sha256"]}
    return {
        "action": "POST",
        "event": _native_review_event_after_preflight(value["event"]),
        "reviewer": expected_signer,
        "commit_id": value["head_sha"],
        "body": value["review_body"],
        "plan_sha256": value["plan_sha256"],
    }


def verify_review_readback(
    *,
    plan: Mapping[str, Any],
    review: Mapping[str, Any],
    expected_signer: str,
    reviews_before: Sequence[Mapping[str, Any]],
    reviews_after: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Bind the submitted review and its post-effect ordering fail-closed."""
    value = validate_plan(plan)
    observed = _mapping(review, "submitted review")
    if value["event"] == NO_EFFECT or expected_signer != value.get("reviewer"):
        return {"exact": False, "first_blocker": "READBACK_PLAN_NOT_EFFECTFUL"}
    user = _mapping(observed.get("user"), "submitted review user")
    state = observed.get("state")
    expected_state = _expected_platform_review_state_for_effect(value["event"])
    response_exact = (
        user.get("login") == expected_signer
        and user.get("type") == "User"
        and observed.get("commit_id") == value["head_sha"]
        and state == expected_state
        and observed.get("body") == value["review_body"]
    )
    review_id = observed.get("id")
    submitted_at = observed.get("submitted_at")
    if (
        not response_exact
        or isinstance(review_id, bool)
        or not isinstance(review_id, int)
        or review_id < 1
    ):
        return {
            "exact": False,
            "first_blocker": "DELEGATED_ACCOUNT_REVIEW_READBACK_MISMATCH",
            "review_id": review_id,
            "plan_sha256": value["plan_sha256"],
        }
    if not isinstance(submitted_at, str) or not submitted_at:
        return {
            "exact": False,
            "first_blocker": "POST_EFFECT_REVIEW_ORDER_AMBIGUOUS",
            "review_id": review_id,
            "plan_sha256": value["plan_sha256"],
        }

    def index_reviews(
        reviews: Sequence[Mapping[str, Any]], label: str
    ) -> dict[int, Mapping[str, Any]]:
        return {
            item["id"]: item for item in canonical_review_inventory(reviews, label)
        }

    def review_projection(item: Mapping[str, Any]) -> dict[str, Any]:
        account = item.get("user")
        return {
            "id": item.get("id"),
            "reviewer": account.get("login") if isinstance(account, Mapping) else None,
            "reviewer_type": account.get("type") if isinstance(account, Mapping) else None,
            "state": item.get("state"),
            "commit_id": item.get("commit_id"),
            "submitted_at": item.get("submitted_at"),
            "body": item.get("body"),
        }

    before = index_reviews(reviews_before, "pre-effect reviews")
    after = index_reviews(reviews_after, "post-effect reviews")
    if review_id in before:
        return {
            "exact": False,
            "first_blocker": "SUBMITTED_REVIEW_ID_PREEXISTED",
            "review_id": review_id,
            "plan_sha256": value["plan_sha256"],
        }
    for identifier, prior in before.items():
        current = after.get(identifier)
        if current is None or review_projection(current) != review_projection(prior):
            return {
                "exact": False,
                "first_blocker": "POST_EFFECT_REVIEW_HISTORY_DRIFT",
                "review_id": review_id,
                "plan_sha256": value["plan_sha256"],
            }

    posted = after.get(review_id)
    if posted is None or review_projection(posted) != review_projection(observed):
        return {
            "exact": False,
            "first_blocker": "DELEGATED_ACCOUNT_REVIEW_POST_EFFECT_READBACK_MISMATCH",
            "review_id": review_id,
            "plan_sha256": value["plan_sha256"],
        }

    new_review_ids = sorted(set(after) - set(before))
    if review_id not in new_review_ids:
        return {
            "exact": False,
            "first_blocker": "DELEGATED_ACCOUNT_REVIEW_POST_EFFECT_READBACK_MISMATCH",
            "review_id": review_id,
            "plan_sha256": value["plan_sha256"],
        }
    for identifier in new_review_ids:
        if identifier == review_id:
            continue
        candidate = after[identifier]
        account = candidate.get("user")
        same_account = (
            isinstance(account, Mapping)
            and isinstance(account.get("login"), str)
            and account["login"].casefold() == expected_signer.casefold()
        )
        if not same_account:
            continue
        body = candidate.get("body")
        manual = not (isinstance(body, str) and MARKER in body)
        target_head = candidate.get("commit_id") == value["head_sha"]
        if manual and target_head:
            blocker = "CONCURRENT_MANUAL_TARGET_REVIEW"
        elif manual:
            blocker = "CONCURRENT_MANUAL_NON_TARGET_REVIEW"
        elif target_head:
            blocker = "CONCURRENT_DELEGATED_TARGET_REVIEW"
        else:
            blocker = "CONCURRENT_DELEGATED_NON_TARGET_REVIEW"
        return {
            "exact": False,
            "first_blocker": blocker,
            "review_id": review_id,
            "concurrent_review_id": identifier,
            "concurrent_review_state": candidate.get("state"),
            "concurrent_review_commit_id": candidate.get("commit_id"),
            "plan_sha256": value["plan_sha256"],
        }

    if expected_state in DECISIVE_REVIEW_STATES:
        decisive_order: list[tuple[str, int]] = []
        for identifier, candidate in after.items():
            account = candidate.get("user")
            if (
                not isinstance(account, Mapping)
                or not isinstance(account.get("login"), str)
                or account["login"].casefold() != expected_signer.casefold()
                or str(candidate.get("state") or "").upper()
                not in DECISIVE_REVIEW_STATES
            ):
                continue
            order_time = candidate.get("submitted_at")
            if not isinstance(order_time, str) or not order_time:
                return {
                    "exact": False,
                    "first_blocker": "POST_EFFECT_REVIEW_ORDER_AMBIGUOUS",
                    "review_id": review_id,
                    "plan_sha256": value["plan_sha256"],
                }
            decisive_order.append((order_time, identifier))
        if not decisive_order or max(decisive_order)[1] != review_id:
            return {
                "exact": False,
                "first_blocker": "POST_EFFECT_REVIEW_ORDER_AMBIGUOUS",
                "review_id": review_id,
                "plan_sha256": value["plan_sha256"],
            }

    return {
        "exact": True,
        "effect_mode": "POST",
        "first_blocker": None,
        "review_id": review_id,
        "reviewer": user.get("login"),
        "commit_id": observed.get("commit_id"),
        "state": state,
        "submitted_at": submitted_at,
        "new_review_ids": new_review_ids,
        "manual_review_guard": "POST_EFFECT_ORDERING_REOBSERVED",
        "plan_sha256": value["plan_sha256"],
    }


def verify_review_adoption_readback(
    *,
    plan: Mapping[str, Any],
    review: Mapping[str, Any],
    expected_signer: str,
    reviews_before: Sequence[Mapping[str, Any]],
    reviews_after: Sequence[Mapping[str, Any]],
    current_signer_run_id: int,
    current_signer_run_attempt: int,
) -> dict[str, Any]:
    """Verify recovery of a review posted before an earlier runner stopped.

    Adoption is no-effect: the exact marked review must exist in both complete
    snapshots, remain the reviewer's latest decisive state, and have no manual
    same-account exact-head companion.  Only a later attempt of its origin run
    may seal the missing receipt.
    """
    value = validate_plan(plan)
    observed = _mapping(review, "adopted review")
    before = canonical_review_inventory(reviews_before, "pre-adoption reviews")
    after = canonical_review_inventory(reviews_after, "post-adoption reviews")

    def indexed(values: Sequence[Mapping[str, Any]], label: str) -> dict[int, dict[str, Any]]:
        result: dict[int, dict[str, Any]] = {}
        for raw in values:
            item = _mapping(raw, f"{label} item")
            identifier = item.get("id")
            if (
                isinstance(identifier, bool)
                or not isinstance(identifier, int)
                or identifier < 1
                or identifier in result
            ):
                raise NativeAccountReviewError(
                    f"{label} contains an invalid or duplicate review id"
                )
            result[identifier] = _signer_review_projection(item)
        return result

    before_index = indexed(before, "pre-adoption reviews")
    after_index = indexed(after, "post-adoption reviews")
    projection = _signer_review_projection(observed)
    review_id = projection.get("id")
    if before_index != after_index:
        return {
            "exact": False,
            "effect_mode": "ADOPT_UNRECEIPTED",
            "first_blocker": "ADOPTION_REVIEW_HISTORY_DRIFT",
            "review_id": review_id,
            "plan_sha256": value["plan_sha256"],
        }
    if (
        isinstance(review_id, bool)
        or not isinstance(review_id, int)
        or before_index.get(review_id) != projection
    ):
        return {
            "exact": False,
            "effect_mode": "ADOPT_UNRECEIPTED",
            "first_blocker": "ADOPTION_REVIEW_IDENTITY_DRIFT",
            "review_id": review_id,
            "plan_sha256": value["plan_sha256"],
        }
    candidate, blocker = _adoptable_unreceipted_review(
        after,
        plan=value,
        reviewer=expected_signer,
        current_signer_run_id=current_signer_run_id,
        current_signer_run_attempt=current_signer_run_attempt,
    )
    if blocker is not None or candidate is None or candidate.get("id") != review_id:
        return {
            "exact": False,
            "effect_mode": "ADOPT_UNRECEIPTED",
            "first_blocker": blocker or "ADOPTION_REVIEW_NOT_EXACT",
            "review_id": review_id,
            "plan_sha256": value["plan_sha256"],
        }
    locator = parse_delegated_review_locator(observed.get("body"))
    plan_locator = parse_delegated_review_locator(value.get("review_body"))
    expected_state = _expected_platform_review_state_for_effect(value["event"])
    submitted_at = observed.get("submitted_at")
    if (
        expected_signer != value.get("reviewer")
        or not isinstance(locator, Mapping)
        or not isinstance(plan_locator, Mapping)
        or locator.get("signer_run_id") != value["signer_run_id"]
        or locator.get("signer_run_attempt") > value["signer_run_attempt"]
        or locator.get("signer_run_attempt") >= current_signer_run_attempt
        or locator.get("signer_evaluator_sha") != value["signer_evaluator_sha"]
        or locator.get("evidence_fingerprint")
        != plan_locator.get("evidence_fingerprint")
        or locator.get("head_sha") != plan_locator.get("head_sha")
        or locator.get("tree_sha") != plan_locator.get("tree_sha")
        or locator.get("event") != plan_locator.get("event")
        or not isinstance(observed.get("body"), str)
        or observed["body"].split("\n", 1)[1]
        != value["review_body"].split("\n", 1)[1]
        or observed.get("commit_id") != value["head_sha"]
        or str(observed.get("state") or "").upper() != expected_state
        or not isinstance(submitted_at, str)
        or not submitted_at
    ):
        return {
            "exact": False,
            "effect_mode": "ADOPT_UNRECEIPTED",
            "first_blocker": "ADOPTION_REVIEW_PROVENANCE_DRIFT",
            "review_id": review_id,
            "plan_sha256": value["plan_sha256"],
        }
    return {
        "exact": True,
        "effect_mode": "ADOPT_UNRECEIPTED",
        "first_blocker": None,
        "review_id": review_id,
        "reviewer": expected_signer,
        "commit_id": observed.get("commit_id"),
        "state": observed.get("state"),
        "submitted_at": submitted_at,
        "new_review_ids": [],
        "manual_review_guard": "ADOPTION_EXACT_HISTORY_REOBSERVED",
        "plan_sha256": value["plan_sha256"],
    }


def _signer_review_projection(review: Mapping[str, Any]) -> dict[str, Any]:
    user = review.get("user")
    return {
        "id": review.get("id"),
        "reviewer": user.get("login") if isinstance(user, Mapping) else None,
        "reviewer_type": user.get("type") if isinstance(user, Mapping) else None,
        "state": review.get("state"),
        "commit_id": review.get("commit_id"),
        "submitted_at": review.get("submitted_at"),
        "body": review.get("body"),
        "body_sha256": (
            hashlib.sha256(review["body"].encode("utf-8")).hexdigest()
            if isinstance(review.get("body"), str)
            else None
        ),
    }


def _signer_job_name(reviewer: str) -> str:
    if reviewer not in ACCOUNTS:
        raise NativeAccountReviewError("signer receipt reviewer is invalid")
    return f"native-account-review-as-{reviewer}"


def signer_receipt_artifact_name(
    *, reviewer: str, pr_number: int, head_sha: str, run_id: int, run_attempt: int
) -> str:
    if reviewer not in ACCOUNTS:
        raise NativeAccountReviewError("signer receipt reviewer is invalid")
    if (
        isinstance(pr_number, bool)
        or not isinstance(pr_number, int)
        or pr_number < 1
        or isinstance(run_id, bool)
        or not isinstance(run_id, int)
        or run_id < 1
        or isinstance(run_attempt, bool)
        or not isinstance(run_attempt, int)
        or run_attempt < 1
    ):
        raise NativeAccountReviewError("signer receipt numeric identity is invalid")
    head_sha = _sha1(head_sha, "signer receipt head")
    return (
        f"qikvrt-native-review-signer-receipt-{reviewer}-pr-{pr_number}-"
        f"head-{head_sha}-run-{run_id}-attempt-{run_attempt}"
    )


def build_signer_post_effect_authority_fence(
    *,
    plan: Mapping[str, Any],
    evaluator_sha: str,
    current_main: Mapping[str, Any],
    upstream_before: Mapping[str, Any],
    upstream_after: Mapping[str, Any],
    rules_before: Sequence[Mapping[str, Any]],
    rules_after: Sequence[Mapping[str, Any]],
    delegation_before: bytes,
    delegation_after: bytes,
    final_pr: Mapping[str, Any],
    final_commit: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal the complete no-secret Authority fence after the review effect."""
    value = validate_plan(plan)
    evaluator = _sha1(evaluator_sha, "post-effect evaluator")
    if (
        evaluator != value.get("signer_evaluator_sha")
        or not isinstance(current_main, Mapping)
        or current_main.get("sha") != evaluator
    ):
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_MAIN_DRIFT")
    if not isinstance(upstream_before, Mapping) or not isinstance(
        upstream_after, Mapping
    ):
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_UPSTREAM_DRIFT")
    expected_upstream_schema = "qikvrt_current_executor_attempt_reobservation_v1"
    if (
        upstream_before.get("schema") != expected_upstream_schema
        or upstream_before.get("exact") is not True
        or upstream_before.get("trusted_main_sha") != evaluator
        or dict(upstream_after) != dict(upstream_before)
    ):
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_UPSTREAM_DRIFT")
    if (
        not isinstance(rules_before, Sequence)
        or isinstance(rules_before, (str, bytes))
        or not isinstance(rules_after, Sequence)
        or isinstance(rules_after, (str, bytes))
        or not all(isinstance(item, Mapping) for item in rules_before)
        or not all(isinstance(item, Mapping) for item in rules_after)
        or _sha256(rules_before) != _sha256(rules_after)
    ):
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_RULES_DRIFT")
    if not isinstance(delegation_before, bytes) or not isinstance(
        delegation_after, bytes
    ):
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_DELEGATION_DRIFT")
    if delegation_before != delegation_after:
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_DELEGATION_DRIFT")
    try:
        delegation_value = json.loads(delegation_after.decode("utf-8"))
        delegation_info = _delegation_info(delegation_value, value["repository"])
    except (UnicodeDecodeError, json.JSONDecodeError, NativeAccountReviewError) as exc:
        raise NativeAccountReviewError(
            "SIGNER_POST_EFFECT_DELEGATION_DRIFT"
        ) from exc
    if (
        delegation_info["state"] != DELEGATION_ACTIVE
        or delegation_info["sha256"] != value.get("delegation_sha256")
    ):
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_DELEGATION_DRIFT")
    pr = _mapping(final_pr, "post-effect pull request")
    commit = _mapping(final_commit, "post-effect commit")
    if (
        pr.get("number") != value["pr_number"]
        or pr.get("state") != "open"
        or not isinstance(pr.get("base"), Mapping)
        or pr["base"].get("ref") != "main"
        or pr["base"].get("sha") != value["base_sha"]
        or not isinstance(pr.get("head"), Mapping)
        or pr["head"].get("sha") != value["head_sha"]
        or commit.get("sha") != value["head_sha"]
        or not isinstance(commit.get("tree"), Mapping)
        or commit["tree"].get("sha") != value["tree_sha"]
    ):
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_SUBJECT_DRIFT")
    result = {
        "schema": SIGNER_POST_EFFECT_FENCE_SCHEMA,
        "repository": value["repository"],
        "evaluator_sha": evaluator,
        "main_sha": current_main["sha"],
        "upstream": dict(upstream_after),
        "rules_sha256": _sha256(rules_after),
        "delegation_sha256": delegation_info["sha256"],
        "subject": {
            "pr_number": value["pr_number"],
            "base_sha": value["base_sha"],
            "head_sha": value["head_sha"],
            "tree_sha": value["tree_sha"],
        },
        "exact": True,
        "productive_effect": False,
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }
    result["fence_sha256"] = _sha256(result)
    return result


def validate_signer_post_effect_authority_fence(
    fence: Mapping[str, Any],
) -> dict[str, Any]:
    value = dict(_mapping(fence, "signer post-effect Authority fence"))
    claimed = value.pop("fence_sha256", None)
    if claimed != _sha256(value):
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_FENCE_DIGEST_DRIFT")
    if (
        value.get("schema") != SIGNER_POST_EFFECT_FENCE_SCHEMA
        or value.get("exact") is not True
        or value.get("productive_effect") is not False
        or value.get("completion_claims")
        != {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        }
    ):
        raise NativeAccountReviewError("SIGNER_POST_EFFECT_FENCE_INVALID")
    return dict(fence)


def build_signer_receipt(
    *,
    plan: Mapping[str, Any],
    review: Mapping[str, Any],
    expected_signer: str,
    reviews_before: Sequence[Mapping[str, Any]],
    reviews_after: Sequence[Mapping[str, Any]],
    readback: Mapping[str, Any],
    final_pr: Mapping[str, Any],
    final_commit: Mapping[str, Any],
    authority_fence: Mapping[str, Any],
    repository: str,
    evaluator_sha: str,
    run_id: int,
    run_attempt: int,
) -> dict[str, Any]:
    """Seal the successful post-effect readback; never infer it from the POST."""
    value = validate_plan(plan)
    observed = _mapping(review, "submitted review")
    before = _list(reviews_before, "pre-effect reviews")
    after = _list(reviews_after, "post-effect reviews")
    supplied_readback = _mapping(readback, "review readback")
    if supplied_readback.get("effect_mode") == "ADOPT_UNRECEIPTED":
        expected_readback = verify_review_adoption_readback(
            plan=value,
            review=observed,
            expected_signer=expected_signer,
            reviews_before=before,
            reviews_after=after,
            current_signer_run_id=run_id,
            current_signer_run_attempt=run_attempt,
        )
    else:
        expected_readback = verify_review_readback(
            plan=value,
            review=observed,
            expected_signer=expected_signer,
            reviews_before=before,
            reviews_after=after,
        )
    if dict(supplied_readback) != expected_readback:
        raise NativeAccountReviewError("SIGNER_RECEIPT_READBACK_RECOMPUTATION_DRIFT")
    if expected_readback.get("exact") is not True:
        raise NativeAccountReviewError("SIGNER_RECEIPT_READBACK_NOT_EXACT")
    if (
        repository != value["repository"]
        or run_id != value["signer_run_id"]
        or isinstance(run_attempt, bool)
        or not isinstance(run_attempt, int)
        or run_attempt < value["signer_run_attempt"]
        or evaluator_sha != value["signer_evaluator_sha"]
        or expected_signer != value["reviewer"]
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_PLAN_PROVENANCE_DRIFT")
    evaluator_sha = _sha1(evaluator_sha, "signer receipt evaluator")
    fence = validate_signer_post_effect_authority_fence(authority_fence)
    if (
        fence.get("repository") != repository
        or fence.get("evaluator_sha") != evaluator_sha
        or fence.get("main_sha") != evaluator_sha
        or fence.get("delegation_sha256") != value.get("delegation_sha256")
        or fence.get("subject")
        != {
            "pr_number": value["pr_number"],
            "base_sha": value["base_sha"],
            "head_sha": value["head_sha"],
            "tree_sha": value["tree_sha"],
        }
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_AUTHORITY_FENCE_DRIFT")
    pr = _mapping(final_pr, "post-effect pull request")
    commit = _mapping(final_commit, "post-effect commit")
    if (
        pr.get("number") != value["pr_number"]
        or pr.get("state") != "open"
        or not isinstance(pr.get("base"), Mapping)
        or pr["base"].get("ref") != "main"
        or pr["base"].get("sha") != value["base_sha"]
        or not isinstance(pr.get("head"), Mapping)
        or pr["head"].get("sha") != value["head_sha"]
        or commit.get("sha") != value["head_sha"]
        or not isinstance(commit.get("tree"), Mapping)
        or commit["tree"].get("sha") != value["tree_sha"]
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_FINAL_SUBJECT_DRIFT")
    review_projection = _signer_review_projection(observed)
    review_locator = parse_delegated_review_locator(review_projection.get("body"))
    if (
        review_locator is None
        or review_locator["signer_run_id"] != run_id
        or review_locator["signer_evaluator_sha"] != evaluator_sha
        or review_locator["signer_run_attempt"] > run_attempt
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_REVIEW_ORIGIN_DRIFT")
    artifact_name = signer_receipt_artifact_name(
        reviewer=expected_signer,
        pr_number=value["pr_number"],
        head_sha=value["head_sha"],
        run_id=run_id,
        run_attempt=run_attempt,
    )
    result: dict[str, Any] = {
        "schema": SIGNER_RECEIPT_SCHEMA,
        "repository": repository,
        "workflow_path": TRUSTED_SIGNER_WORKFLOW_PATH,
        "evaluator_sha": evaluator_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "origin_run_id": review_locator["signer_run_id"],
        "origin_run_attempt": review_locator["signer_run_attempt"],
        "signer_job": _signer_job_name(expected_signer),
        "artifact_name": artifact_name,
        "plan_sha256": value["plan_sha256"],
        "evidence_fingerprint": value["evidence_fingerprint"],
        "pr_number": value["pr_number"],
        "base_sha": value["base_sha"],
        "head_sha": value["head_sha"],
        "tree_sha": value["tree_sha"],
        "review": review_projection,
        "review_ordering": {
            "reviews_before_sha256": _sha256(before),
            "reviews_after_sha256": _sha256(after),
            "review_ids_before": sorted(item.get("id") for item in before),
            "review_ids_after": sorted(item.get("id") for item in after),
            "new_review_ids": expected_readback["new_review_ids"],
            "latest_decisive_review_id": expected_readback["review_id"],
            "manual_review_guard": expected_readback["manual_review_guard"],
        },
        "post_effect_authority_fence": fence,
        "final_subject": {
            "state": pr.get("state"),
            "base_ref": pr["base"].get("ref"),
            "base_sha": pr["base"].get("sha"),
            "head_sha": pr["head"].get("sha"),
            "tree_sha": commit["tree"].get("sha"),
        },
        "effect_readback": {
            "exact": True,
            "effect_mode": expected_readback["effect_mode"],
            "first_blocker": None,
            "review_id": expected_readback["review_id"],
            "state": expected_readback["state"],
            "commit_id": expected_readback["commit_id"],
            "submitted_at": expected_readback["submitted_at"],
        },
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }
    result["receipt_sha256"] = _sha256(result)
    return result


def validate_signer_receipt(
    receipt: Mapping[str, Any],
    *,
    review: Mapping[str, Any],
    current_reviews: Sequence[Mapping[str, Any]],
    repository: str,
    evaluator_sha: str,
    run: Mapping[str, Any],
    workflow: Mapping[str, Any],
    jobs: Sequence[Mapping[str, Any]],
    artifact_name: str,
) -> dict[str, Any]:
    """Validate one prior signer completion before its marked review can gate."""
    value = dict(_mapping(receipt, "signer receipt"))
    claimed = _sha256_text(value.pop("receipt_sha256", None), "signer receipt digest")
    if claimed != _sha256(value):
        raise NativeAccountReviewError("SIGNER_RECEIPT_DIGEST_DRIFT")
    value["receipt_sha256"] = claimed
    if value.get("schema") != SIGNER_RECEIPT_SCHEMA:
        raise NativeAccountReviewError("SIGNER_RECEIPT_SCHEMA_INVALID")
    fence = validate_signer_post_effect_authority_fence(
        value.get("post_effect_authority_fence")
    )
    if (
        fence.get("repository") != repository
        or fence.get("evaluator_sha") != evaluator_sha
        or fence.get("main_sha") != evaluator_sha
        or fence.get("subject")
        != {
            "pr_number": value.get("pr_number"),
            "base_sha": value.get("base_sha"),
            "head_sha": value.get("head_sha"),
            "tree_sha": value.get("tree_sha"),
        }
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_AUTHORITY_FENCE_DRIFT")
    review_projection = _signer_review_projection(_mapping(review, "gate review"))
    locator = parse_delegated_review_locator(review_projection.get("body"))
    if locator is None:
        raise NativeAccountReviewError("SIGNER_RECEIPT_REVIEW_LOCATOR_INVALID")
    expected = {
        "repository": repository,
        "workflow_path": TRUSTED_SIGNER_WORKFLOW_PATH,
        "evaluator_sha": evaluator_sha,
        "run_id": locator["signer_run_id"],
        "origin_run_id": locator["signer_run_id"],
        "origin_run_attempt": locator["signer_run_attempt"],
        "head_sha": locator["head_sha"],
        "tree_sha": locator["tree_sha"],
        "evidence_fingerprint": locator["evidence_fingerprint"],
        "artifact_name": artifact_name,
    }
    if any(value.get(key) != item for key, item in expected.items()):
        raise NativeAccountReviewError("SIGNER_RECEIPT_REVIEW_PROVENANCE_DRIFT")
    if (
        isinstance(value.get("run_attempt"), bool)
        or not isinstance(value.get("run_attempt"), int)
        or value["run_attempt"] < value["origin_run_attempt"]
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_REVIEW_PROVENANCE_DRIFT")
    if value.get("review") != review_projection:
        raise NativeAccountReviewError("SIGNER_RECEIPT_REVIEW_BYTES_DRIFT")
    effect_mode = value.get("effect_readback", {}).get("effect_mode")
    if (
        value.get("effect_readback", {}).get("exact") is not True
        or effect_mode not in {"POST", "ADOPT_UNRECEIPTED"}
        or value.get("effect_readback", {}).get("first_blocker") is not None
        or value.get("effect_readback", {}).get("review_id")
        != review_projection["id"]
        or value.get("effect_readback", {}).get("state")
        != review_projection["state"]
        or value.get("effect_readback", {}).get("commit_id")
        != review_projection["commit_id"]
        or value.get("effect_readback", {}).get("submitted_at")
        != review_projection["submitted_at"]
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_EFFECT_READBACK_DRIFT")
    ordering = value.get("review_ordering")
    if not isinstance(ordering, Mapping):
        raise NativeAccountReviewError("SIGNER_RECEIPT_EFFECT_READBACK_DRIFT")
    if effect_mode == "ADOPT_UNRECEIPTED":
        if (
            value["run_attempt"] <= value["origin_run_attempt"]
            or ordering.get("new_review_ids") != []
            or ordering.get("manual_review_guard")
            != "ADOPTION_EXACT_HISTORY_REOBSERVED"
        ):
            raise NativeAccountReviewError("SIGNER_RECEIPT_ADOPTION_BOUNDARY_DRIFT")
    elif (
        ordering.get("new_review_ids") != [review_projection["id"]]
        or ordering.get("manual_review_guard")
        != "POST_EFFECT_ORDERING_REOBSERVED"
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_POST_BOUNDARY_DRIFT")
    run_object = _mapping(run, "signer workflow run")
    workflow_object = _mapping(workflow, "signer workflow")
    run_repository = run_object.get("repository")
    raw_run_path = run_object.get("path")
    if not isinstance(raw_run_path, str) or raw_run_path.count("@") > 1:
        raise NativeAccountReviewError("SIGNER_RECEIPT_WORKFLOW_RUN_NOT_SUCCESSFUL")
    run_path_parts = raw_run_path.split("@", 1)
    if len(run_path_parts) == 2 and not run_path_parts[1]:
        raise NativeAccountReviewError("SIGNER_RECEIPT_WORKFLOW_RUN_NOT_SUCCESSFUL")
    canonical_run_path = run_path_parts[0]
    if (
        run_object.get("id") != value["run_id"]
        or run_object.get("run_attempt") != value["run_attempt"]
        or run_object.get("status") != "completed"
        or run_object.get("conclusion") != "success"
        or run_object.get("event") not in {"workflow_run", "workflow_dispatch"}
        or run_object.get("head_branch") != "main"
        or run_object.get("head_sha") != evaluator_sha
        or canonical_run_path != TRUSTED_SIGNER_WORKFLOW_PATH
        or not isinstance(run_repository, Mapping)
        or run_repository.get("full_name") != repository
        or run_object.get("workflow_id") != workflow_object.get("id")
        or workflow_object.get("path") != TRUSTED_SIGNER_WORKFLOW_PATH
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_WORKFLOW_RUN_NOT_SUCCESSFUL")
    job_list = _list(jobs, "signer attempt jobs")
    job_matches = [
        job
        for job in job_list
        if isinstance(job, Mapping) and job.get("name") == value.get("signer_job")
    ]
    if (
        len(job_matches) != 1
        or job_matches[0].get("status") != "completed"
        or job_matches[0].get("conclusion") != "success"
        or job_matches[0].get("run_id") != value["run_id"]
        or job_matches[0].get("run_attempt") != value["run_attempt"]
    ):
        raise NativeAccountReviewError("SIGNER_RECEIPT_JOB_NOT_SUCCESSFUL")
    reviews = canonical_review_inventory(current_reviews, "current reviews")
    matching = [
        item
        for item in reviews
        if isinstance(item, Mapping) and item.get("id") == review_projection["id"]
    ]
    if len(matching) != 1 or _signer_review_projection(matching[0]) != review_projection:
        raise NativeAccountReviewError("SIGNER_RECEIPT_CURRENT_REVIEW_DRIFT")
    reviewer = review_projection["reviewer"]
    for item in reviews:
        if not isinstance(item, Mapping) or item.get("id") == review_projection["id"]:
            continue
        user = item.get("user")
        if (
            isinstance(user, Mapping)
            and isinstance(user.get("login"), str)
            and isinstance(reviewer, str)
            and user["login"].casefold() == reviewer.casefold()
            and item.get("commit_id") == value["head_sha"]
            and parse_delegated_review_locator(item.get("body")) is None
        ):
            raise NativeAccountReviewError("SIGNER_RECEIPT_MANUAL_REVIEW_CONFLICT")
    receipt_state = str(review_projection.get("state") or "").upper()
    if receipt_state in DECISIVE_REVIEW_STATES:
        decisive = [
            item
            for item in reviews
            if isinstance(item, Mapping)
            and isinstance(item.get("user"), Mapping)
            and isinstance(item["user"].get("login"), str)
            and isinstance(reviewer, str)
            and item["user"]["login"].casefold() == reviewer.casefold()
            and item.get("commit_id") == value["head_sha"]
            and str(item.get("state") or "").upper() in DECISIVE_REVIEW_STATES
        ]
        latest = _latest_decisive_target_review(
            reviews, reviewer, value["head_sha"]
        )
        if not decisive or latest is None or latest.get("id") != review_projection["id"]:
            raise NativeAccountReviewError("SIGNER_RECEIPT_REVIEW_ORDER_DRIFT")
    elif receipt_state != "COMMENTED":
        raise NativeAccountReviewError("SIGNER_RECEIPT_REVIEW_STATE_INVALID")
    if value.get("completion_claims") != {
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
        "MERGE": False,
    }:
        raise NativeAccountReviewError("SIGNER_RECEIPT_COMPLETION_CLAIMS_INVALID")
    return value


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
    plan_parser.add_argument("--signer-run-id", type=int, required=True)
    plan_parser.add_argument("--signer-run-attempt", type=int, required=True)
    plan_parser.add_argument("--signer-evaluator-sha", required=True)
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
    signer_parser.add_argument("--current-signer-run-id", type=int, required=True)
    signer_parser.add_argument("--current-signer-run-attempt", type=int, required=True)
    signer_parser.add_argument("--current-signer-evaluator-sha", required=True)
    readback_parser = commands.add_parser("verify-readback")
    readback_parser.add_argument("--plan", required=True)
    readback_parser.add_argument("--review", required=True)
    readback_parser.add_argument("--expected-signer", required=True)
    readback_parser.add_argument("--reviews-before", required=True)
    readback_parser.add_argument("--reviews-after", required=True)
    adoption_parser = commands.add_parser("verify-adoption-readback")
    adoption_parser.add_argument("--plan", required=True)
    adoption_parser.add_argument("--review", required=True)
    adoption_parser.add_argument("--expected-signer", required=True)
    adoption_parser.add_argument("--reviews-before", required=True)
    adoption_parser.add_argument("--reviews-after", required=True)
    adoption_parser.add_argument("--current-signer-run-id", type=int, required=True)
    adoption_parser.add_argument(
        "--current-signer-run-attempt", type=int, required=True
    )
    receipt_parser = commands.add_parser("seal-signer-receipt")
    receipt_parser.add_argument("--plan", required=True)
    receipt_parser.add_argument("--review", required=True)
    receipt_parser.add_argument("--expected-signer", required=True)
    receipt_parser.add_argument("--reviews-before", required=True)
    receipt_parser.add_argument("--reviews-after", required=True)
    receipt_parser.add_argument("--readback", required=True)
    receipt_parser.add_argument("--final-pr", required=True)
    receipt_parser.add_argument("--final-commit", required=True)
    receipt_parser.add_argument("--authority-fence", required=True)
    receipt_parser.add_argument("--repository", required=True)
    receipt_parser.add_argument("--evaluator-sha", required=True)
    receipt_parser.add_argument("--run-id", type=int, required=True)
    receipt_parser.add_argument("--run-attempt", type=int, required=True)
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
                signer_run_id=args.signer_run_id,
                signer_run_attempt=args.signer_run_attempt,
                signer_evaluator_sha=args.signer_evaluator_sha,
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
                current_signer_run_id=args.current_signer_run_id,
                current_signer_run_attempt=args.current_signer_run_attempt,
                current_signer_evaluator_sha=args.current_signer_evaluator_sha,
            )
        elif args.command == "verify-readback":
            result = verify_review_readback(
                plan=_load(args.plan),
                review=_load(args.review),
                expected_signer=args.expected_signer,
                reviews_before=_load(args.reviews_before),
                reviews_after=_load(args.reviews_after),
            )
        elif args.command == "verify-adoption-readback":
            result = verify_review_adoption_readback(
                plan=_load(args.plan),
                review=_load(args.review),
                expected_signer=args.expected_signer,
                reviews_before=_load(args.reviews_before),
                reviews_after=_load(args.reviews_after),
                current_signer_run_id=args.current_signer_run_id,
                current_signer_run_attempt=args.current_signer_run_attempt,
            )
        else:
            result = build_signer_receipt(
                plan=_load(args.plan),
                review=_load(args.review),
                expected_signer=args.expected_signer,
                reviews_before=_load(args.reviews_before),
                reviews_after=_load(args.reviews_after),
                readback=_load(args.readback),
                final_pr=_load(args.final_pr),
                final_commit=_load(args.final_commit),
                authority_fence=_load(args.authority_fence),
                repository=args.repository,
                evaluator_sha=args.evaluator_sha,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
            )
    except (OSError, TypeError, ValueError, json.JSONDecodeError, NativeAccountReviewError) as exc:
        result = {"schema": SCHEMA, "state": "HOLD_UNVERIFIED", "first_blocker": str(exc)}
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
