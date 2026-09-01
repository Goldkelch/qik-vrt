#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pure, fail-closed classification for stalled pull-request heads.

The classifier deliberately has no GitHub client and performs no effect.  It turns
already collected run observations into the existing four-state D0 decision.  The
workflow remains responsible for exact-head reobservation and any bounded dispatch.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

_ALLOWED_EXACT_HEAD_STATUSES = frozenset(
    {
        "missing",
        "pending",
        "self_check_success",
        "success",
        "failure",
        "error",
        "incomplete",
        "unbound_verifier_completion",
        "repeated_unbound_verifier_completion",
        "repeated_or_ambiguous_exact_transport_orphan",
    }
)
_ALLOWED_OBSERVATION_EVENTS = frozenset(
    {
        "issue_comment",
        "pull_request",
        "pull_request_review",
        "pull_request_target",
        "push",
        "repository_dispatch",
        "schedule",
        "workflow_dispatch",
        "workflow_run",
    }
)


@dataclass(frozen=True)
class RecoveryDecision:
    """One bounded D0 result for an exact pull-request head."""

    d0: int
    state: str
    reason: str
    active_workflows: int
    executed_failures: int
    zero_job_action_required: int
    continuation_mode: str
    continuation_owner: str
    continuation_next_action: str
    continuation_resume_events: tuple[str, ...]
    persistence_run_terminal: bool
    client_return_allowed: bool

    def to_mapping(self) -> dict[str, object]:
        return {
            "d0": self.d0,
            "state": self.state,
            "reason": self.reason,
            "active_workflows": self.active_workflows,
            "executed_failures": self.executed_failures,
            "zero_job_action_required": self.zero_job_action_required,
            "continuation": {
                "schema": "qikvrt.causal-continuation.v1",
                "mode": self.continuation_mode,
                "owner": self.continuation_owner,
                "next_action": self.continuation_next_action,
                "resume_events": list(self.continuation_resume_events),
                "persistence_run_terminal": self.persistence_run_terminal,
                "client_return_allowed": self.client_return_allowed,
            },
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
        }


@dataclass(frozen=True)
class _Observation:
    run_id: int
    workflow_id: int
    workflow_path: str
    event: str
    name: str
    status: str
    conclusion: str | None
    jobs_total: int
    created_at: datetime


def _require_integer(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _parse_created_at(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError("created_at must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("created_at must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("created_at must include a timezone")
    return parsed


def _normalize(raw: Mapping[str, object]) -> _Observation:
    run_id = _require_integer(raw.get("id"), "id")
    if run_id < 0:
        raise ValueError("id must be non-negative")

    workflow_id = _require_integer(raw.get("workflow_id"), "workflow_id")
    if workflow_id <= 0:
        raise ValueError("workflow_id must be positive")

    workflow_path = raw.get("workflow_path")
    if not isinstance(workflow_path, str) or not workflow_path.strip():
        raise ValueError("workflow_path must be a non-empty string")
    workflow_path = workflow_path.strip().split("@", 1)[0]
    if not workflow_path.startswith(".github/workflows/"):
        raise ValueError("workflow_path must be a repository workflow path")

    event = raw.get("event")
    if not isinstance(event, str) or event not in _ALLOWED_OBSERVATION_EVENTS:
        raise ValueError(
            "event must be a permitted server workflow event: "
            + ", ".join(sorted(_ALLOWED_OBSERVATION_EVENTS))
        )

    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("name must be a non-empty string")

    status = raw.get("status")
    if not isinstance(status, str) or not status:
        raise ValueError("status must be a non-empty string")

    conclusion = raw.get("conclusion")
    if conclusion is not None and not isinstance(conclusion, str):
        raise ValueError("conclusion must be a string or null")

    jobs_total = _require_integer(raw.get("jobs_total"), "jobs_total")
    if jobs_total < 0:
        raise ValueError("jobs_total must be non-negative")

    return _Observation(
        run_id=run_id,
        workflow_id=workflow_id,
        workflow_path=workflow_path,
        event=event,
        name=name.strip(),
        status=status,
        conclusion=conclusion,
        jobs_total=jobs_total,
        created_at=_parse_created_at(raw.get("created_at")),
    )


def _latest_by_workflow(
    observations: Iterable[Mapping[str, object]],
) -> tuple[_Observation, ...]:
    """Return only the latest run per workflow using timestamp and run_id."""

    latest: dict[tuple[int, str, str], _Observation] = {}
    for raw in observations:
        if not isinstance(raw, Mapping):
            raise ValueError("each observation must be an object")
        current = _normalize(raw)
        identity = (current.workflow_id, current.workflow_path, current.event)
        previous = latest.get(identity)
        if previous is None or (current.created_at, current.run_id) > (
            previous.created_at,
            previous.run_id,
        ):
            latest[identity] = current
    return tuple(latest[identity] for identity in sorted(latest))


def flatten_run_pages(pages: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Flatten a fully paginated Actions response and prove count completeness."""

    if not pages:
        raise ValueError("run pages must be a non-empty array")
    total_count = _require_integer(pages[0].get("total_count"), "total_count")
    if total_count < 0:
        raise ValueError("total_count must be non-negative")
    runs: list[Mapping[str, object]] = []
    for page in pages:
        if not isinstance(page, Mapping):
            raise ValueError("each run page must be an object")
        page_total = _require_integer(page.get("total_count"), "total_count")
        if page_total != total_count:
            raise ValueError("run page total_count values must agree")
        page_runs = page.get("workflow_runs")
        if not isinstance(page_runs, list):
            raise ValueError("workflow_runs must be an array")
        for run in page_runs:
            if not isinstance(run, Mapping):
                raise ValueError("each workflow run must be an object")
            runs.append(run)
    if len(runs) != total_count:
        raise ValueError(
            f"incomplete run pagination: observed {len(runs)} of {total_count}"
        )
    return {"total_count": total_count, "workflow_runs": runs}


def validate_publisher_receipt(
    receipt: Mapping[str, object], expected: Mapping[str, object]
) -> dict[str, object]:
    """Validate exact PR subject binding for a trusted publisher receipt.

    A shared commit SHA is deliberately insufficient: PR number, head repository
    and ref, tree, base ref and base SHA are all part of the subject identity.
    """

    bindings = {
        "repository": "repository",
        "pull_request": "pull_request",
        "head_repository": "head_repository",
        "head_ref": "head_ref",
        "head_sha": "head_sha",
        "head_tree_sha": "head_tree_sha",
        "base_ref": "base_ref",
        "base_sha": "base_sha",
        "run_id": "run_id",
        "run_attempt": "run_attempt",
        "workflow_ref": "workflow_ref",
        "workflow_sha": "workflow_sha",
    }
    if receipt.get("schema") != "qikvrt.autonomous-candidate-self-check-publisher.v2":
        raise ValueError("publisher receipt schema mismatch")
    for receipt_field, expected_field in bindings.items():
        if receipt.get(receipt_field) != expected.get(expected_field):
            raise ValueError(f"publisher receipt {receipt_field} mismatch")
    if receipt.get("status_context") != "QIKVRT autonomous candidate self-check":
        raise ValueError("publisher receipt status context mismatch")
    if receipt.get("classification") != "CANDIDATE_SELF_CHECK_ONLY":
        raise ValueError("publisher receipt classification mismatch")
    if receipt.get("trusted_terminal_verification") is not False:
        raise ValueError("candidate self-check cannot be terminal trusted evidence")
    if receipt.get("productive_effect") is not False:
        raise ValueError("publisher receipt cannot claim a productive effect")
    if receipt.get("effect_ack") != "NOT_REQUIRED":
        raise ValueError("publisher receipt effect acknowledgement mismatch")
    dispatch_binding = receipt.get("dispatch_binding")
    if not isinstance(dispatch_binding, Mapping):
        raise ValueError("publisher receipt dispatch binding must be an object")
    binding_artifact = dispatch_binding.get("artifact")
    if not isinstance(binding_artifact, Mapping):
        raise ValueError("publisher receipt dispatch binding artifact missing")
    binding_artifact_id = _require_integer(
        binding_artifact.get("id"), "dispatch_binding.artifact.id"
    )
    if binding_artifact_id <= 0:
        raise ValueError("dispatch binding artifact ID must be positive")
    binding_digest = binding_artifact.get("digest")
    if (
        not isinstance(binding_digest, str)
        or not binding_digest.startswith("sha256:")
        or len(binding_digest) != 71
        or any(
            character not in "0123456789abcdef"
            for character in binding_digest.removeprefix("sha256:")
        )
    ):
        raise ValueError("dispatch binding artifact digest mismatch")
    binding_attempt = _require_integer(
        dispatch_binding.get("run_attempt"), "dispatch_binding.run_attempt"
    )
    receipt_attempt = _require_integer(receipt.get("run_attempt"), "run_attempt")
    if binding_attempt <= 0 or binding_attempt > receipt_attempt:
        raise ValueError("dispatch binding attempt must bind this or an earlier run attempt")
    if dispatch_binding.get("receipt_outcome") != "success":
        raise ValueError("dispatch binding receipt outcome mismatch")
    published_state = receipt.get("published_state")
    if published_state not in {"success", "failure", "error"}:
        raise ValueError("publisher receipt state is not fail-closed terminal")
    review_transport = receipt.get("review_transport")
    if not isinstance(review_transport, Mapping):
        raise ValueError("publisher receipt review transport must be an object")
    if published_state == "success":
        if receipt.get("review_dispatch_outcome") != "pending":
            raise ValueError("successful self-check must preserve a pending review outbox")
        if (
            review_transport.get("attempt") != 1
            or review_transport.get("outcome") != "intent_persisted"
            or not isinstance(review_transport.get("intent_artifact"), Mapping)
        ):
            raise ValueError("successful self-check review outbox mismatch")
    elif (
        receipt.get("review_dispatch_outcome") != "not_applicable"
        or review_transport.get("attempt") is not None
        or review_transport.get("outcome") != "not_applicable"
        or review_transport.get("intent_artifact") is not None
    ):
        raise ValueError("adverse self-check must not claim a review transport")
    producer = receipt.get("producer")
    if not isinstance(producer, Mapping):
        raise ValueError("publisher receipt producer must be an object")
    for field in ("run_id", "run_attempt", "workflow_id"):
        value = _require_integer(producer.get(field), f"producer.{field}")
        if value <= 0:
            raise ValueError(f"producer.{field} must be positive")
    if producer.get("workflow_path") != (
        ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
    ):
        raise ValueError("publisher receipt producer workflow path mismatch")
    producer_sha = producer.get("workflow_sha")
    if (
        not isinstance(producer_sha, str)
        or len(producer_sha) != 40
        or any(character not in "0123456789abcdef" for character in producer_sha)
    ):
        raise ValueError("publisher receipt producer workflow SHA mismatch")
    continuation_artifact = producer.get("continuation_artifact")
    if not isinstance(continuation_artifact, Mapping):
        raise ValueError("publisher receipt producer continuation artifact missing")
    artifact_id = _require_integer(
        continuation_artifact.get("id"), "producer.continuation_artifact.id"
    )
    if artifact_id <= 0:
        raise ValueError("producer continuation artifact ID must be positive")
    artifact_digest = continuation_artifact.get("digest")
    if (
        not isinstance(artifact_digest, str)
        or not artifact_digest.startswith("sha256:")
        or len(artifact_digest) != 71
        or any(
            character not in "0123456789abcdef"
            for character in artifact_digest.removeprefix("sha256:")
        )
    ):
        raise ValueError("producer continuation artifact digest mismatch")
    return {"valid": True, "published_state": published_state}


def classify_observations(
    observations: Iterable[Mapping[str, object]],
    *,
    exact_head_status: str | None = None,
    trusted_exact_head_source: bool = False,
    terminal_gates_bound: bool = False,
) -> RecoveryDecision:
    """Classify one exact head without fabricating productive authority.

    Precedence is fail-closed: active work and executed failures HOLD; a trusted
    exact-head status makes dispatch idempotent; only the characteristic latest
    zero-job ``action_required`` state selects REOBSERVE.  A generic successful
    observation set is never terminal by itself: client return requires an
    explicitly trusted exact-head success with independently bound terminal
    review and ruleset gates.
    """

    normalized_status = "missing" if exact_head_status is None else exact_head_status
    if normalized_status not in _ALLOWED_EXACT_HEAD_STATUSES:
        raise ValueError(
            "exact_head_status must be one of missing, pending, self_check_success, "
            "success, failure, error, incomplete, unbound_verifier_completion, "
            "repeated_unbound_verifier_completion, "
            "repeated_or_ambiguous_exact_transport_orphan"
        )
    untrusted_exact_head_status = (
        normalized_status != "missing" and not trusted_exact_head_source
    )
    if not isinstance(terminal_gates_bound, bool):
        raise ValueError("terminal_gates_bound must be a boolean")
    if terminal_gates_bound and not (
        trusted_exact_head_source and normalized_status == "success"
    ):
        raise ValueError(
            "terminal_gates_bound requires trusted exact-head success"
        )

    latest = _latest_by_workflow(observations)
    active_workflows = sum(item.status != "completed" for item in latest)
    executed_failures = sum(
        item.status == "completed"
        and item.conclusion != "success"
        and not (
            item.conclusion == "action_required" and item.jobs_total == 0
        )
        for item in latest
    )
    zero_job_action_required = sum(
        item.status == "completed"
        and item.conclusion == "action_required"
        and item.jobs_total == 0
        for item in latest
    )

    def decision(d0: int, state: str, reason: str) -> RecoveryDecision:
        if d0 == 0:
            continuation = (
                "NONE",
                "NONE",
                "NONE",
                (),
                True,
                True,
            )
        elif reason in {
            "ACTIVE_WORKFLOW",
            "TRUSTED_EXACT_HEAD_VERIFICATION_PENDING",
            "CANDIDATE_SELF_CHECK_SCOPE_COMPLETE",
            "TRUSTED_EXACT_HEAD_SCOPE_COMPLETE_GATES_PENDING",
            "OBSERVED_WORKFLOW_SCOPE_COMPLETE_GATES_PENDING",
            "UNBOUND_VERIFIER_COMPLETION_AWAITS_EXTERNAL_EDGE",
        }:
            if reason in {
                "CANDIDATE_SELF_CHECK_SCOPE_COMPLETE",
                "TRUSTED_EXACT_HEAD_SCOPE_COMPLETE_GATES_PENDING",
                "OBSERVED_WORKFLOW_SCOPE_COMPLETE_GATES_PENDING",
            }:
                next_action = (
                    "OBSERVE_REQUESTED_REVIEW_EXECUTOR_INDEPENDENT_REVIEW_AND_RULESET_GATES"
                )
                resume_events = (
                    "workflow_run.requested_review_executor.completed",
                    "workflow_run.code_owner_review_observer.completed",
                    "workflow_run.required_review_gate.completed",
                    "workflow_run.main_ruleset_reconciler.completed",
                    "pull_request_target.synchronize",
                )
            elif reason == "UNBOUND_VERIFIER_COMPLETION_AWAITS_EXTERNAL_EDGE":
                next_action = "REOBSERVE_AFTER_EXTERNAL_SUBJECT_OR_MANUAL_EDGE"
                resume_events = (
                    "workflow_run.code_owner_review_observer.completed",
                    "workflow_run.requested_review_executor.completed",
                    "pull_request_target.synchronize",
                    "workflow_dispatch",
                )
            else:
                next_action = "REOBSERVE_EXACT_HEAD_AFTER_WORKFLOW_TRANSITION"
                resume_events = (
                    "workflow_run.completed",
                    "pull_request_target.synchronize",
                    "workflow_dispatch",
                )
            continuation = (
                "AWAIT_EXACT_EVENT",
                "REPOSITORY_EVENT_LOOP",
                next_action,
                resume_events,
                False,
                False,
            )
        elif d0 == 1:
            continuation = (
                "EXECUTE_REPAIR",
                "AUTHORIZED_PERSISTENCE_CLIENT",
                "DIAGNOSE_FIRST_CAUSAL_FAILURE_AND_EXECUTE_SMALLEST_REPOSITORY_SAFE_REPAIR",
                (
                    "workflow_run.completed",
                    "pull_request_target.synchronize",
                    "workflow_dispatch",
                ),
                False,
                False,
            )
        elif d0 == 3:
            if reason == "REPEATED_REQUESTED_REVIEW_TRANSPORT_FAILURE":
                next_action = (
                    "INSPECT_BOUND_REQUESTED_REVIEW_TRANSPORT_AND_AUTHORIZE_ONE_SAFE_CONTINUATION"
                )
            elif reason == "REPEATED_OR_AMBIGUOUS_EXACT_TRANSPORT_ORPHAN":
                next_action = (
                    "INSPECT_BOUND_ORPHAN_EXACT_TRANSPORT_AND_AUTHORIZE_NO_MORE_THAN_ONE_CONTINUATION"
                )
            else:
                next_action = (
                    "INSPECT_REPEATED_UNBOUND_VERIFIER_COMPLETION_AND_AUTHORIZE_ONE_EXACT_CONTINUATION"
                )
            continuation = (
                "REQUEST_AUTHORITY",
                "AUTHORITY_ADMIN",
                next_action,
                (
                    "workflow_dispatch",
                    "pull_request_target.synchronize",
                    "workflow_run.code_owner_review_observer.completed",
                ),
                False,
                False,
            )
        else:
            continuation = (
                "EXECUTE_REOBSERVATION",
                "REPOSITORY_EVENT_LOOP",
                "DISPATCH_EXACT_HEAD_REOBSERVATION",
                (),
                False,
                False,
            )
        return RecoveryDecision(
            d0=d0,
            state=state,
            reason=reason,
            active_workflows=active_workflows,
            executed_failures=executed_failures,
            zero_job_action_required=zero_job_action_required,
            continuation_mode=continuation[0],
            continuation_owner=continuation[1],
            continuation_next_action=continuation[2],
            continuation_resume_events=continuation[3],
            persistence_run_terminal=continuation[4],
            client_return_allowed=continuation[5],
        )

    if active_workflows:
        return decision(1, "HOLD", "ACTIVE_WORKFLOW")
    if untrusted_exact_head_status:
        return decision(2, "REOBSERVE", "UNTRUSTED_EXACT_HEAD_STATUS_SOURCE")
    if normalized_status == "pending":
        return decision(1, "HOLD", "TRUSTED_EXACT_HEAD_VERIFICATION_PENDING")
    if normalized_status == "unbound_verifier_completion":
        return decision(
            1, "HOLD", "UNBOUND_VERIFIER_COMPLETION_AWAITS_EXTERNAL_EDGE"
        )
    if normalized_status == "repeated_unbound_verifier_completion":
        return decision(3, "REQUEST_AUTHORITY", "REPEATED_UNBOUND_VERIFIER_COMPLETION")
    if normalized_status == "repeated_or_ambiguous_exact_transport_orphan":
        return decision(
            3,
            "REQUEST_AUTHORITY",
            "REPEATED_OR_AMBIGUOUS_EXACT_TRANSPORT_ORPHAN",
        )
    if executed_failures:
        return decision(1, "HOLD", "ADVERSE_TERMINAL_RESULT_PRESENT")
    if normalized_status == "self_check_success":
        return decision(1, "HOLD", "CANDIDATE_SELF_CHECK_SCOPE_COMPLETE")
    if normalized_status in {"failure", "error"}:
        return decision(1, "HOLD", "TRUSTED_EXACT_HEAD_VERIFICATION_FAILED")
    if normalized_status == "incomplete":
        return decision(2, "REOBSERVE", "TRUSTED_EXACT_HEAD_EVIDENCE_INCOMPLETE")
    if normalized_status == "success" and terminal_gates_bound:
        return decision(0, "NOOP", "TRUSTED_EXACT_HEAD_VERIFIED")
    if normalized_status == "success":
        return decision(1, "HOLD", "TRUSTED_EXACT_HEAD_SCOPE_COMPLETE_GATES_PENDING")
    if zero_job_action_required:
        return decision(2, "REOBSERVE", "ZERO_JOB_ACTION_REQUIRED")
    if not latest:
        return decision(2, "REOBSERVE", "NO_EXACT_HEAD_WORKFLOW_OBSERVATIONS")
    return decision(1, "HOLD", "OBSERVED_WORKFLOW_SCOPE_COMPLETE_GATES_PENDING")


def _read_json_value(path: str) -> Any:
    stream = sys.stdin if path == "-" else Path(path).open(encoding="utf-8")
    try:
        value: Any = json.load(stream)
    finally:
        if stream is not sys.stdin:
            stream.close()
    return value


def _read_payload(path: str) -> Sequence[Mapping[str, object]]:
    value = _read_json_value(path)
    if isinstance(value, dict):
        value = value.get("observations")
    if not isinstance(value, list):
        raise ValueError("input must be a JSON array or an object with observations")
    return value


def _write_payload(path: str, value: Mapping[str, object]) -> None:
    text = json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    if path == "-":
        sys.stdout.write(text)
        return
    Path(path).write_text(text, encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    classify = commands.add_parser("classify", help="classify collected run observations")
    classify.add_argument("--input", required=True, help="JSON input path or -")
    classify.add_argument("--output", default="-", help="JSON output path or -")
    classify.add_argument(
        "--exact-head-status",
        default="missing",
        choices=sorted(_ALLOWED_EXACT_HEAD_STATUSES),
        help="latest target-commit status for trusted exact-head verification",
    )
    classify.add_argument(
        "--trusted-exact-head-source",
        action="store_true",
        help="status is bound to the trusted verifier publisher run and receipt",
    )
    classify.add_argument(
        "--terminal-gates-bound",
        action="store_true",
        help=(
            "independent exact review and ruleset terminal gates are bound; valid "
            "only with trusted exact-head success"
        ),
    )
    flatten = commands.add_parser(
        "flatten-runs", help="verify and flatten paginated Actions run responses"
    )
    flatten.add_argument("--input", required=True, help="JSON page array path")
    flatten.add_argument("--output", default="-", help="JSON output path or -")
    validate = commands.add_parser(
        "validate-publisher-receipt",
        help="validate an exact-subject candidate self-check publisher receipt",
    )
    validate.add_argument("--input", required=True, help="publisher receipt path")
    validate.add_argument("--expected", required=True, help="expected subject path")
    validate.add_argument("--output", default="-", help="JSON output path or -")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "classify":
            result = classify_observations(
                _read_payload(args.input),
                exact_head_status=args.exact_head_status,
                trusted_exact_head_source=args.trusted_exact_head_source,
                terminal_gates_bound=args.terminal_gates_bound,
            ).to_mapping()
        elif args.command == "flatten-runs":
            pages = _read_json_value(args.input)
            if not isinstance(pages, list):
                raise ValueError("run pages must be a JSON array")
            result = flatten_run_pages(pages)
        elif args.command == "validate-publisher-receipt":
            receipt = _read_json_value(args.input)
            expected = _read_json_value(args.expected)
            if not isinstance(receipt, Mapping) or not isinstance(expected, Mapping):
                raise ValueError("receipt and expected subject must be JSON objects")
            result = validate_publisher_receipt(receipt, expected)
        else:
            raise ValueError(f"unsupported command: {args.command}")
        _write_payload(args.output, result)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
