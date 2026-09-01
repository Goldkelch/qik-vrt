#!/usr/bin/env python3
"""Validate one exact requested-review child and build shared-outbox evidence.

This module is deliberately API-free.  The trusted continuation workflow
downloads one exact run attempt, its paginated jobs, and one run-owned artifact,
then passes those immutable bytes here.  Keeping the business validation in a
small executable contract makes the Auditor/Writer credential boundary
testable: this process never receives either ledger credential.
"""

from __future__ import annotations

import argparse
import hashlib
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
    NO_PREDECESSOR_FINGERPRINT,
    ReviewSnapshotError,
    validate_requested_review_completion_envelope,
)
from tools.qikvrt_ruleset_outbox import (
    AUTHORITY_OBSERVATION_SCHEMA,
    BUSINESS_RECEIPT_SCHEMA,
    COMPLETION_EVIDENCE_SCHEMA,
    OutboxBlock,
    RETRY_SCAN_CURSOR_SCHEMA,
    RETRY_SCAN_INVENTORY_BLOCKERS,
    TERMINAL_EVIDENCE_SCHEMA,
    canonical_bytes,
    digest,
    empty_completion_claims,
    normalize_child_for_intent,
    sha256_bytes,
    validate_authority_observation_record,
    validate_terminal_evidence,
)


HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
SUCCESS_FILES = frozenset(
    {
        "review.json",
        "review.diff",
        "ledger-write.json",
        "review-transport.json",
        "producer-binding.json",
    }
)


class ExactReviewOutboxError(RuntimeError):
    """Fail-closed exact-review completion validation error."""


def materialize_retry_scan_cursor(
    *,
    item: Mapping[str, Any],
    transport_attempt: int,
    actor_run: Mapping[str, Any],
    observer_run: Mapping[str, Any],
    page_response: Mapping[str, Any],
    observation_started_at: str,
    observation_completed_at: str,
    same_second_boundary_complete: bool,
    page_cap: int = 10,
) -> dict[str, Any]:
    """Build one bounded, monotone exact-lane retry scan cursor.

    One invocation consumes at most one API page.  A cursor recorded before
    the actor's timestamp boundary stabilizes consumes no page and carries no
    successor assertion.  Later invocations inherit the immutable window and
    page cap, accumulate at most eight exact child locators, and either expose
    another D0=2 reobservation edge or a closed complete/bound state for the
    Writer.  Core performs the authoritative transition validation when the
    cursor artifact is recorded.
    """

    intent = item.get("intent")
    lane = item.get("lane")
    if (
        item.get("state") != "PENDING"
        or lane not in {"exact-head-dispatch", "exact-review-dispatch"}
        or not isinstance(intent, Mapping)
        or transport_attempt != 1
        or str(transport_attempt) not in item.get("transport", {})
        or isinstance(page_cap, bool)
        or not isinstance(page_cap, int)
        or not (1 <= page_cap <= 100)
        or not isinstance(same_second_boundary_complete, bool)
    ):
        raise ExactReviewOutboxError("retry cursor input is not one exact pending transport")

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
        raise ExactReviewOutboxError("retry cursor actor provenance is malformed") from exc

    current_record = item.get("retry_scan_cursor", {}).get(str(transport_attempt))
    if current_record is not None and not isinstance(current_record, Mapping):
        raise ExactReviewOutboxError("retry cursor current record is malformed")
    prior = current_record.get("cursor") if isinstance(current_record, Mapping) else None
    if prior is not None and not isinstance(prior, Mapping):
        raise ExactReviewOutboxError("retry cursor current projection is malformed")

    if prior is None:
        ordinal = 1
        previous_cursor_sha256 = None
        query_start = actor["created_at"]
        # The transport actor can finish before GitHub materializes an
        # accepted asynchronous receiver run.  Seal the closed-window cutoff
        # only at the first observer tick strictly after the actor's terminal
        # second, so a delayed child created between those instants is not
        # misclassified as absent.
        query_end = (
            observation_started_at
            if same_second_boundary_complete
            else actor["updated_at"]
        )
        inherited_cap = page_cap
        prior_boundary = False
        prior_pages = 0
        prior_candidates: list[dict[str, Any]] = []
        prior_upper = 0
        page_number = 1
    else:
        ordinal = int(prior["ordinal"]) + 1
        previous_cursor_sha256 = digest(dict(current_record))
        query_start = prior["query_window_start"]
        inherited_cap = int(prior["page_cap"])
        if page_cap != inherited_cap:
            raise ExactReviewOutboxError("retry cursor page cap drifted")
        prior_boundary = prior["same_second_boundary_complete"] is True
        # A pre-boundary cursor is only a HOLD; it does not seal an absence
        # window.  The first stable observer expands the cutoff to its own
        # start time.  Every later ordinal inherits that exact stable cutoff.
        query_end = (
            prior["query_window_end"]
            if prior_boundary or not same_second_boundary_complete
            else observation_started_at
        )
        prior_pages = int(prior["pages_scanned"])
        prior_candidates = [dict(value) for value in prior["candidate_locators"]]
        prior_upper = int(prior["upper_bound_run_id"])
        raw_next_page = prior["next_page"]
        page_number = int(raw_next_page) if raw_next_page is not None else 1
        if current_record.get("state") not in {
            "BOUNDARY_STABILIZATION_REOBSERVE",
            "SCAN_INCOMPLETE_REOBSERVE",
        }:
            raise ExactReviewOutboxError("retry cursor is already closed")

    if not isinstance(page_response, Mapping):
        raise ExactReviewOutboxError("retry cursor API response is malformed")
    declared_total = page_response.get("total_count")
    response_runs = page_response.get("workflow_runs")
    if (
        isinstance(declared_total, bool)
        or not isinstance(declared_total, int)
        or declared_total < 0
        or not isinstance(response_runs, Sequence)
        or isinstance(response_runs, (str, bytes))
        or len(response_runs) > 100
        or any(not isinstance(value, Mapping) for value in response_runs)
    ):
        raise ExactReviewOutboxError("retry cursor API response is malformed")
    raw_page = [dict(value) for value in response_runs]
    page_ids = [value.get("id") for value in raw_page]
    if (
        any(
            isinstance(value, bool) or not isinstance(value, int) or value < 1
            for value in page_ids
        )
    ):
        raise ExactReviewOutboxError("retry cursor API page run IDs are invalid")

    # A pre-boundary record is a durable D0=2 HOLD only.  It must not consume
    # API rows or carry a successor claim.  Once the boundary stabilizes the
    # first real page is scanned under the enlarged, then immutable, upper ID.
    if not same_second_boundary_complete:
        if prior_boundary:
            raise ExactReviewOutboxError("retry cursor timestamp boundary regressed")
        if declared_total != 0 or raw_page:
            raise ExactReviewOutboxError(
                "retry cursor boundary HOLD cannot claim an API inventory"
            )
        upper_bound = prior_upper
        pages_scanned = 0
        declared_total_count: int | None = None
        queried_page: int | None = None
        page_run_ids: list[int] = []
        cumulative_run_ids: list[int] = []
        page_candidate_run_ids: list[int] = []
        cumulative_candidate_run_ids: list[int] = []
        observed_unique_run_count = 0
        inventory_consistent = True
        inventory_blocker: str | None = None
        candidates_seen = 0
        candidates: list[dict[str, Any]] = []
        successor_count = 0
        candidate_set_sha256 = digest([])
        last_scanned_run_id = upper_bound
        next_page: int | None = 1
        scan_complete = False
    else:
        upper_bound = (
            max([prior_upper, *page_ids], default=prior_upper)
            if not prior_boundary
            else prior_upper
        )
        declared_total_count = declared_total
        queried_page = page_number
        page_run_ids = list(page_ids)
        prior_run_ids = (
            list(prior.get("cumulative_run_ids", []))
            if isinstance(prior, Mapping)
            else []
        )
        cumulative_run_ids = sorted(
            set(prior_run_ids) | set(page_run_ids), reverse=True
        )
        observed_unique_run_count = len(cumulative_run_ids)
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
                        candidate,
                        intent=intent,
                        attempt=transport_attempt,
                    )
                )
            except OutboxBlock:
                # Dynamic titles are locators only.  Other runs in the exact
                # workflow/time window are not successors for this intent.
                continue
        normalized_page.sort(key=lambda value: value["run_id"], reverse=True)
        page_candidate_run_ids = sorted(
            {value["run_id"] for value in normalized_page}, reverse=True
        )
        prior_candidate_run_ids = (
            list(prior.get("cumulative_candidate_run_ids", []))
            if isinstance(prior, Mapping)
            else []
        )
        cumulative_candidate_run_ids = sorted(
            set(prior_candidate_run_ids) | set(page_candidate_run_ids),
            reverse=True,
        )
        by_run_id = {value["run_id"]: value for value in prior_candidates}
        for candidate in normalized_page:
            previous = by_run_id.get(candidate["run_id"])
            # A repeated run ID is already closed below as PAGE_RUN_ID_OVERLAP.
            # Retain the first immutable locator instead of letting a mutable
            # queued->terminal projection abort before that Authority fact can
            # be persisted.
            if previous is None and len(by_run_id) < 8:
                by_run_id[candidate["run_id"]] = candidate
        candidates = sorted(
            by_run_id.values(), key=lambda value: value["run_id"], reverse=True
        )
        successor_count = len(cumulative_candidate_run_ids)
        if successor_count <= 8:
            candidate_set_sha256 = digest(candidates)
        else:
            candidate_set_sha256 = digest(cumulative_candidate_run_ids)
        pages_scanned = prior_pages + 1
        candidates_seen = successor_count
        # An empty final page advances pagination/completion without inventing
        # movement in the descending run-ID frontier.  Reusing ``prior_upper``
        # here would move the frontier backwards whenever a previous nonempty
        # page had already lowered ``last_scanned_run_id``.
        last_scanned_run_id = (
            min(page_ids)
            if page_ids
            else (
                int(prior["last_scanned_run_id"])
                if isinstance(prior, Mapping)
                else upper_bound
            )
        )
        derived_blockers: list[str] = []
        if len(page_run_ids) != len(set(page_run_ids)):
            derived_blockers.append("PAGE_RUN_ID_DUPLICATE")
        elif page_run_ids != sorted(page_run_ids, reverse=True):
            derived_blockers.append("PAGE_RUN_ID_PAGE_ORDER_DRIFT")
        if (
            prior_boundary
            and declared_total_count != prior.get("declared_total_count")
        ):
            derived_blockers.append("DECLARED_TOTAL_CHANGED")
        if queried_page != page_number or pages_scanned != prior_pages + 1:
            derived_blockers.append("PAGE_SEQUENCE_DRIFT")
        if set(page_run_ids) & set(prior_run_ids):
            derived_blockers.append("PAGE_RUN_ID_OVERLAP")
        if page_run_ids and (
            (prior_run_ids and max(page_run_ids) >= min(prior_run_ids))
            or (prior_boundary and max(page_run_ids) > prior_upper)
        ):
            derived_blockers.append("PAGE_RUN_ID_ORDER_DRIFT")
        if observed_unique_run_count > declared_total_count:
            derived_blockers.append("OBSERVED_COUNT_EXCEEDS_DECLARED_TOTAL")
        if len(page_run_ids) < 100 and observed_unique_run_count < declared_total_count:
            derived_blockers.append("SHORT_PAGE_BEFORE_DECLARED_TOTAL")
        inventory_blocker = derived_blockers[0] if derived_blockers else None
        if inventory_blocker is not None and inventory_blocker not in RETRY_SCAN_INVENTORY_BLOCKERS:
            raise ExactReviewOutboxError("retry cursor inventory blocker is not closed")
        inventory_consistent = inventory_blocker is None
        scan_complete = (
            inventory_consistent
            and observed_unique_run_count == declared_total_count
        )
        if not inventory_consistent or scan_complete or pages_scanned == inherited_cap:
            next_page = None
        else:
            next_page = page_number + 1

    cursor = {
        "schema": RETRY_SCAN_CURSOR_SCHEMA,
        "lane": lane,
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
        "declared_total_count": declared_total_count,
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


def materialize_retry_scan_bound_observation(
    *, item: Mapping[str, Any], transport_attempt: int, observed_main_head_sha: str
) -> dict[str, Any]:
    """Bind a capped incomplete scan to its immutable Core cursor snapshot."""

    lane = item.get("lane")
    intent = item.get("intent")
    record = item.get("retry_scan_cursor", {}).get(str(transport_attempt))
    if (
        item.get("state") != "PENDING"
        or lane not in {"exact-head-dispatch", "exact-review-dispatch"}
        or not isinstance(intent, Mapping)
        or transport_attempt != 1
        or not isinstance(record, Mapping)
        or record.get("state") != "SCAN_BOUND_EXCEEDED_AUTHORITY"
        or not isinstance(record.get("cursor"), Mapping)
        or record["cursor"].get("transport_attempt") != transport_attempt
        or record["cursor"].get("scan_complete") is not False
        or record["cursor"].get("pages_scanned")
        != record["cursor"].get("page_cap")
        or not isinstance(item.get("ledger_ref"), str)
        or HEX40.fullmatch(str(item.get("ledger_head"))) is None
        or HEX40.fullmatch(str(observed_main_head_sha)) is None
        or observed_main_head_sha != intent.get("payload", {}).get("main_head_sha")
    ):
        raise ExactReviewOutboxError("retry scan bound item is not exact")
    cursor = record["cursor"]
    return {
        "schema": AUTHORITY_OBSERVATION_SCHEMA,
        "blocker": "RECOVERY_QUERY_BOUND_EXCEEDED",
        "lane": lane,
        "sequence": item["sequence"],
        "fingerprint": item["fingerprint"],
        "transport_attempt": transport_attempt,
        "retry_scan_cursor_record_sha256": digest(dict(record)),
        "retry_scan_cursor_sha256": record["cursor_sha256"],
        "retry_scan_cursor_state": record["state"],
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
        "cumulative_run_ids_sha256": cursor[
            "cumulative_run_ids_sha256"
        ],
        "observed_unique_run_count": cursor["observed_unique_run_count"],
        "inventory_consistent": cursor["inventory_consistent"],
        "inventory_blocker": cursor["inventory_blocker"],
        "candidate_set_sha256": cursor["candidate_set_sha256"],
        "bound_successor_count": cursor["bound_successor_count"],
        "scan_complete": False,
        "sealed_main_head_sha": intent["payload"]["main_head_sha"],
        "observed_main_head_sha": observed_main_head_sha,
        "verified": True,
        "productive_effect": False,
    }


def materialize_retry_cursor_authority_observation(
    *, item: Mapping[str, Any], transport_attempt: int, observed_main_head_sha: str
) -> dict[str, Any]:
    """Close one terminal Exact retry-cursor outcome without inventing facts.

    A complete cursor is already an immutable, content-addressed observation
    in the shared ledger.  This adapter projects only three fixed points from
    that exact snapshot: two-to-eight successors, more than eight successors,
    the one-shot transport that completed with no successor, or a closed API
    inventory inconsistency.  The cap state is delegated to
    :func:`materialize_retry_scan_bound_observation`.  Every returned value
    still has to win ``record-observation`` before it can be used by
    ``materialize_authority_terminal``.
    """

    lane = item.get("lane")
    intent = item.get("intent")
    record = item.get("retry_scan_cursor", {}).get(str(transport_attempt))
    if (
        item.get("state") != "PENDING"
        or lane not in {"exact-head-dispatch", "exact-review-dispatch"}
        or not isinstance(intent, Mapping)
        or transport_attempt != 1
        or not isinstance(record, Mapping)
        or not isinstance(record.get("cursor"), Mapping)
        or record["cursor"].get("transport_attempt") != transport_attempt
        or not isinstance(item.get("ledger_ref"), str)
        or HEX40.fullmatch(str(item.get("ledger_head"))) is None
        or HEX40.fullmatch(str(observed_main_head_sha)) is None
        or observed_main_head_sha != intent.get("payload", {}).get("main_head_sha")
    ):
        raise ExactReviewOutboxError("retry cursor Authority item is not exact")

    if record.get("state") == "SCAN_BOUND_EXCEEDED_AUTHORITY":
        return materialize_retry_scan_bound_observation(
            item=item,
            transport_attempt=transport_attempt,
            observed_main_head_sha=observed_main_head_sha,
        )

    cursor = record["cursor"]
    common = {
        "schema": AUTHORITY_OBSERVATION_SCHEMA,
        "lane": lane,
        "sequence": item["sequence"],
        "fingerprint": item["fingerprint"],
        "transport_attempt": transport_attempt,
        "retry_scan_cursor_record_sha256": digest(dict(record)),
        "retry_scan_cursor_sha256": record["cursor_sha256"],
        "retry_scan_cursor_state": record["state"],
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
        "cumulative_run_ids_sha256": cursor[
            "cumulative_run_ids_sha256"
        ],
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

    successor_count = cursor.get("bound_successor_count")
    if (
        record.get("state") == "SCAN_INVENTORY_INCONSISTENT_AUTHORITY"
        and cursor.get("inventory_consistent") is False
        and cursor.get("inventory_blocker") in RETRY_SCAN_INVENTORY_BLOCKERS
        and cursor.get("scan_complete") is False
    ):
        return {
            **common,
            "blocker": "RECOVERY_QUERY_INVENTORY_INCONSISTENT",
        }
    if (
        record.get("state")
        in {
            "COMPLETE_SUCCESSOR_OBSERVED",
            "AMBIGUITY_SET_EXCEEDED_AUTHORITY",
        }
        and (
            record.get("state") == "AMBIGUITY_SET_EXCEEDED_AUTHORITY"
            or cursor.get("scan_complete") is True
        )
        and isinstance(successor_count, int)
        and not isinstance(successor_count, bool)
        and 2 <= successor_count <= 8
        and len(cursor.get("candidate_locators", [])) == successor_count
    ):
        return {
            **common,
            "blocker": "BOUND_EVIDENCE_AMBIGUOUS",
            "candidate_sha256s": sorted(
                digest(dict(candidate))
                for candidate in cursor["candidate_locators"]
            ),
        }
    if (
        record.get("state")
        in {
            "COMPLETE_SUCCESSOR_OBSERVED",
            "AMBIGUITY_SET_EXCEEDED_AUTHORITY",
        }
        and (
            record.get("state") == "AMBIGUITY_SET_EXCEEDED_AUTHORITY"
            or cursor.get("scan_complete") is True
        )
        and isinstance(successor_count, int)
        and not isinstance(successor_count, bool)
        and successor_count >= 9
    ):
        return {
            **common,
            "blocker": "BOUND_EVIDENCE_AMBIGUITY_SET_EXCEEDED",
            "candidate_count": successor_count,
        }
    if (
        record.get("state") == "COMPLETE_ZERO_SUCCESSOR"
        and transport_attempt == 1
        and cursor.get("scan_complete") is True
        and successor_count == 0
        and set(item.get("transport", {})) == {"1"}
        and not item.get("acceptance")
        and not item.get("completion")
    ):
        blocker = (
            "REPEATED_EXACT_HEAD_TRANSPORT_UNACKNOWLEDGED"
            if lane == "exact-head-dispatch"
            else "REPEATED_EXACT_REVIEW_TRANSPORT_UNACKNOWLEDGED"
        )
        return {
            **common,
            "blocker": blocker,
            "transport_request_sha256": item["transport"]["1"][
                "request_sha256"
            ],
        }
    raise ExactReviewOutboxError("retry cursor has no terminal Authority outcome")


def materialize_authority_terminal(
    *, item: Mapping[str, Any], authority_record: Mapping[str, Any]
) -> dict[str, Any]:
    """Build one Core-valid D0=3 terminal from a persisted observation.

    The observation must already have won the Writer CAS.  Inline API facts
    are intentionally not accepted here: the returned terminal binds both the
    immutable record and its canonical observation digest.
    """
    intent = item.get("intent")
    if item.get("state") != "PENDING" or not isinstance(intent, Mapping):
        raise ExactReviewOutboxError("Authority terminal item is not pending")
    raw_record = authority_record.get("record", authority_record)
    if not isinstance(raw_record, Mapping):
        raise ExactReviewOutboxError(
            "Authority observation receipt does not contain a record"
        )
    try:
        record = validate_authority_observation_record(
            raw_record, intent=intent
        )
    except OutboxBlock as exc:
        raise ExactReviewOutboxError(
            "Authority observation record is not exact"
        ) from exc
    blocker = record["blocker"]
    value = {
        "schema": TERMINAL_EVIDENCE_SCHEMA,
        "d0": 3,
        "state": "REQUEST_AUTHORITY",
        "reason": blocker,
        "exhaustion": {
            "schema": "qikvrt_ruleset_outbox_exhaustion_v1",
            "lane": intent["lane"],
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
        raise ExactReviewOutboxError(
            "Authority terminal does not match persisted observation"
        ) from exc


def _load(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_bytes())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExactReviewOutboxError(f"{label} is unavailable or malformed") from exc
    if not isinstance(value, dict):
        raise ExactReviewOutboxError(f"{label} must be an object")
    return value


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _jobs(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ExactReviewOutboxError("completed child jobs are absent")
    result: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in value:
        if not isinstance(raw, Mapping):
            raise ExactReviewOutboxError("completed child job is not an object")
        item = dict(raw)
        identifier = item.get("id")
        if (
            isinstance(identifier, bool)
            or not isinstance(identifier, int)
            or identifier < 1
            or identifier in seen
            or not isinstance(item.get("name"), str)
            or not item["name"]
            or item.get("status") != "completed"
            or not isinstance(item.get("conclusion"), str)
            or not item["conclusion"]
            or isinstance(item.get("run_attempt"), bool)
            or not isinstance(item.get("run_attempt"), int)
        ):
            raise ExactReviewOutboxError("completed child job identity is invalid")
        seen.add(identifier)
        result.append(item)
    return result


def _artifact(
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
        or archive_digest != f"sha256:{_sha256_bytes(archive)}"
        or value.get("expired") is not False
        or not isinstance(value.get("workflow_run"), Mapping)
        or value["workflow_run"].get("id") != run_id
    ):
        raise ExactReviewOutboxError("completion artifact API binding is invalid")
    return {
        "id": identifier,
        "name": name,
        "archive_sha256": archive_digest,
        # Filled from the exact validated semantic envelope below.
        "payload_sha256": "",
        "producer_run_id": run_id,
        "producer_run_attempt": run_attempt,
        "verified": True,
    }


def _validate_success_payload(
    files: Mapping[str, bytes],
    *,
    artifact_name: str,
    repository: str,
    run_id: int,
    run_attempt: int,
    pr_number: int,
    head_sha: str,
    semantic_fingerprint: str,
    request_fingerprint: str,
    intent_sha256: str,
    transport_attempt: int,
) -> str:
    if set(files) != SUCCESS_FILES:
        raise ExactReviewOutboxError("trusted review producer file set is not exact")
    try:
        binding = json.loads(files["producer-binding.json"])
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
        review = json.loads(files["review.json"])
        ledger = json.loads(files["ledger-write.json"])
        transport = json.loads(files["review-transport.json"])
    except (json.JSONDecodeError, NativeAccountReviewError) as exc:
        raise ExactReviewOutboxError("trusted review producer binding is invalid") from exc
    if (
        review.get("pr_number") != pr_number
        or review.get("head_sha") != head_sha
        or review.get("evidence_fingerprint") != semantic_fingerprint
        or ledger.get("schema") != "qikvrt_mesh_review_ledger_write_v1"
        or ledger.get("persisted") is not True
        or ledger.get("projection_current") is not True
        or not isinstance(ledger.get("ledger_commit"), str)
        or HEX40.fullmatch(ledger["ledger_commit"]) is None
        or transport.get("schema")
        != "qikvrt_mesh_review_transport_provenance_v1"
        or transport.get("productive_effect") is not False
        or not isinstance(transport.get("review_intake"), Mapping)
        or transport["review_intake"].get("event_name") != "workflow_dispatch"
        or transport["review_intake"].get(
            "predecessor_successor_fingerprint"
        )
        != (
            None
            if request_fingerprint == NO_PREDECESSOR_FINGERPRINT
            else request_fingerprint
        )
        or transport["review_intake"].get("transport_intent_sha256")
        != intent_sha256
        or transport["review_intake"].get("transport_attempt")
        != transport_attempt
    ):
        raise ExactReviewOutboxError("trusted review business payload is not current")
    declared = transport.get("provenance_payload_sha256")
    transport_without_digest = dict(transport)
    transport_without_digest.pop("provenance_payload_sha256", None)
    compact = json.dumps(
        transport_without_digest, sort_keys=True, separators=(",", ":")
    ).encode()
    if declared != _sha256_bytes(compact):
        raise ExactReviewOutboxError("review transport provenance self-seal is invalid")
    return _sha256_bytes(files["producer-binding.json"])


def _validate_adverse_payload(
    files: Mapping[str, bytes],
    *,
    repository: str,
    child: Mapping[str, Any],
    pr_number: int,
    head_sha: str,
    tree_sha: str,
    base_sha: str,
    request_fingerprint: str,
    intent_sha256: str,
    transport_attempt: int,
) -> str:
    if set(files) != {"envelope.json"}:
        raise ExactReviewOutboxError("adverse completion artifact file set is invalid")
    try:
        envelope = validate_requested_review_completion_envelope(
            json.loads(files["envelope.json"])
        )
    except (json.JSONDecodeError, ReviewSnapshotError) as exc:
        raise ExactReviewOutboxError("requested-review completion envelope is invalid") from exc
    subject = envelope["subject"]
    dispatch_locator = envelope["dispatch_locator"]
    run = envelope["run"]
    if (
        envelope["repository"] != repository
        or envelope["workflow"]["path"]
        != ".github/workflows/qikvrt_requested_review_executor.yml"
        or envelope["workflow"]["workflow_sha"] != child["head_sha"]
        or run["id"] != child["run_id"]
        or run["attempt"] != child["run_attempt"]
        or run["event"] != child["event"]
        or run["display_title"] != child["display_title"]
        or subject["pr_number"] != pr_number
        or subject["head_sha"] != head_sha
        # A planner that reached subject materialization must bind the exact
        # tree/base tuple.  An early planner failure has nulls here; the
        # continuation independently binds the same immutable tuple from the
        # accepted Core intent and live PR APIs before this helper is invoked.
        or subject["tree_sha"] not in (None, tree_sha)
        or subject["base_sha"] not in (None, base_sha)
        # The semantic fingerprint is the newly calculated review result and
        # is deliberately distinct from the causal predecessor fingerprint.
        # The latter is carried by the dispatch locator below.
        or not isinstance(dispatch_locator, Mapping)
        or dispatch_locator
        != {
            "schema": "qikvrt_requested_review_run_locator_v3",
            "evaluator_sha": child["head_sha"],
            "pr_number": pr_number,
            "head_sha": head_sha,
            "request_fingerprint": request_fingerprint,
            "transport_intent_sha256": intent_sha256,
            "transport_attempt": transport_attempt,
        }
    ):
        raise ExactReviewOutboxError("completion envelope subject/run binding differs")
    return _sha256_bytes(files["envelope.json"])


def materialize_completion(
    *,
    item: Mapping[str, Any],
    child: Mapping[str, Any],
    jobs: Sequence[Mapping[str, Any]],
    artifact_api: Mapping[str, Any],
    artifact_zip: bytes,
    transport_attempt: int,
    child_recovery: bool,
) -> dict[str, dict[str, Any]]:
    intent = item.get("intent")
    if (
        item.get("state") != "PENDING"
        or item.get("lane") != "exact-review-dispatch"
        or not isinstance(intent, Mapping)
        or transport_attempt != 1
    ):
        raise ExactReviewOutboxError("exact-review FIFO item is not pending")
    if child_recovery:
        recovery = item.get("child_recovery", {}).get(str(transport_attempt), {})
        acceptance = recovery.get("acceptance") if isinstance(recovery, Mapping) else None
    else:
        acceptance = item.get("acceptance", {}).get(str(transport_attempt))
    if not isinstance(acceptance, Mapping):
        raise ExactReviewOutboxError("exact-review child lacks immutable acceptance")
    normalized_child = normalize_child_for_intent(
        child,
        intent=intent,
        attempt=transport_attempt,
        same_run_recovery=child_recovery,
    )
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
    locator = acceptance.get("child")
    if (
        not isinstance(locator, Mapping)
        or normalized_child.get("status") != "completed"
        or any(normalized_child.get(key) != locator.get(key) for key in immutable)
    ):
        raise ExactReviewOutboxError("completed child differs from accepted locator")
    normalized_jobs = _jobs(jobs)
    if any(job["run_attempt"] != normalized_child["run_attempt"] for job in normalized_jobs):
        raise ExactReviewOutboxError("completed child jobs mix run attempts")
    conclusion = normalized_child.get("conclusion")
    if not isinstance(conclusion, str) or not conclusion:
        raise ExactReviewOutboxError("completed child conclusion is absent")
    artifact = _artifact(
        artifact_api,
        archive=artifact_zip,
        run_id=normalized_child["run_id"],
        run_attempt=normalized_child["run_attempt"],
    )
    # Use a temporary in-memory ZIP parse without ever extracting paths.
    import io

    try:
        with zipfile.ZipFile(io.BytesIO(artifact_zip)) as archive_reader:
            infos = archive_reader.infolist()
            if not infos or len(infos) > 32:
                raise ExactReviewOutboxError(
                    "completion artifact file count is invalid"
                )
            files: dict[str, bytes] = {}
            for info in infos:
                name = pathlib.PurePosixPath(info.filename)
                if (
                    info.is_dir()
                    or name.is_absolute()
                    or ".." in name.parts
                    or info.file_size > 8 * 1024 * 1024
                    or name.name in files
                ):
                    raise ExactReviewOutboxError("completion archive file is unsafe")
                files[name.name] = archive_reader.read(info)
    except zipfile.BadZipFile as exc:
        raise ExactReviewOutboxError("completion artifact ZIP is invalid") from exc

    payload = intent["payload"]
    request_inputs = payload["request"]["inputs"]
    subject = payload["subject"]
    pr_number = subject["pull_request"]
    head_sha = subject["head_sha"]
    tree_sha = subject["head_tree_sha"]
    base_sha = subject["base_sha"]
    request_fingerprint = request_inputs["fingerprint"]
    intent_sha256 = intent["fingerprint"]
    if conclusion == "success":
        match = re.fullmatch(
            rf"qikvrt-mesh-review-pr-{pr_number}-{head_sha}-([0-9a-f]{{64}})-"
            rf"run-{normalized_child['run_id']}-attempt-{normalized_child['run_attempt']}",
            artifact["name"],
        )
        if match is None:
            raise ExactReviewOutboxError("successful producer artifact name differs")
        semantic_fingerprint = match.group(1)
        matches = [
            job
            for job in normalized_jobs
            if job["name"] == "project-status" and job["conclusion"] == "success"
        ]
        if len(matches) != 1:
            raise ExactReviewOutboxError("successful producer terminal job is ambiguous")
        terminal_job = matches[0]
        artifact["payload_sha256"] = _validate_success_payload(
            files,
            artifact_name=artifact["name"],
            repository=normalized_child["repository"],
            run_id=normalized_child["run_id"],
            run_attempt=normalized_child["run_attempt"],
            pr_number=pr_number,
            head_sha=head_sha,
            semantic_fingerprint=semantic_fingerprint,
            request_fingerprint=request_fingerprint,
            intent_sha256=intent_sha256,
            transport_attempt=transport_attempt,
        )
    else:
        expected_name = (
            f"qikvrt-requested-review-completion-{normalized_child['run_id']}-"
            f"attempt-{normalized_child['run_attempt']}"
        )
        if artifact["name"] != expected_name:
            raise ExactReviewOutboxError("adverse completion artifact name differs")
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
            raise ExactReviewOutboxError("adverse run lacks exact envelope/job evidence")
        terminal_job = sorted(terminal_matches, key=lambda value: value["id"])[-1]
        artifact["payload_sha256"] = _validate_adverse_payload(
            files,
            repository=normalized_child["repository"],
            child=normalized_child,
            pr_number=pr_number,
            head_sha=head_sha,
            tree_sha=tree_sha,
            base_sha=base_sha,
            request_fingerprint=request_fingerprint,
            intent_sha256=intent_sha256,
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
    child_sha = digest(normalized_child)
    completion_evidence_sha = digest(completion_evidence)
    sequence = intent["sequence"]
    fingerprint = intent["fingerprint"]
    if conclusion == "success":
        terminal = {
            "schema": TERMINAL_EVIDENCE_SCHEMA,
            "d0": 2,
            "state": "REOBSERVE",
            "reason": "EXACT_REVIEW_LEDGER_CONTINUATION_PERSISTED",
            "business_receipt": {
                "schema": BUSINESS_RECEIPT_SCHEMA,
                "lane": "exact-review-dispatch",
                "sequence": sequence,
                "fingerprint": fingerprint,
                "outcome": "EXACT_REVIEW_LEDGER_CONTINUATION",
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
                "completion_evidence_sha256": completion_evidence_sha,
                "evidence_sha256": digest(artifact),
                "verified": True,
                "productive_effect": False,
            },
            "continuation": {
                "schema": "qikvrt.causal-continuation.v1",
                "mode": "AWAIT_EXACT_EVENT",
                "owner": "REPOSITORY_EVENT_LOOP",
                "next_action": "CONSUME_EXACT_REVIEW_LEDGER_CONTINUATION",
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
            "ATTEMPT_2_TERMINAL_ADVERSE"
            if child_recovery
            else "ATTEMPT_1_ACCEPTED_ADVERSE"
        )
        exhaustion: dict[str, Any] = {
            "schema": "qikvrt_ruleset_outbox_exhaustion_v1",
            "lane": "exact-review-dispatch",
            "sequence": sequence,
            "fingerprint": fingerprint,
            "attempts": sorted(int(key) for key in item.get("transport", {})),
            "mode": mode,
            "first_blocker": blocker,
            "transport_attempt": transport_attempt,
            "successor": normalized_child,
            "successor_sha256": child_sha,
            "completion_evidence_sha256": completion_evidence_sha,
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
                "next_action": "INSPECT_EXACT_REQUESTED_REVIEW_RESULT",
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
    parser.add_argument("--transport-attempt", required=True, type=int, choices=(1, 2))
    parser.add_argument("--child-recovery", action="store_true")
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        result = materialize_completion(
            item=_load(args.item, "outbox item"),
            child=_load(args.child, "completed child"),
            jobs=json.loads(args.jobs.read_bytes()),
            artifact_api=_load(args.artifact, "completion artifact API record"),
            artifact_zip=args.archive.read_bytes(),
            transport_attempt=args.transport_attempt,
            child_recovery=args.child_recovery,
        )
    except (OSError, json.JSONDecodeError, ExactReviewOutboxError) as exc:
        parser.error(str(exc))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in result.items():
        (args.output_dir / f"{name.replace('_', '-')}.json").write_text(
            json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
