#!/usr/bin/env python3
"""Create and validate durable logical issue continuations.

This module intentionally separates a continuation's semantic identity from
observation metadata.  An issue ``updated_at`` timestamp, a status comment, or
a workflow refresh must never create a new unit of work by itself.  A live
record consequently has no time-to-live: it remains live until its exact
semantic binding changes, an exact postcondition is observed, or a sourced
external hold is recorded by a caller with the responsible authority.

The module is pure local I/O.  Workflows decide whether and how a validated
record is appended to the repository-native ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any


SCHEMA = "qikvrt_issue_continuation_v1"
LIVENESS = "INDEFINITE_UNTIL_EVIDENCED_OUTCOME"
VOLATILE_ISSUE_FIELDS = frozenset({"updated_at"})
VOLATILE_STATUS_FIELDS = frozenset(
    {
        "generated_at",
        "validated_disposition_at",
        "validated_completion_promoted_at",
    }
)


class ContinuationError(ValueError):
    """The continuation cannot be safely materialized or used."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContinuationError(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContinuationError(f"{label} must be a non-empty string")
    return value


def _issue_number(value: Any, label: str = "issue number") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ContinuationError(f"{label} must be a positive integer")
    return value


def _git_object_id(value: Any, label: str) -> str:
    """Accept an exact Git object id without tying the contract to SHA-1."""
    value = _string(value, label)
    if re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value) is None:
        raise ContinuationError(f"{label} must be an exact lowercase Git object id")
    return value


def source_binding(value: Mapping[str, Any], repository: str) -> dict[str, str]:
    """Validate the immutable processor source binding for this observation."""
    source = _mapping(value, "source binding")
    bound_repository = _string(source.get("repository"), "source binding.repository")
    if bound_repository != repository:
        raise ContinuationError("source binding.repository must equal request.repository")
    return {
        "repository": bound_repository,
        "ref": _string(source.get("ref"), "source binding.ref"),
        "head_sha": _git_object_id(source.get("head_sha"), "source binding.head_sha"),
        "tree_sha": _git_object_id(source.get("tree_sha"), "source binding.tree_sha"),
    }


def semantic_request(issue: Mapping[str, Any], repository: str) -> dict[str, Any]:
    """Return the causal issue input, excluding mutable observation metadata."""
    _string(repository, "repository")
    number = _issue_number(issue.get("number"))
    user = issue.get("user")
    author = user.get("login") if isinstance(user, Mapping) else None
    return {
        "repository": repository,
        "issue_number": number,
        "title": issue.get("title", ""),
        "body": issue.get("body") or "",
        "author": author,
        "html_url": issue.get("html_url"),
        "created_at": issue.get("created_at"),
    }


def issue_observation(issue: Mapping[str, Any]) -> dict[str, Any]:
    """Keep non-causal GitHub metadata explicitly outside the request digest."""
    return {
        "schema": "qikvrt_issue_observation_v1",
        "volatile_fields_excluded_from_semantic_request": sorted(VOLATILE_ISSUE_FIELDS),
        "updated_at": issue.get("updated_at"),
    }


def semantic_status(status: Mapping[str, Any]) -> dict[str, Any]:
    """Return only disposition semantics; generated timestamps are observational."""
    return {
        key: value
        for key, value in status.items()
        if key not in VOLATILE_STATUS_FIELDS
    }


def build_record(
    request: Mapping[str, Any],
    status: Mapping[str, Any],
    *,
    source: Mapping[str, Any],
    subject: str | None = None,
) -> dict[str, Any]:
    repository = _string(request.get("repository"), "request.repository")
    issue_number = _issue_number(request.get("issue_number"))
    bound_source = source_binding(source, repository)
    request_digest = sha256(dict(request))
    status_value = semantic_status(status)
    for key in ("status", "issue_disposition", "disposition_reason", "next_action"):
        _string(status_value.get(key), f"status.{key}")
    status_digest = sha256(status_value)
    identity = {
        "repository": repository,
        "subject": subject or f"issue/{issue_number}",
        "issue_number": issue_number,
        "request_sha256": request_digest,
        "status_semantic_sha256": status_digest,
        "source_binding": bound_source,
    }
    continuation_id = sha256(identity)
    blocker = status_value["disposition_reason"] if status_value["status"] in {"BLOCK", "CONTINUE"} else None
    return {
        "schema": SCHEMA,
        "record_type": "LOGICAL_CONTINUATION",
        "continuation_id": continuation_id,
        "identity": identity,
        "liveness": LIVENESS,
        "state": "LIVE",
        "current_binding": {
            "request_sha256": request_digest,
            "status_semantic_sha256": status_digest,
            "source": bound_source,
            "issue_disposition": status_value["issue_disposition"],
            "next_action": status_value["next_action"],
        },
        "first_blocker": blocker,
        "wake_predicates": [
            "ISSUE_SEMANTIC_REQUEST_SHA256_CHANGED",
            "ISSUE_STATUS_SEMANTIC_SHA256_CHANGED",
            "SOURCE_HEAD_TREE_OR_REF_CHANGED",
            "TRUSTED_MODEL_OR_WORKFLOW_ADMISSION_RECEIPT_CHANGED",
            "EXACT_HEAD_TREE_OR_REVIEW_BINDING_CHANGED",
        ],
        "observation_boundary": {
            "updated_at_is_semantic_input": False,
            "self_generated_status_or_comment_is_semantic_input": False,
            "time_elapsed_alone_wakes_continuation": False,
        },
        "completion": {
            "exact_postcondition_observed": False,
            "predecessor_stale_on_binding_drift": True,
            "external_hold_requires_authority_and_reason": True,
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }


def validate_record(record: Mapping[str, Any], request: Mapping[str, Any], status: Mapping[str, Any]) -> None:
    if record.get("schema") != SCHEMA:
        raise ContinuationError("continuation schema is invalid")
    if record.get("record_type") != "LOGICAL_CONTINUATION":
        raise ContinuationError("continuation record type is invalid")
    if record.get("liveness") != LIVENESS or record.get("state") != "LIVE":
        raise ContinuationError("continuation liveness/state is invalid")
    repository = _string(request.get("repository"), "request.repository")
    binding = _mapping(record.get("current_binding"), "continuation current binding")
    expected = build_record(request, status, source=source_binding(_mapping(binding.get("source"), "source binding"), repository))
    for key in (
        "continuation_id",
        "identity",
        "liveness",
        "state",
        "current_binding",
        "first_blocker",
        "wake_predicates",
        "observation_boundary",
        "completion",
    ):
        if record.get(key) != expected.get(key):
            raise ContinuationError(f"continuation {key} does not match exact semantic binding")


def load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ContinuationError(f"cannot load {label}: {exc}") from exc


def write_record(path: Path, record: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def materialize(
    directory: Path,
    issue: Mapping[str, Any] | None,
    repository: str | None,
    source: Mapping[str, Any] | None,
) -> dict[str, Any]:
    request = load_json(directory / "REQUEST.json", "request")
    status = load_json(directory / "STATUS.json", "status")
    if issue is not None:
        if repository is None:
            raise ContinuationError("repository is required with issue input")
        current = semantic_request(issue, repository)
        if current != request:
            raise ContinuationError("issue semantic input drifted before continuation materialization")
    if source is None:
        raise ContinuationError("exact source ref/head/tree binding is required")
    record = build_record(request, status, source=source)
    write_record(directory / "CONTINUATION.json", record)
    return record


def should_resume(
    issue: Mapping[str, Any],
    repository: str,
    record: Mapping[str, Any],
    source: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a causal wake decision; elapsed time is deliberately ignored."""
    if record.get("schema") != SCHEMA:
        raise ContinuationError("continuation schema is invalid")
    current_request = semantic_request(issue, repository)
    current_request_digest = sha256(current_request)
    identity = _mapping(record.get("identity"), "continuation identity")
    previous_digest = _string(identity.get("request_sha256"), "continuation request digest")
    if current_request_digest != previous_digest:
        return {
            "schema": "qikvrt_issue_continuation_wake_v1",
            "state": "REOBSERVE",
            "dispatch": True,
            "reason": "ISSUE_SEMANTIC_REQUEST_SHA256_CHANGED",
            "predecessor_continuation_id": record.get("continuation_id"),
            "current_request_sha256": current_request_digest,
        }
    current_source = source_binding(source, repository)
    previous_source = source_binding(
        _mapping(_mapping(record.get("current_binding"), "continuation current binding").get("source"), "source binding"),
        repository,
    )
    if current_source != previous_source:
        return {
            "schema": "qikvrt_issue_continuation_wake_v1",
            "state": "REOBSERVE",
            "dispatch": True,
            "reason": "SOURCE_HEAD_TREE_OR_REF_CHANGED",
            "predecessor_continuation_id": record.get("continuation_id"),
            "current_request_sha256": current_request_digest,
            "current_source_binding": current_source,
        }
    return {
        "schema": "qikvrt_issue_continuation_wake_v1",
        "state": "HOLD",
        "dispatch": False,
        "reason": "IDENTICAL_LIVE_CONTINUATION_NO_CAUSAL_WAKE",
        "continuation_id": record.get("continuation_id"),
        "current_request_sha256": current_request_digest,
    }


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    commands = value.add_subparsers(dest="command", required=True)
    materialize_command = commands.add_parser("materialize")
    materialize_command.add_argument("--directory", type=Path, required=True)
    materialize_command.add_argument("--issue", type=Path)
    materialize_command.add_argument("--repository")
    materialize_command.add_argument("--source-ref")
    materialize_command.add_argument("--source-head")
    materialize_command.add_argument("--source-tree")
    check_command = commands.add_parser("check")
    check_command.add_argument("--directory", type=Path, required=True)
    wake_command = commands.add_parser("should-resume")
    wake_command.add_argument("--issue", type=Path, required=True)
    wake_command.add_argument("--repository", required=True)
    wake_command.add_argument("--continuation", type=Path, required=True)
    wake_command.add_argument("--source-ref", required=True)
    wake_command.add_argument("--source-head", required=True)
    wake_command.add_argument("--source-tree", required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "materialize":
            issue = load_json(args.issue, "issue") if args.issue else None
            if not all((args.source_ref, args.source_head, args.source_tree, args.repository)):
                raise ContinuationError("materialization requires repository and exact source ref/head/tree")
            record = materialize(
                args.directory,
                issue,
                args.repository,
                {
                    "repository": args.repository,
                    "ref": args.source_ref,
                    "head_sha": args.source_head,
                    "tree_sha": args.source_tree,
                },
            )
        elif args.command == "check":
            request = load_json(args.directory / "REQUEST.json", "request")
            status = load_json(args.directory / "STATUS.json", "status")
            record = load_json(args.directory / "CONTINUATION.json", "continuation")
            validate_record(record, request, status)
            return 0
        else:
            issue = load_json(args.issue, "issue")
            record = load_json(args.continuation, "continuation")
            record = should_resume(
                issue,
                args.repository,
                record,
                {
                    "repository": args.repository,
                    "ref": args.source_ref,
                    "head_sha": args.source_head,
                    "tree_sha": args.source_tree,
                },
            )
        print(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", end="")
    except ContinuationError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
