#!/usr/bin/env python3
"""Materialize one Mesh-review successor result for the shared FIFO.

This adapter is intentionally API-free.  A trusted default-branch observer
supplies the exact current FIFO item, the accepted child run, the complete job
set and one run-owned artifact.  The adapter validates those bytes and emits
only Core completion/terminal evidence; it never performs a transport or a
ledger mutation itself.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import pathlib
import re
import zipfile
from collections.abc import Mapping, Sequence
from typing import Any

from tools.qikvrt_native_account_review import (
    NativeAccountReviewError,
    verify_trusted_executor_producer_binding,
)
from tools.qikvrt_requested_review_executor import (
    ReviewSnapshotError,
    mesh_receipt_semantics,
    requested_review_dispatch_child,
    validate_requested_review_completion_envelope,
)
from tools.qikvrt_ruleset_outbox import (
    AUTHORITY_OBSERVATION_SCHEMA,
    BUSINESS_RECEIPT_SCHEMA,
    COMPLETION_EVIDENCE_SCHEMA,
    TERMINAL_EVIDENCE_SCHEMA,
    OutboxBlock,
    canonical_bytes,
    digest,
    empty_completion_claims,
    normalize_child_for_intent,
    validate_authority_observation_record,
    validate_retry_scan_cursor_record,
    validate_terminal_evidence,
)


LANE = "mesh-review-successor-dispatch"
WORKFLOW_PATH = ".github/workflows/qikvrt_requested_review_executor.yml"
SUCCESS_FILES = frozenset(
    {
        "review.json",
        "review.diff",
        "ledger-write.json",
        "review-transport.json",
        "producer-binding.json",
    }
)
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
TIMESTAMP = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)


class MeshReviewOutboxError(RuntimeError):
    """Fail-closed Mesh-review successor evidence error."""


def select_mesh_completion_target(item: Mapping[str, Any]) -> dict[str, Any]:
    """Select the sole accepted child or the exact orphan transport to adopt."""
    if not isinstance(item, Mapping):
        raise MeshReviewOutboxError("Mesh frontier item is malformed")
    if item.get("state") in {"EMPTY", "QUEUED", "TERMINAL"}:
        return {
            "schema": "qikvrt_mesh_review_completion_target_v1",
            "state": "NOOP",
            "needed": False,
            "first_blocker": None,
            "sequence": item.get("sequence"),
            "fingerprint": item.get("fingerprint"),
            "transport_attempt": None,
            "child_recovery": False,
            "child": None,
            "productive_effect": False,
        }
    intent = item.get("intent")
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != LANE
        or not isinstance(intent, Mapping)
    ):
        raise MeshReviewOutboxError("Mesh frontier item is not current pending work")
    acceptances = item.get("acceptance")
    recoveries = item.get("child_recovery")
    transports = item.get("transport")
    if (
        not isinstance(acceptances, Mapping)
        or not isinstance(recoveries, Mapping)
        or not isinstance(transports, Mapping)
    ):
        raise MeshReviewOutboxError("Mesh frontier state maps are malformed")
    recovered = []
    for key, value in recoveries.items():
        acceptance = value.get("acceptance") if isinstance(value, Mapping) else None
        if isinstance(acceptance, Mapping):
            recovered.append((key, acceptance))
    direct = [
        (key, value)
        for key, value in acceptances.items()
        if isinstance(value, Mapping)
    ]
    if recovered:
        if len(recovered) != 1:
            raise MeshReviewOutboxError("Mesh recovered acceptance is ambiguous")
        attempt_text, acceptance = recovered[0]
        child_recovery = True
    elif direct:
        if len(direct) != 1:
            raise MeshReviewOutboxError("Mesh direct acceptance is ambiguous")
        attempt_text, acceptance = direct[0]
        child_recovery = False
    else:
        if len(transports) != 1:
            raise MeshReviewOutboxError("Mesh orphan transport is ambiguous")
        attempt_text = next(iter(transports))
        try:
            attempt = int(attempt_text)
        except (TypeError, ValueError) as exc:
            raise MeshReviewOutboxError("Mesh transport attempt is invalid") from exc
        if attempt != 1:
            raise MeshReviewOutboxError(
                "Mesh one-shot transport must not create attempt two"
            )
        cursor_records = item.get("retry_scan_cursor", {})
        if not isinstance(cursor_records, Mapping):
            raise MeshReviewOutboxError("Mesh retry cursor projection is malformed")
        record = cursor_records.get(str(attempt))
        if record is not None and not isinstance(record, Mapping):
            raise MeshReviewOutboxError("Mesh retry cursor record is malformed")
        cursor = record.get("cursor") if isinstance(record, Mapping) else None
        if cursor is not None and not isinstance(cursor, Mapping):
            raise MeshReviewOutboxError("Mesh retry cursor body is malformed")
        cursor_state = record.get("state") if isinstance(record, Mapping) else None
        if cursor_state in {
            "COMPLETE_SUCCESSOR_OBSERVED",
            "AMBIGUITY_SET_EXCEEDED_AUTHORITY",
        }:
            candidates = cursor.get("candidate_locators")
            count = cursor.get("bound_successor_count")
            if (
                not isinstance(candidates, list)
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 1
            ):
                raise MeshReviewOutboxError("Mesh closed cursor is malformed")
            if (
                cursor_state == "COMPLETE_SUCCESSOR_OBSERVED"
                and count == 1
                and len(candidates) == 1
            ):
                return {
                    "schema": "qikvrt_mesh_review_completion_target_v1",
                    "state": "ADOPT_CURSOR_CHILD",
                    "needed": True,
                    "first_blocker": None,
                    "sequence": intent["sequence"],
                    "fingerprint": intent["fingerprint"],
                    "transport_attempt": attempt,
                    "child_recovery": False,
                    "child": dict(candidates[0]),
                    "productive_effect": False,
                }
            return {
                "schema": "qikvrt_mesh_review_completion_target_v1",
                "state": "TERMINALIZE_ORPHAN",
                "needed": True,
                "first_blocker": (
                    "MESH_REVIEW_TRANSPORT_CHILD_AMBIGUOUS"
                    if count <= 8
                    else "MESH_REVIEW_TRANSPORT_CHILD_SET_EXCEEDED"
                ),
                "sequence": intent["sequence"],
                "fingerprint": intent["fingerprint"],
                "transport_attempt": attempt,
                "child_recovery": False,
                "child": None,
                "productive_effect": False,
            }
        if cursor_state == "COMPLETE_ZERO_SUCCESSOR":
            return {
                "schema": "qikvrt_mesh_review_completion_target_v1",
                "state": "TERMINALIZE_ORPHAN",
                "needed": True,
                "first_blocker": "REPEATED_MESH_REVIEW_TRANSPORT_UNACKNOWLEDGED",
                "sequence": intent["sequence"],
                "fingerprint": intent["fingerprint"],
                "transport_attempt": attempt,
                "child_recovery": False,
                "child": None,
                "productive_effect": False,
            }
        if cursor_state == "SCAN_BOUND_EXCEEDED_AUTHORITY":
            return {
                "schema": "qikvrt_mesh_review_completion_target_v1",
                "state": "TERMINALIZE_ORPHAN",
                "needed": True,
                "first_blocker": "MESH_REVIEW_RECOVERY_QUERY_BOUND_EXCEEDED",
                "sequence": intent["sequence"],
                "fingerprint": intent["fingerprint"],
                "transport_attempt": attempt,
                "child_recovery": False,
                "child": None,
                "productive_effect": False,
            }
        if cursor_state == "SCAN_INVENTORY_INCONSISTENT_AUTHORITY":
            return {
                "schema": "qikvrt_mesh_review_completion_target_v1",
                "state": "TERMINALIZE_ORPHAN",
                "needed": True,
                "first_blocker": (
                    "MESH_REVIEW_RECOVERY_QUERY_INVENTORY_INCONSISTENT"
                ),
                "sequence": intent["sequence"],
                "fingerprint": intent["fingerprint"],
                "transport_attempt": attempt,
                "child_recovery": False,
                "child": None,
                "productive_effect": False,
            }
        if cursor_state not in {
            None,
            "BOUNDARY_STABILIZATION_REOBSERVE",
            "SCAN_INCOMPLETE_REOBSERVE",
        }:
            raise MeshReviewOutboxError("Mesh retry cursor state is unsupported")
        return {
            "schema": "qikvrt_mesh_review_completion_target_v1",
            "state": "SCAN_ORPHAN",
            "needed": True,
            "first_blocker": "MESH_REVIEW_TRANSPORT_ACCEPTANCE_NOT_RECORDED",
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "transport_attempt": attempt,
            "child_recovery": False,
            "child": None,
            "productive_effect": False,
        }
    try:
        attempt = int(attempt_text)
    except (TypeError, ValueError) as exc:
        raise MeshReviewOutboxError("Mesh accepted transport attempt is invalid") from exc
    child = acceptance.get("child")
    if attempt != 1 or not isinstance(child, Mapping):
        raise MeshReviewOutboxError("Mesh accepted child binding is invalid")
    return {
        "schema": "qikvrt_mesh_review_completion_target_v1",
        "state": "OBSERVE_CHILD",
        "needed": True,
        "first_blocker": None,
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "transport_attempt": attempt,
        "child_recovery": child_recovery,
        "child": dict(child),
        "productive_effect": False,
    }


def select_mesh_orphan_adoption(
    *,
    item: Mapping[str, Any],
    actor_run: Mapping[str, Any],
    candidate_runs: Sequence[Mapping[str, Any]],
    scan_complete: bool,
    transport_attempt: int,
) -> dict[str, Any]:
    """Select one exact child after POST-to-acceptance interruption.

    Discovery is bounded to the immutable actor execution interval.  The
    caller must completely paginate that exact interval.  A missing or
    ambiguous child is a non-authorizing observation; only a unique canonical
    v3 locator may be handed to Core ``accept``.
    """
    intent = item.get("intent")
    transports = item.get("transport")
    acceptances = item.get("acceptance")
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != LANE
        or not isinstance(intent, Mapping)
        or transport_attempt != 1
        or not isinstance(transports, Mapping)
        or not isinstance(transports.get(str(transport_attempt)), Mapping)
        or (isinstance(acceptances, Mapping) and acceptances)
        or scan_complete is not True
        or not isinstance(candidate_runs, Sequence)
        or isinstance(candidate_runs, (str, bytes))
    ):
        raise MeshReviewOutboxError("orphan adoption input is incomplete")
    transport = transports[str(transport_attempt)]
    start = actor_run.get("run_started_at")
    end = actor_run.get("updated_at")
    raw_path = actor_run.get("path")
    actor_repository = actor_run.get("repository")
    if (
        actor_run.get("id") != transport.get("actor_run_id")
        or actor_run.get("run_attempt") != transport.get("actor_run_attempt")
        or not isinstance(raw_path, str)
        or raw_path.split("@", 1)[0] != WORKFLOW_PATH
        or not isinstance(actor_repository, Mapping)
        or actor_repository.get("full_name") != intent.get("repository")
        or actor_run.get("status") != "completed"
        or not isinstance(actor_run.get("conclusion"), str)
        or not actor_run["conclusion"]
        or not isinstance(start, str)
        or not isinstance(end, str)
        or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", start)
        is None
        or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", end)
        is None
        or start > end
    ):
        raise MeshReviewOutboxError("orphan adoption actor binding is invalid")
    target = intent.get("payload", {}).get("target")
    inputs = intent.get("payload", {}).get("request", {}).get("inputs")
    if not isinstance(target, Mapping) or not isinstance(inputs, Mapping):
        raise MeshReviewOutboxError("orphan adoption target is invalid")
    matches: list[dict[str, Any]] = []
    for raw in candidate_runs:
        if not isinstance(raw, Mapping):
            raise MeshReviewOutboxError("orphan candidate run is malformed")
        created_at = raw.get("created_at")
        if (
            not isinstance(created_at, str)
            or re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",
                created_at,
            )
            is None
        ):
            raise MeshReviewOutboxError("orphan candidate timestamp is invalid")
        if created_at < start or created_at > end:
            continue
        try:
            child = requested_review_dispatch_child(
                raw,
                repository=intent["repository"],
                workflow_id=target["workflow_id"],
                evaluator_sha=inputs["evaluator_sha"],
                display_title=(
                    f"qikvrt-rr-v3 e={inputs['evaluator_sha']} "
                    f"p={inputs['pr']} h={inputs['head']} "
                    f"f={inputs['fingerprint']} i={intent['fingerprint']} "
                    f"a={transport_attempt}"
                ),
            )
            child = normalize_child_for_intent(
                child, intent=intent, attempt=transport_attempt
            )
        except (ReviewSnapshotError, OutboxBlock, KeyError, TypeError, ValueError):
            continue
        matches.append(child)
    unique = {digest(child): child for child in matches}
    if len(unique) > 1:
        return {
            "schema": "qikvrt_mesh_review_orphan_adoption_v1",
            "state": "REQUEST_AUTHORITY",
            "adopted": False,
            "first_blocker": "MESH_REVIEW_ORPHAN_CHILD_AMBIGUOUS",
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "transport_attempt": transport_attempt,
            "actor_run_id": actor_run["id"],
            "actor_run_attempt": actor_run["run_attempt"],
            "window_start": start,
            "window_end": end,
            "matching_child_count": len(unique),
            "child": None,
            "verified": True,
            "productive_effect": False,
        }
    child = next(iter(unique.values()), None)
    return {
        "schema": "qikvrt_mesh_review_orphan_adoption_v1",
        "state": "ADOPT" if child is not None else "WAIT",
        "adopted": child is not None,
        "first_blocker": (
            None if child is not None else "MESH_REVIEW_ORPHAN_CHILD_NOT_OBSERVED"
        ),
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "transport_attempt": transport_attempt,
        "actor_run_id": actor_run["id"],
        "actor_run_attempt": actor_run["run_attempt"],
        "window_start": start,
        "window_end": end,
        "matching_child_count": len(unique),
        "child": child,
        "verified": True,
        "productive_effect": False,
    }


def materialize_mesh_retry_scan_cursor(
    *,
    item: Mapping[str, Any],
    transport_attempt: int,
    actor_run: Mapping[str, Any],
    observer_run: Mapping[str, Any],
    page_runs: Sequence[Mapping[str, Any]],
    declared_total_count: int,
    queried_window_start: str,
    queried_window_end: str,
    observation_started_at: str,
    observation_completed_at: str,
    same_second_boundary_complete: bool,
    page_cap: int = 10,
) -> dict[str, Any]:
    """Build one durable, bounded Mesh orphan-discovery cursor.

    The cursor is the sole source for adoption or one-shot Authority closure.
    It consumes at most one API page per scheduled observer run, freezes the
    actor time/ID boundary before making an absence claim, and carries no
    transport authority itself.  In particular it never creates attempt two;
    Mesh transport is at-most-once and replay is observe/adopt/terminalize only.
    """

    intent = item.get("intent")
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != LANE
        or not isinstance(intent, Mapping)
        or transport_attempt != 1
        or str(transport_attempt) not in item.get("transport", {})
        or item.get("acceptance")
        or item.get("completion")
        or isinstance(page_cap, bool)
        or not isinstance(page_cap, int)
        or not (1 <= page_cap <= 100)
        or not isinstance(same_second_boundary_complete, bool)
        or isinstance(declared_total_count, bool)
        or not isinstance(declared_total_count, int)
        or declared_total_count < 0
    ):
        raise MeshReviewOutboxError(
            "Mesh retry cursor input is not one unaccepted attempt-one transport"
        )

    transport = item["transport"][str(transport_attempt)]
    try:
        actor = {
            "workflow_path": str(actor_run["path"]).split("@", 1)[0],
            "workflow_sha": intent["payload"]["main_head_sha"],
            "workflow_id": int(actor_run["workflow_id"]),
            "run_id": int(actor_run["id"]),
            "run_attempt": int(actor_run["run_attempt"]),
            "event": actor_run["event"],
            "status": actor_run["status"],
            "conclusion": actor_run["conclusion"],
            "created_at": actor_run["created_at"],
            "updated_at": actor_run["updated_at"],
        }
        observer = {
            "workflow_path": str(observer_run["path"]).split("@", 1)[0],
            "workflow_sha": observer_run["head_sha"],
            "workflow_id": int(observer_run["workflow_id"]),
            "run_id": int(observer_run["id"]),
            "run_attempt": int(observer_run["run_attempt"]),
            "event": observer_run["event"],
        }
    except (KeyError, TypeError, ValueError) as exc:
        raise MeshReviewOutboxError(
            "Mesh retry cursor actor/observer provenance is malformed"
        ) from exc

    records = item.get("retry_scan_cursor", {})
    if not isinstance(records, Mapping):
        raise MeshReviewOutboxError("Mesh retry cursor projection is malformed")
    current_record = records.get(str(transport_attempt))
    if current_record is not None and not isinstance(current_record, Mapping):
        raise MeshReviewOutboxError("Mesh retry cursor record is malformed")
    prior = current_record.get("cursor") if current_record is not None else None
    if prior is not None and not isinstance(prior, Mapping):
        raise MeshReviewOutboxError("Mesh retry cursor state is malformed")

    if prior is None:
        ordinal = 1
        previous_cursor_sha256 = None
        query_start = actor["created_at"]
        query_end = (
            observation_started_at
            if same_second_boundary_complete
            else actor["updated_at"]
        )
        inherited_cap = page_cap
        prior_boundary = False
        prior_pages = 0
        prior_candidates: list[dict[str, Any]] = []
        prior_run_ids: list[int] = []
        prior_candidate_run_ids: list[int] = []
        prior_declared_total_count: int | None = None
        prior_upper = 0
        page_number = 1
    else:
        ordinal = int(prior["ordinal"]) + 1
        previous_cursor_sha256 = digest(dict(current_record))
        query_start = prior["query_window_start"]
        inherited_cap = int(prior["page_cap"])
        if page_cap != inherited_cap:
            raise MeshReviewOutboxError("Mesh retry cursor page cap drifted")
        prior_boundary = prior["same_second_boundary_complete"] is True
        # A pre-boundary cursor is a HOLD, not a closed absence window.  The
        # first stable observer therefore expands the immutable cutoff to its
        # own start time.  Once a stable cursor exists every later ordinal must
        # inherit exactly the same cutoff.
        query_end = (
            prior["query_window_end"]
            if prior_boundary or not same_second_boundary_complete
            else observation_started_at
        )
        prior_pages = int(prior["pages_scanned"])
        prior_candidates = [dict(value) for value in prior["candidate_locators"]]
        prior_run_ids = list(prior["cumulative_run_ids"])
        prior_candidate_run_ids = list(prior["cumulative_candidate_run_ids"])
        prior_declared_total_count = (
            int(prior["declared_total_count"])
            if prior_boundary else None
        )
        prior_upper = int(prior["upper_bound_run_id"])
        raw_next_page = prior["next_page"]
        page_number = int(raw_next_page) if raw_next_page is not None else 1
        if current_record.get("state") not in {
            "BOUNDARY_STABILIZATION_REOBSERVE",
            "SCAN_INCOMPLETE_REOBSERVE",
        }:
            raise MeshReviewOutboxError("Mesh retry cursor is already closed")

    if (
        queried_window_start != query_start
        or queried_window_end != query_end
    ):
        raise MeshReviewOutboxError(
            "Mesh retry cursor API window differs from sealed query window"
        )
    if not isinstance(page_runs, Sequence) or isinstance(page_runs, (str, bytes)):
        raise MeshReviewOutboxError("Mesh retry cursor API page is malformed")
    raw_page = [dict(value) for value in page_runs if isinstance(value, Mapping)]
    if len(raw_page) != len(page_runs):
        raise MeshReviewOutboxError("Mesh retry cursor API page is malformed")
    try:
        page_ids = [int(value["id"]) for value in raw_page]
    except (KeyError, TypeError, ValueError) as exc:
        raise MeshReviewOutboxError("Mesh retry cursor API page is malformed") from exc
    if (
        len(page_ids) > 100
        or any(value < 1 for value in page_ids)
        or len(set(page_ids)) != len(page_ids)
        or page_ids != sorted(page_ids, reverse=True)
    ):
        raise MeshReviewOutboxError("Mesh retry cursor API run IDs are invalid")

    if not same_second_boundary_complete:
        if prior_boundary:
            raise MeshReviewOutboxError("Mesh retry cursor boundary regressed")
        upper_bound = max([prior_upper, *page_ids], default=prior_upper)
        if prior is not None and upper_bound <= prior_upper:
            raise MeshReviewOutboxError("Mesh retry cursor boundary did not progress")
        pages_scanned = 0
        candidates_seen = 0
        candidates: list[dict[str, Any]] = []
        successor_count = 0
        candidate_set_sha256 = digest([])
        cursor_declared_total_count: int | None = None
        queried_page: int | None = None
        page_run_ids: list[int] = []
        cumulative_run_ids: list[int] = []
        page_candidate_run_ids: list[int] = []
        cumulative_candidate_run_ids: list[int] = []
        observed_unique_run_count = 0
        inventory_consistent = True
        inventory_blocker: str | None = None
        last_scanned_run_id = upper_bound
        next_page: int | None = 1
        scan_complete = False
    else:
        upper_bound = (
            max([prior_upper, *page_ids], default=prior_upper)
            if not prior_boundary
            else prior_upper
        )
        if prior_boundary and any(value > upper_bound for value in page_ids):
            raise MeshReviewOutboxError("Mesh retry cursor closed window shifted")
        normalized_page: list[dict[str, Any]] = []
        for run in raw_page:
            candidate = {
                "run_id": run.get("id"),
                "run_attempt": run.get("run_attempt"),
                "workflow_id": run.get("workflow_id"),
                "workflow_path": str(run.get("path", "")).split("@", 1)[0],
                "event": run.get("event"),
                "repository": (
                    run.get("repository", {}).get("full_name")
                    if isinstance(run.get("repository"), Mapping)
                    else run.get("repository")
                ),
                "head_sha": run.get("head_sha"),
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "display_title": run.get("display_title"),
            }
            try:
                normalized_page.append(
                    normalize_child_for_intent(
                        candidate, intent=intent, attempt=transport_attempt
                    )
                )
            except OutboxBlock:
                continue
        normalized_page.sort(key=lambda value: value["run_id"], reverse=True)
        by_run_id = {value["run_id"]: value for value in prior_candidates}
        for candidate in normalized_page:
            previous = by_run_id.get(candidate["run_id"])
            if previous is not None and previous != candidate:
                raise MeshReviewOutboxError(
                    "Mesh retry cursor candidate identity drifted"
                )
            if previous is None:
                by_run_id[candidate["run_id"]] = candidate
        page_run_ids = list(page_ids)
        cumulative_run_ids = sorted(
            set(prior_run_ids) | set(page_run_ids), reverse=True
        )
        page_candidate_run_ids = sorted(
            {value["run_id"] for value in normalized_page}, reverse=True
        )
        cumulative_candidate_run_ids = sorted(
            set(prior_candidate_run_ids) | set(page_candidate_run_ids),
            reverse=True,
        )
        candidates = [
            by_run_id[run_id]
            for run_id in cumulative_candidate_run_ids[:8]
            if run_id in by_run_id
        ]
        if len(candidates) != min(8, len(cumulative_candidate_run_ids)):
            raise MeshReviewOutboxError(
                "Mesh retry cursor candidate witness is incomplete"
            )
        successor_count = len(cumulative_candidate_run_ids)
        candidates_seen = successor_count
        if successor_count <= 8:
            candidate_set_sha256 = digest(candidates)
        else:
            candidate_set_sha256 = digest(cumulative_candidate_run_ids)
        pages_scanned = prior_pages + 1
        last_scanned_run_id = (
            min(page_ids)
            if page_ids
            else (
                int(prior["last_scanned_run_id"])
                if isinstance(prior, Mapping)
                else upper_bound
            )
        )
        cursor_declared_total_count = declared_total_count
        queried_page = page_number
        observed_unique_run_count = len(cumulative_run_ids)
        inventory_blockers: list[str] = []
        if (
            prior_boundary
            and cursor_declared_total_count != prior_declared_total_count
        ):
            inventory_blockers.append("DECLARED_TOTAL_CHANGED")
        expected_page = (
            int(prior["queried_page"]) + 1 if prior_boundary else 1
        )
        if queried_page != expected_page or pages_scanned != expected_page:
            inventory_blockers.append("PAGE_SEQUENCE_DRIFT")
        if set(page_run_ids) & set(prior_run_ids):
            inventory_blockers.append("PAGE_RUN_ID_OVERLAP")
        if page_run_ids and (
            (prior_run_ids and max(page_run_ids) >= min(prior_run_ids))
            or (prior_boundary and max(page_run_ids) > prior_upper)
        ):
            inventory_blockers.append("PAGE_RUN_ID_ORDER_DRIFT")
        if observed_unique_run_count > cursor_declared_total_count:
            inventory_blockers.append("OBSERVED_COUNT_EXCEEDS_DECLARED_TOTAL")
        if (
            len(page_run_ids) < 100
            and observed_unique_run_count < cursor_declared_total_count
        ):
            inventory_blockers.append("SHORT_PAGE_BEFORE_DECLARED_TOTAL")
        inventory_consistent = not inventory_blockers
        inventory_blocker = inventory_blockers[0] if inventory_blockers else None
        scan_complete = (
            inventory_consistent
            and observed_unique_run_count == cursor_declared_total_count
        )
        next_page = (
            None
            if not inventory_consistent
            or scan_complete
            or pages_scanned == inherited_cap
            else queried_page + 1
        )

    cursor = {
        "schema": "qikvrt_ruleset_outbox_retry_scan_cursor_v2",
        "lane": LANE,
        "sequence": item["sequence"],
        "fingerprint": item["fingerprint"],
        "transport_attempt": transport_attempt,
        "transport_request_sha256": transport["request_sha256"],
        "ordinal": ordinal,
        "previous_cursor_sha256": previous_cursor_sha256,
        "transport_actor": actor,
        "transport_actor_sha256": digest(actor),
        "observation_producer": observer,
        "observation_producer_sha256": digest(observer),
        "target_workflow_id": intent["payload"]["target"]["workflow_id"],
        "query_window_start": query_start,
        "query_window_end": query_end,
        "observation_started_at": observation_started_at,
        "observation_completed_at": observation_completed_at,
        "upper_bound_run_id": upper_bound,
        "last_scanned_run_id": last_scanned_run_id,
        "next_page": next_page,
        "page_cap": inherited_cap,
        "pages_scanned": pages_scanned,
        "declared_total_count": cursor_declared_total_count,
        "queried_page": queried_page,
        "page_run_ids": page_run_ids,
        "page_run_ids_sha256": digest(page_run_ids),
        "cumulative_run_ids": cumulative_run_ids,
        "cumulative_run_ids_sha256": digest(cumulative_run_ids),
        "page_candidate_run_ids": page_candidate_run_ids,
        "page_candidate_run_ids_sha256": digest(page_candidate_run_ids),
        "cumulative_candidate_run_ids": cumulative_candidate_run_ids,
        "cumulative_candidate_run_ids_sha256": digest(
            cumulative_candidate_run_ids
        ),
        "observed_unique_run_count": observed_unique_run_count,
        "inventory_consistent": inventory_consistent,
        "inventory_blocker": inventory_blocker,
        "candidates_seen": candidates_seen,
        "candidate_locators": candidates,
        "candidate_set_sha256": candidate_set_sha256,
        "bound_successor_count": successor_count,
        "same_second_boundary_complete": same_second_boundary_complete,
        "scan_complete": scan_complete,
        "verified": True,
        "productive_effect": False,
    }
    return cursor


def materialize_mesh_orphan_authority_observation(
    *,
    item: Mapping[str, Any],
    transport_attempt: int,
    observed_main_head_sha: str,
) -> dict[str, Any]:
    """Bind a closed/capped Mesh cursor to one immutable Authority fact."""

    intent = item.get("intent")
    records = item.get("retry_scan_cursor", {})
    transport = item.get("transport", {}).get(str(transport_attempt))
    record = records.get(str(transport_attempt)) if isinstance(records, Mapping) else None
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != LANE
        or not isinstance(intent, Mapping)
        or transport_attempt != 1
        or not isinstance(transport, Mapping)
        or not isinstance(record, Mapping)
        or item.get("acceptance")
        or item.get("completion")
        or item.get("child_recovery")
        or not isinstance(item.get("ledger_ref"), str)
        or HEX40.fullmatch(str(item.get("ledger_head"))) is None
        or HEX40.fullmatch(str(observed_main_head_sha)) is None
        or observed_main_head_sha != intent.get("payload", {}).get("main_head_sha")
    ):
        raise MeshReviewOutboxError("Mesh orphan Authority item is not exact")
    try:
        normalized_record = validate_retry_scan_cursor_record(
            record, intent=intent, transport=transport
        )
    except OutboxBlock as exc:
        raise MeshReviewOutboxError("Mesh orphan cursor is not Core-valid") from exc
    if normalized_record != record:
        raise MeshReviewOutboxError("Mesh orphan cursor normalization drifted")
    cursor = record["cursor"]
    state = record["state"]
    common = {
        "schema": AUTHORITY_OBSERVATION_SCHEMA,
        "lane": LANE,
        "sequence": item["sequence"],
        "fingerprint": item["fingerprint"],
        "transport_attempt": transport_attempt,
        "retry_scan_cursor_record_sha256": digest(dict(record)),
        "retry_scan_cursor_sha256": record["cursor_sha256"],
        "retry_scan_cursor_state": state,
        "retry_scan_cursor_ledger_ref": item["ledger_ref"],
        "retry_scan_cursor_ledger_head": item["ledger_head"],
        "query_window_start": cursor["query_window_start"],
        "query_window_end": cursor["query_window_end"],
        "upper_bound_run_id": cursor["upper_bound_run_id"],
        "last_scanned_run_id": cursor["last_scanned_run_id"],
        "page_cap": cursor["page_cap"],
        "pages_scanned": cursor["pages_scanned"],
        "declared_total_count": cursor["declared_total_count"],
        "queried_page": cursor["queried_page"],
        "page_run_ids_sha256": cursor["page_run_ids_sha256"],
        "cumulative_run_ids_sha256": cursor["cumulative_run_ids_sha256"],
        "observed_unique_run_count": cursor["observed_unique_run_count"],
        "inventory_consistent": cursor["inventory_consistent"],
        "inventory_blocker": cursor["inventory_blocker"],
        "candidate_set_sha256": cursor["candidate_set_sha256"],
        "bound_successor_count": cursor["bound_successor_count"],
        "scan_complete": cursor["scan_complete"],
        "sealed_main_head_sha": intent["payload"]["main_head_sha"],
        "observed_main_head_sha": observed_main_head_sha,
        "verified": True,
        "productive_effect": False,
    }
    count = cursor["bound_successor_count"]
    if state == "COMPLETE_ZERO_SUCCESSOR" and count == 0:
        return {
            **common,
            "blocker": "REPEATED_MESH_REVIEW_TRANSPORT_UNACKNOWLEDGED",
            "transport_request_sha256": transport["request_sha256"],
        }
    if state == "COMPLETE_SUCCESSOR_OBSERVED" and 2 <= count <= 8:
        return {
            **common,
            "blocker": "MESH_REVIEW_TRANSPORT_CHILD_AMBIGUOUS",
            "candidate_sha256s": sorted(
                digest(dict(value)) for value in cursor["candidate_locators"]
            ),
        }
    if state in {
        "COMPLETE_SUCCESSOR_OBSERVED",
        "AMBIGUITY_SET_EXCEEDED_AUTHORITY",
    } and count > 8:
        return {
            **common,
            "blocker": "MESH_REVIEW_TRANSPORT_CHILD_SET_EXCEEDED",
            "candidate_count": count,
        }
    if (
        state == "SCAN_BOUND_EXCEEDED_AUTHORITY"
        and cursor["pages_scanned"] == cursor["page_cap"]
        and cursor["scan_complete"] is False
    ):
        return {
            **common,
            "blocker": "MESH_REVIEW_RECOVERY_QUERY_BOUND_EXCEEDED",
        }
    if (
        state == "SCAN_INVENTORY_INCONSISTENT_AUTHORITY"
        and cursor["inventory_consistent"] is False
        and isinstance(cursor["inventory_blocker"], str)
        and cursor["scan_complete"] is False
    ):
        return {
            **common,
            "blocker": "MESH_REVIEW_RECOVERY_QUERY_INVENTORY_INCONSISTENT",
        }
    raise MeshReviewOutboxError("Mesh orphan cursor is not terminal Authority state")


def materialize_mesh_target_workflow_supersession(
    *,
    item: Mapping[str, Any],
    observed_workflow: Mapping[str, Any],
    observed_main_head_sha: str,
) -> dict[str, Any]:
    """Bind a live target-workflow identity change to a terminal Authority fact.

    The workflow REST resource does not expose its dispatch event, so the
    observer may only re-use the sealed event while independently binding the
    live workflow ID and canonical path.  At least one of those independently
    observed fields must differ.  Main drift is a separate Core Authority
    mode and is deliberately rejected here.
    """

    intent = item.get("intent")
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != LANE
        or not isinstance(intent, Mapping)
        or not isinstance(observed_workflow, Mapping)
        or HEX40.fullmatch(str(observed_main_head_sha)) is None
    ):
        raise MeshReviewOutboxError(
            "Mesh target-workflow supersession input is malformed"
        )
    payload = intent.get("payload")
    sealed_target = payload.get("target") if isinstance(payload, Mapping) else None
    sealed_main = (
        payload.get("main_head_sha") if isinstance(payload, Mapping) else None
    )
    raw_path = observed_workflow.get("path")
    observed_target = {
        "workflow_id": observed_workflow.get("id"),
        "workflow_path": (
            raw_path.split("@", 1)[0] if isinstance(raw_path, str) else raw_path
        ),
        "event": (
            sealed_target.get("event")
            if isinstance(sealed_target, Mapping)
            else None
        ),
    }
    if (
        not isinstance(sealed_target, Mapping)
        or set(sealed_target) != {"workflow_id", "workflow_path", "event"}
        or observed_main_head_sha != sealed_main
        or observed_target == sealed_target
    ):
        raise MeshReviewOutboxError(
            "Mesh target workflow has not been exactly superseded"
        )
    return {
        "schema": AUTHORITY_OBSERVATION_SCHEMA,
        "blocker": "OUTBOX_TARGET_WORKFLOW_SUPERSEDED",
        "lane": LANE,
        "sequence": item["sequence"],
        "fingerprint": item["fingerprint"],
        "sealed_target": dict(sealed_target),
        "sealed_target_sha256": digest(dict(sealed_target)),
        "observed_target": observed_target,
        "observed_target_sha256": digest(observed_target),
        "sealed_main_head_sha": sealed_main,
        "observed_main_head_sha": observed_main_head_sha,
        "verified": True,
        "productive_effect": False,
    }


def materialize_mesh_subject_supersession(
    *,
    item: Mapping[str, Any],
    observed_pr: Mapping[str, Any],
    observed_tree_sha: str,
) -> dict[str, Any]:
    """Bind a live PR/head/tree/base transition without reusing sealed facts."""

    intent = item.get("intent")
    payload = intent.get("payload") if isinstance(intent, Mapping) else None
    sealed_subject = payload.get("subject") if isinstance(payload, Mapping) else None
    sealed_queue = (
        sealed_subject.get("queue_intent")
        if isinstance(sealed_subject, Mapping)
        else None
    )
    head = observed_pr.get("head") if isinstance(observed_pr, Mapping) else None
    base = observed_pr.get("base") if isinstance(observed_pr, Mapping) else None
    observed_head_sha = head.get("sha") if isinstance(head, Mapping) else None
    observed_base_sha = base.get("sha") if isinstance(base, Mapping) else None
    observed_state = observed_pr.get("state") if isinstance(observed_pr, Mapping) else None
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != LANE
        or not isinstance(intent, Mapping)
        or not isinstance(sealed_subject, Mapping)
        or not isinstance(sealed_queue, Mapping)
        or observed_pr.get("number") != sealed_queue.get("pr_number")
        or not isinstance(observed_state, str)
        or not observed_state
        or HEX40.fullmatch(str(observed_head_sha)) is None
        or HEX40.fullmatch(str(observed_base_sha)) is None
        or HEX40.fullmatch(str(observed_tree_sha)) is None
    ):
        raise MeshReviewOutboxError("Mesh observed PR subject is malformed")
    observed_subject = copy.deepcopy(dict(sealed_subject))
    observed_queue = observed_subject.get("queue_intent")
    if not isinstance(observed_queue, dict):
        raise MeshReviewOutboxError("Mesh sealed PR queue is malformed")
    observed_queue["head_sha"] = observed_head_sha
    observed_queue["tree_sha"] = observed_tree_sha
    observed_queue["base_sha"] = observed_base_sha
    observed_queue["work_unit_id"] = (
        f"pr-{sealed_queue['pr_number']}/{observed_head_sha}/"
        f"{sealed_queue['successor_fingerprint']}"
    )
    if observed_state != "open":
        observed_queue["state"] = f"LIVE_PR_{observed_state.upper()}"
    observed_subject["queue_intent_sha256"] = digest(observed_queue)
    if observed_subject == sealed_subject:
        raise MeshReviewOutboxError("Mesh PR subject has not been superseded")
    return {
        "schema": AUTHORITY_OBSERVATION_SCHEMA,
        "blocker": "OUTBOX_SUBJECT_SUPERSEDED",
        "lane": LANE,
        "sequence": item["sequence"],
        "fingerprint": item["fingerprint"],
        "sealed_subject_sha256": digest(dict(sealed_subject)),
        "observed_subject": observed_subject,
        "observed_subject_sha256": digest(observed_subject),
        "verified": True,
        "productive_effect": False,
    }


def _mesh_observed_acceptance(
    *,
    item: Mapping[str, Any],
    child: Mapping[str, Any],
    transport_attempt: int,
    child_recovery: bool,
) -> tuple[Mapping[str, Any], dict[str, Any]]:
    """Return the exact direct or same-run-recovery acceptance and result."""

    intent = item.get("intent")
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != LANE
        or not isinstance(intent, Mapping)
        or transport_attempt != 1
        or not isinstance(child_recovery, bool)
    ):
        raise MeshReviewOutboxError("Mesh completion acceptance input is invalid")
    if child_recovery:
        recovery = item.get("child_recovery", {}).get("1")
        acceptance = (
            recovery.get("acceptance") if isinstance(recovery, Mapping) else None
        )
        completion = (
            recovery.get("completion") if isinstance(recovery, Mapping) else None
        )
    else:
        acceptance = item.get("acceptance", {}).get("1")
        completion = item.get("completion", {}).get("1")
    if not isinstance(acceptance, Mapping) or completion is not None:
        raise MeshReviewOutboxError(
            "Mesh completion lacks one uncompleted immutable acceptance"
        )
    try:
        observed = normalize_child_for_intent(
            child,
            intent=intent,
            attempt=1,
            same_run_recovery=child_recovery,
        )
    except OutboxBlock as exc:
        raise MeshReviewOutboxError(
            "Mesh completed child lane identity is invalid"
        ) from exc
    locator = acceptance.get("child")
    immutable = (
        "run_id",
        "run_attempt",
        "workflow_id",
        "workflow_path",
        "event",
        "repository",
        "head_sha",
        "display_title",
    )
    if (
        not isinstance(locator, Mapping)
        or observed.get("status") != "completed"
        or not isinstance(observed.get("conclusion"), str)
        or not observed["conclusion"]
        or any(observed.get(key) != locator.get(key) for key in immutable)
        or (
            locator.get("status") == "completed"
            and (
                locator.get("status") != observed.get("status")
                or locator.get("conclusion") != observed.get("conclusion")
            )
        )
    ):
        raise MeshReviewOutboxError(
            "Mesh completed child differs from accepted locator"
        )
    return acceptance, observed


def _mesh_artifact_inventory(
    artifacts: Sequence[Mapping[str, Any]], *, run_id: int
) -> list[dict[str, Any]]:
    if not isinstance(artifacts, Sequence) or isinstance(artifacts, (str, bytes)):
        raise MeshReviewOutboxError("Mesh artifact inventory is malformed")
    result: list[dict[str, Any]] = []
    for raw in artifacts:
        if not isinstance(raw, Mapping):
            raise MeshReviewOutboxError("Mesh artifact inventory is malformed")
        workflow_run = raw.get("workflow_run")
        value = {
            "id": raw.get("id"),
            "name": raw.get("name"),
            "digest": raw.get("digest"),
            "expired": raw.get("expired"),
            "workflow_run_id": (
                workflow_run.get("id")
                if isinstance(workflow_run, Mapping)
                else None
            ),
        }
        if (
            isinstance(value["id"], bool)
            or not isinstance(value["id"], int)
            or value["id"] < 1
            or not isinstance(value["name"], str)
            or not value["name"]
            or not isinstance(value["digest"], str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", value["digest"]) is None
            or not isinstance(value["expired"], bool)
            or value["workflow_run_id"] != run_id
        ):
            raise MeshReviewOutboxError("Mesh artifact inventory binding is invalid")
        result.append(value)
    if len({value["id"] for value in result}) != len(result):
        raise MeshReviewOutboxError("Mesh artifact inventory contains duplicate IDs")
    return sorted(result, key=lambda value: value["id"])


def _mesh_inventory_fields(
    *,
    jobs: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]],
    child: Mapping[str, Any],
    jobs_pages_scanned: int,
    jobs_page_cap: int,
    jobs_scan_complete: bool,
    artifacts_pages_scanned: int,
    artifacts_page_cap: int,
    artifacts_scan_complete: bool,
    observation_started_at: str,
    observation_completed_at: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    normalized_jobs = _normalized_jobs(jobs)
    if any(job["run_attempt"] != child["run_attempt"] for job in normalized_jobs):
        raise MeshReviewOutboxError("Mesh completion jobs mix run attempts")
    normalized_artifacts = _mesh_artifact_inventory(
        artifacts, run_id=child["run_id"]
    )
    if (
        isinstance(jobs_pages_scanned, bool)
        or not isinstance(jobs_pages_scanned, int)
        or isinstance(jobs_page_cap, bool)
        or not isinstance(jobs_page_cap, int)
        or isinstance(artifacts_pages_scanned, bool)
        or not isinstance(artifacts_pages_scanned, int)
        or isinstance(artifacts_page_cap, bool)
        or not isinstance(artifacts_page_cap, int)
        or not isinstance(jobs_scan_complete, bool)
        or not isinstance(artifacts_scan_complete, bool)
        or not isinstance(observation_started_at, str)
        or TIMESTAMP.fullmatch(observation_started_at) is None
        or not isinstance(observation_completed_at, str)
        or TIMESTAMP.fullmatch(observation_completed_at) is None
        or observation_started_at > observation_completed_at
    ):
        raise MeshReviewOutboxError("Mesh completion inventory metadata is invalid")
    fields = {
        "jobs_total_count": len(normalized_jobs),
        "jobs_set_sha256": digest(normalized_jobs),
        "jobs_pages_scanned": jobs_pages_scanned,
        "jobs_page_cap": jobs_page_cap,
        "jobs_scan_complete": jobs_scan_complete,
        "artifacts_total_count": len(normalized_artifacts),
        "artifact_inventory_sha256": digest(normalized_artifacts),
        "artifacts_pages_scanned": artifacts_pages_scanned,
        "artifacts_page_cap": artifacts_page_cap,
        "artifacts_scan_complete": artifacts_scan_complete,
        "observation_started_at": observation_started_at,
        "observation_completed_at": observation_completed_at,
    }
    return normalized_jobs, normalized_artifacts, fields


def _mesh_completion_observation_common(
    *,
    item: Mapping[str, Any],
    acceptance: Mapping[str, Any],
    child: Mapping[str, Any],
    child_recovery: bool,
) -> dict[str, Any]:
    return {
        "schema": AUTHORITY_OBSERVATION_SCHEMA,
        "lane": LANE,
        "sequence": item["sequence"],
        "fingerprint": item["fingerprint"],
        "transport_attempt": 1,
        "child_recovery": child_recovery,
        "accepted_child_sha256": acceptance["child_sha256"],
        "observed_child": dict(child),
        "observed_child_sha256": digest(dict(child)),
        "verified": True,
        "productive_effect": False,
    }


def materialize_mesh_completion_query_bound_observation(
    *,
    item: Mapping[str, Any],
    child: Mapping[str, Any],
    child_recovery: bool,
    query_kind: str,
    jobs: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]],
    jobs_declared_total_count: int,
    jobs_pages_scanned: int,
    jobs_page_cap: int,
    jobs_scan_complete: bool,
    artifacts_declared_total_count: int,
    artifacts_pages_scanned: int,
    artifacts_page_cap: int,
    artifacts_scan_complete: bool,
    observation_started_at: str,
    observation_completed_at: str,
) -> dict[str, Any]:
    """Bind a capped terminal-child job or artifact query to D0=3 evidence."""

    acceptance, observed = _mesh_observed_acceptance(
        item=item,
        child=child,
        transport_attempt=1,
        child_recovery=child_recovery,
    )
    normalized_jobs = _normalized_jobs(jobs)
    normalized_artifacts = _mesh_artifact_inventory(
        artifacts, run_id=observed["run_id"]
    )
    for value, label in (
        (jobs_declared_total_count, "jobs declared count"),
        (artifacts_declared_total_count, "artifacts declared count"),
        (jobs_pages_scanned, "jobs pages"),
        (jobs_page_cap, "jobs cap"),
        (artifacts_pages_scanned, "artifacts pages"),
        (artifacts_page_cap, "artifacts cap"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise MeshReviewOutboxError(f"Mesh completion {label} is invalid")
    if (
        query_kind not in {"JOBS", "ARTIFACTS"}
        or not isinstance(jobs_scan_complete, bool)
        or not isinstance(artifacts_scan_complete, bool)
        or not isinstance(observation_started_at, str)
        or TIMESTAMP.fullmatch(observation_started_at) is None
        or not isinstance(observation_completed_at, str)
        or TIMESTAMP.fullmatch(observation_completed_at) is None
        or observation_started_at > observation_completed_at
    ):
        raise MeshReviewOutboxError("Mesh completion bounded query is invalid")
    return {
        **_mesh_completion_observation_common(
            item=item,
            acceptance=acceptance,
            child=observed,
            child_recovery=child_recovery,
        ),
        "blocker": "MESH_REVIEW_COMPLETION_QUERY_BOUND_EXCEEDED",
        "query_kind": query_kind,
        "jobs_declared_total_count": jobs_declared_total_count,
        "jobs_observed_count": len(normalized_jobs),
        "jobs_set_sha256": digest(normalized_jobs),
        "jobs_pages_scanned": jobs_pages_scanned,
        "jobs_page_cap": jobs_page_cap,
        "jobs_scan_complete": jobs_scan_complete,
        "artifacts_declared_total_count": artifacts_declared_total_count,
        "artifacts_observed_count": len(normalized_artifacts),
        "artifact_inventory_sha256": digest(normalized_artifacts),
        "artifacts_pages_scanned": artifacts_pages_scanned,
        "artifacts_page_cap": artifacts_page_cap,
        "artifacts_scan_complete": artifacts_scan_complete,
        "observation_started_at": observation_started_at,
        "observation_completed_at": observation_completed_at,
    }


def materialize_mesh_authority_terminal(
    *, item: Mapping[str, Any], authority_record: Mapping[str, Any]
) -> dict[str, Any]:
    """Build the D0=3 Mesh fixed point from a persisted API observation."""

    intent = item.get("intent")
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != LANE
        or not isinstance(intent, Mapping)
    ):
        raise MeshReviewOutboxError("Mesh Authority terminal item is not pending")
    raw_record = authority_record.get("record", authority_record)
    if not isinstance(raw_record, Mapping):
        raise MeshReviewOutboxError(
            "Mesh Authority observation receipt does not contain a record"
        )
    try:
        record = validate_authority_observation_record(raw_record, intent=intent)
    except OutboxBlock as exc:
        raise MeshReviewOutboxError(
            "Mesh Authority observation record is not exact"
        ) from exc
    blocker = record["blocker"]
    value = {
        "schema": TERMINAL_EVIDENCE_SCHEMA,
        "d0": 3,
        "state": "REQUEST_AUTHORITY",
        "reason": blocker,
        "exhaustion": {
            "schema": "qikvrt_ruleset_outbox_exhaustion_v1",
            "lane": LANE,
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "attempts": sorted(int(key) for key in item.get("transport", {})),
            "mode": "AMBIGUOUS_OR_DRIFT",
            "first_blocker": blocker,
            "authority_observation_sha256": digest(record),
            "observation_sha256": digest(record["observation"]),
            "verified": True,
            "productive_effect": False,
        },
        "completion_claims": empty_completion_claims(),
        "productive_effect": False,
        "effect_ack": "NOT_REQUIRED",
    }
    observed_item = dict(item)
    observed_item["authority_observation"] = record
    try:
        return validate_terminal_evidence(value, next_item=observed_item)
    except OutboxBlock as exc:
        raise MeshReviewOutboxError(
            "Mesh Authority terminal does not match persisted observation"
        ) from exc


def _sha256(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise MeshReviewOutboxError("digest input must be bytes")
    return hashlib.sha256(value).hexdigest()


def _load(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MeshReviewOutboxError(f"{label} is unavailable or malformed") from exc
    if not isinstance(value, dict):
        raise MeshReviewOutboxError(f"{label} must be an object")
    return value


def _normalized_jobs(value: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise MeshReviewOutboxError("completed child jobs are absent")
    result: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in value:
        if not isinstance(raw, Mapping):
            raise MeshReviewOutboxError("completed child job is not an object")
        job = dict(raw)
        identifier = job.get("id")
        if (
            isinstance(identifier, bool)
            or not isinstance(identifier, int)
            or identifier < 1
            or identifier in seen
            or not isinstance(job.get("name"), str)
            or not job["name"]
            or job.get("status") != "completed"
            or not isinstance(job.get("conclusion"), str)
            or not job["conclusion"]
            or isinstance(job.get("run_attempt"), bool)
            or not isinstance(job.get("run_attempt"), int)
            or job["run_attempt"] < 1
        ):
            raise MeshReviewOutboxError("completed child job identity is invalid")
        seen.add(identifier)
        result.append(job)
    return result


def _artifact_projection(
    value: Mapping[str, Any],
    *,
    archive: bytes,
    run_id: int,
    run_attempt: int,
) -> dict[str, Any]:
    identifier = value.get("id")
    name = value.get("name")
    archive_digest = value.get("digest")
    if (
        isinstance(identifier, bool)
        or not isinstance(identifier, int)
        or identifier < 1
        or not isinstance(name, str)
        or not name
        or not isinstance(archive_digest, str)
        or re.fullmatch(r"sha256:[0-9a-f]{64}", archive_digest) is None
        or archive_digest != f"sha256:{_sha256(archive)}"
        or value.get("expired") is not False
        or not isinstance(value.get("workflow_run"), Mapping)
        or value["workflow_run"].get("id") != run_id
    ):
        raise MeshReviewOutboxError("completion artifact API binding is invalid")
    return {
        "id": identifier,
        "name": name,
        "archive_sha256": archive_digest,
        "payload_sha256": "",
        "producer_run_id": run_id,
        "producer_run_attempt": run_attempt,
        "verified": True,
    }


def _zip_files(value: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(value)) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > 32:
                raise MeshReviewOutboxError("completion artifact file count is invalid")
            files: dict[str, bytes] = {}
            for info in infos:
                path = pathlib.PurePosixPath(info.filename)
                if (
                    info.is_dir()
                    or path.is_absolute()
                    or len(path.parts) != 1
                    or ".." in path.parts
                    or info.file_size > 8 * 1024 * 1024
                    or path.name in files
                ):
                    raise MeshReviewOutboxError("completion archive file is unsafe")
                files[path.name] = archive.read(info)
            return files
    except zipfile.BadZipFile as exc:
        raise MeshReviewOutboxError("completion artifact ZIP is invalid") from exc


def _queue_subject(item: Mapping[str, Any]) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    intent = item.get("intent")
    if not isinstance(intent, Mapping):
        raise MeshReviewOutboxError("Mesh FIFO intent is absent")
    payload = intent.get("payload")
    subject = payload.get("subject") if isinstance(payload, Mapping) else None
    queue = subject.get("queue_intent") if isinstance(subject, Mapping) else None
    request = payload.get("request") if isinstance(payload, Mapping) else None
    inputs = request.get("inputs") if isinstance(request, Mapping) else None
    if (
        not isinstance(queue, Mapping)
        or queue.get("schema") != "qikvrt_mesh_review_queue_intent_v1"
        or not isinstance(inputs, Mapping)
        or inputs.get("pr") != str(queue.get("pr_number"))
        or inputs.get("head") != queue.get("head_sha")
        or inputs.get("fingerprint") != queue.get("predecessor_fingerprint")
        or inputs.get("evaluator_sha") != payload.get("main_head_sha")
        or inputs.get("transport_intent_sha256") != intent.get("fingerprint")
    ):
        raise MeshReviewOutboxError("Mesh FIFO subject/request binding is invalid")
    return queue, inputs


def _success_payload_digest(
    files: Mapping[str, bytes],
    *,
    artifact_name: str,
    repository: str,
    run_id: int,
    run_attempt: int,
    pr_number: int,
    head_sha: str,
    tree_sha: str,
    base_sha: str,
    semantic_fingerprint: str,
    predecessor_fingerprint: str,
    intent_sha256: str,
    transport_attempt: int,
) -> str:
    if set(files) != SUCCESS_FILES:
        raise MeshReviewOutboxError("trusted review producer file set is not exact")
    try:
        review = json.loads(files["review.json"])
        ledger = json.loads(files["ledger-write.json"])
        transport = json.loads(files["review-transport.json"])
        binding = json.loads(files["producer-binding.json"])
        semantics = mesh_receipt_semantics(review)
        verify_trusted_executor_producer_binding(
            binding,
            repository=repository,
            run_id=run_id,
            run_attempt=run_attempt,
            artifact_name=artifact_name,
            pr_number=pr_number,
            head_sha=head_sha,
            evidence_fingerprint=semantic_fingerprint,
            files={name: files[name] for name in SUCCESS_FILES - {"producer-binding.json"}},
        )
    except (
        json.JSONDecodeError,
        NativeAccountReviewError,
        ReviewSnapshotError,
    ) as exc:
        raise MeshReviewOutboxError("trusted review producer binding is invalid") from exc
    review_intake = (
        transport.get("review_intake") if isinstance(transport, Mapping) else None
    )
    if (
        semantics.get("current") is not True
        or review.get("repository") != repository
        or review.get("pr_number") != pr_number
        or review.get("head_sha") != head_sha
        or review.get("tree_sha") != tree_sha
        or review.get("base_sha") != base_sha
        or review.get("evidence_fingerprint") != semantic_fingerprint
        or ledger.get("schema") != "qikvrt_mesh_review_ledger_write_v1"
        or ledger.get("persisted") is not True
        or ledger.get("projection_current") is not True
        or not isinstance(ledger.get("ledger_commit"), str)
        or HEX40.fullmatch(ledger["ledger_commit"]) is None
        or transport.get("schema") != "qikvrt_mesh_review_transport_provenance_v1"
        or transport.get("productive_effect") is not False
        or not isinstance(review_intake, Mapping)
        or review_intake.get("event_name") != "workflow_dispatch"
        or review_intake.get("predecessor_successor_fingerprint")
        != predecessor_fingerprint
        or review_intake.get("transport_intent_sha256") != intent_sha256
        or review_intake.get("transport_attempt") != transport_attempt
    ):
        raise MeshReviewOutboxError("trusted Mesh-review business payload is not current")
    declared = transport.get("provenance_payload_sha256")
    transport_without_digest = dict(transport)
    transport_without_digest.pop("provenance_payload_sha256", None)
    compact = json.dumps(
        transport_without_digest, sort_keys=True, separators=(",", ":")
    ).encode()
    if declared != _sha256(compact):
        raise MeshReviewOutboxError("review transport provenance self-seal is invalid")
    return _sha256(files["producer-binding.json"])


def _adverse_payload_digest(
    files: Mapping[str, bytes],
    *,
    repository: str,
    child: Mapping[str, Any],
    queue: Mapping[str, Any],
    inputs: Mapping[str, Any],
    intent_sha256: str,
    transport_attempt: int,
) -> str:
    if set(files) != {"envelope.json"}:
        raise MeshReviewOutboxError("adverse completion artifact file set is invalid")
    try:
        envelope = validate_requested_review_completion_envelope(
            json.loads(files["envelope.json"])
        )
    except (json.JSONDecodeError, ReviewSnapshotError) as exc:
        raise MeshReviewOutboxError("requested-review completion envelope is invalid") from exc
    subject = envelope["subject"]
    locator = envelope["dispatch_locator"]
    run = envelope["run"]
    if (
        envelope["repository"] != repository
        or envelope["workflow"]["path"] != WORKFLOW_PATH
        or envelope["workflow"]["workflow_sha"] != child["head_sha"]
        or run["id"] != child["run_id"]
        or run["attempt"] != child["run_attempt"]
        or run["event"] != child["event"]
        or run["display_title"] != child["display_title"]
        or subject["pr_number"] != queue["pr_number"]
        or subject["head_sha"] != queue["head_sha"]
        or subject["tree_sha"] not in (None, queue["tree_sha"])
        or subject["base_sha"] not in (None, queue["base_sha"])
        or locator
        != {
            "schema": "qikvrt_requested_review_run_locator_v3",
            "evaluator_sha": child["head_sha"],
            "pr_number": queue["pr_number"],
            "head_sha": queue["head_sha"],
            "request_fingerprint": inputs["fingerprint"],
            "transport_intent_sha256": intent_sha256,
            "transport_attempt": transport_attempt,
        }
    ):
        raise MeshReviewOutboxError("completion envelope subject/run binding differs")
    return _sha256(files["envelope.json"])


def materialize_mesh_missing_evidence_observation(
    *,
    item: Mapping[str, Any],
    child: Mapping[str, Any],
    child_recovery: bool,
    jobs: Sequence[Mapping[str, Any]],
    artifacts: Sequence[Mapping[str, Any]],
    artifact_archives: Mapping[int, bytes | None],
    jobs_pages_scanned: int,
    jobs_page_cap: int,
    artifacts_pages_scanned: int,
    artifacts_page_cap: int,
    observation_started_at: str,
    observation_completed_at: str,
) -> dict[str, Any]:
    """Classify one complete-but-insufficient terminal child observation.

    The caller has already completed both bounded REST inventories.  Exact
    artifact archives are optional values keyed by artifact ID: ``None``
    means that the exact archive could not be read or did not match its API
    digest.  A valid business result raises instead of manufacturing an
    Authority HOLD; callers must then use :func:`materialize_mesh_completion`.
    """

    if not isinstance(artifact_archives, Mapping):
        raise MeshReviewOutboxError("Mesh completion archive map is malformed")
    acceptance, observed = _mesh_observed_acceptance(
        item=item,
        child=child,
        transport_attempt=1,
        child_recovery=child_recovery,
    )
    normalized_jobs, normalized_artifacts, inventory = _mesh_inventory_fields(
        jobs=jobs,
        artifacts=artifacts,
        child=observed,
        jobs_pages_scanned=jobs_pages_scanned,
        jobs_page_cap=jobs_page_cap,
        jobs_scan_complete=True,
        artifacts_pages_scanned=artifacts_pages_scanned,
        artifacts_page_cap=artifacts_page_cap,
        artifacts_scan_complete=True,
        observation_started_at=observation_started_at,
        observation_completed_at=observation_completed_at,
    )
    queue, inputs = _queue_subject(item)
    completion_name = (
        f"qikvrt-requested-review-completion-{observed['run_id']}-"
        f"attempt-{observed['run_attempt']}"
    )
    completion_matches = [
        value
        for value in normalized_artifacts
        if value["name"] == completion_name and value["expired"] is False
    ]

    def archive_for(value: Mapping[str, Any]) -> bytes | None:
        archive = artifact_archives.get(value["id"])
        if not isinstance(archive, bytes):
            return None
        if value["digest"] != f"sha256:{_sha256(archive)}":
            return None
        return archive

    completion_classification: str | None = None
    if not completion_matches:
        completion_classification = "MISSING_ARTIFACT"
    elif len(completion_matches) > 1:
        completion_classification = "DUPLICATE_ARTIFACTS"
    else:
        completion_archive = archive_for(completion_matches[0])
        if completion_archive is None:
            completion_classification = "ARCHIVE_INVALID"
        else:
            try:
                completion_files = _zip_files(completion_archive)
            except MeshReviewOutboxError:
                completion_classification = "ARCHIVE_INVALID"
            else:
                try:
                    _adverse_payload_digest(
                        completion_files,
                        repository=observed["repository"],
                        child=observed,
                        queue=queue,
                        inputs=inputs,
                        intent_sha256=item["intent"]["fingerprint"],
                        transport_attempt=1,
                    )
                except MeshReviewOutboxError:
                    completion_classification = "PAYLOAD_INVALID"
    envelope_jobs = [
        job
        for job in normalized_jobs
        if job["name"] == "publish-run-completion-envelope"
        and job["conclusion"] == "success"
    ]
    terminal_jobs = [
        job for job in normalized_jobs if job["conclusion"] == observed["conclusion"]
    ]
    if (
        completion_classification is None
        and (len(envelope_jobs) != 1 or not terminal_jobs)
    ):
        completion_classification = "JOB_EVIDENCE_INVALID"
    common = _mesh_completion_observation_common(
        item=item,
        acceptance=acceptance,
        child=observed,
        child_recovery=child_recovery,
    )
    if completion_classification is not None:
        return {
            **common,
            **inventory,
            "blocker": "MESH_REVIEW_COMPLETION_EVIDENCE_MISSING",
            "expected_artifact_name": completion_name,
            "completion_artifact_count": len(completion_matches),
            "completion_artifact_set_sha256": digest(completion_matches),
            "evidence_classification": completion_classification,
        }

    if observed["conclusion"] != "success":
        raise MeshReviewOutboxError(
            "Mesh adverse completion evidence is exact and not missing"
        )
    business_pattern = re.compile(
        rf"qikvrt-mesh-review-pr-{queue['pr_number']}-{queue['head_sha']}-"
        rf"[0-9a-f]{{64}}-run-{observed['run_id']}-"
        rf"attempt-{observed['run_attempt']}"
    )
    business_matches = [
        value
        for value in normalized_artifacts
        if business_pattern.fullmatch(value["name"])
        and value["expired"] is False
    ]
    if not business_matches:
        business_classification = "MISSING_ARTIFACT"
    elif len(business_matches) > 1:
        business_classification = "DUPLICATE_ARTIFACTS"
    else:
        business_archive = archive_for(business_matches[0])
        if business_archive is None:
            business_classification = "ARCHIVE_INVALID"
        else:
            try:
                business_files = _zip_files(business_archive)
            except MeshReviewOutboxError:
                business_classification = "ARCHIVE_INVALID"
            else:
                match = business_pattern.fullmatch(business_matches[0]["name"])
                semantic_match = re.search(
                    rf"-{queue['head_sha']}-([0-9a-f]{{64}})-run-",
                    business_matches[0]["name"],
                )
                try:
                    if match is None or semantic_match is None:
                        raise MeshReviewOutboxError(
                            "Mesh business artifact locator is malformed"
                        )
                    _success_payload_digest(
                        business_files,
                        artifact_name=business_matches[0]["name"],
                        repository=observed["repository"],
                        run_id=observed["run_id"],
                        run_attempt=observed["run_attempt"],
                        pr_number=queue["pr_number"],
                        head_sha=queue["head_sha"],
                        tree_sha=queue["tree_sha"],
                        base_sha=queue["base_sha"],
                        semantic_fingerprint=semantic_match.group(1),
                        predecessor_fingerprint=inputs["fingerprint"],
                        intent_sha256=item["intent"]["fingerprint"],
                        transport_attempt=1,
                    )
                except MeshReviewOutboxError:
                    business_classification = "PAYLOAD_INVALID"
                else:
                    raise MeshReviewOutboxError(
                        "Mesh business completion evidence is exact and not missing"
                    )
    if not any(
        job["name"] == "project-status" and job["conclusion"] == "success"
        for job in normalized_jobs
    ):
        # The missing business result cannot be separated from invalid
        # terminal job evidence, so use the completion-evidence blocker.
        return {
            **common,
            **inventory,
            "blocker": "MESH_REVIEW_COMPLETION_EVIDENCE_MISSING",
            "expected_artifact_name": completion_name,
            "completion_artifact_count": 1,
            "completion_artifact_set_sha256": digest(completion_matches),
            "evidence_classification": "JOB_EVIDENCE_INVALID",
        }
    return {
        **common,
        **inventory,
        "blocker": "MESH_REVIEW_BUSINESS_EVIDENCE_MISSING",
        "completion_envelope_artifact_name": completion_name,
        "completion_envelope_artifact_count": 1,
        "completion_envelope_artifact_set_sha256": digest(completion_matches),
        "expected_business_artifact_prefix": (
            f"qikvrt-mesh-review-pr-{queue['pr_number']}-{queue['head_sha']}-"
        ),
        "expected_business_artifact_suffix": (
            f"-run-{observed['run_id']}-attempt-{observed['run_attempt']}"
        ),
        "business_artifact_count": len(business_matches),
        "business_artifact_set_sha256": digest(business_matches),
        "business_evidence_classification": business_classification,
    }


def materialize_mesh_completion(
    *,
    item: Mapping[str, Any],
    child: Mapping[str, Any],
    jobs: Sequence[Mapping[str, Any]],
    artifact_api: Mapping[str, Any],
    artifact_zip: bytes,
    transport_attempt: int,
    child_recovery: bool,
) -> dict[str, dict[str, Any]]:
    """Return Core-valid completion and terminal evidence for one FIFO item."""
    intent = item.get("intent")
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != LANE
        or not isinstance(intent, Mapping)
        or transport_attempt != 1
    ):
        raise MeshReviewOutboxError("Mesh-review FIFO item is not pending")
    queue, inputs = _queue_subject(item)
    if inputs.get("transport_attempt") != "1":
        raise MeshReviewOutboxError("Mesh transport attempt binding is invalid")
    if child_recovery:
        recovery = item.get("child_recovery", {}).get(str(transport_attempt), {})
        acceptance = recovery.get("acceptance") if isinstance(recovery, Mapping) else None
    else:
        acceptance = item.get("acceptance", {}).get(str(transport_attempt))
    if not isinstance(acceptance, Mapping):
        raise MeshReviewOutboxError("Mesh-review child lacks immutable acceptance")
    try:
        normalized_child = normalize_child_for_intent(
            child,
            intent=intent,
            attempt=transport_attempt,
            same_run_recovery=child_recovery,
        )
    except OutboxBlock as exc:
        raise MeshReviewOutboxError("completed child lane identity is invalid") from exc
    locator = acceptance.get("child")
    immutable = (
        "run_id",
        "run_attempt",
        "workflow_id",
        "workflow_path",
        "event",
        "repository",
        "head_sha",
        "display_title",
    )
    if (
        not isinstance(locator, Mapping)
        or normalized_child.get("status") != "completed"
        or any(normalized_child.get(key) != locator.get(key) for key in immutable)
    ):
        raise MeshReviewOutboxError("completed child differs from accepted locator")
    normalized_jobs = _normalized_jobs(jobs)
    if any(job["run_attempt"] != normalized_child["run_attempt"] for job in normalized_jobs):
        raise MeshReviewOutboxError("completed child jobs mix run attempts")
    conclusion = normalized_child.get("conclusion")
    if not isinstance(conclusion, str) or not conclusion:
        raise MeshReviewOutboxError("completed child conclusion is absent")
    artifact = _artifact_projection(
        artifact_api,
        archive=artifact_zip,
        run_id=normalized_child["run_id"],
        run_attempt=normalized_child["run_attempt"],
    )
    files = _zip_files(artifact_zip)
    if conclusion == "success":
        match = re.fullmatch(
            rf"qikvrt-mesh-review-pr-{queue['pr_number']}-{queue['head_sha']}-"
            rf"([0-9a-f]{{64}})-run-{normalized_child['run_id']}-"
            rf"attempt-{normalized_child['run_attempt']}",
            artifact["name"],
        )
        if match is None:
            raise MeshReviewOutboxError("successful producer artifact name differs")
        terminal_jobs = [
            job
            for job in normalized_jobs
            if job["name"] == "project-status" and job["conclusion"] == "success"
        ]
        if len(terminal_jobs) != 1:
            raise MeshReviewOutboxError("successful producer terminal job is ambiguous")
        terminal_job = terminal_jobs[0]
        artifact["payload_sha256"] = _success_payload_digest(
            files,
            artifact_name=artifact["name"],
            repository=normalized_child["repository"],
            run_id=normalized_child["run_id"],
            run_attempt=normalized_child["run_attempt"],
            pr_number=queue["pr_number"],
            head_sha=queue["head_sha"],
            tree_sha=queue["tree_sha"],
            base_sha=queue["base_sha"],
            semantic_fingerprint=match.group(1),
            predecessor_fingerprint=inputs["fingerprint"],
            intent_sha256=intent["fingerprint"],
            transport_attempt=transport_attempt,
        )
    else:
        expected_name = (
            f"qikvrt-requested-review-completion-{normalized_child['run_id']}-"
            f"attempt-{normalized_child['run_attempt']}"
        )
        if artifact["name"] != expected_name:
            raise MeshReviewOutboxError("adverse completion artifact name differs")
        envelope_jobs = [
            job
            for job in normalized_jobs
            if job["name"] == "publish-run-completion-envelope"
            and job["conclusion"] == "success"
        ]
        terminal_matches = [
            job for job in normalized_jobs if job["conclusion"] == conclusion
        ]
        if len(envelope_jobs) != 1 or not terminal_matches:
            raise MeshReviewOutboxError("adverse run lacks exact envelope/job evidence")
        terminal_job = sorted(terminal_matches, key=lambda value: value["id"])[-1]
        artifact["payload_sha256"] = _adverse_payload_digest(
            files,
            repository=normalized_child["repository"],
            child=normalized_child,
            queue=queue,
            inputs=inputs,
            intent_sha256=intent["fingerprint"],
            transport_attempt=transport_attempt,
        )
    terminal_job_projection = {
        key: terminal_job[key]
        for key in ("id", "name", "run_attempt", "status", "conclusion")
    }
    completion_evidence = {
        "schema": COMPLETION_EVIDENCE_SCHEMA,
        "run_id": normalized_child["run_id"],
        "run_attempt": normalized_child["run_attempt"],
        "jobs_total_count": len(normalized_jobs),
        "terminal_job": terminal_job_projection,
        "artifact": artifact,
        "verified": True,
        "productive_effect": False,
    }
    completion_sha = digest(completion_evidence)
    child_sha = digest(normalized_child)
    if conclusion == "success":
        terminal: dict[str, Any] = {
            "schema": TERMINAL_EVIDENCE_SCHEMA,
            "d0": 2,
            "state": "REOBSERVE",
            "reason": "MESH_REVIEW_LEDGER_CONTINUATION_PERSISTED",
            "business_receipt": {
                "schema": BUSINESS_RECEIPT_SCHEMA,
                "lane": LANE,
                "sequence": intent["sequence"],
                "fingerprint": intent["fingerprint"],
                "outcome": "MESH_REVIEW_LEDGER_CONTINUATION",
                "attempt": transport_attempt,
                "run_id": normalized_child["run_id"],
                "run_attempt": normalized_child["run_attempt"],
                "workflow_id": normalized_child["workflow_id"],
                "workflow_path": normalized_child["workflow_path"],
                "head_sha": normalized_child["head_sha"],
                "locator_child_sha256": acceptance["child_sha256"],
                "child_sha256": child_sha,
                "child_recovery": child_recovery,
                "same_run_result": False,
                "artifact": artifact,
                "completion_evidence_sha256": completion_sha,
                "evidence_sha256": digest(artifact),
                "verified": True,
                "productive_effect": False,
            },
            "continuation": {
                "schema": "qikvrt.causal-continuation.v1",
                "mode": "REOBSERVE",
                "owner": "REPOSITORY_EVENT_LOOP",
                "next_action": "CONSUME_MESH_REVIEW_LEDGER_CONTINUATION",
                "resume_events": ["workflow_run.completed", "schedule"],
                "persistence_run_terminal": False,
                "client_return_allowed": False,
            },
            "completion_claims": empty_completion_claims(),
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
        }
    else:
        mode = "CHILD_RERUN_EXHAUSTED" if child_recovery else "CHILD_RESULT_ADVERSE"
        blocker = (
            "MESH_REVIEW_RERUN_ATTEMPT_2_ADVERSE"
            if child_recovery
            else "MESH_REVIEW_RESULT_ADVERSE"
        )
        exhaustion: dict[str, Any] = {
            "schema": "qikvrt_ruleset_outbox_exhaustion_v1",
            "lane": LANE,
            "sequence": intent["sequence"],
            "fingerprint": intent["fingerprint"],
            "attempts": sorted(int(key) for key in item.get("transport", {})),
            "mode": mode,
            "first_blocker": blocker,
            "transport_attempt": transport_attempt,
            "successor": normalized_child,
            "successor_sha256": child_sha,
            "completion_evidence_sha256": completion_sha,
            "verified": True,
            "productive_effect": False,
        }
        if child_recovery:
            exhaustion.update(
                target_run_id=normalized_child["run_id"], target_run_attempt=2
            )
        terminal = {
            "schema": TERMINAL_EVIDENCE_SCHEMA,
            "d0": 3,
            "state": "REQUEST_AUTHORITY",
            "reason": blocker,
            "exhaustion": exhaustion,
            "continuation": {
                "schema": "qikvrt.causal-continuation.v1",
                "mode": "REQUEST_AUTHORITY",
                "owner": "AUTHORITY_ADMIN",
                "next_action": "INSPECT_MESH_REQUESTED_REVIEW_RESULT",
                "resume_events": ["workflow_dispatch", "schedule"],
                "persistence_run_terminal": False,
                "client_return_allowed": False,
            },
            "completion_claims": empty_completion_claims(),
            "productive_effect": False,
            "effect_ack": "NOT_REQUIRED",
        }
    return {
        "child": normalized_child,
        "completion_evidence": completion_evidence,
        "terminal": terminal,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--item", required=True, type=pathlib.Path)
    parser.add_argument("--child", required=True, type=pathlib.Path)
    parser.add_argument("--jobs", required=True, type=pathlib.Path)
    parser.add_argument("--artifact", required=True, type=pathlib.Path)
    parser.add_argument("--archive", required=True, type=pathlib.Path)
    parser.add_argument("--transport-attempt", required=True, type=int, choices=(1,))
    parser.add_argument("--child-recovery", action="store_true")
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        jobs = json.loads(args.jobs.read_bytes())
        result = materialize_mesh_completion(
            item=_load(args.item, "outbox item"),
            child=_load(args.child, "completed child"),
            jobs=jobs,
            artifact_api=_load(args.artifact, "completion artifact API record"),
            artifact_zip=args.archive.read_bytes(),
            transport_attempt=args.transport_attempt,
            child_recovery=args.child_recovery,
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, MeshReviewOutboxError) as exc:
        parser.error(str(exc))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in result.items():
        (args.output_dir / f"{name.replace('_', '-')}.json").write_text(
            json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
