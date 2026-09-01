#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Durable, bounded FIFO outbox for ruleset continuation transports.

The outbox is deliberately stored on a dedicated non-main Git ref.  Producers
append a sealed intent before a transport effect.  The scheduled continuation
reads only the next exact FIFO slot for each lane; it never discovers work by
walking the repository-wide retained Actions-artifact collection.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from typing import Any, Protocol


LEDGER_REF_PREFIX = "refs/heads/qikvrt/outbox-ledger-v2"
LEDGER_SHORT_REF_PREFIX = "qikvrt/outbox-ledger-v2"
LEDGER_API_REF_PREFIX = "heads/qikvrt/outbox-ledger-v2"
LEDGER_SCHEMA = "qikvrt_ruleset_outbox_ledger_v2"
META_SCHEMA = "qikvrt_ruleset_outbox_lane_meta_v1"
PAYLOAD_SCHEMA = "qikvrt_ruleset_outbox_payload_v1"
INTENT_SCHEMA = "qikvrt_ruleset_outbox_intent_v1"
SLOT_SCHEMA = "qikvrt_ruleset_outbox_slot_v1"
LOCATOR_SCHEMA = "qikvrt_ruleset_outbox_fingerprint_locator_v1"
WITNESS_INDEX_SCHEMA = "qikvrt_ruleset_outbox_witness_index_v2"
WITNESS_SCHEMA = "qikvrt_ruleset_outbox_witness_v1"
TRANSPORT_SCHEMA = "qikvrt_ruleset_outbox_transport_v2"
ACCEPTANCE_SCHEMA = "qikvrt_ruleset_outbox_acceptance_v1"
LATE_ACCEPTANCE_SCHEMA = "qikvrt_ruleset_outbox_late_acceptance_conflict_v1"
LATE_ACCEPTANCE_A2_OBSERVATION_SCHEMA = (
    "qikvrt_ruleset_outbox_late_acceptance_attempt_two_observation_v1"
)
COMPLETION_SCHEMA = "qikvrt_ruleset_outbox_completion_v1"
COMPLETION_EVIDENCE_SCHEMA = "qikvrt_ruleset_outbox_completion_evidence_v1"
TERMINAL_SCHEMA = "qikvrt_ruleset_outbox_terminal_v1"
TERMINAL_SUPERSESSION_SCHEMA = "qikvrt_ruleset_outbox_terminal_supersession_v2"
TERMINAL_EVIDENCE_SCHEMA = "qikvrt_ruleset_outbox_terminal_evidence_v2"
RETRY_EVIDENCE_SCHEMA = "qikvrt_ruleset_outbox_retry_evidence_v3"
RETRY_OBSERVATION_SCHEMA = "qikvrt_ruleset_outbox_retry_observation_v2"
RETRY_SCAN_CURSOR_SCHEMA = "qikvrt_ruleset_outbox_retry_scan_cursor_v2"
RETRY_SCAN_CURSOR_RECORD_SCHEMA = (
    "qikvrt_ruleset_outbox_retry_scan_cursor_record_v2"
)
RETRY_SCAN_CURSOR_LOCATOR_SCHEMA = (
    "qikvrt_ruleset_outbox_retry_scan_cursor_locator_v1"
)
RETRY_SCAN_INVENTORY_BLOCKERS = frozenset(
    {
        "DECLARED_TOTAL_CHANGED",
        "OBSERVED_COUNT_EXCEEDS_DECLARED_TOTAL",
        "PAGE_RUN_ID_DUPLICATE",
        "PAGE_RUN_ID_ORDER_DRIFT",
        "PAGE_RUN_ID_PAGE_ORDER_DRIFT",
        "PAGE_RUN_ID_OVERLAP",
        "PAGE_SEQUENCE_DRIFT",
        "SHORT_PAGE_BEFORE_DECLARED_TOTAL",
    }
)
BUSINESS_RECEIPT_SCHEMA = "qikvrt_ruleset_outbox_business_receipt_v1"
EXHAUSTION_SCHEMA = "qikvrt_ruleset_outbox_exhaustion_v1"
CHILD_RETRY_EVIDENCE_SCHEMA = "qikvrt_ruleset_outbox_child_retry_evidence_v3"
CHILD_RERUN_SCHEMA = "qikvrt_ruleset_outbox_child_rerun_v1"
CHILD_RERUN_ACCEPTANCE_SCHEMA = "qikvrt_ruleset_outbox_child_rerun_acceptance_v1"
SAME_RUN_RESULT_SCHEMA = "qikvrt_ruleset_outbox_same_run_result_v1"
RERUN_TRANSPORT_OBSERVATION_SCHEMA = (
    "qikvrt_ruleset_outbox_rerun_transport_observation_v1"
)
CHILD_RERUN_OBSERVATION_SCHEMA = (
    "qikvrt_ruleset_outbox_child_rerun_observation_v2"
)
AUTHORITY_OBSERVATION_SCHEMA = "qikvrt_ruleset_outbox_authority_observation_v1"
AUTHORITY_OBSERVATION_RECORD_SCHEMA = (
    "qikvrt_ruleset_outbox_authority_observation_record_v1"
)
AUTHORITY_OBSERVATION_RECEIPT_SCHEMA = (
    "qikvrt_ruleset_outbox_authority_observation_receipt_v2"
)
LANES = (
    "ruleset-dispatch",
    "reconciler-rerun",
    "requested-review-dispatch",
    "exact-head-dispatch",
    "exact-review-dispatch",
    "mesh-review-successor-dispatch",
)
MAX_CAS_ATTEMPTS = 32
MAX_ACTIVE_WITNESSES = 3
AUTHORITY_ENVIRONMENT = "qikvrt-outbox-ledger-authority"
AUDITOR_SECRET_NAME = "QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN"
WRITER_SECRET_NAME = "QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN"
AUTHORITY_READBACK_SCHEMA = "qikvrt_outbox_ledger_authority_readback_v1"
AUTHORITY_OBSERVER_WORKFLOW_PATHS = frozenset(
    {
        ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml",
        ".github/workflows/qikvrt_review_admission_recovery.yml",
    }
)
TRANSPORT_ACTOR_EVENTS = {
    ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml": frozenset(
        {
            "schedule",
            "workflow_run",
            "workflow_dispatch",
            "pull_request_target",
        }
    ),
    ".github/workflows/qikvrt_review_admission_recovery.yml": frozenset(
        {"schedule", "workflow_dispatch", "workflow_run"}
    ),
    ".github/workflows/qikvrt_autonomous_exact_head_verify.yml": frozenset(
        {"repository_dispatch"}
    ),
}
MESH_TRANSPORT_ACTOR_EVENTS = {
    ".github/workflows/qikvrt_requested_review_executor.yml": frozenset(
        {
            "pull_request_target",
            "issue_comment",
            "workflow_run",
            "workflow_dispatch",
        }
    )
}
MESH_AUTHORITY_OBSERVER_EVENTS = {
    ".github/workflows/qikvrt_mesh_review_successor_completion.yml": frozenset(
        {"schedule", "workflow_run", "workflow_dispatch"}
    )
}
MESH_CHILD_RERUN_AUTHORITY_OBSERVER_EVENTS = {
    ".github/workflows/qikvrt_review_admission_recovery.yml": frozenset(
        {"schedule", "workflow_run", "workflow_dispatch"}
    )
}
ADMISSION_AUTHORITY_OBSERVATION_BLOCKERS = frozenset(
    {
        "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED",
        "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
    }
)
TERMINAL_RUN_CONCLUSIONS = frozenset(
    {
        "action_required",
        "cancelled",
        "failure",
        "neutral",
        "skipped",
        "stale",
        "startup_failure",
        "success",
        "timed_out",
    }
)
FORBIDDEN_FALLBACK_SECRET_NAMES = frozenset(
    {
        AUDITOR_SECRET_NAME,
        WRITER_SECRET_NAME,
        "QIKVRT_OUTBOX_LEDGER_AUDITOR_TOKEN",
        "QIKVRT_OUTBOX_LEDGER_WRITER_TOKEN",
    }
)
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
LANE_PATTERN = re.compile(r"[a-z][a-z0-9-]{0,62}")
BUSINESS_OUTCOMES = {
    "ruleset-dispatch": frozenset({"RULESET_CURRENT_RECEIPT"}),
    "reconciler-rerun": frozenset({"RECONCILER_CURRENT_RECEIPT"}),
    "requested-review-dispatch": frozenset(
        {"REQUESTED_REVIEW_LEDGER_CONTINUATION"}
    ),
    "exact-head-dispatch": frozenset({"EXACT_HEAD_TERMINAL_CONTINUATION"}),
    "exact-review-dispatch": frozenset({"EXACT_REVIEW_LEDGER_CONTINUATION"}),
    "mesh-review-successor-dispatch": frozenset(
        {"MESH_REVIEW_LEDGER_CONTINUATION"}
    ),
}
D0_2_TECHNICAL_REASONS = {
    "ruleset-dispatch": frozenset({"RULESET_CURRENT_RECEIPT_PERSISTED"}),
    "reconciler-rerun": frozenset({"RECONCILER_CURRENT_RECEIPT_PERSISTED"}),
    "requested-review-dispatch": frozenset(
        {"REQUESTED_REVIEW_LEDGER_CONTINUATION_PERSISTED"}
    ),
    "exact-head-dispatch": frozenset({"EXACT_HEAD_RESULT_PERSISTED"}),
    "exact-review-dispatch": frozenset(
        {"EXACT_REVIEW_LEDGER_CONTINUATION_PERSISTED"}
    ),
    "mesh-review-successor-dispatch": frozenset(
        {"MESH_REVIEW_LEDGER_CONTINUATION_PERSISTED"}
    ),
}
RETRY_BLOCKERS = {
    "ruleset-dispatch": frozenset(),
    "reconciler-rerun": frozenset(),
    "requested-review-dispatch": frozenset(),
    "exact-head-dispatch": frozenset(),
    "exact-review-dispatch": frozenset(),
    # Mesh successor transport is deliberately one-shot.  A complete orphan
    # observation closes as Authority HOLD; it never authorizes a second
    # repository/workflow dispatch.  Same-run attempt two is modelled only by
    # the child-recovery state machine below.
    "mesh-review-successor-dispatch": frozenset(),
}
COMMON_EXHAUSTION_BLOCKERS = {
    "CHILD_RESULT_ADVERSE": frozenset(
        {"ATTEMPT_1_ACCEPTED_ADVERSE", "ATTEMPT_2_TERMINAL_ADVERSE"}
    ),
    "ONE_SHOT_RERUN_EXHAUSTED": frozenset(
        {
            "RECONCILER_ATTEMPT_2_ACTION_REQUIRED",
            "RECONCILER_ATTEMPT_2_CANCELLED",
            "RECONCILER_ATTEMPT_2_FAILURE",
            "RECONCILER_ATTEMPT_2_SKIPPED",
            "RECONCILER_ATTEMPT_2_TIMED_OUT",
        }
    ),
    "ONE_SHOT_RERUN_TRANSPORT_AMBIGUOUS": frozenset(
        {
            "RECONCILER_RERUN_TRANSPORT_AMBIGUOUS",
            "RECONCILER_RERUN_TRANSPORT_NOT_OBSERVED",
        }
    ),
    "CHILD_RERUN_EXHAUSTED": frozenset(
        {"ATTEMPT_2_TERMINAL_ADVERSE", "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED"}
    ),
    "SAME_RUN_RESULT_ADVERSE": frozenset({"SAME_RUN_EXACT_RESULT_ADVERSE"}),
    "AMBIGUOUS_OR_DRIFT": frozenset(
        {
            "BOUND_EVIDENCE_AMBIGUOUS",
            "LATE_ATTEMPT_1_ACCEPTANCE_AFTER_ATTEMPT_2_SEALED",
            "OUTBOX_TARGET_WORKFLOW_SUPERSEDED",
        }
    ),
}
LANE_EXHAUSTION_BLOCKERS = {
    "ruleset-dispatch": {
        "CHILD_RESULT_ADVERSE": frozenset(
            {
                "RULESET_RECONCILER_ACTION_REQUIRED",
                "RULESET_RECONCILER_CANCELLED",
                "RULESET_RECONCILER_FAILURE",
                "RULESET_RECONCILER_SKIPPED",
                "RULESET_RECONCILER_TIMED_OUT",
            }
        ),
        "AMBIGUOUS_OR_DRIFT": frozenset(
            {
                "OUTBOX_EVALUATOR_SUPERSEDED",
                "OUTBOX_SUBJECT_SUPERSEDED",
                "REPEATED_RULESET_TRANSPORT_UNACKNOWLEDGED",
            }
        ),
    },
    "reconciler-rerun": {
        "CHILD_RESULT_ADVERSE": frozenset(
            {
                "RECONCILER_ATTEMPT_2_ACTION_REQUIRED",
                "RECONCILER_ATTEMPT_2_CANCELLED",
                "RECONCILER_ATTEMPT_2_FAILURE",
                "RECONCILER_ATTEMPT_2_SKIPPED",
                "RECONCILER_ATTEMPT_2_TIMED_OUT",
            }
        ),
    },
    "requested-review-dispatch": {
        "CHILD_RESULT_ADVERSE": frozenset(
            {"REQUESTED_REVIEW_RESULT_ADVERSE"}
        ),
        "CHILD_RERUN_EXHAUSTED": frozenset(
            {"REQUESTED_REVIEW_RERUN_ATTEMPT_2_ADVERSE"}
        ),
        "AMBIGUOUS_OR_DRIFT": frozenset(
            {
                "OUTBOX_EVALUATOR_SUPERSEDED",
                "OUTBOX_SUBJECT_SUPERSEDED",
                "REPEATED_REQUESTED_REVIEW_TRANSPORT_UNACKNOWLEDGED",
            }
        ),
    },
    "exact-head-dispatch": {
        "CHILD_RESULT_ADVERSE": frozenset(
            {"REPEATED_EXACT_HEAD_RESULT_ADVERSE"}
        ),
        "AMBIGUOUS_OR_DRIFT": frozenset(
            {
                "OUTBOX_EVALUATOR_SUPERSEDED",
                "OUTBOX_SUBJECT_SUPERSEDED",
                "BOUND_EVIDENCE_AMBIGUITY_SET_EXCEEDED",
                "EXACT_HEAD_COMPLETION_EVIDENCE_MISSING",
                "RECOVERY_QUERY_BOUND_EXCEEDED",
                "RECOVERY_QUERY_INVENTORY_INCONSISTENT",
                "REPEATED_EXACT_HEAD_RESULT_NOT_PERSISTED",
                "REPEATED_EXACT_HEAD_TRANSPORT_UNACKNOWLEDGED",
            }
        ),
    },
    "exact-review-dispatch": {
        "CHILD_RESULT_ADVERSE": frozenset({"EXACT_REVIEW_RESULT_ADVERSE"}),
        "CHILD_RERUN_EXHAUSTED": frozenset(
            {"EXACT_REVIEW_RERUN_ATTEMPT_2_ADVERSE"}
        ),
        "AMBIGUOUS_OR_DRIFT": frozenset(
            {
                "BOUND_EVIDENCE_AMBIGUITY_SET_EXCEEDED",
                "EXACT_REVIEW_BUSINESS_EVIDENCE_MISSING",
                "EXACT_REVIEW_COMPLETION_EVIDENCE_MISSING",
                "OUTBOX_EVALUATOR_SUPERSEDED",
                "OUTBOX_SUBJECT_SUPERSEDED",
                "RECOVERY_QUERY_BOUND_EXCEEDED",
                "RECOVERY_QUERY_INVENTORY_INCONSISTENT",
                "REPEATED_EXACT_REVIEW_TRANSPORT_UNACKNOWLEDGED",
                "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
            }
        ),
    },
    "mesh-review-successor-dispatch": {
        "CHILD_RESULT_ADVERSE": frozenset({"MESH_REVIEW_RESULT_ADVERSE"}),
        "CHILD_RERUN_EXHAUSTED": frozenset(
            {"MESH_REVIEW_RERUN_ATTEMPT_2_ADVERSE"}
        ),
        "AMBIGUOUS_OR_DRIFT": frozenset(
            {
                "MESH_REVIEW_BUSINESS_EVIDENCE_MISSING",
                "MESH_REVIEW_COMPLETION_EVIDENCE_MISSING",
                "MESH_REVIEW_COMPLETION_QUERY_BOUND_EXCEEDED",
                "MESH_REVIEW_RECOVERY_QUERY_BOUND_EXCEEDED",
                "MESH_REVIEW_RECOVERY_QUERY_INVENTORY_INCONSISTENT",
                "MESH_REVIEW_TRANSPORT_CHILD_AMBIGUOUS",
                "MESH_REVIEW_TRANSPORT_CHILD_SET_EXCEEDED",
                "OUTBOX_EVALUATOR_SUPERSEDED",
                "OUTBOX_SUBJECT_SUPERSEDED",
                "REPEATED_MESH_REVIEW_TRANSPORT_UNACKNOWLEDGED",
                "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
            }
        ),
    },
}
COMPLETION_CLAIM_KEYS = (
    "physical_atari_boot",
    "physical_atari_execution",
    "merge",
    "approval",
    "pass",
    "final_pass",
    "publication",
    "release",
    "deployment",
    "authority_mirror_synchronization",
    "effect_ack_done",
)
REVIEW_TRANSPORT_LANES = frozenset(
    {
        "requested-review-dispatch",
        "exact-review-dispatch",
        "mesh-review-successor-dispatch",
    }
)
REPOSITORY_DISPATCH_TRANSPORT_LANES = frozenset(
    {"ruleset-dispatch", "exact-head-dispatch"}
)


class OutboxBlock(RuntimeError):
    """Fail-closed outbox contract violation."""


class GitHubApiError(OutboxBlock):
    def __init__(self, status: int, message: str):
        super().__init__(f"GitHub API {status}: {message}")
        self.status = status


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def compact_canonical_bytes(value: Any) -> bytes:
    """Canonical compact JSON used by the pre-existing Admission receipts."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise OutboxBlock("digest input must be bytes")
    return hashlib.sha256(value).hexdigest()


def digest(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def compact_digest(value: Any) -> str:
    return sha256_bytes(compact_canonical_bytes(value))


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise OutboxBlock(f"{label} must be an object")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise OutboxBlock(f"{label} must be a positive integer")
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX40.fullmatch(value) is None:
        raise OutboxBlock(f"{label} must be a lowercase SHA-1")
    return value


def _digest(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise OutboxBlock(f"{label} must be a SHA-256")
    normalized = value.removeprefix("sha256:")
    if HEX64.fullmatch(normalized) is None:
        raise OutboxBlock(f"{label} must be a lowercase SHA-256")
    return normalized


def _repository(value: Any) -> str:
    if value != "Goldkelch/qik-vrt":
        raise OutboxBlock("outbox repository mismatch")
    return str(value)


def _lane(value: Any) -> str:
    if not isinstance(value, str) or LANE_PATTERN.fullmatch(value) is None:
        raise OutboxBlock("outbox lane is invalid")
    if value not in LANES:
        raise OutboxBlock("outbox lane is not authorized")
    return value


def _sequence(value: Any, label: str = "outbox sequence") -> int:
    return _positive_int(value, label)


def _sequence_text(sequence: int) -> str:
    return f"{_sequence(sequence):020d}"


def ledger_ref(lane: str) -> str:
    return f"{LEDGER_REF_PREFIX}/{_lane(lane)}"


def ledger_short_ref(lane: str) -> str:
    return f"{LEDGER_SHORT_REF_PREFIX}/{_lane(lane)}"


def ledger_api_ref(lane: str) -> str:
    return f"{LEDGER_API_REF_PREFIX}/{_lane(lane)}"


def writer_concurrency_group(lane: str) -> str:
    """Return the mandatory cross-workflow writer key for one isolated lane."""
    return f"qikvrt-outbox-ledger-v2-{_lane(lane)}"


def writer_token_from_environment(
    environ: Mapping[str, str] | None = None,
) -> str:
    values = os.environ if environ is None else environ
    token = values.get("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", "")
    if not token:
        raise OutboxBlock(
            "OUTBOX_LEDGER_WRITER_TOKEN_UNAVAILABLE: environment-scoped "
            "GitHub App installation token is required"
        )
    if token in {values.get("GH_TOKEN", ""), values.get("GITHUB_TOKEN", "")} - {""}:
        raise OutboxBlock(
            "OUTBOX_LEDGER_WRITER_TOKEN_SCOPE_INVALID: ordinary workflow "
            "token fallback is forbidden"
        )
    return token


def auditor_token_from_environment(
    environ: Mapping[str, str] | None = None,
) -> str:
    values = os.environ if environ is None else environ
    token = values.get("QIKVRT_ENV_OUTBOX_LEDGER_AUDITOR_TOKEN", "")
    if not token:
        raise OutboxBlock(
            "OUTBOX_LEDGER_AUDITOR_TOKEN_UNAVAILABLE: environment-scoped "
            "read-only ledger/ruleset token is required"
        )
    forbidden = {
        values.get("GH_TOKEN", ""),
        values.get("GITHUB_TOKEN", ""),
        values.get("QIKVRT_ENV_OUTBOX_LEDGER_WRITER_TOKEN", ""),
    } - {""}
    if token in forbidden:
        raise OutboxBlock(
            "OUTBOX_LEDGER_AUDITOR_TOKEN_SCOPE_INVALID: auditor, ordinary, "
            "and writer credentials must remain distinct"
        )
    return token


def writer_actor_id_from_environment(
    environ: Mapping[str, str] | None = None,
) -> int:
    """Read the non-secret Integration identity used by exact protection checks."""
    values = os.environ if environ is None else environ
    raw = values.get("QIKVRT_OUTBOX_LEDGER_WRITER_ACTOR_ID", "")
    try:
        actor_id = int(raw)
    except (TypeError, ValueError) as exc:
        raise OutboxBlock(
            "OUTBOX_LEDGER_WRITER_ACTOR_ID_UNAVAILABLE: a positive Integration "
            "actor id is required"
        ) from exc
    try:
        return _positive_int(actor_id, "outbox writer actor id")
    except OutboxBlock as exc:
        raise OutboxBlock(
            "OUTBOX_LEDGER_WRITER_ACTOR_ID_UNAVAILABLE: a positive Integration "
            "actor id is required"
        ) from exc


def meta_path(lane: str) -> str:
    return f"meta/{_lane(lane)}.json"


def slot_path(lane: str, sequence: int) -> str:
    return f"slots/{_lane(lane)}/{_sequence_text(sequence)}.json"


def intent_path(lane: str, sequence: int, fingerprint: str) -> str:
    return (
        f"intents/{_lane(lane)}/{_sequence_text(sequence)}-"
        f"{_digest(fingerprint, 'intent fingerprint')}.json"
    )


def locator_path(lane: str, fingerprint: str) -> str:
    return (
        f"fingerprints/{_lane(lane)}/"
        f"{_digest(fingerprint, 'intent fingerprint')}.json"
    )


def witness_index_path(lane: str, fingerprint: str) -> str:
    return (
        f"witnesses/{_lane(lane)}/"
        f"{_digest(fingerprint, 'intent fingerprint')}/index.json"
    )


def witness_path(
    lane: str, fingerprint: str, producer_run_id: int, producer_run_attempt: int
) -> str:
    return (
        f"witnesses/{_lane(lane)}/"
        f"{_digest(fingerprint, 'intent fingerprint')}/"
        f"run-{_positive_int(producer_run_id, 'witness producer run id')}-"
        f"attempt-{_positive_int(producer_run_attempt, 'witness producer run attempt')}.json"
    )


def transport_path(lane: str, sequence: int, attempt: int) -> str:
    if attempt not in {1, 2}:
        raise OutboxBlock("transport attempt must be 1 or 2")
    return (
        f"transport/{_lane(lane)}/{_sequence_text(sequence)}-"
        f"attempt-{attempt}.json"
    )


def acceptance_path(lane: str, sequence: int, attempt: int) -> str:
    if attempt not in {1, 2}:
        raise OutboxBlock("acceptance attempt must be 1 or 2")
    return (
        f"acceptance/{_lane(lane)}/{_sequence_text(sequence)}-"
        f"attempt-{attempt}.json"
    )


def late_acceptance_path(lane: str, sequence: int) -> str:
    return (
        f"late-acceptance-conflicts/{_lane(lane)}/"
        f"{_sequence_text(sequence)}-attempt-1-after-attempt-2.json"
    )


def authority_observation_path(
    lane: str, sequence: int, record_sha256: str
) -> str:
    return (
        f"authority-observation/{_lane(lane)}/"
        f"{_sequence_text(sequence)}/{_digest(record_sha256, 'authority observation record digest')}.json"
    )


def retry_scan_cursor_path(
    lane: str,
    sequence: int,
    transport_attempt: int,
    ordinal: int,
    record_sha256: str,
) -> str:
    if transport_attempt not in {1, 2}:
        raise OutboxBlock("retry scan transport attempt must be 1 or 2")
    return (
        f"retry-scan-cursor/{_lane(lane)}/{_sequence_text(sequence)}/"
        f"attempt-{transport_attempt}/{_sequence_text(ordinal)}-"
        f"{_digest(record_sha256, 'retry scan cursor record digest')}.json"
    )


def retry_scan_cursor_locator_path(
    lane: str, sequence: int, transport_attempt: int
) -> str:
    if transport_attempt not in {1, 2}:
        raise OutboxBlock("retry scan transport attempt must be 1 or 2")
    return (
        f"retry-scan-cursor/{_lane(lane)}/{_sequence_text(sequence)}/"
        f"attempt-{transport_attempt}/current.json"
    )


def completion_path(
    lane: str, sequence: int, attempt: int, *, child_recovery: bool = False
) -> str:
    if attempt not in {1, 2}:
        raise OutboxBlock("completion attempt must be 1 or 2")
    namespace = "child-rerun-completion" if child_recovery else "completion"
    return (
        f"{namespace}/{_lane(lane)}/{_sequence_text(sequence)}-"
        f"attempt-{attempt}.json"
    )


def terminal_path(lane: str, sequence: int) -> str:
    return f"terminal/{_lane(lane)}/{_sequence_text(sequence)}.json"


def terminal_supersession_path(lane: str, sequence: int) -> str:
    return (
        f"terminal-supersession/{_lane(lane)}/"
        f"{_sequence_text(sequence)}-same-run-attempt-2.json"
    )


def child_rerun_path(lane: str, sequence: int, transport_attempt: int) -> str:
    if transport_attempt not in {1, 2}:
        raise OutboxBlock("child-rerun transport attempt must be 1 or 2")
    return (
        f"child-rerun/{_lane(lane)}/{_sequence_text(sequence)}-"
        f"transport-attempt-{transport_attempt}.json"
    )


def child_rerun_acceptance_path(
    lane: str, sequence: int, transport_attempt: int
) -> str:
    if transport_attempt not in {1, 2}:
        raise OutboxBlock("child-rerun acceptance transport attempt must be 1 or 2")
    return (
        f"child-rerun-acceptance/{_lane(lane)}/{_sequence_text(sequence)}-"
        f"transport-attempt-{transport_attempt}.json"
    )


def same_run_result_path(
    lane: str,
    sequence: int,
    transport_attempt: int,
    observed_run_attempt: int,
) -> str:
    if transport_attempt not in {1, 2}:
        raise OutboxBlock("same-run transport attempt must be 1 or 2")
    return (
        f"same-run-result/{_lane(lane)}/{_sequence_text(sequence)}-"
        f"transport-attempt-{transport_attempt}-"
        f"run-attempt-{_positive_int(observed_run_attempt, 'observed run attempt')}.json"
    )


def initial_meta(lane: str) -> dict[str, Any]:
    return {
        "schema": META_SCHEMA,
        "lane": _lane(lane),
        "next_seq": 1,
        "drain_seq": 1,
    }


def validate_meta(value: Any, lane: str) -> dict[str, Any]:
    item = _mapping(value, "outbox lane metadata")
    expected_lane = _lane(lane)
    if item.get("schema") != META_SCHEMA or item.get("lane") != expected_lane:
        raise OutboxBlock("outbox lane metadata binding mismatch")
    next_seq = _sequence(item.get("next_seq"), "outbox next sequence")
    drain_seq = _sequence(item.get("drain_seq"), "outbox drain sequence")
    if drain_seq > next_seq:
        raise OutboxBlock("outbox drain sequence exceeds next sequence")
    return {
        "schema": META_SCHEMA,
        "lane": expected_lane,
        "next_seq": next_seq,
        "drain_seq": drain_seq,
    }


def validate_payload(value: Any, *, lane: str | None = None) -> dict[str, Any]:
    raw = _mapping(value, "outbox payload")
    payload_lane = _lane(raw.get("lane"))
    if lane is not None and payload_lane != _lane(lane):
        raise OutboxBlock("outbox payload lane mismatch")
    repository = _repository(raw.get("repository"))
    main_head = _sha(raw.get("main_head_sha"), "outbox payload main head")
    producer = _mapping(raw.get("producer"), "outbox producer")
    normalized_producer = {
        "workflow_path": producer.get("workflow_path"),
        "workflow_sha": _sha(
            producer.get("workflow_sha"), "outbox producer workflow sha"
        ),
        "workflow_id": _positive_int(
            producer.get("workflow_id"), "outbox producer workflow id"
        ),
        "run_id": _positive_int(producer.get("run_id"), "outbox producer run id"),
        "run_attempt": _positive_int(
            producer.get("run_attempt"), "outbox producer run attempt"
        ),
        "event": producer.get("event"),
    }
    if (
        not isinstance(normalized_producer["workflow_path"], str)
        or not normalized_producer["workflow_path"].startswith(".github/workflows/")
        or normalized_producer["workflow_sha"] != main_head
        or not isinstance(normalized_producer["event"], str)
        or not normalized_producer["event"]
    ):
        raise OutboxBlock("outbox producer identity is incomplete")
    subject = dict(_mapping(raw.get("subject"), "outbox subject"))
    target = _mapping(raw.get("target"), "outbox target workflow")
    expected_targets = {
        "ruleset-dispatch": (
            ".github/workflows/qikvrt_ruleset_reconcile.yml",
            "repository_dispatch",
        ),
        "reconciler-rerun": (
            ".github/workflows/qikvrt_ruleset_reconcile.yml",
            "repository_dispatch",
        ),
        "requested-review-dispatch": (
            ".github/workflows/qikvrt_requested_review_executor.yml",
            "workflow_dispatch",
        ),
        "exact-head-dispatch": (
            ".github/workflows/qikvrt_autonomous_exact_head_verify.yml",
            "repository_dispatch",
        ),
        "exact-review-dispatch": (
            ".github/workflows/qikvrt_requested_review_executor.yml",
            "workflow_dispatch",
        ),
        "mesh-review-successor-dispatch": (
            ".github/workflows/qikvrt_requested_review_executor.yml",
            "workflow_dispatch",
        ),
    }
    expected_target_path, expected_target_event = expected_targets[payload_lane]
    normalized_target = {
        "workflow_id": _positive_int(
            target.get("workflow_id"), "outbox target workflow id"
        ),
        "workflow_path": target.get("workflow_path"),
        "event": target.get("event"),
    }
    if normalized_target != {
        "workflow_id": normalized_target["workflow_id"],
        "workflow_path": expected_target_path,
        "event": expected_target_event,
    }:
        raise OutboxBlock("outbox target workflow identity mismatch")
    request = dict(_mapping(raw.get("request"), "outbox request"))
    causal = _mapping(raw.get("causal"), "outbox causal binding")
    if (
        causal.get("d0") != 2
        or causal.get("productive_effect") is not False
        or not isinstance(causal.get("state"), str)
        or not causal.get("state")
    ):
        raise OutboxBlock("outbox causal binding is not a D0=2 intent")
    if payload_lane == "ruleset-dispatch":
        client_payload = request.get("client_payload")
        if (
            set(request) != {"event_type", "client_payload"}
            or request.get("event_type") != "qikvrt_ruleset_reconcile"
            or not isinstance(client_payload, Mapping)
            or set(client_payload)
            != {"schema", "repository", "source", "binding", "review", "causal"}
            or client_payload.get("schema")
            != "qikvrt_ruleset_reconcile_dispatch_v1"
            or client_payload.get("repository") != repository
            or not all(
                isinstance(client_payload.get(field), Mapping)
                for field in ("source", "binding", "review", "causal")
            )
        ):
            raise OutboxBlock("ruleset-dispatch request is invalid")
    elif payload_lane == "reconciler-rerun":
        endpoint = request.get("endpoint")
        run_id = request.get("reconciler_run_id")
        original_child = request.get("original_child")
        expected_request_keys = {
            "schema",
            "repository",
            "reconciler_run_id",
            "reconciler_run_attempt",
            "method",
            "endpoint",
            "target_attempt",
            "original_child",
            "original_child_sha256",
            "productive_effect",
        }
        if (
            set(request) != expected_request_keys
            or
            request.get("schema")
            != "qikvrt_ruleset_reconciler_rerun_request_v1"
            or request.get("repository") != repository
            or request.get("method") != "POST"
            or request.get("target_attempt") != 2
            or request.get("productive_effect") is not False
            or isinstance(run_id, bool)
            or not isinstance(run_id, int)
            or run_id < 1
            or endpoint
            != f"repos/{repository}/actions/runs/{run_id}/rerun"
            or not isinstance(original_child, Mapping)
            or set(original_child)
            != {
                "run_id",
                "run_attempt",
                "workflow_id",
                "workflow_path",
                "event",
                "repository",
                "head_sha",
                "status",
                "conclusion",
                "display_title",
            }
            or original_child.get("run_id") != run_id
            or original_child.get("run_attempt") != 1
            or request.get("reconciler_run_attempt") != 1
            or isinstance(original_child.get("workflow_id"), bool)
            or not isinstance(original_child.get("workflow_id"), int)
            or original_child.get("workflow_id", 0) < 1
            or original_child.get("workflow_path")
            != ".github/workflows/qikvrt_ruleset_reconcile.yml"
            or original_child.get("event") != "repository_dispatch"
            or original_child.get("repository") != repository
            or HEX40.fullmatch(str(original_child.get("head_sha"))) is None
            or original_child.get("status") != "completed"
            or not isinstance(original_child.get("conclusion"), str)
            or not original_child.get("conclusion")
            or not isinstance(original_child.get("display_title"), str)
            or re.search(
                r"(?:^| )intent=[0-9a-f]{64} seq=[1-9][0-9]* "
                r"transport-attempt=[12](?: |$)",
                str(original_child.get("display_title")),
            )
            is None
            or request.get("original_child_sha256")
            != digest(dict(original_child))
        ):
            raise OutboxBlock("reconciler-rerun request is invalid")
    elif payload_lane in {
        "requested-review-dispatch",
        "mesh-review-successor-dispatch",
    }:
        inputs = request.get("inputs")
        if (
            set(request) != {"ref", "return_run_details", "inputs"}
            or request.get("ref") != "main"
            or request.get("return_run_details") is not True
            or not isinstance(inputs, Mapping)
            or set(inputs)
            != {
                "pr",
                "head",
                "fingerprint",
                "evaluator_sha",
                "transport_intent_sha256",
                "transport_attempt",
            }
            or not isinstance(inputs.get("pr"), str)
            or re.fullmatch(r"[1-9][0-9]{0,9}", inputs["pr"]) is None
            or not isinstance(inputs.get("head"), str)
            or HEX40.fullmatch(inputs["head"]) is None
            or not isinstance(inputs.get("fingerprint"), str)
            or HEX64.fullmatch(inputs["fingerprint"]) is None
            or not isinstance(inputs.get("evaluator_sha"), str)
            or HEX40.fullmatch(inputs["evaluator_sha"]) is None
            or not isinstance(inputs.get("transport_intent_sha256"), str)
            or HEX64.fullmatch(inputs["transport_intent_sha256"]) is None
            or inputs.get("transport_attempt") != "1"
        ):
            raise OutboxBlock(f"{payload_lane} request is invalid")
    elif payload_lane == "exact-head-dispatch":
        client_payload = request.get("client_payload")
        exact_subject = (
            _mapping(client_payload.get("subject"), "exact-head subject")
            if isinstance(client_payload, Mapping)
            else {}
        )
        exact_producer = (
            _mapping(client_payload.get("producer"), "exact-head producer")
            if isinstance(client_payload, Mapping)
            else {}
        )
        exact_causal = (
            _mapping(client_payload.get("causal"), "exact-head causal")
            if isinstance(client_payload, Mapping)
            else {}
        )
        if (
            set(request) != {"event_type", "client_payload"}
            or request.get("event_type") != "qikvrt_autonomous_exact_head_verify"
            or not isinstance(client_payload, Mapping)
            or set(client_payload)
            != {"schema", "repository", "subject", "producer", "causal"}
            or client_payload.get("schema")
            != "qikvrt_autonomous_exact_head_verify_dispatch_v1"
            or client_payload.get("repository") != repository
            or set(exact_subject)
            != {
                "pull_request",
                "head_repository",
                "head_ref",
                "head_sha",
                "head_tree_sha",
                "base_ref",
                "base_sha",
            }
            or _positive_int(
                exact_subject.get("pull_request"), "exact-head pull request"
            )
            < 1
            or exact_subject.get("head_repository") != repository
            or not isinstance(exact_subject.get("head_ref"), str)
            or not exact_subject.get("head_ref")
            or HEX40.fullmatch(str(exact_subject.get("head_sha"))) is None
            or HEX40.fullmatch(str(exact_subject.get("head_tree_sha"))) is None
            or not isinstance(exact_subject.get("base_ref"), str)
            or not exact_subject.get("base_ref")
            or HEX40.fullmatch(str(exact_subject.get("base_sha"))) is None
            or dict(subject) != dict(exact_subject)
            or set(exact_producer)
            != {
                "run_id",
                "run_attempt",
                "workflow_id",
                "workflow_path",
                "workflow_sha",
            }
            or dict(exact_producer)
            != {
                key: normalized_producer[key]
                for key in (
                    "run_id",
                    "run_attempt",
                    "workflow_id",
                    "workflow_path",
                    "workflow_sha",
                )
            }
            or set(exact_causal)
            != {"attempt", "d0", "state", "productive_effect"}
            or exact_causal.get("attempt") != 1
            or exact_causal.get("d0") != 2
            or exact_causal.get("state") != "REOBSERVE"
            or exact_causal.get("productive_effect") is not False
        ):
            raise OutboxBlock("exact-head repository-dispatch request is invalid")
    elif payload_lane == "exact-review-dispatch":
        inputs = request.get("inputs")
        if (
            set(request) != {"ref", "return_run_details", "inputs"}
            or request.get("ref") != "main"
            or request.get("return_run_details") is not True
            or not isinstance(inputs, Mapping)
            or set(inputs)
            != {
                "pr",
                "head",
                "fingerprint",
                "evaluator_sha",
                "transport_intent_sha256",
                "transport_attempt",
            }
            or any(
                not isinstance(inputs.get(field), str) or not inputs.get(field)
                for field in ("pr", "head", "evaluator_sha")
            )
            or re.fullmatch(r"[1-9][0-9]{0,9}", inputs["pr"]) is None
            or HEX40.fullmatch(inputs["head"]) is None
            or HEX40.fullmatch(inputs["evaluator_sha"]) is None
            or HEX64.fullmatch(str(inputs.get("fingerprint"))) is None
            or HEX64.fullmatch(str(inputs.get("transport_intent_sha256"))) is None
            or inputs.get("transport_attempt") != "1"
        ):
            raise OutboxBlock("exact-review dispatch request is invalid")
    return {
        "schema": PAYLOAD_SCHEMA,
        "repository": repository,
        "lane": payload_lane,
        "main_head_sha": main_head,
        "producer": normalized_producer,
        "subject": subject,
        "target": normalized_target,
        "request": request,
        "causal": {
            "d0": 2,
            "state": causal["state"],
            "productive_effect": False,
        },
    }


def validate_artifact(
    value: Any,
    *,
    payload_sha256: str,
    producer: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    raw = _mapping(value, "outbox artifact binding")
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        raise OutboxBlock("outbox artifact name is missing")
    normalized = {
        "id": _positive_int(raw.get("id"), "outbox artifact id"),
        "name": name,
        "archive_sha256": _digest(
            raw.get("archive_sha256"), "outbox artifact archive digest"
        ),
        "payload_sha256": _digest(
            raw.get("payload_sha256"), "outbox artifact payload digest"
        ),
        "producer_run_id": _positive_int(
            raw.get("producer_run_id"), "outbox artifact producer run id"
        ),
        "producer_run_attempt": _positive_int(
            raw.get("producer_run_attempt"),
            "outbox artifact producer run attempt",
        ),
        "producer_workflow_id": _positive_int(
            raw.get("producer_workflow_id"),
            "outbox artifact producer workflow id",
        ),
    }
    if normalized["payload_sha256"] != _digest(
        payload_sha256, "sealed payload digest"
    ):
        raise OutboxBlock("outbox artifact payload digest differs from sealed bytes")
    if producer is not None and (
        normalized["producer_run_id"] != producer.get("run_id")
        or normalized["producer_run_attempt"] != producer.get("run_attempt")
        or normalized["producer_workflow_id"] != producer.get("workflow_id")
    ):
        raise OutboxBlock("outbox artifact producer differs from sealed producer")
    return normalized


def _witness_record(
    payload: Mapping[str, Any], artifact: Mapping[str, Any], fingerprint: str
) -> dict[str, Any]:
    normalized_payload = validate_payload(payload)
    if digest(semantic_work_unit(normalized_payload)) != _digest(
        fingerprint, "witness fingerprint"
    ):
        raise OutboxBlock("outbox witness semantic work unit differs")
    payload_sha = sha256_bytes(canonical_bytes(normalized_payload))
    normalized_artifact = validate_artifact(
        artifact,
        payload_sha256=payload_sha,
        producer=_mapping(normalized_payload.get("producer"), "witness producer"),
    )
    producer = dict(
        _mapping(normalized_payload.get("producer"), "witness producer")
    )
    record = {
        "schema": WITNESS_SCHEMA,
        "repository": normalized_payload["repository"],
        "lane": normalized_payload["lane"],
        "fingerprint": fingerprint,
        "payload_sha256": payload_sha,
        "payload": normalized_payload,
        "producer": producer,
        "artifact": normalized_artifact,
        "state": "SEALED",
        "productive_effect": False,
    }
    record["witness_sha256"] = digest(record)
    return record


def _validate_witness_record(
    value: Any, *, lane: str, fingerprint: str
) -> dict[str, Any]:
    raw = dict(_mapping(value, "outbox witness record"))
    claimed = raw.pop("witness_sha256", None)
    payload = validate_payload(raw.get("payload"), lane=lane)
    record = _witness_record(payload, raw.get("artifact"), fingerprint)
    if (
        claimed != record["witness_sha256"]
        or raw != {key: value for key, value in record.items() if key != "witness_sha256"}
    ):
        raise OutboxBlock("outbox witness record binding mismatch")
    return record


def _read_witnesses(
    backend: "LedgerBackend", head: str, lane: str, fingerprint: str
) -> list[dict[str, Any]]:
    index = _mapping(
        _read_json(backend, head, witness_index_path(lane, fingerprint)),
        "outbox witness index",
    )
    entries = index.get("entries")
    page = index.get("page")
    next_ordinal = index.get("next_ordinal")
    if (
        index.get("schema") != WITNESS_INDEX_SCHEMA
        or index.get("lane") != lane
        or index.get("fingerprint") != fingerprint
        or isinstance(page, bool)
        or not isinstance(page, int)
        or page < 1
        or isinstance(next_ordinal, bool)
        or not isinstance(next_ordinal, int)
        or next_ordinal < 2
        or not isinstance(entries, list)
        or not entries
        or len(entries) > MAX_ACTIVE_WITNESSES
    ):
        raise OutboxBlock("outbox witness index binding mismatch")
    result: list[dict[str, Any]] = []
    seen: set[tuple[int, int]] = set()
    seen_ordinals: set[int] = set()
    for entry in entries:
        item = _mapping(entry, "outbox witness index entry")
        run_id = _positive_int(item.get("producer_run_id"), "witness run id")
        run_attempt = _positive_int(
            item.get("producer_run_attempt"), "witness run attempt"
        )
        key = (run_id, run_attempt)
        ordinal = _positive_int(item.get("ordinal"), "witness ordinal")
        expected_path = witness_path(lane, fingerprint, run_id, run_attempt)
        if (
            key in seen
            or ordinal in seen_ordinals
            or ordinal >= next_ordinal
            or item.get("path") != expected_path
            or HEX64.fullmatch(str(item.get("witness_sha256"))) is None
        ):
            raise OutboxBlock("outbox witness index entry is invalid")
        seen.add(key)
        seen_ordinals.add(ordinal)
        witness = _validate_witness_record(
            _read_json(backend, head, expected_path),
            lane=lane,
            fingerprint=fingerprint,
        )
        if witness["witness_sha256"] != item.get("witness_sha256"):
            raise OutboxBlock("outbox witness index digest differs")
        result.append(witness)
    expected_page = 1
    expected_first = 1
    if (
        page != expected_page
        or sorted(seen_ordinals)
        != list(range(expected_first, next_ordinal))
    ):
        raise OutboxBlock("outbox witness index page/ordinal mismatch")

    # Rotation never makes the immutable primary authority witness disappear
    # from an O(1) read.  Older retry witnesses remain addressable by their
    # exact content path but are not walked repository-wide.
    intent = _read_intent_by_fingerprint(backend, head, lane, fingerprint)
    if intent is None:
        raise OutboxBlock("outbox witness intent is absent")
    primary_payload = _mapping(intent.get("payload"), "primary witness payload")
    primary_producer = _mapping(
        primary_payload.get("producer"), "primary witness producer"
    )
    primary_key = (
        _positive_int(primary_producer.get("run_id"), "primary witness run id"),
        _positive_int(
            primary_producer.get("run_attempt"), "primary witness run attempt"
        ),
    )
    if primary_key not in seen:
        primary = _validate_witness_record(
            _read_json(
                backend,
                head,
                witness_path(lane, fingerprint, *primary_key),
            ),
            lane=lane,
            fingerprint=fingerprint,
        )
        if (
            primary.get("producer") != primary_producer
            or primary.get("artifact") != intent.get("artifact")
        ):
            raise OutboxBlock("outbox primary witness binding mismatch")
        result.insert(0, primary)
    return result


def semantic_work_unit(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return the effect identity, excluding retry/transport provenance.

    A workflow rerun or a re-upload is a new witness for the same sealed work
    unit, not permission to enqueue a second effect.  The exact request bytes,
    subject, evaluator/main binding and lane remain in the semantic key.
    """
    normalized = validate_payload(payload)
    request = dict(normalized["request"])
    if normalized["lane"] == "ruleset-dispatch":
        client_payload = dict(_mapping(request["client_payload"], "ruleset request"))
        request = {
            "event_type": request["event_type"],
            "client_payload": {
                key: client_payload[key]
                for key in ("schema", "repository", "binding", "review")
            },
        }
    elif normalized["lane"] == "exact-head-dispatch":
        client_payload = dict(_mapping(request["client_payload"], "exact request"))
        request = {
            "event_type": request["event_type"],
            "client_payload": {
                key: client_payload[key]
                for key in ("schema", "repository", "subject")
            },
        }
    elif normalized["lane"] in REVIEW_TRANSPORT_LANES:
        inputs = dict(_mapping(request["inputs"], "review transport inputs"))
        inputs.pop("transport_intent_sha256", None)
        inputs.pop("transport_attempt", None)
        request = {**request, "inputs": inputs}
    return {
        "schema": "qikvrt_ruleset_outbox_work_unit_v1",
        "repository": normalized["repository"],
        "lane": normalized["lane"],
        "main_head_sha": normalized["main_head_sha"],
        "subject": normalized["subject"],
        "target": normalized["target"],
        "request": request,
    }


def seal_review_transport_payload(
    value: Mapping[str, Any], *, attempt: int = 1
) -> dict[str, Any]:
    """Bind attempt-specific Requested-Executor inputs to one semantic intent."""
    if attempt != 1:
        raise OutboxBlock("new-run review transport is one-shot")
    raw = json.loads(json.dumps(dict(_mapping(value, "review payload draft"))))
    request = _mapping(raw.get("request"), "review payload request")
    inputs = dict(_mapping(request.get("inputs"), "review payload inputs"))
    inputs["transport_intent_sha256"] = "0" * 64
    inputs["transport_attempt"] = str(attempt)
    raw["request"] = {**dict(request), "inputs": inputs}
    normalized = validate_payload(raw)
    if normalized["lane"] not in REVIEW_TRANSPORT_LANES:
        raise OutboxBlock("transport locator is only valid for review lanes")
    fingerprint = digest(semantic_work_unit(normalized))
    inputs["transport_intent_sha256"] = fingerprint
    raw["request"] = {**dict(request), "inputs": inputs}
    return validate_payload(raw)


def request_for_transport_attempt(
    intent: Mapping[str, Any],
    attempt: int,
    *,
    witness: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = _mapping(
        witness.get("payload") if witness is not None else intent.get("payload"),
        "transport request payload",
    )
    request = dict(_mapping(payload.get("request"), "transport sealed request"))
    lane = _lane(intent.get("lane"))
    if attempt != 1:
        raise OutboxBlock("new-run transport is one-shot")
    if lane in REVIEW_TRANSPORT_LANES:
        inputs = dict(_mapping(request.get("inputs"), "transport review inputs"))
        inputs["transport_intent_sha256"] = _digest(
            intent.get("fingerprint"), "transport intent fingerprint"
        )
        inputs["transport_attempt"] = str(attempt)
        request["inputs"] = inputs
    elif lane in REPOSITORY_DISPATCH_TRANSPORT_LANES:
        client_payload = dict(
            _mapping(request.get("client_payload"), "repository dispatch payload")
        )
        client_payload["transport"] = {
            "intent_sha256": _digest(
                intent.get("fingerprint"), "repository dispatch intent fingerprint"
            ),
            "sequence": _sequence(intent.get("sequence")),
            "attempt": attempt,
        }
        request["client_payload"] = client_payload
    return request


class LedgerBackend(Protocol):
    repository: str

    def get_ledger_head(self, lane: str) -> str | None: ...

    def verify_ledger_protection(self, lane: str) -> None: ...

    def verify_authority_environment(self, lane: str) -> Mapping[str, Any]: ...

    def verify_writer_scope(self, lane: str) -> None: ...

    def get_main_head(self) -> str: ...

    def read_file(self, commit: str, path: str) -> bytes | None: ...

    def build_commit(
        self, parent: str, files: Mapping[str, bytes], message: str
    ) -> str: ...

    def update_ledger_ref(self, lane: str, commit: str) -> None: ...


class GitHubLedgerBackend:
    """Small Git Data API adapter; secret values are never serialized."""

    def __init__(self, repository: str, token: str):
        self.repository = _repository(repository)
        if not isinstance(token, str) or not token:
            raise OutboxBlock("GH_TOKEN is unavailable for ruleset outbox")
        self._token = token
        self.last_authority_readback: dict[str, Any] | None = None

    def _request(
        self,
        method: str,
        endpoint: str,
        payload: Mapping[str, Any] | None = None,
        *,
        allow_not_found: bool = False,
    ) -> Mapping[str, Any] | None:
        url = f"https://api.github.com/repos/{self.repository}/{endpoint}"
        data = canonical_bytes(payload) if payload is not None else None
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "qik-vrt-ruleset-outbox-v2",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return None
            try:
                detail = exc.read().decode("utf-8", "replace")[:500]
            except Exception:
                detail = str(exc.reason)
            raise GitHubApiError(exc.code, detail) from exc
        except urllib.error.URLError as exc:
            raise OutboxBlock(f"GitHub outbox transport failed: {exc.reason}") from exc
        if not raw:
            return {}
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OutboxBlock("GitHub outbox response is not JSON") from exc
        return _mapping(value, "GitHub outbox response")

    def _request_list(self, endpoint: str) -> list[Any]:
        url = f"https://api.github.com/repos/{self.repository}/{endpoint}"
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "qik-vrt-ruleset-outbox-v2",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")[:500]
            except Exception:
                detail = str(exc.reason)
            raise GitHubApiError(exc.code, detail) from exc
        except urllib.error.URLError as exc:
            raise OutboxBlock(f"GitHub outbox transport failed: {exc.reason}") from exc
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OutboxBlock("GitHub outbox response is not JSON") from exc
        if not isinstance(value, list):
            raise OutboxBlock("GitHub outbox response is not a list")
        return value

    def _request_absolute(self, url: str) -> Mapping[str, Any]:
        if not isinstance(url, str) or not url.startswith("https://api.github.com/"):
            raise OutboxBlock("outbox authority URL is not GitHub API scoped")
        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self._token}",
                "X-GitHub-Api-Version": "2026-03-10",
                "User-Agent": "qik-vrt-ruleset-outbox-v2",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", "replace")[:500]
            except Exception:
                detail = str(exc.reason)
            raise GitHubApiError(exc.code, detail) from exc
        except urllib.error.URLError as exc:
            raise OutboxBlock(
                f"GitHub outbox authority readback failed: {exc.reason}"
            ) from exc
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OutboxBlock("GitHub outbox authority response is not JSON") from exc
        return _mapping(value, "GitHub outbox authority response")

    def _complete_named_inventory(
        self,
        *,
        endpoint: str,
        key: str,
        absolute: bool = False,
    ) -> list[dict[str, Any]]:
        # These inventories protect the credential scope used for a mutation.
        # Offset pagination cannot prove absence under concurrent insert/delete
        # shifts, so only one complete bounded page is admissible.  Read the
        # exact page twice and require byte-equivalent API objects; larger or
        # moving inventories deterministically HOLD at the Authority boundary.
        separator = "&" if "?" in endpoint else "?"
        target = f"{endpoint}{separator}per_page=100&page=1"

        def one_read() -> tuple[int, list[dict[str, Any]]]:
            response = (
                self._request_absolute(target)
                if absolute
                else self._request("GET", target)
            )
            assert response is not None
            total = response.get("total_count")
            items = response.get(key)
            if (
                isinstance(total, bool)
                or not isinstance(total, int)
                or not (0 <= total <= 100)
                or not isinstance(items, list)
                or len(items) != total
            ):
                raise OutboxBlock(
                    "outbox authority inventory is not one complete bounded page"
                )
            return total, [
                dict(_mapping(item, "outbox authority inventory item"))
                for item in items
            ]

        first_total, first_values = one_read()
        second_total, values = one_read()
        if first_total != second_total or digest(first_values) != digest(values):
            raise OutboxBlock("outbox authority inventory changed during readback")
        names = [item.get("name") for item in values]
        if any(not isinstance(name, str) or not name for name in names):
            raise OutboxBlock("outbox authority inventory name is invalid")
        if len(set(names)) != len(names):
            raise OutboxBlock("outbox authority inventory is ambiguous")
        return values

    def _verify_authority_environment(self, lane: str) -> Mapping[str, Any]:
        """Verify the external environment/secret scope without reading values."""
        lane = _lane(lane)
        environment_name = urllib.parse.quote(AUTHORITY_ENVIRONMENT, safe="")
        environment = self._request("GET", f"environments/{environment_name}")
        assert environment is not None
        protection_rules = environment.get("protection_rules")
        branch_policy = _mapping(
            environment.get("deployment_branch_policy"),
            "outbox environment deployment policy",
        )
        branch_policies = self._complete_named_inventory(
            endpoint=f"environments/{environment_name}/deployment-branch-policies",
            key="branch_policies",
        )
        environment_secrets = self._complete_named_inventory(
            endpoint=f"environments/{environment_name}/secrets",
            key="secrets",
        )
        repository_secrets = self._complete_named_inventory(
            endpoint="actions/secrets", key="secrets"
        )
        repository_metadata = self._request_absolute(
            f"https://api.github.com/repos/{self.repository}"
        )
        owner = _mapping(repository_metadata.get("owner"), "outbox repository owner")
        expected_owner = self.repository.split("/", 1)[0]
        owner_login = owner.get("login")
        owner_type = owner.get("type")
        owner_id = _positive_int(owner.get("id"), "outbox repository owner id")
        if owner_login != expected_owner or owner_type not in {"User", "Organization"}:
            raise OutboxBlock("outbox repository owner identity is invalid")
        if owner_type == "Organization":
            organization = urllib.parse.quote(str(owner_login), safe="")
            organization_secrets = self._complete_named_inventory(
                endpoint=f"https://api.github.com/orgs/{organization}/actions/secrets",
                key="secrets",
                absolute=True,
            )
            organization_scope = "VERIFIED_ORGANIZATION_SECRET_INVENTORY"
        else:
            organization_secrets = []
            organization_scope = "NOT_APPLICABLE_USER_OWNER"
        environment_secret_names = {item["name"] for item in environment_secrets}
        repository_secret_names = {item["name"] for item in repository_secrets}
        organization_secret_names = {item["name"] for item in organization_secrets}
        exact_branch_policies = [
            {"name": item.get("name"), "type": item.get("type")}
            for item in branch_policies
        ]
        actor_id = writer_actor_id_from_environment()
        if (
            environment.get("name") != AUTHORITY_ENVIRONMENT
            or not isinstance(protection_rules, list)
            or not protection_rules
            or branch_policy.get("protected_branches") is not False
            or branch_policy.get("custom_branch_policies") is not True
            or exact_branch_policies != [{"name": "main", "type": "branch"}]
            or not {AUDITOR_SECRET_NAME, WRITER_SECRET_NAME}.issubset(
                environment_secret_names
            )
            or FORBIDDEN_FALLBACK_SECRET_NAMES & repository_secret_names
            or FORBIDDEN_FALLBACK_SECRET_NAMES & organization_secret_names
        ):
            raise OutboxBlock(
                "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED: protected "
                "main-only environment and exact secret scopes are required"
            )
        receipt = {
            "schema": AUTHORITY_READBACK_SCHEMA,
            "state": "VERIFIED_FOR_THIS_EFFECT_ONLY",
            "repository": self.repository,
            "lane": lane,
            "repository_owner": {
                "login": owner_login,
                "type": owner_type,
                "id": owner_id,
            },
            "environment": AUTHORITY_ENVIRONMENT,
            "deployment_branch": "main",
            "protection_rules_present": True,
            "environment_secret_names_present": [
                AUDITOR_SECRET_NAME,
                WRITER_SECRET_NAME,
            ],
            "repository_scope_fallback_names_absent": True,
            "organization_scope_fallback_names_absent": True,
            "organization_scope_readback": organization_scope,
            "writer_actor_id": actor_id,
            "secret_values_observed": False,
            "external_configuration_claimed_by_repository": False,
        }
        self.last_authority_readback = receipt
        return receipt

    def verify_authority_environment(self, lane: str) -> Mapping[str, Any]:
        """Return one effect-local proof or a deterministic Authority HOLD."""
        try:
            return self._verify_authority_environment(lane)
        except OutboxBlock as exc:
            detail = str(exc)
            if detail.startswith(
                "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED"
            ):
                raise
            raise OutboxBlock(
                "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED: " + detail
            ) from exc

    def _ref_head(self, api_ref: str, *, allow_not_found: bool) -> str | None:
        value = self._request(
            "GET", f"git/ref/{api_ref}", allow_not_found=allow_not_found
        )
        if value is None:
            return None
        obj = _mapping(value.get("object"), "GitHub ref object")
        return _sha(obj.get("sha"), "GitHub ref head")

    def get_ledger_head(self, lane: str) -> str | None:
        return self._ref_head(ledger_api_ref(lane), allow_not_found=True)

    def verify_ledger_protection(self, lane: str) -> None:
        branch = urllib.parse.quote(ledger_short_ref(lane), safe="")
        endpoint = f"rules/branches/{branch}?per_page=100&page=1"
        first_rules = self._request_list(endpoint)
        rules = self._request_list(endpoint)
        # The applied-rules endpoint has no declared total.  A full 100-item
        # page is therefore ambiguous (there may be another page), and any
        # change between the two complete reads is an Authority HOLD.
        if (
            len(first_rules) >= 100
            or len(rules) >= 100
            or digest(first_rules) != digest(rules)
        ):
            raise OutboxBlock(
                "OUTBOX_LEDGER_PROTECTION_NOT_VERIFIED: applied rule inventory "
                "is moving or exceeds one bounded page"
            )
        required_types = {"deletion", "non_fast_forward", "update"}
        authoritative_rules = [
            item
            for item in rules
            if isinstance(item, Mapping) and item.get("type") in required_types
        ]
        rule_types = {item.get("type") for item in authoritative_rules}
        ruleset_ids = {
            item.get("ruleset_id")
            for item in authoritative_rules
            if isinstance(item.get("ruleset_id"), int)
            and not isinstance(item.get("ruleset_id"), bool)
        }
        if not required_types.issubset(rule_types) or len(ruleset_ids) != 1:
            raise OutboxBlock(
                "OUTBOX_LEDGER_PROTECTION_NOT_VERIFIED: one exact active "
                "ruleset must restrict updates, deletion, and force pushes"
            )
        ruleset_id = next(iter(ruleset_ids))
        ruleset = self._request("GET", f"rulesets/{ruleset_id}")
        assert ruleset is not None
        bypass_actors = ruleset.get("bypass_actors")
        try:
            actor_id = writer_actor_id_from_environment()
        except OutboxBlock as exc:
            raise OutboxBlock(
                "OUTBOX_LEDGER_WRITER_IDENTITY_NOT_VERIFIED: dedicated GitHub "
                "App integration id is unavailable"
            ) from exc
        expected_bypass = [
            {
                "actor_id": actor_id,
                "actor_type": "Integration",
                "bypass_mode": "always",
            }
        ]
        conditions = _mapping(ruleset.get("conditions"), "outbox ruleset conditions")
        ref_name = _mapping(conditions.get("ref_name"), "outbox ref conditions")
        ruleset_rule_types = {
            item.get("type")
            for item in ruleset.get("rules", [])
            if isinstance(item, Mapping)
        }
        if (
            ruleset.get("id") != ruleset_id
            or ruleset.get("target") != "branch"
            or ruleset.get("source_type") != "Repository"
            or ruleset.get("source") != self.repository
            or ruleset.get("enforcement") != "active"
            or bypass_actors != expected_bypass
            or ref_name.get("include") != [ledger_ref(lane)]
            or ref_name.get("exclude") != []
            or not required_types.issubset(ruleset_rule_types)
        ):
            raise OutboxBlock(
                "OUTBOX_LEDGER_WRITER_IDENTITY_NOT_VERIFIED: exact active "
                "ref restriction and sole GitHub App bypass are required"
            )

    def verify_writer_scope(self, lane: str) -> None:
        expected = writer_concurrency_group(lane)
        if os.environ.get("QIKVRT_OUTBOX_WRITER_GROUP") != expected:
            raise OutboxBlock(
                "OUTBOX_LEDGER_WRITER_SCOPE_NOT_VERIFIED: exact lane writer "
                "concurrency declaration is required"
            )

    def get_main_head(self) -> str:
        value = self._ref_head("heads/main", allow_not_found=False)
        if value is None:
            raise OutboxBlock("main ref is unavailable")
        return value

    def read_file(self, commit: str, path: str) -> bytes | None:
        commit_sha = _sha(commit, "outbox read commit")
        if not isinstance(path, str) or not path or path.startswith("/"):
            raise OutboxBlock("outbox read path is invalid")
        encoded_path = urllib.parse.quote(path, safe="/")
        value = self._request(
            "GET",
            f"contents/{encoded_path}?ref={commit_sha}",
            allow_not_found=True,
        )
        if value is None:
            return None
        if value.get("type") != "file" or value.get("encoding") != "base64":
            raise OutboxBlock("outbox content response is not a base64 file")
        content = value.get("content")
        if not isinstance(content, str):
            raise OutboxBlock("outbox content bytes are absent")
        try:
            return base64.b64decode("".join(content.split()), validate=True)
        except (TypeError, ValueError) as exc:
            raise OutboxBlock("outbox content is not valid base64") from exc

    def _blob(self, content: bytes) -> str:
        value = self._request(
            "POST",
            "git/blobs",
            {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"},
        )
        assert value is not None
        return _sha(value.get("sha"), "outbox blob")

    def _tree(self, files: Mapping[str, bytes], *, base_tree: str | None) -> str:
        entries = []
        for path, content in sorted(files.items()):
            if not isinstance(path, str) or not path or path.startswith("/"):
                raise OutboxBlock("outbox write path is invalid")
            entries.append(
                {"path": path, "mode": "100644", "type": "blob", "sha": self._blob(content)}
            )
        payload: dict[str, Any] = {"tree": entries}
        if base_tree is not None:
            payload["base_tree"] = _sha(base_tree, "outbox base tree")
        value = self._request("POST", "git/trees", payload)
        assert value is not None
        return _sha(value.get("sha"), "outbox tree")

    def build_commit(
        self, parent: str, files: Mapping[str, bytes], message: str
    ) -> str:
        parent_sha = _sha(parent, "outbox parent")
        parent_value = self._request("GET", f"git/commits/{parent_sha}")
        assert parent_value is not None
        tree_obj = _mapping(parent_value.get("tree"), "outbox parent tree")
        tree = self._tree(files, base_tree=_sha(tree_obj.get("sha"), "parent tree"))
        value = self._request(
            "POST",
            "git/commits",
            {"message": message, "tree": tree, "parents": [parent_sha]},
        )
        assert value is not None
        return _sha(value.get("sha"), "outbox commit")

    def update_ledger_ref(self, lane: str, commit: str) -> None:
        self._request(
            "PATCH",
            f"git/refs/heads/{ledger_short_ref(lane)}",
            {"sha": _sha(commit, "outbox update commit"), "force": False},
        )


def _json_bytes(value: Any, label: str) -> bytes:
    try:
        return canonical_bytes(value)
    except (TypeError, ValueError) as exc:
        raise OutboxBlock(f"{label} is not canonical JSON") from exc


def _read_json(
    backend: LedgerBackend, commit: str, path: str, *, required: bool = True
) -> Mapping[str, Any] | None:
    raw = backend.read_file(_sha(commit, "outbox read head"), path)
    if raw is None:
        if required:
            raise OutboxBlock(f"required outbox path is absent: {path}")
        return None
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OutboxBlock(f"outbox path is not JSON: {path}") from exc
    return _mapping(value, f"outbox path {path}")


def _root_files(lane: str) -> dict[str, bytes]:
    lane = _lane(lane)
    values: dict[str, bytes] = {
        "ledger.json": canonical_bytes(
            {
                "schema": LEDGER_SCHEMA,
                "ref": ledger_ref(lane),
                "lane": lane,
                "force_updates": False,
                "deletion_allowed": False,
                "candidate_or_main_bytes": False,
                "external_genesis_required": True,
                "external_ref_protection_required": True,
                "external_dedicated_writer_required": True,
                "ordinary_contents_writer_bypass_allowed": False,
                "writer_concurrency_group": writer_concurrency_group(lane),
            }
        )
    }
    values[meta_path(lane)] = canonical_bytes(initial_meta(lane))
    return values


def ensure_initialized(backend: LedgerBackend, lane: str) -> str:
    lane = _lane(lane)
    backend.verify_authority_environment(lane)
    head = backend.get_ledger_head(lane)
    if head is None:
        raise OutboxBlock(
            "OUTBOX_LEDGER_GENESIS_MISSING: external Authority must create "
            "and protect the exact lane ref"
        )
    backend.verify_ledger_protection(lane)
    head = _sha(head, "outbox ledger head")
    manifest = _read_json(backend, head, "ledger.json")
    assert manifest is not None
    if (
        manifest.get("schema") != LEDGER_SCHEMA
        or manifest.get("ref") != ledger_ref(lane)
        or manifest.get("lane") != lane
        or manifest.get("force_updates") is not False
        or manifest.get("deletion_allowed") is not False
        or manifest.get("candidate_or_main_bytes") is not False
        or manifest.get("external_genesis_required") is not True
        or manifest.get("external_ref_protection_required") is not True
        or manifest.get("external_dedicated_writer_required") is not True
        or manifest.get("ordinary_contents_writer_bypass_allowed") is not False
        or manifest.get("writer_concurrency_group")
        != writer_concurrency_group(lane)
    ):
        raise OutboxBlock("outbox ledger manifest mismatch")
    meta = _read_json(backend, head, meta_path(lane))
    validate_meta(meta, lane)
    return head


def bounded_ff_cas(
    backend: LedgerBackend,
    *,
    lane: str,
    plan_at: Any,
    build_message: str,
    verify_at: Any,
    max_attempts: int = MAX_CAS_ATTEMPTS,
) -> dict[str, Any]:
    if (
        isinstance(max_attempts, bool)
        or not isinstance(max_attempts, int)
        or max_attempts < 1
        or max_attempts > 32
    ):
        raise OutboxBlock("outbox CAS retry bound is invalid")
    lane = _lane(lane)
    backend.verify_writer_scope(lane)
    ensure_initialized(backend, lane)
    for attempt in range(1, max_attempts + 1):
        parent = backend.get_ledger_head(lane)
        if parent is None:
            raise OutboxBlock("outbox ledger ref disappeared")
        parent = _sha(parent, "outbox CAS parent")
        changes = plan_at(parent)
        if changes is None:
            if not verify_at(parent):
                raise OutboxBlock("outbox CAS no-op readback mismatch")
            return {
                "schema": "qikvrt_ruleset_outbox_cas_v1",
                "persisted": True,
                "appended": False,
                "head": parent,
                "attempts": attempt,
                "force": False,
            }
        if not isinstance(changes, Mapping) or not changes:
            raise OutboxBlock("outbox CAS plan returned invalid changes")
        commit = backend.build_commit(parent, changes, build_message)
        try:
            backend.update_ledger_ref(lane, commit)
        except Exception:
            observed = backend.get_ledger_head(lane)
            if observed is None or observed == parent:
                raise
            time.sleep(min(0.01 * attempt, 0.20))
            continue
        observed = backend.get_ledger_head(lane)
        if observed is None:
            raise OutboxBlock("outbox CAS readback ref disappeared")
        observed = _sha(observed, "outbox CAS readback")
        if verify_at(observed):
            return {
                "schema": "qikvrt_ruleset_outbox_cas_v1",
                "persisted": True,
                "appended": True,
                "head": observed,
                "attempts": attempt,
                "force": False,
            }
        if observed == parent:
            raise OutboxBlock("outbox CAS update was not observable")
    raise OutboxBlock("outbox CAS retry bound exhausted")


def _validate_intent_record(value: Any, *, lane: str | None = None) -> dict[str, Any]:
    raw = _mapping(value, "outbox intent record")
    record_lane = _lane(raw.get("lane"))
    if lane is not None and record_lane != _lane(lane):
        raise OutboxBlock("outbox intent record lane mismatch")
    sequence = _sequence(raw.get("sequence"))
    payload = validate_payload(raw.get("payload"), lane=record_lane)
    payload_bytes = canonical_bytes(payload)
    payload_sha = sha256_bytes(payload_bytes)
    artifact = validate_artifact(
        raw.get("artifact"),
        payload_sha256=payload_sha,
        producer=_mapping(payload.get("producer"), "intent producer"),
    )
    # The semantic fingerprint is the sealed request/subject payload.  Artifact
    # metadata is still immutable evidence in the intent record, but a later
    # producer retry cannot enqueue the same subject twice merely because its
    # upload received a different artifact id/archive digest.
    work_unit = semantic_work_unit(payload)
    fingerprint = digest(work_unit)
    if record_lane in REVIEW_TRANSPORT_LANES:
        request_inputs = _mapping(
            _mapping(payload.get("request"), "review intent request").get("inputs"),
            "review intent inputs",
        )
        if (
            request_inputs.get("transport_intent_sha256") != fingerprint
            or request_inputs.get("transport_attempt") != "1"
        ):
            raise OutboxBlock("review intent transport locator mismatch")
    if (
        raw.get("schema") != INTENT_SCHEMA
        or raw.get("repository") != payload["repository"]
        or raw.get("fingerprint") != fingerprint
        or raw.get("work_unit_sha256") != fingerprint
        or raw.get("payload_sha256") != payload_sha
        or raw.get("state") != "SEALED"
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("outbox intent record digest/binding mismatch")
    return {
        "schema": INTENT_SCHEMA,
        "repository": payload["repository"],
        "lane": record_lane,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "work_unit_sha256": fingerprint,
        "payload_sha256": payload_sha,
        "payload": payload,
        "artifact": artifact,
        "state": "SEALED",
        "productive_effect": False,
    }


def _read_intent_by_fingerprint(
    backend: LedgerBackend, head: str, lane: str, fingerprint: str
) -> dict[str, Any] | None:
    locator_value = _read_json(
        backend, head, locator_path(lane, fingerprint), required=False
    )
    if locator_value is None:
        return None
    locator = _mapping(locator_value, "outbox fingerprint locator")
    sequence = _sequence(locator.get("sequence"))
    expected_path = intent_path(lane, sequence, fingerprint)
    if (
        locator.get("schema") != LOCATOR_SCHEMA
        or locator.get("lane") != lane
        or locator.get("fingerprint") != fingerprint
        or locator.get("intent_path") != expected_path
    ):
        raise OutboxBlock("outbox fingerprint locator mismatch")
    record_value = _read_json(backend, head, expected_path)
    record = _validate_intent_record(record_value, lane=lane)
    if record["sequence"] != sequence or record["fingerprint"] != fingerprint:
        raise OutboxBlock("outbox locator and intent differ")
    return record


def append_intent(
    backend: LedgerBackend,
    *,
    payload: Mapping[str, Any],
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_payload = validate_payload(payload)
    lane = normalized_payload["lane"]
    payload_sha = sha256_bytes(canonical_bytes(normalized_payload))
    normalized_artifact = validate_artifact(
        artifact,
        payload_sha256=payload_sha,
        producer=_mapping(normalized_payload.get("producer"), "outbox producer"),
    )
    if backend.get_main_head() != normalized_payload["main_head_sha"]:
        raise OutboxBlock("outbox producer main head is no longer current")
    work_unit = semantic_work_unit(normalized_payload)
    fingerprint = digest(work_unit)
    witness = _witness_record(normalized_payload, normalized_artifact, fingerprint)
    witness_record_path = witness_path(
        lane,
        fingerprint,
        witness["producer"]["run_id"],
        witness["producer"]["run_attempt"],
    )
    if lane in REVIEW_TRANSPORT_LANES:
        request_inputs = _mapping(
            _mapping(
                normalized_payload.get("request"), "review outbox request"
            ).get("inputs"),
            "review outbox inputs",
        )
        if (
            request_inputs.get("transport_intent_sha256") != fingerprint
            or request_inputs.get("transport_attempt") != "1"
        ):
            raise OutboxBlock("review outbox payload is not sealed for attempt one")
    plans: dict[str, Mapping[str, bytes] | None] = {}

    def plan_at(parent: str) -> Mapping[str, bytes] | None:
        existing = _read_intent_by_fingerprint(backend, parent, lane, fingerprint)
        if existing is not None:
            if semantic_work_unit(existing["payload"]) != work_unit:
                raise OutboxBlock("content-addressed outbox intent collision")
            terminal = _read_json(
                backend,
                parent,
                terminal_path(lane, existing["sequence"]),
                required=False,
            )
            if terminal is not None:
                # A terminal semantic work unit is already closed.  A later
                # producer rerun is idempotent and must not grow witness state.
                plans[parent] = None
                return None
            if any(
                _read_json(
                    backend,
                    parent,
                    transport_path(lane, existing["sequence"], attempt),
                    required=False,
                )
                is not None
                for attempt in (1, 2)
            ):
                # Once an exact pre-effect transport selected a witness, later
                # producer reruns cannot improve that transport and therefore
                # must not grow the immutable ledger.
                plans[parent] = None
                return None
            index_path = witness_index_path(lane, fingerprint)
            index = dict(
                _mapping(
                    _read_json(backend, parent, index_path),
                    "outbox witness index",
                )
            )
            entries = index.get("entries")
            if (
                index.get("schema") != WITNESS_INDEX_SCHEMA
                or index.get("lane") != lane
                or index.get("fingerprint") != fingerprint
                or isinstance(index.get("page"), bool)
                or not isinstance(index.get("page"), int)
                or index.get("page", 0) < 1
                or isinstance(index.get("next_ordinal"), bool)
                or not isinstance(index.get("next_ordinal"), int)
                or index.get("next_ordinal", 0) < 2
                or not isinstance(entries, list)
            ):
                raise OutboxBlock("outbox witness index binding mismatch")
            existing_raw = backend.read_file(parent, witness_record_path)
            witness_raw = canonical_bytes(witness)
            if existing_raw is not None:
                if existing_raw != witness_raw:
                    raise OutboxBlock("immutable outbox witness collision")
                plans[parent] = None
                return None
            if len(entries) >= MAX_ACTIVE_WITNESSES:
                raise OutboxBlock(
                    "OUTBOX_WITNESS_BOUND_EXHAUSTED: Authority must inspect "
                    "the bounded producer witness set"
                )
            entry = {
                "producer_run_id": witness["producer"]["run_id"],
                "producer_run_attempt": witness["producer"]["run_attempt"],
                "path": witness_record_path,
                "witness_sha256": witness["witness_sha256"],
                "ordinal": index["next_ordinal"],
            }
            next_index = {
                **index,
                "next_ordinal": index["next_ordinal"] + 1,
                "entries": [*entries, entry],
            }
            changes = {
                witness_record_path: witness_raw,
                index_path: canonical_bytes(next_index),
            }
            plans[parent] = changes
            return changes
        meta = validate_meta(_read_json(backend, parent, meta_path(lane)), lane)
        sequence = meta["next_seq"]
        if _read_json(backend, parent, slot_path(lane, sequence), required=False):
            raise OutboxBlock("outbox FIFO slot collision")
        record = {
            "schema": INTENT_SCHEMA,
            "repository": normalized_payload["repository"],
            "lane": lane,
            "sequence": sequence,
            "fingerprint": fingerprint,
            "work_unit_sha256": fingerprint,
            "payload_sha256": payload_sha,
            "payload": normalized_payload,
            "artifact": normalized_artifact,
            "state": "SEALED",
            "productive_effect": False,
        }
        record_path = intent_path(lane, sequence, fingerprint)
        slot = {
            "schema": SLOT_SCHEMA,
            "lane": lane,
            "sequence": sequence,
            "fingerprint": fingerprint,
            "intent_path": record_path,
            "intent_sha256": digest(record),
        }
        locator = {
            "schema": LOCATOR_SCHEMA,
            "lane": lane,
            "sequence": sequence,
            "fingerprint": fingerprint,
            "intent_path": record_path,
        }
        next_meta = {**meta, "next_seq": sequence + 1}
        witness_index = {
            "schema": WITNESS_INDEX_SCHEMA,
            "lane": lane,
            "fingerprint": fingerprint,
            "page": 1,
            "next_ordinal": 2,
            "entries": [
                {
                    "producer_run_id": witness["producer"]["run_id"],
                    "producer_run_attempt": witness["producer"]["run_attempt"],
                    "path": witness_record_path,
                    "witness_sha256": witness["witness_sha256"],
                    "ordinal": 1,
                }
            ],
        }
        changes = {
            meta_path(lane): canonical_bytes(next_meta),
            slot_path(lane, sequence): canonical_bytes(slot),
            record_path: canonical_bytes(record),
            locator_path(lane, fingerprint): canonical_bytes(locator),
            witness_record_path: canonical_bytes(witness),
            witness_index_path(lane, fingerprint): canonical_bytes(witness_index),
        }
        plans[parent] = changes
        return changes

    def verify_at(head: str) -> bool:
        persisted = _read_intent_by_fingerprint(backend, head, lane, fingerprint)
        if persisted is None:
            return False
        terminal = _read_json(
            backend,
            head,
            terminal_path(lane, persisted["sequence"]),
            required=False,
        )
        if terminal is not None:
            return True
        if any(
            _read_json(
                backend,
                head,
                transport_path(lane, persisted["sequence"], attempt),
                required=False,
            )
            is not None
            for attempt in (1, 2)
        ):
            # Once a transport has selected and sealed one exact witness,
            # later producer reruns are intentionally idempotent.  They do
            # not need (and must not append) another witness merely to make
            # this no-op readback succeed.
            return True
        return backend.read_file(head, witness_record_path) == canonical_bytes(witness)

    cas = bounded_ff_cas(
        backend,
        lane=lane,
        plan_at=plan_at,
        build_message=f"Append {lane} outbox intent {fingerprint}",
        verify_at=verify_at,
    )
    record = _read_intent_by_fingerprint(backend, cas["head"], lane, fingerprint)
    if record is None:
        raise OutboxBlock("persisted outbox intent disappeared")
    witnesses = _read_witnesses(backend, cas["head"], lane, fingerprint)
    return {
        **record,
        "witnesses": witnesses,
        "ledger_ref": ledger_ref(lane),
        "ledger_head": cas["head"],
        "cas": cas,
    }


def _normalize_transport_actor(
    value: Any, *, intent: Mapping[str, Any]
) -> dict[str, Any]:
    raw = dict(_mapping(value, "outbox transport actor"))
    expected_keys = {
        "workflow_path",
        "workflow_sha",
        "workflow_id",
        "run_id",
        "run_attempt",
        "event",
        "status",
        "conclusion",
        "created_at",
        "updated_at",
    }
    timestamp = re.compile(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    )
    workflow_path = raw.get("workflow_path")
    created_at = raw.get("created_at")
    updated_at = raw.get("updated_at")
    payload = _mapping(intent.get("payload"), "transport actor intent payload")
    actor = {
        "workflow_path": workflow_path,
        "workflow_sha": _sha(raw.get("workflow_sha"), "transport actor workflow sha"),
        "workflow_id": _positive_int(
            raw.get("workflow_id"), "transport actor workflow id"
        ),
        "run_id": _positive_int(raw.get("run_id"), "transport actor run id"),
        "run_attempt": _positive_int(
            raw.get("run_attempt"), "transport actor run attempt"
        ),
        "event": raw.get("event"),
        "status": raw.get("status"),
        "conclusion": raw.get("conclusion"),
        "created_at": created_at,
        "updated_at": updated_at,
    }
    lane = _lane(intent.get("lane"))
    target = _mapping(payload.get("target"), "transport actor target")
    ordinary_actor = (
        lane != "mesh-review-successor-dispatch"
        and workflow_path in TRANSPORT_ACTOR_EVENTS
        and actor["event"] in TRANSPORT_ACTOR_EVENTS[workflow_path]
    )
    mesh_actor = (
        lane == "mesh-review-successor-dispatch"
        and workflow_path in MESH_TRANSPORT_ACTOR_EVENTS
        and actor["event"] in MESH_TRANSPORT_ACTOR_EVENTS[workflow_path]
        and actor["workflow_id"] == target.get("workflow_id")
    )
    if (
        set(raw) != expected_keys
        or not (ordinary_actor or mesh_actor)
        or actor["workflow_sha"] != payload.get("main_head_sha")
        or actor["status"] != "completed"
        or actor["conclusion"] not in TERMINAL_RUN_CONCLUSIONS
        or not isinstance(created_at, str)
        or timestamp.fullmatch(created_at) is None
        or not isinstance(updated_at, str)
        or timestamp.fullmatch(updated_at) is None
        or created_at > updated_at
    ):
        raise OutboxBlock("outbox retry actor is not exact terminal provenance")
    return actor


def validate_retry_scan_cursor_record(
    value: Any,
    *,
    intent: Mapping[str, Any],
    transport: Mapping[str, Any],
) -> dict[str, Any]:
    raw = dict(_mapping(value, "retry scan cursor record"))
    cursor = dict(_mapping(raw.get("cursor"), "retry scan cursor"))
    lane = _lane(intent.get("lane"))
    sequence = _sequence(intent.get("sequence"))
    fingerprint = _digest(intent.get("fingerprint"), "retry cursor fingerprint")
    attempt = cursor.get("transport_attempt")
    if attempt != 1:
        raise OutboxBlock("retry scan cursor binds the one-shot transport")
    actor = _normalize_transport_actor(cursor.get("transport_actor"), intent=intent)
    producer = _normalize_authority_observer(
        cursor.get("observation_producer"), intent=intent
    )
    timestamp = re.compile(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    )
    start = cursor.get("query_window_start")
    end = cursor.get("query_window_end")
    observed_start = cursor.get("observation_started_at")
    observed_end = cursor.get("observation_completed_at")
    ordinal = cursor.get("ordinal")
    upper_run_id = cursor.get("upper_bound_run_id")
    last_run_id = cursor.get("last_scanned_run_id")
    next_page = cursor.get("next_page")
    page_cap = cursor.get("page_cap")
    pages_scanned = cursor.get("pages_scanned")
    declared_total_count = cursor.get("declared_total_count")
    queried_page = cursor.get("queried_page")
    raw_page_run_ids = cursor.get("page_run_ids")
    raw_cumulative_run_ids = cursor.get("cumulative_run_ids")
    raw_page_candidate_run_ids = cursor.get("page_candidate_run_ids")
    raw_cumulative_candidate_run_ids = cursor.get(
        "cumulative_candidate_run_ids"
    )
    observed_unique_run_count = cursor.get("observed_unique_run_count")
    inventory_consistent = cursor.get("inventory_consistent")
    inventory_blocker = cursor.get("inventory_blocker")
    candidates_seen = cursor.get("candidates_seen")
    successor_count = cursor.get("bound_successor_count")
    for numeric_value, label, minimum in (
        (ordinal, "ordinal", 1),
        (upper_run_id, "upper-bound run id", 0),
        (last_run_id, "last-scanned run id", 0),
        (page_cap, "page cap", 1),
        (pages_scanned, "pages scanned", 0),
        (candidates_seen, "candidates seen", 0),
        (successor_count, "bound successor count", 0),
    ):
        if (
            isinstance(numeric_value, bool)
            or not isinstance(numeric_value, int)
            or numeric_value < minimum
        ):
            raise OutboxBlock(f"retry scan cursor {label} is invalid")
    if page_cap > 100:
        raise OutboxBlock("retry scan cursor page cap is invalid")
    raw_candidates = cursor.get("candidate_locators")
    normalized_candidates = (
        [
            normalize_child_for_intent(
                _mapping(item, "retry scan candidate locator"),
                intent=intent,
                attempt=attempt,
            )
            for item in raw_candidates
        ]
        if isinstance(raw_candidates, list)
        else []
    )
    cursor_keys = {
        "schema",
        "lane",
        "sequence",
        "fingerprint",
        "transport_attempt",
        "transport_request_sha256",
        "ordinal",
        "previous_cursor_sha256",
        "transport_actor",
        "transport_actor_sha256",
        "observation_producer",
        "observation_producer_sha256",
        "target_workflow_id",
        "query_window_start",
        "query_window_end",
        "observation_started_at",
        "observation_completed_at",
        "upper_bound_run_id",
        "last_scanned_run_id",
        "next_page",
        "page_cap",
        "pages_scanned",
        "declared_total_count",
        "queried_page",
        "page_run_ids",
        "page_run_ids_sha256",
        "cumulative_run_ids",
        "cumulative_run_ids_sha256",
        "page_candidate_run_ids",
        "page_candidate_run_ids_sha256",
        "cumulative_candidate_run_ids",
        "cumulative_candidate_run_ids_sha256",
        "observed_unique_run_count",
        "inventory_consistent",
        "inventory_blocker",
        "candidates_seen",
        "candidate_locators",
        "candidate_set_sha256",
        "bound_successor_count",
        "same_second_boundary_complete",
        "scan_complete",
        "verified",
        "productive_effect",
    }
    target = _mapping(
        _mapping(intent.get("payload"), "retry cursor payload").get("target"),
        "retry cursor target",
    )
    if (
        set(cursor) != cursor_keys
        or cursor.get("schema") != RETRY_SCAN_CURSOR_SCHEMA
        or cursor.get("lane") != lane
        or cursor.get("sequence") != sequence
        or cursor.get("fingerprint") != fingerprint
        or cursor.get("transport_request_sha256") != transport.get("request_sha256")
        or actor["run_id"] != transport.get("actor_run_id")
        or actor["run_attempt"] != transport.get("actor_run_attempt")
        or cursor.get("transport_actor_sha256") != digest(actor)
        or cursor.get("observation_producer_sha256") != digest(producer)
        or cursor.get("target_workflow_id") != target.get("workflow_id")
        or any(
            not isinstance(value, str) or timestamp.fullmatch(value) is None
            for value in (start, end, observed_start, observed_end)
        )
        or start > actor["created_at"]
        or end < actor["updated_at"]
        or end > observed_start
        or observed_start > observed_end
        or isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or ordinal > page_cap + 1
        or isinstance(upper_run_id, bool)
        or not isinstance(upper_run_id, int)
        or upper_run_id < 0
        or isinstance(last_run_id, bool)
        or not isinstance(last_run_id, int)
        or last_run_id < 0
        or (
            last_run_id > upper_run_id
            and not (
                inventory_consistent is False
                and inventory_blocker == "PAGE_RUN_ID_ORDER_DRIFT"
            )
        )
        or (
            next_page is not None
            and (
                isinstance(next_page, bool)
                or not isinstance(next_page, int)
                or next_page < 1
            )
        )
        or isinstance(page_cap, bool)
        or not isinstance(page_cap, int)
        or not (1 <= page_cap <= 100)
        or (next_page is not None and next_page > page_cap + 1)
        or isinstance(pages_scanned, bool)
        or not isinstance(pages_scanned, int)
        or not (0 <= pages_scanned <= page_cap)
        or isinstance(candidates_seen, bool)
        or not isinstance(candidates_seen, int)
        or candidates_seen < 0
        or not isinstance(raw_page_run_ids, list)
        or len(raw_page_run_ids) > 100
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 1
            for item in raw_page_run_ids
        )
        or (
            raw_page_run_ids != sorted(set(raw_page_run_ids), reverse=True)
            and not (
                inventory_consistent is False
                and inventory_blocker
                in {"PAGE_RUN_ID_DUPLICATE", "PAGE_RUN_ID_PAGE_ORDER_DRIFT"}
            )
        )
        or cursor.get("page_run_ids_sha256") != digest(raw_page_run_ids)
        or not isinstance(raw_cumulative_run_ids, list)
        or len(raw_cumulative_run_ids) > page_cap * 100
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 1
            for item in raw_cumulative_run_ids
        )
        or raw_cumulative_run_ids
        != sorted(set(raw_cumulative_run_ids), reverse=True)
        or not set(raw_page_run_ids).issubset(raw_cumulative_run_ids)
        or cursor.get("cumulative_run_ids_sha256")
        != digest(raw_cumulative_run_ids)
        or not isinstance(raw_page_candidate_run_ids, list)
        or raw_page_candidate_run_ids
        != sorted(set(raw_page_candidate_run_ids), reverse=True)
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 1
            for item in raw_page_candidate_run_ids
        )
        or not set(raw_page_candidate_run_ids).issubset(raw_page_run_ids)
        or cursor.get("page_candidate_run_ids_sha256")
        != digest(raw_page_candidate_run_ids)
        or not isinstance(raw_cumulative_candidate_run_ids, list)
        or raw_cumulative_candidate_run_ids
        != sorted(set(raw_cumulative_candidate_run_ids), reverse=True)
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 1
            for item in raw_cumulative_candidate_run_ids
        )
        or not set(raw_cumulative_candidate_run_ids).issubset(
            raw_cumulative_run_ids
        )
        or cursor.get("cumulative_candidate_run_ids_sha256")
        != digest(raw_cumulative_candidate_run_ids)
        or isinstance(observed_unique_run_count, bool)
        or not isinstance(observed_unique_run_count, int)
        or observed_unique_run_count != len(raw_cumulative_run_ids)
        or candidates_seen != len(raw_cumulative_candidate_run_ids)
        or successor_count != len(raw_cumulative_candidate_run_ids)
        or (
            any(item > upper_run_id for item in raw_cumulative_run_ids)
            and not (
                inventory_consistent is False
                and inventory_blocker == "PAGE_RUN_ID_ORDER_DRIFT"
            )
        )
        or not isinstance(inventory_consistent, bool)
        or successor_count > candidates_seen
        or not isinstance(raw_candidates, list)
        or len(normalized_candidates) > 8
        or normalized_candidates
        != sorted(normalized_candidates, key=lambda item: item["run_id"], reverse=True)
        or len({item["run_id"] for item in normalized_candidates})
        != len(normalized_candidates)
        or not {
            item["run_id"] for item in normalized_candidates
        }.issubset(raw_cumulative_candidate_run_ids)
        or (
            successor_count <= 8
            and (
                len(normalized_candidates) != successor_count
                or sorted(
                    [item["run_id"] for item in normalized_candidates],
                    reverse=True,
                )
                != raw_cumulative_candidate_run_ids
                or cursor.get("candidate_set_sha256")
                != digest(normalized_candidates)
            )
        )
        or (
            successor_count > 8
            and (
                len(normalized_candidates) != 8
                or cursor.get("candidate_set_sha256")
                != digest(raw_cumulative_candidate_run_ids)
            )
        )
        or HEX64.fullmatch(str(cursor.get("candidate_set_sha256"))) is None
        or isinstance(successor_count, bool)
        or not isinstance(successor_count, int)
        or successor_count < 0
        or not isinstance(cursor.get("same_second_boundary_complete"), bool)
        or not isinstance(cursor.get("scan_complete"), bool)
        or (
            cursor.get("same_second_boundary_complete") is False
            and (
                cursor.get("scan_complete") is not False
                or ordinal != 1
                or cursor.get("previous_cursor_sha256") is not None
                or next_page != 1
                or pages_scanned != 0
                or declared_total_count is not None
                or queried_page is not None
                or raw_page_run_ids
                or raw_cumulative_run_ids
                or raw_page_candidate_run_ids
                or raw_cumulative_candidate_run_ids
                or observed_unique_run_count != 0
                or inventory_consistent is not True
                or inventory_blocker is not None
                or candidates_seen != 0
                or successor_count != 0
                or normalized_candidates
            )
        )
        or (
            cursor.get("same_second_boundary_complete") is True
            and (
                isinstance(declared_total_count, bool)
                or not isinstance(declared_total_count, int)
                or declared_total_count < 0
                or isinstance(queried_page, bool)
                or not isinstance(queried_page, int)
                or not (1 <= queried_page <= page_cap)
                or pages_scanned != queried_page
                or (
                    inventory_consistent is True
                    and (
                        inventory_blocker is not None
                        or observed_unique_run_count > declared_total_count
                        or cursor.get("scan_complete")
                        is not (
                            observed_unique_run_count == declared_total_count
                        )
                        or (
                            cursor.get("scan_complete") is False
                            and len(raw_page_run_ids) < 100
                        )
                        or (
                            cursor.get("scan_complete") is True
                            and next_page is not None
                        )
                        or (
                            cursor.get("scan_complete") is False
                            and pages_scanned < page_cap
                            and next_page != queried_page + 1
                        )
                        or (
                            cursor.get("scan_complete") is False
                            and pages_scanned == page_cap
                            and next_page is not None
                        )
                    )
                )
                or (
                    inventory_consistent is False
                    and (
                        inventory_blocker not in RETRY_SCAN_INVENTORY_BLOCKERS
                        or cursor.get("scan_complete") is not False
                        or next_page is not None
                    )
                )
            )
        )
        or (
            cursor.get("scan_complete") is True
            and (
                cursor.get("same_second_boundary_complete") is not True
                or next_page is not None
            )
        )
        or cursor.get("verified") is not True
        or cursor.get("productive_effect") is not False
    ):
        raise OutboxBlock("retry scan cursor binding mismatch")
    cursor_sha = digest(cursor)
    artifact = validate_artifact(
        raw.get("artifact"),
        payload_sha256=sha256_bytes(canonical_bytes(cursor)),
        producer=producer,
    )
    expected_name = (
        f"qikvrt-outbox-retry-scan-cursor-{lane}-{sequence}-attempt-{attempt}-"
        f"ordinal-{ordinal}-run-{producer['run_id']}-attempt-{producer['run_attempt']}"
    )
    state = (
        "BOUNDARY_STABILIZATION_REOBSERVE"
        if cursor["same_second_boundary_complete"] is False
        else (
            "SCAN_INVENTORY_INCONSISTENT_AUTHORITY"
            if cursor["inventory_consistent"] is False
            else (
                "AMBIGUITY_SET_EXCEEDED_AUTHORITY"
                if successor_count > 8
                else (
                    "COMPLETE_ZERO_SUCCESSOR"
                    if cursor["scan_complete"] and successor_count == 0
                    else (
                        "COMPLETE_SUCCESSOR_OBSERVED"
                        if cursor["scan_complete"]
                        else (
                            "SCAN_BOUND_EXCEEDED_AUTHORITY"
                            if pages_scanned == page_cap
                            else "SCAN_INCOMPLETE_REOBSERVE"
                        )
                    )
                )
            )
        )
    )
    if (
        set(raw)
        != {
            "schema",
            "lane",
            "sequence",
            "fingerprint",
            "transport_attempt",
            "cursor",
            "cursor_sha256",
            "artifact",
            "state",
            "productive_effect",
        }
        or raw.get("schema") != RETRY_SCAN_CURSOR_RECORD_SCHEMA
        or raw.get("lane") != lane
        or raw.get("sequence") != sequence
        or raw.get("fingerprint") != fingerprint
        or raw.get("transport_attempt") != attempt
        or raw.get("cursor_sha256") != cursor_sha
        or artifact.get("name") != expected_name
        or raw.get("state") != state
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("retry scan cursor record binding mismatch")
    return {
        "schema": RETRY_SCAN_CURSOR_RECORD_SCHEMA,
        "lane": lane,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "transport_attempt": attempt,
        "cursor": {
            **cursor,
            "transport_actor": actor,
            "observation_producer": producer,
            "candidate_locators": normalized_candidates,
        },
        "cursor_sha256": cursor_sha,
        "artifact": artifact,
        "state": state,
        "productive_effect": False,
    }


def _validate_retry_cursor_transition(
    current: Mapping[str, Any] | None,
    candidate: Mapping[str, Any],
) -> None:
    cursor = _mapping(candidate.get("cursor"), "candidate retry cursor")
    if current is None:
        if cursor.get("ordinal") != 1 or cursor.get("previous_cursor_sha256") is not None:
            raise OutboxBlock("first retry scan cursor must start at ordinal one")
        if cursor.get("same_second_boundary_complete") is True:
            page_run_ids = list(cursor.get("page_run_ids", []))
            first_blockers = []
            if len(page_run_ids) != len(set(page_run_ids)):
                first_blockers.append("PAGE_RUN_ID_DUPLICATE")
            elif page_run_ids != sorted(page_run_ids, reverse=True):
                first_blockers.append("PAGE_RUN_ID_PAGE_ORDER_DRIFT")
            if (
                cursor.get("queried_page") != 1
                or cursor.get("pages_scanned") != 1
            ):
                first_blockers.append("PAGE_SEQUENCE_DRIFT")
            if (
                cursor.get("observed_unique_run_count")
                > cursor.get("declared_total_count")
            ):
                first_blockers.append(
                    "OBSERVED_COUNT_EXCEEDS_DECLARED_TOTAL"
                )
            if (
                len(page_run_ids) < 100
                and cursor.get("observed_unique_run_count")
                < cursor.get("declared_total_count")
            ):
                first_blockers.append(
                    "SHORT_PAGE_BEFORE_DECLARED_TOTAL"
                )
            expected_blocker = first_blockers[0] if first_blockers else None
            if (
                cursor.get("cumulative_run_ids")
                != sorted(set(page_run_ids), reverse=True)
                or cursor.get("cumulative_candidate_run_ids")
                != cursor.get("page_candidate_run_ids")
                or (
                    cursor.get("inventory_consistent") is True
                    and expected_blocker is not None
                )
                or (
                    cursor.get("inventory_consistent") is False
                    and cursor.get("inventory_blocker") != expected_blocker
                )
            ):
                raise OutboxBlock(
                    "first retry scan cursor inventory is not exact"
                )
        return
    prior_cursor = _mapping(current.get("cursor"), "current retry cursor")
    immutable = (
        "lane",
        "sequence",
        "fingerprint",
        "transport_attempt",
        "transport_request_sha256",
        "transport_actor_sha256",
        "target_workflow_id",
        "query_window_start",
        "page_cap",
    )
    prior_boundary = prior_cursor.get("same_second_boundary_complete") is True
    candidate_boundary = cursor.get("same_second_boundary_complete") is True
    prior_candidates = {
        digest(dict(item))
        for item in prior_cursor.get("candidate_locators", [])
    }
    candidate_candidates = {
        digest(dict(item)) for item in cursor.get("candidate_locators", [])
    }
    prior_count = prior_cursor.get("bound_successor_count")
    candidate_count = cursor.get("bound_successor_count")
    prior_run_ids = list(prior_cursor.get("cumulative_run_ids", []))
    page_run_ids = list(cursor.get("page_run_ids", []))
    candidate_run_ids = list(cursor.get("cumulative_run_ids", []))
    exact_union = sorted(set(prior_run_ids) | set(page_run_ids), reverse=True)
    prior_candidate_run_ids = list(
        prior_cursor.get("cumulative_candidate_run_ids", [])
    )
    page_candidate_run_ids = list(cursor.get("page_candidate_run_ids", []))
    candidate_candidate_run_ids = list(
        cursor.get("cumulative_candidate_run_ids", [])
    )
    exact_candidate_union = sorted(
        set(prior_candidate_run_ids) | set(page_candidate_run_ids),
        reverse=True,
    )
    expected_page = (
        1
        if not prior_boundary
        else int(prior_cursor.get("queried_page")) + 1
    )
    expected_pages_scanned = prior_cursor.get("pages_scanned") + 1
    derived_inventory_blockers: list[str] = []
    if len(page_run_ids) != len(set(page_run_ids)):
        derived_inventory_blockers.append("PAGE_RUN_ID_DUPLICATE")
    elif page_run_ids != sorted(page_run_ids, reverse=True):
        derived_inventory_blockers.append("PAGE_RUN_ID_PAGE_ORDER_DRIFT")
    if (
        prior_boundary
        and cursor.get("declared_total_count")
        != prior_cursor.get("declared_total_count")
    ):
        derived_inventory_blockers.append("DECLARED_TOTAL_CHANGED")
    if (
        cursor.get("queried_page") != expected_page
        or cursor.get("pages_scanned") != expected_pages_scanned
    ):
        derived_inventory_blockers.append("PAGE_SEQUENCE_DRIFT")
    if set(page_run_ids) & set(prior_run_ids):
        derived_inventory_blockers.append("PAGE_RUN_ID_OVERLAP")
    if (
        page_run_ids
        and (
            (
                prior_run_ids
                and max(page_run_ids) >= min(prior_run_ids)
            )
            or (
                prior_boundary
                and max(page_run_ids)
                > prior_cursor.get("upper_bound_run_id")
            )
        )
    ):
        derived_inventory_blockers.append("PAGE_RUN_ID_ORDER_DRIFT")
    if (
        cursor.get("observed_unique_run_count")
        > cursor.get("declared_total_count")
    ):
        derived_inventory_blockers.append(
            "OBSERVED_COUNT_EXCEEDS_DECLARED_TOTAL"
        )
    if (
        len(page_run_ids) < 100
        and cursor.get("observed_unique_run_count")
        < cursor.get("declared_total_count")
    ):
        derived_inventory_blockers.append(
            "SHORT_PAGE_BEFORE_DECLARED_TOTAL"
        )
    expected_inventory_blocker = (
        derived_inventory_blockers[0] if derived_inventory_blockers else None
    )
    if (
        current.get("state")
        not in {"BOUNDARY_STABILIZATION_REOBSERVE", "SCAN_INCOMPLETE_REOBSERVE"}
        or any(cursor.get(key) != prior_cursor.get(key) for key in immutable)
        or cursor.get("ordinal") != prior_cursor.get("ordinal") + 1
        or cursor.get("previous_cursor_sha256") != digest(dict(current))
        or (
            prior_boundary
            and cursor.get("query_window_end")
            != prior_cursor.get("query_window_end")
        )
        or (
            not prior_boundary
            and (
                cursor.get("query_window_end")
                < prior_cursor.get("query_window_end")
                or cursor.get("query_window_end")
                != cursor.get("observation_started_at")
            )
        )
        or (
            prior_boundary
            and cursor.get("upper_bound_run_id")
            != prior_cursor.get("upper_bound_run_id")
        )
        or (
            not prior_boundary
            and cursor.get("upper_bound_run_id")
            < prior_cursor.get("upper_bound_run_id")
        )
        or (prior_boundary and not candidate_boundary)
        or (
            not prior_boundary
            and not candidate_boundary
        )
        or candidate_run_ids != exact_union
        or candidate_candidate_run_ids != exact_candidate_union
        or cursor.get("observed_unique_run_count") != len(exact_union)
        or cursor.get("observation_started_at")
        < prior_cursor.get("observation_completed_at")
        or (
            page_run_ids
            and cursor.get("last_scanned_run_id") != min(page_run_ids)
        )
        or (
            not page_run_ids
            and cursor.get("last_scanned_run_id")
            != prior_cursor.get("last_scanned_run_id")
        )
        or cursor.get("candidates_seen") < prior_cursor.get("candidates_seen")
        or cursor.get("bound_successor_count")
        < prior_cursor.get("bound_successor_count")
        or not prior_candidates.issubset(candidate_candidates)
        or (
            candidate_count > 8
            and candidate_count > prior_count
            and cursor.get("candidate_set_sha256")
            == prior_cursor.get("candidate_set_sha256")
        )
        or (
            cursor.get("inventory_consistent") is True
            and expected_inventory_blocker is not None
        )
        or (
            cursor.get("inventory_consistent") is False
            and cursor.get("inventory_blocker")
            != expected_inventory_blocker
        )
    ):
        raise OutboxBlock("retry scan cursor is not a monotone continuation")


def record_retry_scan_cursor(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    cursor: Mapping[str, Any],
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    lane = _lane(lane)
    sequence = _sequence(sequence)
    seed = read_next(backend, lane)
    if seed.get("state") != "PENDING" or seed.get("sequence") != sequence:
        raise OutboxBlock("retry scan cursor is not for the current FIFO item")
    attempt = cursor.get("transport_attempt")
    if attempt != 1:
        raise OutboxBlock("retry scan cursor binds the one-shot transport")
    transport = _mapping(
        _mapping(seed.get("transport"), "retry cursor transports").get(str(attempt)),
        "retry cursor transport",
    )
    raw_successor_count = cursor.get("bound_successor_count")
    ambiguity_set_exceeded = (
        isinstance(raw_successor_count, int)
        and not isinstance(raw_successor_count, bool)
        and raw_successor_count > 8
    )
    record = validate_retry_scan_cursor_record(
        {
            "schema": RETRY_SCAN_CURSOR_RECORD_SCHEMA,
            "lane": lane,
            "sequence": sequence,
            "fingerprint": seed["fingerprint"],
            "transport_attempt": attempt,
            "cursor": dict(cursor),
            "cursor_sha256": digest(dict(cursor)),
            "artifact": dict(artifact),
            "state": (
                "BOUNDARY_STABILIZATION_REOBSERVE"
                if cursor.get("same_second_boundary_complete") is False
                else (
                    "SCAN_INVENTORY_INCONSISTENT_AUTHORITY"
                    if cursor.get("inventory_consistent") is False
                    else (
                        "AMBIGUITY_SET_EXCEEDED_AUTHORITY"
                        if ambiguity_set_exceeded
                        else (
                            "COMPLETE_ZERO_SUCCESSOR"
                            if cursor.get("scan_complete") is True
                            and cursor.get("bound_successor_count") == 0
                            else (
                                "COMPLETE_SUCCESSOR_OBSERVED"
                                if cursor.get("scan_complete") is True
                                else (
                                    "SCAN_BOUND_EXCEEDED_AUTHORITY"
                                    if cursor.get("pages_scanned")
                                    == cursor.get("page_cap")
                                    else "SCAN_INCOMPLETE_REOBSERVE"
                                )
                            )
                        )
                    )
                )
            ),
            "productive_effect": False,
        },
        intent=_mapping(seed.get("intent"), "retry cursor intent"),
        transport=transport,
    )
    record_sha = digest(record)
    ordinal = _sequence(_mapping(record.get("cursor"), "retry cursor").get("ordinal"))
    path = retry_scan_cursor_path(lane, sequence, attempt, ordinal, record_sha)
    locator_path = retry_scan_cursor_locator_path(lane, sequence, attempt)
    locator = {
        "schema": RETRY_SCAN_CURSOR_LOCATOR_SCHEMA,
        "lane": lane,
        "sequence": sequence,
        "fingerprint": seed["fingerprint"],
        "transport_attempt": attempt,
        "ordinal": ordinal,
        "record_path": path,
        "record_sha256": record_sha,
    }

    def plan_at(parent: str) -> Mapping[str, bytes] | None:
        current_item = _read_next_at(backend, parent, lane)
        if current_item.get("state") != "PENDING" or current_item.get("sequence") != sequence:
            raise OutboxBlock("retry scan cursor FIFO item changed during CAS")
        current_transport = _mapping(
            _mapping(current_item.get("transport"), "retry CAS transports").get(str(attempt)),
            "retry CAS transport",
        )
        if validate_retry_scan_cursor_record(
            record,
            intent=_mapping(current_item.get("intent"), "retry CAS intent"),
            transport=current_transport,
        ) != record:
            raise OutboxBlock("retry scan cursor changed during CAS")
        current_record = _mapping(
            _mapping(current_item.get("retry_scan_cursor"), "retry CAS cursors").get(str(attempt)),
            "retry CAS current cursor",
        ) if str(attempt) in _mapping(current_item.get("retry_scan_cursor"), "retry CAS cursors") else None
        existing = backend.read_file(parent, path)
        if existing is not None and existing != canonical_bytes(record):
            raise OutboxBlock("immutable retry scan cursor collision")
        existing_locator = backend.read_file(parent, locator_path)
        if (
            existing_locator == canonical_bytes(locator)
            and existing == canonical_bytes(record)
        ):
            return None
        if (
            current_record is not None
            and _mapping(current_record.get("cursor"), "current retry cursor").get(
                "ordinal"
            )
            == ordinal
        ):
            raise OutboxBlock("immutable retry scan cursor ordinal collision")
        _validate_retry_cursor_transition(current_record, record)
        changes = {locator_path: canonical_bytes(locator)}
        if existing is None:
            changes[path] = canonical_bytes(record)
        return changes

    def verify_at(head: str) -> bool:
        return (
            backend.read_file(head, path) == canonical_bytes(record)
            and backend.read_file(head, locator_path) == canonical_bytes(locator)
        )

    cas = bounded_ff_cas(
        backend,
        lane=lane,
        plan_at=plan_at,
        build_message=f"Record {lane} retry scan cursor {sequence}/{attempt}/{ordinal}",
        verify_at=verify_at,
    )
    return {
        "schema": "qikvrt_ruleset_outbox_retry_scan_cursor_receipt_v1",
        "state": record["state"],
        "record": record,
        "record_sha256": record_sha,
        "record_path": path,
        "ledger_ref": ledger_ref(lane),
        "ledger_head": cas["head"],
        "cas": cas,
        "productive_effect": False,
    }


def validate_retry_evidence(
    value: Any,
    *,
    lane: str,
    sequence: int,
    fingerprint: str,
    attempt_one_accepted: bool,
    attempt_one_transport: Mapping[str, Any],
    intent: Mapping[str, Any],
    retry_scan_cursor: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    raw = _mapping(value, "outbox retry evidence")
    classification = raw.get("classification")
    if classification != "ORPHAN_NO_BOUND_SUCCESSOR":
        raise OutboxBlock("outbox retry classification is not bounded")
    successor = raw.get("successor")
    if attempt_one_accepted or successor is not None:
        raise OutboxBlock("orphan retry contradicts an accepted successor")
    blocker = _technical_code(
        raw.get("first_blocker"),
        "outbox retry blocker",
        RETRY_BLOCKERS[_lane(lane)],
    )
    scan_cursor = validate_retry_scan_cursor_record(
        raw.get("retry_scan_cursor"),
        intent=intent,
        transport=attempt_one_transport,
    )
    cursor = _mapping(scan_cursor.get("cursor"), "retry final scan cursor")
    expected_keys = {
        "schema",
        "lane",
        "sequence",
        "fingerprint",
        "attempt",
        "classification",
        "first_blocker",
        "successor",
        "retry_scan_cursor",
        "retry_scan_cursor_sha256",
        "d0",
        "verified",
        "productive_effect",
    }
    if (
        set(raw) != expected_keys
        or raw.get("schema") != RETRY_EVIDENCE_SCHEMA
        or raw.get("lane") != _lane(lane)
        or raw.get("sequence") != _sequence(sequence)
        or raw.get("fingerprint")
        != _digest(fingerprint, "outbox retry fingerprint")
        or raw.get("attempt") != 1
        or scan_cursor.get("transport_attempt") != 1
        or scan_cursor.get("state") != "COMPLETE_ZERO_SUCCESSOR"
        or cursor.get("scan_complete") is not True
        or cursor.get("bound_successor_count") != 0
        or raw.get("retry_scan_cursor_sha256") != digest(scan_cursor)
        or (
            retry_scan_cursor is not None
            and digest(dict(retry_scan_cursor)) != digest(scan_cursor)
        )
        or raw.get("d0") != 2
        or raw.get("verified") is not True
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("outbox retry evidence binding mismatch")
    return {
        "schema": RETRY_EVIDENCE_SCHEMA,
        "lane": lane,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "attempt": 1,
        "classification": classification,
        "first_blocker": blocker,
        "successor": dict(successor) if isinstance(successor, Mapping) else None,
        "retry_scan_cursor": scan_cursor,
        "retry_scan_cursor_sha256": digest(scan_cursor),
        "d0": 2,
        "verified": True,
        "productive_effect": False,
    }


def validate_transport_record(
    value: Any,
    *,
    intent: Mapping[str, Any],
    attempt: int,
    attempt_one_accepted: bool = False,
    attempt_one_transport: Mapping[str, Any] | None = None,
    retry_scan_cursor: Mapping[str, Any] | None = None,
    witnesses: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    raw = _mapping(value, "outbox transport record")
    lane = _lane(intent.get("lane"))
    if attempt != 1:
        raise OutboxBlock("new-run transport record is one-shot")
    sequence = _sequence(intent.get("sequence"))
    fingerprint = _digest(intent.get("fingerprint"), "transport intent fingerprint")
    witness_sha = _digest(raw.get("witness_sha256"), "transport witness digest")
    witness_run_id = _positive_int(
        raw.get("witness_producer_run_id"), "transport witness producer run id"
    )
    witness_run_attempt = _positive_int(
        raw.get("witness_producer_run_attempt"),
        "transport witness producer run attempt",
    )
    expected_witness_path = witness_path(
        lane, fingerprint, witness_run_id, witness_run_attempt
    )
    matching_witnesses = [
        item
        for item in (witnesses or ())
        if item.get("witness_sha256") == witness_sha
    ]
    if len(matching_witnesses) != 1:
        raise OutboxBlock("outbox transport does not bind one exact witness")
    selected_witness = matching_witnesses[0]
    selected_producer = _mapping(
        selected_witness.get("producer"), "transport selected witness producer"
    )
    if (
        selected_producer.get("run_id") != witness_run_id
        or selected_producer.get("run_attempt") != witness_run_attempt
        or raw.get("witness_path") != expected_witness_path
    ):
        raise OutboxBlock("outbox transport witness locator mismatch")
    request = request_for_transport_attempt(
        intent, attempt, witness=selected_witness
    )
    retry = raw.get("retry_evidence")
    normalized_retry = None
    if attempt == 1:
        if retry is not None:
            raise OutboxBlock("attempt-one transport cannot carry retry evidence")
    elif attempt == 2:
        if not isinstance(attempt_one_transport, Mapping):
            raise OutboxBlock("attempt two lacks exact attempt-one transport")
        normalized_retry = validate_retry_evidence(
            retry,
            lane=lane,
            sequence=sequence,
            fingerprint=fingerprint,
            attempt_one_accepted=attempt_one_accepted,
            attempt_one_transport=attempt_one_transport,
            intent=intent,
            retry_scan_cursor=retry_scan_cursor,
        )
        if attempt_one_accepted:
            raise OutboxBlock(
                "attempt two cannot create a new child after an accepted "
                "attempt-one result"
            )
    else:
        raise OutboxBlock("transport attempt must be 1 or 2")
    if (
        raw.get("schema") != TRANSPORT_SCHEMA
        or raw.get("repository") != intent.get("repository")
        or raw.get("lane") != lane
        or raw.get("sequence") != sequence
        or raw.get("fingerprint") != fingerprint
        or raw.get("attempt") != attempt
        or raw.get("request_sha256") != digest(request)
        or raw.get("main_head_sha")
        != _mapping(intent.get("payload"), "transport payload").get("main_head_sha")
        or raw.get("state") != "PRE_EFFECT_REOBSERVED"
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("outbox transport record binding mismatch")
    return {
        "schema": TRANSPORT_SCHEMA,
        "repository": intent["repository"],
        "lane": lane,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "attempt": attempt,
        "request_sha256": digest(request),
        "witness_sha256": witness_sha,
        "witness_producer_run_id": witness_run_id,
        "witness_producer_run_attempt": witness_run_attempt,
        "witness_path": expected_witness_path,
        "main_head_sha": raw["main_head_sha"],
        "actor_run_id": _positive_int(
            raw.get("actor_run_id"), "transport actor run id"
        ),
        "actor_run_attempt": _positive_int(
            raw.get("actor_run_attempt"), "transport actor run attempt"
        ),
        "retry_evidence": normalized_retry,
        "state": "PRE_EFFECT_REOBSERVED",
        "productive_effect": False,
    }


def validate_acceptance_record(
    value: Any,
    *,
    intent: Mapping[str, Any],
    transport: Mapping[str, Any],
    attempt: int,
) -> dict[str, Any]:
    raw = _mapping(value, "outbox acceptance record")
    child = _mapping(raw.get("child"), "outbox accepted child")
    child_value = normalize_child_for_intent(child, intent=intent, attempt=attempt)

    if (
        raw.get("schema") != ACCEPTANCE_SCHEMA
        or raw.get("lane") != intent.get("lane")
        or raw.get("sequence") != intent.get("sequence")
        or raw.get("fingerprint") != intent.get("fingerprint")
        or raw.get("attempt") != attempt
        or raw.get("request_sha256") != transport.get("request_sha256")
        or raw.get("child_sha256") != digest(child_value)
        or raw.get("state") != "TRANSPORT_ACCEPTED_LOCATOR"
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("outbox acceptance record binding mismatch")
    return {
        "schema": ACCEPTANCE_SCHEMA,
        "lane": intent["lane"],
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "attempt": attempt,
        "request_sha256": transport["request_sha256"],
        "child": child_value,
        "child_sha256": digest(child_value),
        "state": "TRANSPORT_ACCEPTED_LOCATOR",
        "productive_effect": False,
    }


def validate_late_acceptance_record(
    value: Any,
    *,
    intent: Mapping[str, Any],
    attempt_two_transport: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind a causally dominated A1 child without treating it as acceptance."""
    raw = _mapping(value, "outbox late-acceptance conflict")
    child = normalize_child_for_intent(
        _mapping(raw.get("child"), "outbox late accepted child"),
        intent=intent,
        attempt=1,
    )
    if (
        set(raw)
        != {
            "schema",
            "lane",
            "sequence",
            "fingerprint",
            "late_attempt",
            "dominating_transport_attempt",
            "dominating_request_sha256",
            "child",
            "child_sha256",
            "state",
            "productive_effect",
        }
        or raw.get("schema") != LATE_ACCEPTANCE_SCHEMA
        or raw.get("lane") != intent.get("lane")
        or raw.get("sequence") != intent.get("sequence")
        or raw.get("fingerprint") != intent.get("fingerprint")
        or raw.get("late_attempt") != 1
        or raw.get("dominating_transport_attempt") != 2
        or raw.get("dominating_request_sha256")
        != attempt_two_transport.get("request_sha256")
        or raw.get("child_sha256") != digest(child)
        or raw.get("state") != "LATE_ACCEPTANCE_CONFLICT"
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("outbox late-acceptance conflict binding mismatch")
    return {
        "schema": LATE_ACCEPTANCE_SCHEMA,
        "lane": intent["lane"],
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "late_attempt": 1,
        "dominating_transport_attempt": 2,
        "dominating_request_sha256": attempt_two_transport["request_sha256"],
        "child": child,
        "child_sha256": digest(child),
        "state": "LATE_ACCEPTANCE_CONFLICT",
        "productive_effect": False,
    }


def validate_completion_record(
    value: Any,
    *,
    intent: Mapping[str, Any],
    acceptance: Mapping[str, Any],
    attempt: int,
    child_recovery: bool,
) -> dict[str, Any]:
    raw = _mapping(value, "outbox completion record")
    locator_child = _mapping(acceptance.get("child"), "accepted locator child")
    same_run_result = (
        intent.get("lane") == "exact-head-dispatch"
        and locator_child.get("run_attempt") == 2
    )
    completed_child = normalize_child_for_intent(
        _mapping(raw.get("child"), "completed child"),
        intent=intent,
        attempt=attempt,
        same_run_recovery=child_recovery or same_run_result,
    )
    evidence = _mapping(raw.get("evidence"), "completed child evidence")
    terminal_job = _mapping(
        evidence.get("terminal_job"), "completed child terminal job"
    )
    artifact = _mapping(evidence.get("artifact"), "completed child artifact")
    immutable_fields = (
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
        raw.get("schema") != COMPLETION_SCHEMA
        or raw.get("lane") != intent.get("lane")
        or raw.get("sequence") != intent.get("sequence")
        or raw.get("fingerprint") != intent.get("fingerprint")
        or raw.get("attempt") != attempt
        or raw.get("child_recovery") is not child_recovery
        or raw.get("locator_child_sha256") != acceptance.get("child_sha256")
        or any(
            completed_child.get(field) != locator_child.get(field)
            for field in immutable_fields
        )
        or (
            locator_child.get("status") == "completed"
            and (
                completed_child.get("status") != locator_child.get("status")
                or completed_child.get("conclusion")
                != locator_child.get("conclusion")
            )
        )
        or completed_child.get("status") != "completed"
        or not isinstance(completed_child.get("conclusion"), str)
        or not completed_child.get("conclusion")
        or raw.get("child_sha256") != digest(completed_child)
        or evidence.get("schema") != COMPLETION_EVIDENCE_SCHEMA
        or evidence.get("run_id") != completed_child.get("run_id")
        or evidence.get("run_attempt") != completed_child.get("run_attempt")
        or isinstance(evidence.get("jobs_total_count"), bool)
        or not isinstance(evidence.get("jobs_total_count"), int)
        or evidence.get("jobs_total_count", 0) < 1
        or isinstance(terminal_job.get("id"), bool)
        or not isinstance(terminal_job.get("id"), int)
        or terminal_job.get("id", 0) < 1
        or not isinstance(terminal_job.get("name"), str)
        or not terminal_job.get("name")
        or terminal_job.get("run_attempt") != completed_child.get("run_attempt")
        or terminal_job.get("status") != "completed"
        or terminal_job.get("conclusion") != completed_child.get("conclusion")
        or isinstance(artifact.get("id"), bool)
        or not isinstance(artifact.get("id"), int)
        or artifact.get("id", 0) < 1
        or not isinstance(artifact.get("name"), str)
        or not artifact.get("name")
        or HEX64.fullmatch(
            str(artifact.get("archive_sha256", "")).removeprefix("sha256:")
        )
        is None
        or HEX64.fullmatch(str(artifact.get("payload_sha256"))) is None
        or artifact.get("producer_run_id") != completed_child.get("run_id")
        or artifact.get("producer_run_attempt") != completed_child.get("run_attempt")
        or artifact.get("verified") is not True
        or evidence.get("verified") is not True
        or evidence.get("productive_effect") is not False
        or raw.get("evidence_sha256") != digest(dict(evidence))
        or raw.get("state") != "COMPLETED_RESULT_OBSERVED"
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("outbox completed child binding mismatch")
    return {
        "schema": COMPLETION_SCHEMA,
        "lane": intent["lane"],
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "attempt": attempt,
        "child_recovery": child_recovery,
        "locator_child_sha256": acceptance["child_sha256"],
        "child": completed_child,
        "child_sha256": digest(completed_child),
        "evidence": dict(evidence),
        "evidence_sha256": digest(dict(evidence)),
        "state": "COMPLETED_RESULT_OBSERVED",
        "productive_effect": False,
    }


def normalize_child_for_intent(
    child: Mapping[str, Any],
    *,
    intent: Mapping[str, Any],
    attempt: int,
    same_run_recovery: bool = False,
) -> dict[str, Any]:
    payload = _mapping(intent.get("payload"), "accepted child payload")
    request = _mapping(payload.get("request"), "accepted child request")
    target = _mapping(payload.get("target"), "accepted child target")
    lane = _lane(intent.get("lane"))
    child_value = {
        "run_id": _positive_int(child.get("run_id"), "accepted child run id"),
        "run_attempt": _positive_int(
            child.get("run_attempt"), "accepted child run attempt"
        ),
        "workflow_id": _positive_int(
            child.get("workflow_id"), "accepted child workflow id"
        ),
        "workflow_path": child.get("workflow_path"),
        "event": child.get("event"),
        "repository": child.get("repository"),
        "head_sha": _sha(child.get("head_sha"), "accepted child head"),
        "status": child.get("status"),
        "conclusion": child.get("conclusion"),
        "display_title": child.get("display_title"),
    }
    if (
        not isinstance(child_value["workflow_path"], str)
        or not child_value["workflow_path"].startswith(".github/workflows/")
        or not isinstance(child_value["event"], str)
        or not child_value["event"]
        or child_value["repository"] != intent.get("repository")
        or child_value["status"]
        not in {"queued", "in_progress", "waiting", "pending", "completed"}
        or (
            child_value["status"] == "completed"
            and (
                not isinstance(child_value["conclusion"], str)
                or not child_value["conclusion"]
            )
        )
        or (
            child_value["status"] != "completed"
            and child_value["conclusion"] is not None
        )
        or not isinstance(child_value["display_title"], str)
        or not child_value["display_title"]
    ):
        raise OutboxBlock("outbox accepted child identity is incomplete")
    expected_run_attempt = (
        2 if lane == "reconciler-rerun" or same_run_recovery else 1
    )
    if child_value["run_attempt"] != expected_run_attempt:
        if same_run_recovery:
            raise OutboxBlock(
                "outbox same-run recovery child must be exact run attempt two"
            )
        raise OutboxBlock(
            "outbox direct transport child must be exact run attempt one"
        )
    if lane in {"ruleset-dispatch", "reconciler-rerun"}:
        expected_path = ".github/workflows/qikvrt_ruleset_reconcile.yml"
        expected_event = "repository_dispatch"
        expected_head = payload["main_head_sha"]
    elif lane in {
        "requested-review-dispatch",
        "exact-review-dispatch",
        "mesh-review-successor-dispatch",
    }:
        expected_path = ".github/workflows/qikvrt_requested_review_executor.yml"
        expected_event = "workflow_dispatch"
        expected_head = _mapping(request.get("inputs"), "review child inputs").get(
            "evaluator_sha"
        )
    else:
        expected_path = ".github/workflows/qikvrt_autonomous_exact_head_verify.yml"
        expected_event = "repository_dispatch"
        expected_head = payload["main_head_sha"]
    if (
        child_value["workflow_id"] != target.get("workflow_id")
        or child_value["workflow_path"] != expected_path
        or child_value["event"] != expected_event
        or child_value["head_sha"] != expected_head
    ):
        raise OutboxBlock("outbox accepted child lane identity mismatch")
    if lane in REVIEW_TRANSPORT_LANES:
        inputs = _mapping(request.get("inputs"), "accepted review inputs")
        expected_title = (
            f"qikvrt-rr-v3 e={inputs['evaluator_sha']} p={inputs['pr']} "
            f"h={inputs['head']} f={inputs['fingerprint']} "
            f"i={intent['fingerprint']} a={attempt}"
        )
        if child_value["display_title"] != expected_title:
            raise OutboxBlock("requested-review child title locator mismatch")
    elif lane == "reconciler-rerun":
        # GitHub preserves the original workflow run's display title when the
        # same run is rerun.  A rerun-lane locator therefore cannot truthfully
        # be required in that immutable title.  Bind the exact original child
        # sealed in the rerun request and require only the attempt transition.
        original = _mapping(
            request.get("original_child"), "reconciler-rerun original child"
        )
        immutable_fields = (
            "run_id",
            "workflow_id",
            "workflow_path",
            "event",
            "repository",
            "head_sha",
            "display_title",
        )
        if (
            request.get("reconciler_run_id") != child_value["run_id"]
            or request.get("reconciler_run_attempt") != 1
            or child_value["run_attempt"] != 2
            or request.get("target_attempt") != 2
            or request.get("original_child_sha256") != digest(dict(original))
            or any(
                child_value.get(field) != original.get(field)
                for field in immutable_fields
            )
        ):
            raise OutboxBlock(
                "reconciler-rerun child differs from exact original run provenance"
            )
    else:
        locator_tokens = (
            f"intent={intent['fingerprint']}",
            f"seq={intent['sequence']}",
            f"transport-attempt={attempt}",
        )
        if any(token not in child_value["display_title"] for token in locator_tokens):
            raise OutboxBlock(
                "outbox accepted child title omits exact transport locator"
            )
    return child_value


def _read_next_at(backend: LedgerBackend, head: str, lane: str) -> dict[str, Any]:
    lane = _lane(lane)
    meta = validate_meta(_read_json(backend, head, meta_path(lane)), lane)
    if meta["drain_seq"] == meta["next_seq"]:
        return {
            "schema": "qikvrt_ruleset_outbox_next_v1",
            "state": "EMPTY",
            "lane": lane,
            "meta": meta,
            "ledger_ref": ledger_ref(lane),
            "ledger_head": head,
        }
    sequence = meta["drain_seq"]
    slot_value = _read_json(backend, head, slot_path(lane, sequence))
    slot = _mapping(slot_value, "outbox FIFO slot")
    fingerprint = _digest(slot.get("fingerprint"), "outbox slot fingerprint")
    expected_intent_path = intent_path(lane, sequence, fingerprint)
    if (
        slot.get("schema") != SLOT_SCHEMA
        or slot.get("lane") != lane
        or slot.get("sequence") != sequence
        or slot.get("intent_path") != expected_intent_path
    ):
        raise OutboxBlock("outbox FIFO slot binding mismatch")
    record = _validate_intent_record(
        _read_json(backend, head, expected_intent_path), lane=lane
    )
    if (
        record["sequence"] != sequence
        or record["fingerprint"] != fingerprint
        or slot.get("intent_sha256") != digest(record)
    ):
        raise OutboxBlock("outbox FIFO slot and intent differ")
    locator = _read_intent_by_fingerprint(backend, head, lane, fingerprint)
    if locator != record:
        raise OutboxBlock("outbox FIFO locator and intent differ")
    witnesses = _read_witnesses(backend, head, lane, fingerprint)
    if not any(
        witness.get("producer") == record["payload"].get("producer")
        and witness.get("artifact") == record.get("artifact")
        for witness in witnesses
    ):
        raise OutboxBlock("outbox primary intent witness is absent")
    raw_transports: dict[str, Mapping[str, Any]] = {}
    raw_acceptances: dict[str, Mapping[str, Any]] = {}
    raw_completions: dict[str, Mapping[str, Any]] = {}
    raw_late_acceptance = _read_json(
        backend,
        head,
        late_acceptance_path(lane, sequence),
        required=False,
    )
    for attempt in (1, 2):
        transport = _read_json(
            backend, head, transport_path(lane, sequence, attempt), required=False
        )
        acceptance = _read_json(
            backend, head, acceptance_path(lane, sequence, attempt), required=False
        )
        completion = _read_json(
            backend,
            head,
            completion_path(lane, sequence, attempt),
            required=False,
        )
        if transport is not None:
            raw_transports[str(attempt)] = transport
        if acceptance is not None:
            raw_acceptances[str(attempt)] = acceptance
        if completion is not None:
            raw_completions[str(attempt)] = completion
    if "2" in raw_transports and "1" not in raw_transports:
        raise OutboxBlock("attempt-two transport exists without attempt one")
    if any(key not in raw_transports for key in raw_acceptances):
        raise OutboxBlock("outbox acceptance exists without matching transport")
    if any(key not in raw_acceptances for key in raw_completions):
        raise OutboxBlock("outbox completion exists without accepted locator")
    transport_witnesses = list(witnesses)
    for raw_transport in raw_transports.values():
        witness_run_id = _positive_int(
            raw_transport.get("witness_producer_run_id"),
            "persisted transport witness run id",
        )
        witness_run_attempt = _positive_int(
            raw_transport.get("witness_producer_run_attempt"),
            "persisted transport witness run attempt",
        )
        exact_path = witness_path(
            lane, fingerprint, witness_run_id, witness_run_attempt
        )
        if raw_transport.get("witness_path") != exact_path:
            raise OutboxBlock("persisted transport witness path mismatch")
        if not any(
            item.get("producer", {}).get("run_id") == witness_run_id
            and item.get("producer", {}).get("run_attempt")
            == witness_run_attempt
            for item in transport_witnesses
        ):
            direct_witness = _validate_witness_record(
                _read_json(backend, head, exact_path),
                lane=lane,
                fingerprint=fingerprint,
            )
            if direct_witness.get("witness_sha256") != raw_transport.get(
                "witness_sha256"
            ):
                raise OutboxBlock("persisted transport witness digest mismatch")
            transport_witnesses.append(direct_witness)
    transports: dict[str, Any] = {}
    acceptances: dict[str, Any] = {}
    completions: dict[str, Any] = {}
    child_recovery: dict[str, Any] = {}
    if "1" in raw_transports:
        transports["1"] = validate_transport_record(
            raw_transports["1"],
            intent=record,
            attempt=1,
            witnesses=transport_witnesses,
        )
    if "1" in raw_acceptances:
        acceptances["1"] = validate_acceptance_record(
            raw_acceptances["1"],
            intent=record,
            transport=transports["1"],
            attempt=1,
        )
    if "2" in raw_transports:
        transports["2"] = validate_transport_record(
            raw_transports["2"],
            intent=record,
            attempt=2,
            attempt_one_accepted="1" in acceptances,
            attempt_one_transport=transports["1"],
            witnesses=transport_witnesses,
        )
    if "2" in raw_acceptances:
        acceptances["2"] = validate_acceptance_record(
            raw_acceptances["2"],
            intent=record,
            transport=transports["2"],
            attempt=2,
        )
    late_acceptance_conflict = None
    if raw_late_acceptance is not None:
        if "2" not in transports or "1" in acceptances:
            raise OutboxBlock(
                "late attempt-one acceptance lacks dominating attempt-two state"
            )
        late_acceptance_conflict = validate_late_acceptance_record(
            raw_late_acceptance,
            intent=record,
            attempt_two_transport=transports["2"],
        )
    for attempt in (1, 2):
        if str(attempt) in raw_completions:
            completions[str(attempt)] = validate_completion_record(
                raw_completions[str(attempt)],
                intent=record,
                acceptance=acceptances[str(attempt)],
                attempt=attempt,
                child_recovery=False,
            )
    retry_scan_cursors: dict[str, Any] = {}
    for attempt in (1, 2):
        raw_locator = _read_json(
            backend,
            head,
            retry_scan_cursor_locator_path(lane, sequence, attempt),
            required=False,
        )
        if raw_locator is None:
            continue
        locator = dict(_mapping(raw_locator, "retry scan cursor locator"))
        record_sha = _digest(
            locator.get("record_sha256"), "retry scan cursor locator digest"
        )
        ordinal = _sequence(
            locator.get("ordinal"), "retry scan cursor locator ordinal"
        )
        expected_path = retry_scan_cursor_path(
            lane, sequence, attempt, ordinal, record_sha
        )
        if (
            set(locator)
            != {
                "schema",
                "lane",
                "sequence",
                "fingerprint",
                "transport_attempt",
                "ordinal",
                "record_path",
                "record_sha256",
            }
            or locator.get("schema") != RETRY_SCAN_CURSOR_LOCATOR_SCHEMA
            or locator.get("lane") != lane
            or locator.get("sequence") != sequence
            or locator.get("fingerprint") != fingerprint
            or locator.get("transport_attempt") != attempt
            or locator.get("record_path") != expected_path
            or str(attempt) not in transports
        ):
            raise OutboxBlock("retry scan cursor locator binding mismatch")
        record_value = validate_retry_scan_cursor_record(
            _read_json(backend, head, expected_path),
            intent=record,
            transport=transports[str(attempt)],
        )
        if (
            digest(record_value) != record_sha
            or _mapping(record_value.get("cursor"), "retry scan cursor").get(
                "ordinal"
            )
            != ordinal
        ):
            raise OutboxBlock("retry scan cursor content address mismatch")
        retry_scan_cursors[str(attempt)] = record_value
    if "2" in transports:
        attempt_one_cursor = retry_scan_cursors.get("1")
        retry = _mapping(
            transports["2"].get("retry_evidence"),
            "attempt-two persisted retry evidence",
        )
        if (
            not isinstance(attempt_one_cursor, Mapping)
            or retry.get("retry_scan_cursor_sha256")
            != digest(dict(attempt_one_cursor))
        ):
            raise OutboxBlock(
                "attempt-two transport lacks the exact persisted final retry cursor"
            )
    for attempt in (1, 2):
        rerun = _read_json(
            backend,
            head,
            child_rerun_path(lane, sequence, attempt),
            required=False,
        )
        rerun_acceptance = _read_json(
            backend,
            head,
            child_rerun_acceptance_path(lane, sequence, attempt),
            required=False,
        )
        rerun_completion = _read_json(
            backend,
            head,
            completion_path(
                lane, sequence, attempt, child_recovery=True
            ),
            required=False,
        )
        if (
            rerun is not None
            or rerun_acceptance is not None
            or rerun_completion is not None
        ):
            if lane not in REVIEW_TRANSPORT_LANES:
                raise OutboxBlock("child rerun exists outside a review lane")
            if str(attempt) not in acceptances:
                raise OutboxBlock("child rerun lacks original accepted child")
            original = acceptances[str(attempt)]
            if rerun is None:
                raise OutboxBlock("child-rerun acceptance lacks pre-effect record")
            rerun_value = _mapping(rerun, "child-rerun record")
            original_child = _mapping(original.get("child"), "original child")
            retry = _normalize_child_retry_evidence(
                rerun_value.get("retry_evidence"),
                intent=record,
                acceptance=original,
                transport_attempt=attempt,
            )
            observed_terminal = _mapping(
                retry.get("observed_terminal_child"),
                "child-rerun observed terminal child",
            )
            if (
                rerun_value.get("schema") != CHILD_RERUN_SCHEMA
                or rerun_value.get("lane") != lane
                or rerun_value.get("sequence") != sequence
                or rerun_value.get("fingerprint") != fingerprint
                or rerun_value.get("transport_attempt") != attempt
                or rerun_value.get("target_run_id")
                != observed_terminal.get("run_id")
                or rerun_value.get("target_run_attempt") != 2
                or rerun_value.get("actor_run_id") is None
                or rerun_value.get("actor_run_attempt") is None
                or rerun_value.get("productive_effect") is not False
            ):
                raise OutboxBlock("child-rerun record binding mismatch")
            _positive_int(
                rerun_value.get("actor_run_id"), "child-rerun actor run id"
            )
            _positive_int(
                rerun_value.get("actor_run_attempt"),
                "child-rerun actor run attempt",
            )
            recovered = None
            recovered_completion = None
            if rerun_acceptance is not None:
                recovered_value = _mapping(
                    rerun_acceptance, "child-rerun acceptance"
                )
                recovered_child = normalize_child_for_intent(
                    _mapping(recovered_value.get("child"), "recovered child"),
                    intent=record,
                    attempt=attempt,
                    same_run_recovery=True,
                )
                if (
                    recovered_value.get("schema")
                    != CHILD_RERUN_ACCEPTANCE_SCHEMA
                    or recovered_value.get("lane") != lane
                    or recovered_value.get("sequence") != sequence
                    or recovered_value.get("fingerprint") != fingerprint
                    or recovered_value.get("transport_attempt") != attempt
                    or recovered_child.get("run_id")
                    != original_child.get("run_id")
                    or recovered_child.get("run_attempt") != 2
                    or recovered_value.get("child_sha256")
                    != digest(recovered_child)
                    or recovered_value.get("productive_effect") is not False
                ):
                    raise OutboxBlock("child-rerun acceptance binding mismatch")
                recovered = {**dict(recovered_value), "child": recovered_child}
            if rerun_completion is not None:
                if recovered is None:
                    raise OutboxBlock(
                        "child-rerun completion lacks accepted locator"
                    )
                recovered_completion = validate_completion_record(
                    rerun_completion,
                    intent=record,
                    acceptance=recovered,
                    attempt=attempt,
                    child_recovery=True,
                )
            child_recovery[str(attempt)] = {
                "rerun": dict(rerun_value),
                "acceptance": recovered,
                "completion": recovered_completion,
            }
    same_run_results: dict[str, Any] = {}
    if lane == "exact-head-dispatch":
        for attempt in (1, 2):
            acceptance = acceptances.get(str(attempt))
            if not isinstance(acceptance, Mapping):
                continue
            locator_child = _mapping(
                acceptance.get("child"), "same-run locator child"
            )
            observed_attempt = int(locator_child["run_attempt"]) + 1
            raw_same_run = _read_json(
                backend,
                head,
                same_run_result_path(
                    lane, sequence, attempt, observed_attempt
                ),
                required=False,
            )
            if raw_same_run is not None:
                same_run_results[str(attempt)] = validate_same_run_result(
                    raw_same_run,
                    intent=record,
                    acceptance=acceptance,
                    transport_attempt=attempt,
                )
    if _read_json(backend, head, terminal_path(lane, sequence), required=False) is not None:
        raise OutboxBlock("outbox terminal exists before drain cursor advanced")
    return {
        "schema": "qikvrt_ruleset_outbox_next_v1",
        "state": "PENDING",
        "lane": lane,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "intent": record,
        "witnesses": witnesses,
        "transport": transports,
        "acceptance": acceptances,
        "completion": completions,
        "child_recovery": child_recovery,
        "same_run_result": same_run_results,
        "retry_scan_cursor": retry_scan_cursors,
        "late_acceptance_conflict": late_acceptance_conflict,
        # Authority observations are content-addressed and selected by the
        # terminal evidence itself.  A FIFO read never guesses a "latest"
        # observation and therefore cannot be wedged by a crash after an
        # older observation was persisted.
        "authority_observation": None,
        "meta": meta,
        "ledger_ref": ledger_ref(lane),
        "ledger_head": head,
    }


def read_next(backend: LedgerBackend, lane: str) -> dict[str, Any]:
    lane = _lane(lane)
    # Authority/protection validation and the ledger read deliberately share
    # the one exact head returned by ensure_initialized().  Returning that
    # head lets a later effect bind its mutation to this immutable snapshot
    # without a second, racy read-only lookup.
    head = ensure_initialized(backend, lane)
    return _read_next_at(backend, head, lane)


def lookup(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    fingerprint: str,
) -> dict[str, Any]:
    """Read and validate one exact pending or historical terminal FIFO item.

    Historical lookup never moves/reopens a cursor.  It is intended for a
    same-run recovery binder that already carries the immutable sequence and
    semantic fingerprint; there is deliberately no repository-wide search.
    """
    lane = _lane(lane)
    sequence = _sequence(sequence)
    fingerprint = _digest(fingerprint, "lookup fingerprint")
    head = ensure_initialized(backend, lane)
    return _lookup_at(
        backend,
        lane=lane,
        sequence=sequence,
        fingerprint=fingerprint,
        head=head,
    )


def _lookup_at(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    fingerprint: str,
    head: str,
) -> dict[str, Any]:
    """Validate one exact FIFO item at a caller-sealed ledger snapshot."""
    lane = _lane(lane)
    sequence = _sequence(sequence)
    fingerprint = _digest(fingerprint, "lookup fingerprint")
    head = _sha(head, "outbox lookup head")
    exact_ref = ledger_ref(lane)
    actual_meta = validate_meta(
        _read_json(backend, head, meta_path(lane)), lane
    )
    if sequence >= actual_meta["next_seq"]:
        raise OutboxBlock("outbox lookup sequence was never allocated")

    class _SequenceView:
        repository = backend.repository

        def read_file(self, commit: str, path: str) -> bytes | None:
            if path == meta_path(lane):
                return canonical_bytes(
                    {
                        "schema": META_SCHEMA,
                        "lane": lane,
                        "next_seq": sequence + 1,
                        "drain_seq": sequence,
                    }
                )
            if path == terminal_path(lane, sequence):
                return None
            return backend.read_file(commit, path)

    pending = _read_next_at(_SequenceView(), head, lane)  # type: ignore[arg-type]
    if pending.get("fingerprint") != fingerprint:
        raise OutboxBlock("outbox historical lookup fingerprint mismatch")
    terminal_raw = _read_json(
        backend, head, terminal_path(lane, sequence), required=False
    )
    if terminal_raw is None:
        if actual_meta["drain_seq"] > sequence:
            raise OutboxBlock("outbox cursor advanced without a terminal record")
        if actual_meta["drain_seq"] < sequence:
            return {
                **pending,
                "state": "QUEUED",
                "lookup_state": "QUEUED",
                "meta": actual_meta,
                "ledger_ref": exact_ref,
                "ledger_head": head,
            }
        return {
            **pending,
            "state": "PENDING",
            "lookup_state": "PENDING",
            "meta": actual_meta,
            "ledger_ref": exact_ref,
            "ledger_head": head,
        }
    terminal = dict(_mapping(terminal_raw, "outbox historical terminal"))
    supersession_raw = _read_json(
        backend,
        head,
        terminal_supersession_path(lane, sequence),
        required=False,
    )
    validation_view = pending
    if supersession_raw is not None:
        # The prior D0=2 record was valid before the exact same GitHub run was
        # rerun.  Validate it against that historical frontier, then validate
        # the append-only effective D0=3 supersession against the latest result.
        validation_view = {**pending, "same_run_result": {}}
    validation_view = _bind_authority_observation_at(
        backend,
        head,
        validation_view,
        _mapping(terminal.get("evidence"), "historical terminal evidence"),
    )
    evidence = validate_terminal_evidence(
        terminal.get("evidence"), next_item=validation_view
    )
    if (
        actual_meta["drain_seq"] <= sequence
        or terminal.get("schema") != TERMINAL_SCHEMA
        or terminal.get("lane") != lane
        or terminal.get("sequence") != sequence
        or terminal.get("fingerprint") != fingerprint
        or terminal.get("state") != "TERMINAL"
        or terminal.get("d0") != evidence.get("d0")
        or terminal.get("evidence_sha256") != digest(evidence)
        or terminal.get("productive_effect") is not False
    ):
        raise OutboxBlock("outbox historical terminal binding mismatch")
    supersession = None
    effective_d0 = terminal["d0"]
    if supersession_raw is not None:
        supersession = dict(
            _mapping(supersession_raw, "outbox terminal supersession")
        )
        same_run_values = _mapping(
            pending.get("same_run_result"), "superseding same-run results"
        )
        matching_values = [
            value
            for value in same_run_values.values()
            if isinstance(value, Mapping)
            and digest(dict(value))
            == supersession.get("same_run_result_sha256")
        ]
        if len(matching_values) != 1:
            raise OutboxBlock("terminal supersession lacks one exact latest result")
        latest_result = dict(matching_values[0])
        effective_d0 = latest_result.get("d0")
        expected_state = (
            "EFFECTIVE_REOBSERVE"
            if effective_d0 == 2
            else "EFFECTIVE_REQUEST_AUTHORITY"
        )
        expected_reason = (
            "SAME_RUN_EXACT_RESULT_SUCCESS"
            if effective_d0 == 2
            else "SAME_RUN_EXACT_RESULT_ADVERSE"
        )
        effective_evidence_value = _mapping(
            supersession.get("evidence"), "terminal supersession evidence"
        )
        effective_view = _bind_authority_observation_at(
            backend, head, pending, effective_evidence_value
        )
        effective_evidence = validate_terminal_evidence(
            effective_evidence_value, next_item=effective_view
        )
        if (
            supersession.get("schema") != TERMINAL_SUPERSESSION_SCHEMA
            or supersession.get("lane") != lane
            or supersession.get("sequence") != sequence
            or supersession.get("fingerprint") != fingerprint
            or supersession.get("prior_terminal_sha256") != digest(terminal)
            or supersession.get("same_run_result_sha256")
            != digest(latest_result)
            or supersession.get("d0") != effective_d0
            or supersession.get("state") != expected_state
            or supersession.get("effective_reason") != expected_reason
            or effective_evidence.get("d0") != effective_d0
            or supersession.get("evidence_sha256") != digest(effective_evidence)
            or supersession.get("productive_effect") is not False
        ):
            raise OutboxBlock("outbox terminal supersession binding mismatch")
        effective_d0 = int(effective_d0)
    return {
        **pending,
        "state": "TERMINAL",
        "lookup_state": "TERMINAL",
        # Return the exact content-addressed Authority record selected and
        # validated by the terminal evidence at this ledger snapshot.  This
        # lets a read-only adopter bind its local receipt to durable Core
        # evidence without a second path lookup or a racy "latest" guess.
        "authority_observation": validation_view.get(
            "authority_observation"
        ),
        "terminal": terminal,
        "terminal_supersession": supersession,
        "effective_d0": effective_d0,
        "meta": actual_meta,
        "ledger_ref": exact_ref,
        "ledger_head": head,
    }


def lookup_fingerprint(
    backend: LedgerBackend, *, lane: str, fingerprint: str
) -> dict[str, Any]:
    """Resolve one content-addressed locator, then perform exact O(1) lookup."""
    lane = _lane(lane)
    fingerprint = _digest(fingerprint, "lookup fingerprint")
    head = ensure_initialized(backend, lane)
    intent = _read_intent_by_fingerprint(backend, head, lane, fingerprint)
    if intent is None:
        raise OutboxBlock("OUTBOX_FINGERPRINT_NOT_FOUND")
    return _lookup_at(
        backend,
        lane=lane,
        sequence=_sequence(intent.get("sequence")),
        fingerprint=fingerprint,
        head=head,
    )


def _append_immutable_record(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    path: str,
    record: Mapping[str, Any],
    message: str,
    validate_current: Any | None = None,
) -> dict[str, Any]:
    lane = _lane(lane)
    sequence = _sequence(sequence)
    raw = canonical_bytes(record)

    def plan_at(parent: str) -> Mapping[str, bytes] | None:
        current = _read_next_at(backend, parent, lane)
        if current.get("state") != "PENDING" or current.get("sequence") != sequence:
            existing = backend.read_file(parent, path)
            if existing == raw:
                return None
            raise OutboxBlock("outbox record is not for current FIFO sequence")
        if validate_current is not None:
            validate_current(current)
        existing = backend.read_file(parent, path)
        if existing is None:
            return {path: raw}
        if existing != raw:
            raise OutboxBlock("immutable outbox record collision")
        return None

    def verify_at(head: str) -> bool:
        return backend.read_file(head, path) == raw

    cas = bounded_ff_cas(
        backend,
        lane=lane,
        plan_at=plan_at,
        build_message=message,
        verify_at=verify_at,
    )
    return {
        **dict(record),
        "ledger_ref": ledger_ref(lane),
        "ledger_head": cas["head"],
        "cas": cas,
    }


def prepare_transport(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    attempt: int,
    request: Mapping[str, Any],
    actor_run_id: int,
    actor_run_attempt: int,
    retry_evidence: Mapping[str, Any] | None = None,
    witness_run_id: int | None = None,
    witness_run_attempt: int | None = None,
) -> dict[str, Any]:
    lane = _lane(lane)
    sequence = _sequence(sequence)
    if attempt != 1:
        raise OutboxBlock("new-run transport is one-shot")
    next_item = read_next(backend, lane)
    if next_item.get("state") != "PENDING" or next_item.get("sequence") != sequence:
        raise OutboxBlock("transport does not bind the current outbox item")
    intent = _mapping(next_item.get("intent"), "transport intent")
    payload = _mapping(intent.get("payload"), "transport payload")
    witnesses = list(next_item.get("witnesses") or [])
    if (witness_run_id is None) != (witness_run_attempt is None):
        raise OutboxBlock("transport witness run id/attempt must be supplied together")
    if witness_run_id is None:
        selected_witnesses = witnesses[:1]
    else:
        selected_witnesses = [
            item
            for item in witnesses
            if item.get("producer", {}).get("run_id") == witness_run_id
            and item.get("producer", {}).get("run_attempt")
            == witness_run_attempt
        ]
    if len(selected_witnesses) != 1:
        raise OutboxBlock("transport does not bind one exact producer witness")
    selected_witness = selected_witnesses[0]
    selected_producer = _mapping(
        selected_witness.get("producer"), "transport selected witness producer"
    )
    selected_run_id = _positive_int(
        selected_producer.get("run_id"), "transport witness producer run id"
    )
    selected_run_attempt = _positive_int(
        selected_producer.get("run_attempt"),
        "transport witness producer run attempt",
    )
    expected_request = request_for_transport_attempt(
        intent, attempt, witness=selected_witness
    )
    if dict(request) != expected_request:
        raise OutboxBlock("transport request differs from sealed outbox request")
    transports = _mapping(next_item.get("transport"), "outbox transports")
    acceptances = _mapping(next_item.get("acceptance"), "outbox acceptances")
    normalized_retry = None
    if attempt == 1:
        if retry_evidence is not None:
            raise OutboxBlock("attempt-one transport cannot carry retry evidence")
        if "2" in transports:
            raise OutboxBlock("attempt one cannot follow attempt two")
    else:
        if "1" not in transports:
            raise OutboxBlock("attempt two requires exact attempt one")
        normalized_retry = validate_retry_evidence(
            retry_evidence,
            lane=lane,
            sequence=sequence,
            fingerprint=str(intent["fingerprint"]),
            attempt_one_accepted="1" in acceptances,
            attempt_one_transport=_mapping(
                transports["1"], "attempt-one transport"
            ),
            intent=intent,
            retry_scan_cursor=_mapping(
                _mapping(
                    next_item.get("retry_scan_cursor"),
                    "outbox retry scan cursors",
                ).get("1"),
                "attempt-one final retry scan cursor",
            ),
        )
    live_main = backend.get_main_head()
    if live_main != payload.get("main_head_sha"):
        raise OutboxBlock("transport main head drifted after outbox sealing")
    record = {
        "schema": TRANSPORT_SCHEMA,
        "repository": payload["repository"],
        "lane": lane,
        "sequence": sequence,
        "fingerprint": intent["fingerprint"],
        "attempt": attempt,
        "request_sha256": digest(dict(request)),
        "witness_sha256": selected_witness["witness_sha256"],
        "witness_producer_run_id": selected_run_id,
        "witness_producer_run_attempt": selected_run_attempt,
        "witness_path": witness_path(
            lane, intent["fingerprint"], selected_run_id, selected_run_attempt
        ),
        "main_head_sha": live_main,
        "actor_run_id": _positive_int(actor_run_id, "transport actor run id"),
        "actor_run_attempt": _positive_int(
            actor_run_attempt, "transport actor run attempt"
        ),
        "retry_evidence": normalized_retry,
        "state": "PRE_EFFECT_REOBSERVED",
        "productive_effect": False,
    }

    def validate_transport_current(current: Mapping[str, Any]) -> None:
        current_intent = _mapping(
            current.get("intent"), "transport CAS-current intent"
        )
        if (
            current_intent.get("fingerprint") != intent.get("fingerprint")
            or current_intent.get("payload_sha256") != intent.get("payload_sha256")
        ):
            raise OutboxBlock("transport intent changed during CAS")
        current_witnesses = list(current.get("witnesses") or [])
        current_selected = [
            item
            for item in current_witnesses
            if item.get("producer", {}).get("run_id") == selected_run_id
            and item.get("producer", {}).get("run_attempt")
            == selected_run_attempt
            and item.get("witness_sha256") == selected_witness.get("witness_sha256")
        ]
        if len(current_selected) != 1:
            raise OutboxBlock("transport witness changed during CAS")
        if request_for_transport_attempt(
            current_intent, attempt, witness=current_selected[0]
        ) != dict(request):
            raise OutboxBlock("transport request changed during CAS")
        current_transports = _mapping(
            current.get("transport"), "transport CAS-current transports"
        )
        current_acceptances = _mapping(
            current.get("acceptance"), "transport CAS-current acceptances"
        )
        if attempt == 1:
            if "2" in current_transports:
                raise OutboxBlock("attempt one cannot follow attempt two")
        else:
            if "1" not in current_transports:
                raise OutboxBlock("attempt two requires exact attempt one")
            validate_retry_evidence(
                normalized_retry,
                lane=lane,
                sequence=sequence,
                fingerprint=str(current_intent["fingerprint"]),
                attempt_one_accepted="1" in current_acceptances,
                attempt_one_transport=_mapping(
                    current_transports["1"], "CAS attempt-one transport"
                ),
                intent=current_intent,
                retry_scan_cursor=_mapping(
                    _mapping(
                        current.get("retry_scan_cursor"),
                        "CAS retry scan cursors",
                    ).get("1"),
                    "CAS attempt-one final retry scan cursor",
                ),
            )
        if backend.get_main_head() != payload.get("main_head_sha"):
            raise OutboxBlock("transport main head drifted during CAS")

    return _append_immutable_record(
        backend,
        lane=lane,
        sequence=sequence,
        path=transport_path(lane, sequence, attempt),
        record=record,
        message=f"Prepare {lane} outbox transport {sequence} attempt {attempt}",
        validate_current=validate_transport_current,
    )


def record_acceptance(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    attempt: int,
    child: Mapping[str, Any],
) -> dict[str, Any]:
    lane = _lane(lane)
    sequence = _sequence(sequence)
    if attempt != 1:
        raise OutboxBlock("new-run transport acceptance is one-shot")
    next_item = read_next(backend, lane)
    if next_item.get("state") != "PENDING" or next_item.get("sequence") != sequence:
        raise OutboxBlock("acceptance does not bind the current outbox item")
    intent = _mapping(next_item.get("intent"), "acceptance intent")
    transports = _mapping(next_item.get("transport"), "acceptance transports")
    transport = transports.get(str(attempt))
    if not isinstance(transport, Mapping):
        raise OutboxBlock("acceptance requires matching pre-effect transport")
    child_value = normalize_child_for_intent(
        _mapping(child, "outbox accepted child"), intent=intent, attempt=attempt
    )
    final_record: dict[str, Any] = {}
    final_path = ""
    final_raw = b""
    late_conflict = False

    def plan_at(parent: str) -> Mapping[str, bytes] | None:
        nonlocal final_record, final_path, final_raw, late_conflict
        current = _read_next_at(backend, parent, lane)
        current_intent = _mapping(current.get("intent"), "acceptance CAS intent")
        current_transports = _mapping(
            current.get("transport"), "acceptance CAS transports"
        )
        current_acceptances = _mapping(
            current.get("acceptance"), "acceptance CAS acceptances"
        )
        current_transport = current_transports.get(str(attempt))
        if (
            current.get("state") != "PENDING"
            or current.get("sequence") != sequence
            or current_intent.get("fingerprint") != intent.get("fingerprint")
            or not isinstance(current_transport, Mapping)
            or current_transport.get("request_sha256")
            != transport.get("request_sha256")
            or normalize_child_for_intent(
                child_value, intent=current_intent, attempt=attempt
            )
            != child_value
        ):
            raise OutboxBlock("acceptance state changed during CAS")
        late_conflict = attempt == 1 and "2" in current_transports
        if late_conflict:
            if "1" in current_acceptances:
                raise OutboxBlock(
                    "late attempt-one acceptance conflicts with existing acceptance"
                )
            attempt_two_transport = _mapping(
                current_transports["2"], "dominating attempt-two transport"
            )
            final_record = {
                "schema": LATE_ACCEPTANCE_SCHEMA,
                "lane": lane,
                "sequence": sequence,
                "fingerprint": current_intent["fingerprint"],
                "late_attempt": 1,
                "dominating_transport_attempt": 2,
                "dominating_request_sha256": attempt_two_transport[
                    "request_sha256"
                ],
                "child": child_value,
                "child_sha256": digest(child_value),
                "state": "LATE_ACCEPTANCE_CONFLICT",
                "productive_effect": False,
            }
            final_path = late_acceptance_path(lane, sequence)
        else:
            final_record = {
                "schema": ACCEPTANCE_SCHEMA,
                "lane": lane,
                "sequence": sequence,
                "fingerprint": current_intent["fingerprint"],
                "attempt": attempt,
                "request_sha256": current_transport["request_sha256"],
                "child": child_value,
                "child_sha256": digest(child_value),
                "state": "TRANSPORT_ACCEPTED_LOCATOR",
                "productive_effect": False,
            }
            final_path = acceptance_path(lane, sequence, attempt)
        final_raw = canonical_bytes(final_record)
        existing = backend.read_file(parent, final_path)
        if existing is None:
            return {final_path: final_raw}
        if existing != final_raw:
            raise OutboxBlock("immutable outbox acceptance collision")
        return None

    def verify_at(head: str) -> bool:
        return bool(final_path) and backend.read_file(head, final_path) == final_raw

    cas = bounded_ff_cas(
        backend,
        lane=lane,
        plan_at=plan_at,
        build_message=f"Record {lane} outbox acceptance {sequence} attempt {attempt}",
        verify_at=verify_at,
    )
    if late_conflict:
        raise OutboxBlock(
            "LATE_ATTEMPT_1_ACCEPTANCE_AFTER_ATTEMPT_2_SEALED: conflict "
            "persisted; attempt two requires exact adoption or Authority HOLD"
        )
    return {
        **final_record,
        "ledger_ref": ledger_ref(lane),
        "ledger_head": cas["head"],
        "cas": cas,
    }


def record_completion(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    attempt: int,
    child: Mapping[str, Any],
    evidence: Mapping[str, Any],
    child_recovery: bool = False,
) -> dict[str, Any]:
    item = read_next(backend, lane)
    if item.get("state") != "PENDING" or item.get("sequence") != sequence:
        raise OutboxBlock("completion does not bind current FIFO item")
    intent = _mapping(item.get("intent"), "completion intent")
    if child_recovery:
        recovery = _mapping(
            _mapping(item.get("child_recovery"), "completion recovery state").get(
                str(attempt)
            ),
            "completion recovery attempt",
        )
        acceptance = _mapping(
            recovery.get("acceptance"), "completion recovered acceptance"
        )
    else:
        acceptance = _mapping(
            _mapping(item.get("acceptance"), "completion acceptances").get(
                str(attempt)
            ),
            "completion acceptance",
        )
    locator_child = _mapping(acceptance.get("child"), "completion locator child")
    completed_child = normalize_child_for_intent(
        _mapping(child, "completion child"),
        intent=intent,
        attempt=attempt,
        same_run_recovery=child_recovery,
    )
    evidence_value = dict(_mapping(evidence, "completion evidence"))
    immutable_fields = (
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
        completed_child.get("status") != "completed"
        or not isinstance(completed_child.get("conclusion"), str)
        or not completed_child.get("conclusion")
        or any(
            completed_child.get(field) != locator_child.get(field)
            for field in immutable_fields
        )
        or (
            locator_child.get("status") == "completed"
            and (
                completed_child.get("status") != locator_child.get("status")
                or completed_child.get("conclusion")
                != locator_child.get("conclusion")
            )
        )
    ):
        raise OutboxBlock("completion is not the exact accepted child result")
    record = {
        "schema": COMPLETION_SCHEMA,
        "lane": _lane(lane),
        "sequence": _sequence(sequence),
        "fingerprint": intent["fingerprint"],
        "attempt": attempt,
        "child_recovery": child_recovery,
        "locator_child_sha256": acceptance["child_sha256"],
        "child": completed_child,
        "child_sha256": digest(completed_child),
        "evidence": evidence_value,
        "evidence_sha256": digest(evidence_value),
        "state": "COMPLETED_RESULT_OBSERVED",
        "productive_effect": False,
    }
    # Validate the complete immutable record before its CAS write.
    record = validate_completion_record(
        record,
        intent=intent,
        acceptance=acceptance,
        attempt=attempt,
        child_recovery=child_recovery,
    )

    def validate_current(current: Mapping[str, Any]) -> None:
        current_intent = _mapping(
            current.get("intent"), "completion CAS intent"
        )
        if current_intent.get("fingerprint") != intent.get("fingerprint"):
            raise OutboxBlock("completion intent changed during CAS")
        if child_recovery:
            current_recovery = _mapping(
                _mapping(
                    current.get("child_recovery"),
                    "completion CAS recovery state",
                ).get(str(attempt)),
                "completion CAS recovery attempt",
            )
            current_acceptance = _mapping(
                current_recovery.get("acceptance"),
                "completion CAS recovered acceptance",
            )
        else:
            current_acceptance = _mapping(
                _mapping(
                    current.get("acceptance"),
                    "completion CAS acceptances",
                ).get(str(attempt)),
                "completion CAS acceptance",
            )
        if current_acceptance.get("child_sha256") != acceptance.get(
            "child_sha256"
        ):
            raise OutboxBlock("completion acceptance changed during CAS")
        validate_completion_record(
            record,
            intent=current_intent,
            acceptance=current_acceptance,
            attempt=attempt,
            child_recovery=child_recovery,
        )

    return _append_immutable_record(
        backend,
        lane=lane,
        sequence=sequence,
        path=completion_path(
            lane, sequence, attempt, child_recovery=child_recovery
        ),
        record=record,
        message=(
            f"Record {lane} outbox completion {sequence} attempt {attempt}"
            + (" child-rerun" if child_recovery else "")
        ),
        validate_current=validate_current,
    )


def validate_same_run_result(
    value: Any,
    *,
    intent: Mapping[str, Any],
    acceptance: Mapping[str, Any],
    transport_attempt: int,
) -> dict[str, Any]:
    raw = _mapping(value, "same-run result")
    lane = _lane(intent.get("lane"))
    if lane != "exact-head-dispatch":
        raise OutboxBlock("same-run result is restricted to exact-head lane")
    locator_child = _mapping(
        acceptance.get("child"), "same-run accepted locator"
    )
    observed_child = normalize_child_for_intent(
        _mapping(raw.get("child"), "same-run observed child"),
        intent=intent,
        attempt=transport_attempt,
        same_run_recovery=True,
    )
    immutable_fields = (
        "run_id",
        "workflow_id",
        "workflow_path",
        "event",
        "repository",
        "head_sha",
        "display_title",
    )
    if (
        locator_child.get("run_attempt") != 1
        or observed_child.get("run_attempt") != 2
        or observed_child.get("status") != "completed"
        or any(
            observed_child.get(field) != locator_child.get(field)
            for field in immutable_fields
        )
    ):
        raise OutboxBlock("same-run result does not bind exact attempt two")
    fake_acceptance = {
        "child": observed_child,
        "child_sha256": digest(observed_child),
    }
    fake_completion = {
        "schema": COMPLETION_SCHEMA,
        "lane": lane,
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "attempt": transport_attempt,
        "child_recovery": False,
        "locator_child_sha256": fake_acceptance["child_sha256"],
        "child": observed_child,
        "child_sha256": digest(observed_child),
        "evidence": raw.get("evidence"),
        "evidence_sha256": raw.get("evidence_sha256"),
        "state": "COMPLETED_RESULT_OBSERVED",
        "productive_effect": False,
    }
    completed = validate_completion_record(
        fake_completion,
        intent=intent,
        acceptance=fake_acceptance,
        attempt=transport_attempt,
        child_recovery=False,
    )
    expected_d0 = 2 if observed_child.get("conclusion") == "success" else 3
    if (
        raw.get("schema") != SAME_RUN_RESULT_SCHEMA
        or raw.get("lane") != lane
        or raw.get("sequence") != intent.get("sequence")
        or raw.get("fingerprint") != intent.get("fingerprint")
        or raw.get("transport_attempt") != transport_attempt
        or raw.get("locator_child_sha256") != acceptance.get("child_sha256")
        or raw.get("child_sha256") != completed.get("child_sha256")
        or raw.get("d0") != expected_d0
        or raw.get("state")
        != ("REOBSERVE" if expected_d0 == 2 else "REQUEST_AUTHORITY")
        or raw.get("dominates_prior_attempt") is not True
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("same-run result binding mismatch")
    return {
        "schema": SAME_RUN_RESULT_SCHEMA,
        "lane": lane,
        "sequence": intent["sequence"],
        "fingerprint": intent["fingerprint"],
        "transport_attempt": transport_attempt,
        "locator_child_sha256": acceptance["child_sha256"],
        "child": observed_child,
        "child_sha256": completed["child_sha256"],
        "evidence": completed["evidence"],
        "evidence_sha256": completed["evidence_sha256"],
        "d0": expected_d0,
        "state": "REOBSERVE" if expected_d0 == 2 else "REQUEST_AUTHORITY",
        "dominates_prior_attempt": True,
        "productive_effect": False,
    }


def record_same_run_result(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    fingerprint: str,
    transport_attempt: int,
    child: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    item = lookup(
        backend,
        lane=lane,
        sequence=sequence,
        fingerprint=fingerprint,
    )
    intent = _mapping(item.get("intent"), "same-run intent")
    acceptance = _mapping(
        _mapping(item.get("acceptance"), "same-run acceptances").get(
            str(transport_attempt)
        ),
        "same-run acceptance",
    )
    observed_child = normalize_child_for_intent(
        _mapping(child, "same-run child"),
        intent=intent,
        attempt=transport_attempt,
        same_run_recovery=True,
    )
    draft = {
        "schema": SAME_RUN_RESULT_SCHEMA,
        "lane": lane,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "transport_attempt": transport_attempt,
        "locator_child_sha256": acceptance["child_sha256"],
        "child": observed_child,
        "child_sha256": digest(observed_child),
        "evidence": dict(_mapping(evidence, "same-run evidence")),
        "evidence_sha256": digest(dict(evidence)),
        "d0": 2 if observed_child.get("conclusion") == "success" else 3,
        "state": (
            "REOBSERVE"
            if observed_child.get("conclusion") == "success"
            else "REQUEST_AUTHORITY"
        ),
        "dominates_prior_attempt": True,
        "productive_effect": False,
    }
    record = validate_same_run_result(
        draft,
        intent=intent,
        acceptance=acceptance,
        transport_attempt=transport_attempt,
    )
    path = same_run_result_path(
        lane, sequence, transport_attempt, observed_child["run_attempt"]
    )
    raw = canonical_bytes(record)
    supersession_path = terminal_supersession_path(lane, sequence)
    final_supersession: dict[str, Any] | None = None

    def sequence_view(parent: str) -> dict[str, Any]:
        class _SequenceView:
            repository = backend.repository

            def read_file(self, commit: str, requested_path: str) -> bytes | None:
                if requested_path == meta_path(lane):
                    return canonical_bytes(
                        {
                            "schema": META_SCHEMA,
                            "lane": lane,
                            "next_seq": sequence + 1,
                            "drain_seq": sequence,
                        }
                    )
                if requested_path == terminal_path(lane, sequence):
                    return None
                return backend.read_file(commit, requested_path)

        return _read_next_at(_SequenceView(), parent, lane)  # type: ignore[arg-type]

    def plan_at(parent: str) -> Mapping[str, bytes] | None:
        nonlocal final_supersession
        persisted = _read_intent_by_fingerprint(
            backend, parent, lane, fingerprint
        )
        if persisted is None or persisted.get("sequence") != sequence:
            raise OutboxBlock("same-run intent disappeared during CAS")
        current = sequence_view(parent)
        current_acceptance = _mapping(
            _mapping(current.get("acceptance"), "same-run CAS acceptances").get(
                str(transport_attempt)
            ),
            "same-run CAS acceptance",
        )
        if validate_same_run_result(
            record,
            intent=_mapping(current.get("intent"), "same-run CAS intent"),
            acceptance=current_acceptance,
            transport_attempt=transport_attempt,
        ) != record:
            raise OutboxBlock("same-run result changed during CAS")
        if record["d0"] == 2:
            sealed_main = _sha(
                _mapping(
                    _mapping(current.get("intent"), "same-run CAS intent").get(
                        "payload"
                    ),
                    "same-run CAS payload",
                ).get("main_head_sha"),
                "same-run sealed main",
            )
            if backend.get_main_head() != sealed_main:
                raise OutboxBlock(
                    "OUTBOX_EVALUATOR_SUPERSEDED: favorable same-run result "
                    "cannot cross evaluator drift"
                )
        changes: dict[str, bytes] = {}
        existing = backend.read_file(parent, path)
        if existing is None:
            changes[path] = raw
        elif existing != raw:
            raise OutboxBlock("immutable same-run result collision")
        prior_terminal = _read_json(
            backend,
            parent,
            terminal_path(lane, sequence),
            required=False,
        )
        if prior_terminal is not None:
            prior_terminal = dict(
                _mapping(prior_terminal, "same-run prior terminal")
            )
            if (
                prior_terminal.get("schema") != TERMINAL_SCHEMA
                or prior_terminal.get("lane") != lane
                or prior_terminal.get("sequence") != sequence
                or prior_terminal.get("fingerprint") != fingerprint
                or prior_terminal.get("d0") not in {2, 3}
            ):
                raise OutboxBlock("same-run result cannot supersede this terminal")
            if prior_terminal.get("d0") == record["d0"]:
                return changes or None
            if record["d0"] == 2:
                prior_evidence = _mapping(
                    prior_terminal.get("evidence"),
                    "same-run prior terminal evidence",
                )
                prior_exhaustion = _mapping(
                    prior_evidence.get("exhaustion"),
                    "same-run prior terminal exhaustion",
                )
                prior_completion = _mapping(
                    _mapping(
                        current.get("completion"),
                        "same-run prior completions",
                    ).get(str(transport_attempt)),
                    "same-run prior adverse completion",
                )
                if (
                    prior_evidence.get("d0") != 3
                    or prior_exhaustion.get("mode") != "CHILD_RESULT_ADVERSE"
                    or prior_exhaustion.get("transport_attempt")
                    != transport_attempt
                    or prior_exhaustion.get("successor_sha256")
                    != prior_completion.get("child_sha256")
                    or prior_exhaustion.get("completion_evidence_sha256")
                    != prior_completion.get("evidence_sha256")
                ):
                    raise OutboxBlock(
                        "favorable same-run result cannot supersede an "
                        "Authority or ambiguity terminal"
                    )
            effective_view = {
                **current,
                "same_run_result": {
                    **dict(
                        _mapping(
                            current.get("same_run_result"),
                            "same-run CAS results",
                        )
                    ),
                    str(transport_attempt): record,
                },
            }
            attempts = sorted(
                int(item)
                for item in _mapping(
                    current.get("transport"), "same-run CAS transports"
                )
            )
            if record["d0"] == 3:
                effective_reason = "SAME_RUN_EXACT_RESULT_ADVERSE"
                effective_state = "EFFECTIVE_REQUEST_AUTHORITY"
                effective_evidence = {
                    "schema": TERMINAL_EVIDENCE_SCHEMA,
                    "d0": 3,
                    "state": "REQUEST_AUTHORITY",
                    "reason": effective_reason,
                    "exhaustion": {
                        "schema": EXHAUSTION_SCHEMA,
                        "lane": lane,
                        "sequence": sequence,
                        "fingerprint": fingerprint,
                        "mode": "SAME_RUN_RESULT_ADVERSE",
                        "attempts": attempts,
                        "first_blocker": effective_reason,
                        "transport_attempt": transport_attempt,
                        "successor": record["child"],
                        "successor_sha256": record["child_sha256"],
                        "verified": True,
                        "productive_effect": False,
                    },
                    "completion_claims": empty_completion_claims(),
                    "productive_effect": False,
                    "effect_ack": "NOT_REQUIRED",
                }
            else:
                effective_reason = "SAME_RUN_EXACT_RESULT_SUCCESS"
                effective_state = "EFFECTIVE_REOBSERVE"
                completion_evidence = _mapping(
                    record.get("evidence"),
                    "same-run success completion evidence",
                )
                business_artifact = dict(
                    _mapping(
                        completion_evidence.get("artifact"),
                        "same-run success business artifact",
                    )
                )
                effective_evidence = {
                    "schema": TERMINAL_EVIDENCE_SCHEMA,
                    "d0": 2,
                    "state": "REOBSERVE",
                    "reason": "EXACT_HEAD_RESULT_PERSISTED",
                    "business_receipt": {
                        "schema": BUSINESS_RECEIPT_SCHEMA,
                        "lane": lane,
                        "sequence": sequence,
                        "fingerprint": fingerprint,
                        "outcome": "EXACT_HEAD_TERMINAL_CONTINUATION",
                        "attempt": transport_attempt,
                        "run_id": record["child"]["run_id"],
                        "run_attempt": record["child"]["run_attempt"],
                        "workflow_id": record["child"]["workflow_id"],
                        "workflow_path": record["child"]["workflow_path"],
                        "head_sha": record["child"]["head_sha"],
                        "locator_child_sha256": current_acceptance[
                            "child_sha256"
                        ],
                        "child_sha256": record["child_sha256"],
                        "child_recovery": False,
                        "same_run_result": True,
                        "artifact": business_artifact,
                        "completion_evidence_sha256": record[
                            "evidence_sha256"
                        ],
                        "evidence_sha256": digest(business_artifact),
                        "verified": True,
                        "productive_effect": False,
                    },
                    "completion_claims": empty_completion_claims(),
                    "productive_effect": False,
                    "effect_ack": "NOT_REQUIRED",
                }
            effective_evidence = validate_terminal_evidence(
                effective_evidence, next_item=effective_view
            )
            final_supersession = {
                "schema": TERMINAL_SUPERSESSION_SCHEMA,
                "lane": lane,
                "sequence": sequence,
                "fingerprint": fingerprint,
                "prior_terminal_sha256": digest(prior_terminal),
                "same_run_result_sha256": digest(record),
                "d0": record["d0"],
                "state": effective_state,
                "effective_reason": effective_reason,
                "evidence": effective_evidence,
                "evidence_sha256": digest(effective_evidence),
                "productive_effect": False,
            }
            supersession_raw = canonical_bytes(final_supersession)
            existing_supersession = backend.read_file(parent, supersession_path)
            if existing_supersession is None:
                changes[supersession_path] = supersession_raw
            elif existing_supersession != supersession_raw:
                raise OutboxBlock("immutable terminal supersession collision")
        return changes or None

    def verify_at(head: str) -> bool:
        if backend.read_file(head, path) != raw:
            return False
        if final_supersession is None:
            return True
        return backend.read_file(head, supersession_path) == canonical_bytes(
            final_supersession
        )

    cas = bounded_ff_cas(
        backend,
        lane=lane,
        plan_at=plan_at,
        build_message=(
            f"Record {lane} same-run result {sequence} attempt "
            f"{observed_child['run_attempt']}"
        ),
        verify_at=verify_at,
    )
    return {
        **record,
        "terminal_supersession": final_supersession,
        "ledger_ref": ledger_ref(lane),
        "ledger_head": cas["head"],
        "cas": cas,
    }


def _normalize_child_retry_evidence(
    value: Any,
    *,
    intent: Mapping[str, Any],
    acceptance: Mapping[str, Any],
    transport_attempt: int,
) -> dict[str, Any]:
    """Bind a terminal zero-job REST observation to a sealed child locator."""
    raw = dict(_mapping(value, "child-rerun retry evidence"))
    lane = _lane(intent.get("lane"))
    sequence = _sequence(intent.get("sequence"))
    fingerprint = _digest(intent.get("fingerprint"), "child retry fingerprint")
    accepted_child = _mapping(
        acceptance.get("child"), "child retry accepted locator"
    )
    observed_child = _validate_observed_child_for_acceptance(
        raw.get("observed_terminal_child"),
        intent=intent,
        acceptance=acceptance,
        transport_attempt=transport_attempt,
    )
    expected_keys = {
        "schema",
        "lane",
        "sequence",
        "fingerprint",
        "transport_attempt",
        "classification",
        "first_blocker",
        "accepted_child_sha256",
        "observed_terminal_child",
        "observed_terminal_child_sha256",
        "jobs_total_count",
        "verified",
        "productive_effect",
    }
    if (
        lane not in REVIEW_TRANSPORT_LANES
        or transport_attempt != 1
        or set(raw) != expected_keys
        or raw.get("schema") != CHILD_RETRY_EVIDENCE_SCHEMA
        or raw.get("lane") != lane
        or raw.get("sequence") != sequence
        or raw.get("fingerprint") != fingerprint
        or raw.get("transport_attempt") != 1
        or raw.get("classification") != "ZERO_JOB_CONCURRENCY_CANCELLED"
        or raw.get("first_blocker")
        != "ATTEMPT_1_ZERO_JOB_CONCURRENCY_CANCELLED"
        or raw.get("accepted_child_sha256") != acceptance.get("child_sha256")
        or raw.get("accepted_child_sha256") != digest(dict(accepted_child))
        or observed_child.get("run_attempt") != 1
        or observed_child.get("status") != "completed"
        or observed_child.get("conclusion") != "cancelled"
        or raw.get("observed_terminal_child_sha256") != digest(observed_child)
        or raw.get("jobs_total_count") != 0
        or raw.get("verified") is not True
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("child-rerun retry evidence binding mismatch")
    return {
        "schema": CHILD_RETRY_EVIDENCE_SCHEMA,
        "lane": lane,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "transport_attempt": 1,
        "classification": "ZERO_JOB_CONCURRENCY_CANCELLED",
        "first_blocker": "ATTEMPT_1_ZERO_JOB_CONCURRENCY_CANCELLED",
        "accepted_child_sha256": acceptance["child_sha256"],
        "observed_terminal_child": observed_child,
        "observed_terminal_child_sha256": digest(observed_child),
        "jobs_total_count": 0,
        "verified": True,
        "productive_effect": False,
    }


def prepare_child_rerun(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    transport_attempt: int,
    retry_evidence: Mapping[str, Any],
    actor_run_id: int,
    actor_run_attempt: int,
) -> dict[str, Any]:
    lane = _lane(lane)
    if lane not in REVIEW_TRANSPORT_LANES:
        raise OutboxBlock("child rerun is restricted to review lanes")
    item = read_next(backend, lane)
    if item.get("state") != "PENDING" or item.get("sequence") != sequence:
        raise OutboxBlock("child rerun does not bind current FIFO item")
    intent = _mapping(item.get("intent"), "child-rerun intent")
    acceptance = _mapping(
        _mapping(item.get("acceptance"), "child-rerun acceptances").get(
            str(transport_attempt)
        ),
        "child-rerun original acceptance",
    )
    child = _mapping(acceptance.get("child"), "child-rerun original child")
    evidence = _normalize_child_retry_evidence(
        retry_evidence,
        intent=intent,
        acceptance=acceptance,
        transport_attempt=transport_attempt,
    )
    observed_terminal = _mapping(
        evidence.get("observed_terminal_child"),
        "child-rerun observed terminal child",
    )
    record = {
        "schema": CHILD_RERUN_SCHEMA,
        "lane": lane,
        "sequence": sequence,
        "fingerprint": intent["fingerprint"],
        "transport_attempt": transport_attempt,
        "target_run_id": observed_terminal["run_id"],
        "target_run_attempt": 2,
        "endpoint": (
            f"repos/{intent['repository']}/actions/runs/{child['run_id']}/rerun"
        ),
        "actor_run_id": _positive_int(actor_run_id, "child-rerun actor run id"),
        "actor_run_attempt": _positive_int(
            actor_run_attempt, "child-rerun actor run attempt"
        ),
        "retry_evidence": evidence,
        "state": "PRE_EFFECT_REOBSERVED",
        "productive_effect": False,
    }

    def validate_current(current: Mapping[str, Any]) -> None:
        current_intent = _mapping(
            current.get("intent"), "child-rerun CAS intent"
        )
        current_acceptance = _mapping(
            _mapping(
                current.get("acceptance"), "child-rerun CAS acceptances"
            ).get(str(transport_attempt)),
            "child-rerun CAS original acceptance",
        )
        current_child = _mapping(
            current_acceptance.get("child"),
            "child-rerun CAS original child",
        )
        current_recovery = _mapping(
            current.get("child_recovery"), "child-rerun CAS recovery state"
        ).get(str(transport_attempt))
        current_evidence = _normalize_child_retry_evidence(
            evidence,
            intent=current_intent,
            acceptance=current_acceptance,
            transport_attempt=transport_attempt,
        )
        if (
            current_intent.get("fingerprint") != intent.get("fingerprint")
            or current_acceptance.get("child_sha256")
            != acceptance.get("child_sha256")
            or current_child != child
            or current_evidence != evidence
            or str(transport_attempt)
            in _mapping(current.get("completion"), "child-rerun CAS completions")
            or current_recovery is not None
        ):
            raise OutboxBlock(
                "child rerun state changed or exact result already exists during CAS"
            )

    return _append_immutable_record(
        backend,
        lane=lane,
        sequence=sequence,
        path=child_rerun_path(lane, sequence, transport_attempt),
        record=record,
        message=(
            f"Prepare {lane} child rerun {sequence} transport {transport_attempt}"
        ),
        validate_current=validate_current,
    )


def record_child_rerun_acceptance(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    transport_attempt: int,
    child: Mapping[str, Any],
) -> dict[str, Any]:
    item = read_next(backend, lane)
    if item.get("state") != "PENDING" or item.get("sequence") != sequence:
        raise OutboxBlock("child-rerun acceptance does not bind current FIFO item")
    intent = _mapping(item.get("intent"), "child-rerun acceptance intent")
    recovery = _mapping(
        _mapping(item.get("child_recovery"), "child recovery state").get(
            str(transport_attempt)
        ),
        "child-rerun state",
    )
    rerun = _mapping(recovery.get("rerun"), "child-rerun pre-effect record")
    original = _mapping(
        _mapping(
            _mapping(item.get("acceptance"), "child-rerun acceptances").get(
                str(transport_attempt)
            ),
            "child-rerun original acceptance",
        ).get("child"),
        "child-rerun original child",
    )
    normalized_child = normalize_child_for_intent(
        _mapping(child, "recovered child"),
        intent=intent,
        attempt=transport_attempt,
        same_run_recovery=True,
    )
    if (
        rerun.get("target_run_id") != normalized_child.get("run_id")
        or normalized_child.get("run_id") != original.get("run_id")
        or normalized_child.get("run_attempt") != 2
    ):
        raise OutboxBlock("recovered child is not exact same-run attempt two")
    record = {
        "schema": CHILD_RERUN_ACCEPTANCE_SCHEMA,
        "lane": lane,
        "sequence": sequence,
        "fingerprint": intent["fingerprint"],
        "transport_attempt": transport_attempt,
        "child": normalized_child,
        "child_sha256": digest(normalized_child),
        "state": "CHILD_RERUN_ACCEPTED_LOCATOR",
        "productive_effect": False,
    }

    def validate_current(current: Mapping[str, Any]) -> None:
        current_intent = _mapping(
            current.get("intent"), "child-rerun acceptance CAS intent"
        )
        current_recovery = _mapping(
            _mapping(
                current.get("child_recovery"),
                "child-rerun acceptance CAS recovery state",
            ).get(str(transport_attempt)),
            "child-rerun acceptance CAS recovery attempt",
        )
        current_rerun = _mapping(
            current_recovery.get("rerun"),
            "child-rerun acceptance CAS pre-effect record",
        )
        current_original = _mapping(
            _mapping(
                _mapping(
                    current.get("acceptance"),
                    "child-rerun acceptance CAS originals",
                ).get(str(transport_attempt)),
                "child-rerun acceptance CAS original",
            ).get("child"),
            "child-rerun acceptance CAS original child",
        )
        if (
            current_intent.get("fingerprint") != intent.get("fingerprint")
            or current_rerun != rerun
            or current_original != original
            or normalize_child_for_intent(
                normalized_child,
                intent=current_intent,
                attempt=transport_attempt,
                same_run_recovery=True,
            )
            != normalized_child
        ):
            raise OutboxBlock("child-rerun acceptance state changed during CAS")

    return _append_immutable_record(
        backend,
        lane=lane,
        sequence=sequence,
        path=child_rerun_acceptance_path(lane, sequence, transport_attempt),
        record=record,
        message=(
            f"Record {lane} child-rerun acceptance {sequence} "
            f"transport {transport_attempt}"
        ),
        validate_current=validate_current,
    )


def empty_completion_claims() -> dict[str, bool]:
    return {key: False for key in COMPLETION_CLAIM_KEYS}


def _claim_key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _technical_code(value: Any, label: str, allowed: Sequence[str]) -> str:
    """Accept one enumerated machine code, never caller-authored claim text."""
    if (
        not isinstance(value, str)
        or re.fullmatch(r"[A-Z][A-Z0-9_]{0,127}", value) is None
        or value not in set(allowed)
    ):
        raise OutboxBlock(f"{label} is not an authorized technical code")
    return value


def _reject_recursive_completion_claims(value: Any, *, path: str = "evidence") -> None:
    forbidden = {_claim_key(key) for key in COMPLETION_CLAIM_KEYS}
    forbidden.update({"merged", "approved", "published", "deployed"})
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = _claim_key(key)
            if normalized in forbidden and item is not False:
                raise OutboxBlock(
                    f"outbox terminal evidence contains forbidden claim at {path}.{key}"
                )
            if normalized in {"state", "status", "outcome", "claim", "effectack"}:
                claimed_value = _claim_key(item)
                if claimed_value in forbidden or claimed_value in {
                    "pass",
                    "finalpass",
                    "effectackdone",
                }:
                    raise OutboxBlock(
                        f"outbox terminal evidence contains forbidden claim value at {path}.{key}"
                    )
            _reject_recursive_completion_claims(item, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_recursive_completion_claims(item, path=f"{path}[{index}]")


def _validate_terminal_continuation(value: Any) -> dict[str, Any]:
    continuation = dict(_mapping(value, "outbox terminal continuation"))
    expected_keys = {
        "schema",
        "mode",
        "owner",
        "next_action",
        "resume_events",
        "persistence_run_terminal",
        "client_return_allowed",
    }
    modes = {
        "AWAIT_BOUND_RESULT",
        "AWAIT_EXACT_EVENT",
        "AWAIT_WORKFLOW_RESULT",
        "CONTINUE",
        "REOBSERVE",
        "REQUEST_AUTHORITY",
    }
    owners = {
        "AUTHORITY_ADMIN",
        "REPOSITORY_AUTOMATION",
        "REPOSITORY_EVENT_LOOP",
        "REQUESTED_REVIEW_EXECUTOR",
    }
    resume_events = continuation.get("resume_events")
    next_action = continuation.get("next_action")
    if (
        set(continuation) != expected_keys
        or continuation.get("schema") != "qikvrt.causal-continuation.v1"
        or continuation.get("mode") not in modes
        or continuation.get("owner") not in owners
        or not isinstance(next_action, str)
        or re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", next_action) is None
        or not isinstance(resume_events, list)
        or not (1 <= len(resume_events) <= 8)
        or any(
            not isinstance(item, str)
            or re.fullmatch(r"[a-z][a-z0-9_.-]{0,95}", item) is None
            for item in resume_events
        )
        or continuation.get("persistence_run_terminal") is not False
        or continuation.get("client_return_allowed") is not False
    ):
        raise OutboxBlock("outbox terminal continuation contract is invalid")

    # Composite aliases are not made safe by avoiding one exact key spelling.
    # Reject completion/effect semantics by stem across every continuation
    # token while retaining a small positive vocabulary for actual routing.
    forbidden_stems = {
        "approval",
        "approve",
        "atariboot",
        "atariexecution",
        "authoritymirrorsync",
        "deployment",
        "deploy",
        "effectackdone",
        "finalpass",
        "merge",
        "mirror synchronized",
        "mirrorsync",
        "pass",
        "physicalatari",
        "publication",
        "publish",
        "release",
    }
    for label, token in (
        ("mode", continuation["mode"]),
        ("owner", continuation["owner"]),
        ("next_action", continuation["next_action"]),
        *(('resume_event', item) for item in resume_events),
    ):
        normalized = _claim_key(token)
        if any(_claim_key(stem) in normalized for stem in forbidden_stems):
            raise OutboxBlock(
                f"outbox terminal continuation contains forbidden semantics in {label}"
            )
    return continuation


TRANSPORT_ABSENCE_BLOCKERS = frozenset(
    {
        "REPEATED_RULESET_TRANSPORT_UNACKNOWLEDGED",
        "REPEATED_REQUESTED_REVIEW_TRANSPORT_UNACKNOWLEDGED",
        "REPEATED_EXACT_HEAD_TRANSPORT_UNACKNOWLEDGED",
        "REPEATED_EXACT_REVIEW_TRANSPORT_UNACKNOWLEDGED",
        "REPEATED_MESH_REVIEW_TRANSPORT_UNACKNOWLEDGED",
    }
)
EXACT_CURSOR_BOUND_BLOCKERS = frozenset(
    {
        "BOUND_EVIDENCE_AMBIGUOUS",
        "BOUND_EVIDENCE_AMBIGUITY_SET_EXCEEDED",
        "RECOVERY_QUERY_BOUND_EXCEEDED",
        "RECOVERY_QUERY_INVENTORY_INCONSISTENT",
        "REPEATED_EXACT_HEAD_TRANSPORT_UNACKNOWLEDGED",
        "REPEATED_EXACT_REVIEW_TRANSPORT_UNACKNOWLEDGED",
    }
)
MESH_CURSOR_BOUND_BLOCKERS = frozenset(
    {
        "MESH_REVIEW_RECOVERY_QUERY_BOUND_EXCEEDED",
        "MESH_REVIEW_RECOVERY_QUERY_INVENTORY_INCONSISTENT",
        "MESH_REVIEW_TRANSPORT_CHILD_AMBIGUOUS",
        "MESH_REVIEW_TRANSPORT_CHILD_SET_EXCEEDED",
        "REPEATED_MESH_REVIEW_TRANSPORT_UNACKNOWLEDGED",
    }
)
CURSOR_BOUND_BLOCKERS = EXACT_CURSOR_BOUND_BLOCKERS | MESH_CURSOR_BOUND_BLOCKERS
MAIN_BOUND_AUTHORITY_BLOCKERS = CURSOR_BOUND_BLOCKERS | frozenset(
    {
        "OUTBOX_TARGET_WORKFLOW_SUPERSEDED",
        "SOURCE_ATTEMPT_1_ACTION_REQUIRED",
    }
)
EXACT_CURSOR_OBSERVATION_KEYS = frozenset(
    {
        "transport_attempt",
        "retry_scan_cursor_record_sha256",
        "retry_scan_cursor_sha256",
        "retry_scan_cursor_state",
        "retry_scan_cursor_ledger_ref",
        "retry_scan_cursor_ledger_head",
        "query_window_start",
        "query_window_end",
        "upper_bound_run_id",
        "last_scanned_run_id",
        "page_cap",
        "pages_scanned",
        "declared_total_count",
        "queried_page",
        "page_run_ids_sha256",
        "cumulative_run_ids_sha256",
        "observed_unique_run_count",
        "inventory_consistent",
        "inventory_blocker",
        "candidate_set_sha256",
        "bound_successor_count",
        "scan_complete",
        "sealed_main_head_sha",
        "observed_main_head_sha",
    }
)


def _validate_observed_subject_shape(
    sealed: Mapping[str, Any], observed: Mapping[str, Any]
) -> None:
    """Require a type- and locator-preserving live subject observation."""
    if set(observed) != set(sealed):
        raise OutboxBlock("observed subject key set differs from sealed subject")
    for key, sealed_value in sealed.items():
        observed_value = observed.get(key)
        if isinstance(sealed_value, Mapping):
            if not isinstance(observed_value, Mapping):
                raise OutboxBlock("observed subject nested shape is invalid")
            _validate_observed_subject_shape(sealed_value, observed_value)
        elif isinstance(sealed_value, bool):
            if not isinstance(observed_value, bool):
                raise OutboxBlock("observed subject boolean shape is invalid")
        elif isinstance(sealed_value, int):
            if (
                isinstance(observed_value, bool)
                or not isinstance(observed_value, int)
                or observed_value < 1
            ):
                raise OutboxBlock("observed subject ordinal is invalid")
        elif isinstance(sealed_value, str):
            if not isinstance(observed_value, str) or not observed_value:
                raise OutboxBlock("observed subject string locator is invalid")
            if HEX40.fullmatch(sealed_value) is not None and HEX40.fullmatch(
                observed_value
            ) is None:
                raise OutboxBlock("observed subject SHA-40 locator is invalid")
            if HEX64.fullmatch(sealed_value) is not None and HEX64.fullmatch(
                observed_value
            ) is None:
                raise OutboxBlock("observed subject SHA-256 locator is invalid")
        else:
            raise OutboxBlock("sealed subject contains unsupported locator type")


def _validate_observed_child_for_acceptance(
    value: Any,
    *,
    intent: Mapping[str, Any],
    acceptance: Mapping[str, Any],
    transport_attempt: int,
    same_run_result: bool = False,
) -> dict[str, Any]:
    """Bind a later REST result to an immutable transport acceptance locator."""
    observed = normalize_child_for_intent(
        _mapping(value, "observed accepted child"),
        intent=intent,
        attempt=transport_attempt,
        same_run_recovery=same_run_result,
    )
    locator = _mapping(acceptance.get("child"), "accepted child locator")
    immutable_fields = (
        "run_id",
        "workflow_id",
        "workflow_path",
        "event",
        "repository",
        "head_sha",
        "display_title",
    )
    if (
        observed.get("status") != "completed"
        or not isinstance(observed.get("conclusion"), str)
        or not observed.get("conclusion")
        or any(observed.get(field) != locator.get(field) for field in immutable_fields)
        or (
            same_run_result
            and (
                intent.get("lane") != "exact-head-dispatch"
                or locator.get("run_attempt") != 1
                or observed.get("run_attempt") != 2
            )
        )
        or (
            not same_run_result
            and observed.get("run_attempt") != locator.get("run_attempt")
        )
        or (
            not same_run_result
            and locator.get("status") == "completed"
            and (
                locator.get("status") != observed.get("status")
                or locator.get("conclusion") != observed.get("conclusion")
            )
        )
    ):
        raise OutboxBlock("observed child differs from accepted locator")
    return observed


def _validate_admission_action_required_receipt(
    value: Any,
    *,
    observed_child: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the existing Admission terminal receipt without importing it.

    The receipt is produced by the dedicated Admission workflow.  Core binds
    its source projection back to the exact accepted child; the surrounding
    Authority-observation record then content-addresses both this receipt and
    the sealed Core intent/acceptance.
    """
    raw = dict(_mapping(value, "Admission action-required receipt"))
    claimed = raw.get("receipt_sha256")
    unsigned = dict(raw)
    unsigned.pop("receipt_sha256", None)
    source = dict(
        _mapping(raw.get("source"), "Admission action-required source")
    )
    source_keys = {
        "run_id",
        "run_attempt",
        "workflow_id",
        "workflow_path",
        "repository",
        "repository_id",
        "event",
        "head_branch",
        "head_sha",
        "display_title",
        "status",
        "conclusion",
        "created_at",
        "jobs_total",
        "artifacts_total",
        "pull_requests",
    }
    immutable_fields = (
        "run_id",
        "run_attempt",
        "workflow_id",
        "workflow_path",
        "repository",
        "event",
        "head_sha",
        "display_title",
        "status",
        "conclusion",
    )
    timestamp = re.compile(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    )
    if (
        set(raw)
        != {
            "schema",
            "source",
            "source_key",
            "state",
            "first_blocker",
            "d0",
            "native_account_review_authorized",
            "completion_claims",
            "receipt_sha256",
        }
        or set(source) != source_keys
        or raw.get("schema")
        != "qikvrt_review_admission_terminal_receipt_v1"
        or raw.get("state") != "ACTION_REQUIRED_D0_3"
        or raw.get("first_blocker") != "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
        or raw.get("d0") != 3
        or raw.get("native_account_review_authorized") is not False
        or raw.get("completion_claims")
        != {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        }
        or claimed != compact_digest(unsigned)
        or raw.get("source_key")
        != (
            f"{source.get('workflow_id')}:{source.get('run_id')}:"
            f"{source.get('run_attempt')}"
        )
        or any(
            source.get(field) != observed_child.get(field)
            for field in immutable_fields
        )
        or source.get("head_branch") != "main"
        or isinstance(source.get("repository_id"), bool)
        or not isinstance(source.get("repository_id"), int)
        or source.get("repository_id") < 1
        or not isinstance(source.get("created_at"), str)
        or timestamp.fullmatch(source.get("created_at")) is None
        or source.get("jobs_total") != 0
        or source.get("artifacts_total") != 0
        or source.get("pull_requests") != []
    ):
        raise OutboxBlock("Admission action-required receipt binding mismatch")
    return raw


MESH_COMPLETION_INVENTORY_KEYS = frozenset(
    {
        "jobs_total_count",
        "jobs_set_sha256",
        "jobs_pages_scanned",
        "jobs_page_cap",
        "jobs_scan_complete",
        "artifacts_total_count",
        "artifact_inventory_sha256",
        "artifacts_pages_scanned",
        "artifacts_page_cap",
        "artifacts_scan_complete",
        "observation_started_at",
        "observation_completed_at",
    }
)


def _validate_mesh_completion_observation_context(
    raw: Mapping[str, Any],
    *,
    intent: Mapping[str, Any],
    acceptances: Mapping[str, Any],
    completions: Mapping[str, Any],
    child_recovery: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind a complete Mesh REST inventory to one accepted child locator."""
    if intent.get("lane") != "mesh-review-successor-dispatch":
        raise OutboxBlock("Mesh completion observation is outside its lane")
    use_recovery = raw.get("child_recovery")
    if not isinstance(use_recovery, bool) or raw.get("transport_attempt") != 1:
        raise OutboxBlock("Mesh completion acceptance selector is invalid")
    recovery = child_recovery.get("1")
    if use_recovery:
        acceptance = (
            recovery.get("acceptance") if isinstance(recovery, Mapping) else None
        )
        completion = (
            recovery.get("completion") if isinstance(recovery, Mapping) else None
        )
    else:
        acceptance = acceptances.get("1")
        completion = completions.get("1")
    if not isinstance(acceptance, Mapping) or completion is not None:
        raise OutboxBlock("Mesh completion observation lacks an uncompleted acceptance")

    child = normalize_child_for_intent(
        _mapping(raw.get("observed_child"), "Mesh observed completed child"),
        intent=intent,
        attempt=1,
        same_run_recovery=use_recovery,
    )
    locator = _mapping(acceptance.get("child"), "Mesh accepted child locator")
    immutable_fields = (
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
        child.get("status") != "completed"
        or child.get("conclusion") not in TERMINAL_RUN_CONCLUSIONS
        or any(child.get(field) != locator.get(field) for field in immutable_fields)
        or (
            locator.get("status") == "completed"
            and (
                locator.get("status") != child.get("status")
                or locator.get("conclusion") != child.get("conclusion")
            )
        )
        or raw.get("accepted_child_sha256") != acceptance.get("child_sha256")
        or raw.get("observed_child_sha256") != digest(child)
    ):
        raise OutboxBlock("Mesh completed child differs from accepted locator")

    timestamp = re.compile(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
    )
    started = raw.get("observation_started_at")
    completed = raw.get("observation_completed_at")
    if (
        not isinstance(started, str)
        or timestamp.fullmatch(started) is None
        or not isinstance(completed, str)
        or timestamp.fullmatch(completed) is None
        or started > completed
    ):
        raise OutboxBlock("Mesh completion observation window is invalid")
    return dict(acceptance), child


def _validate_complete_mesh_inventory(raw: Mapping[str, Any]) -> None:
    """Validate complete bounded jobs/artifact inventories, including empty artifacts."""
    for prefix, count_key, digest_key in (
        ("jobs", "jobs_total_count", "jobs_set_sha256"),
        ("artifacts", "artifacts_total_count", "artifact_inventory_sha256"),
    ):
        count = raw.get(count_key)
        pages = raw.get(f"{prefix}_pages_scanned")
        cap = raw.get(f"{prefix}_page_cap")
        if (
            isinstance(count, bool)
            or not isinstance(count, int)
            or count < (1 if prefix == "jobs" else 0)
            or isinstance(pages, bool)
            or not isinstance(pages, int)
            or isinstance(cap, bool)
            or not isinstance(cap, int)
            or not (1 <= cap <= 100)
            or pages != max(1, (count + 99) // 100)
            or pages > cap
            or raw.get(f"{prefix}_scan_complete") is not True
            or HEX64.fullmatch(str(raw.get(digest_key))) is None
        ):
            raise OutboxBlock(f"Mesh {prefix} inventory is not complete and bounded")


def _validate_bounded_mesh_inventory(raw: Mapping[str, Any]) -> None:
    """Validate the exact capped jobs/artifact API scan that caused a HOLD."""
    query_kind = raw.get("query_kind")
    if query_kind not in {"JOBS", "ARTIFACTS"}:
        raise OutboxBlock("Mesh completion bounded query kind is invalid")
    for prefix, declared_key, observed_key, digest_key in (
        ("jobs", "jobs_declared_total_count", "jobs_observed_count", "jobs_set_sha256"),
        (
            "artifacts",
            "artifacts_declared_total_count",
            "artifacts_observed_count",
            "artifact_inventory_sha256",
        ),
    ):
        declared = raw.get(declared_key)
        observed = raw.get(observed_key)
        pages = raw.get(f"{prefix}_pages_scanned")
        cap = raw.get(f"{prefix}_page_cap")
        complete = raw.get(f"{prefix}_scan_complete")
        if (
            isinstance(declared, bool)
            or not isinstance(declared, int)
            or declared < 0
            or isinstance(observed, bool)
            or not isinstance(observed, int)
            or observed < 0
            or observed > declared
            or isinstance(pages, bool)
            or not isinstance(pages, int)
            or isinstance(cap, bool)
            or not isinstance(cap, int)
            or not (1 <= cap <= 100)
            or HEX64.fullmatch(str(raw.get(digest_key))) is None
            or not isinstance(complete, bool)
        ):
            raise OutboxBlock(f"Mesh bounded {prefix} query is malformed")
        if prefix == "jobs":
            if query_kind == "JOBS" and (
                complete is not False or pages != cap or observed < 1
            ):
                raise OutboxBlock("Mesh jobs query bound is not exact")
            if query_kind == "ARTIFACTS" and (
                complete is not True
                or declared < 1
                or observed != declared
                or pages != max(1, (declared + 99) // 100)
                or pages > cap
            ):
                raise OutboxBlock("Mesh jobs prerequisite inventory is incomplete")
        elif query_kind == "JOBS":
            if not (
                declared == observed == pages == 0 and complete is False
            ):
                raise OutboxBlock("Mesh artifact query started before jobs completed")
        elif complete is not False or pages != cap:
            raise OutboxBlock("Mesh artifact query bound is not exact")


def _validate_cursor_observation_binding(
    raw: Mapping[str, Any],
    *,
    intent: Mapping[str, Any],
    retry_scan_cursors: Mapping[str, Any],
    allowed_states: frozenset[str],
    allowed_lanes: frozenset[str] = frozenset(
        {"exact-head-dispatch", "exact-review-dispatch"}
    ),
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind an Authority fact to one exact persisted cursor snapshot."""
    lane = _lane(intent.get("lane"))
    if lane not in allowed_lanes:
        raise OutboxBlock("cursor-bound observation is outside its authorized lane")
    attempt = raw.get("transport_attempt")
    record = (
        dict(
            _mapping(
                retry_scan_cursors.get(str(attempt)),
                "cursor-bound observation record",
            )
        )
        if attempt == 1 and str(attempt) in retry_scan_cursors
        else {}
    )
    cursor = (
        dict(_mapping(record.get("cursor"), "cursor-bound observation cursor"))
        if record
        else {}
    )
    payload = _mapping(intent.get("payload"), "cursor-bound intent payload")
    sealed_main = _sha(
        payload.get("main_head_sha"), "cursor-bound sealed main"
    )
    if (
        attempt != 1
        or not record
        or record.get("state") not in allowed_states
        or raw.get("retry_scan_cursor_record_sha256") != digest(record)
        or raw.get("retry_scan_cursor_sha256") != record.get("cursor_sha256")
        or raw.get("retry_scan_cursor_state") != record.get("state")
        or raw.get("retry_scan_cursor_ledger_ref") != ledger_ref(lane)
        or HEX40.fullmatch(str(raw.get("retry_scan_cursor_ledger_head")))
        is None
        or raw.get("query_window_start") != cursor.get("query_window_start")
        or raw.get("query_window_end") != cursor.get("query_window_end")
        or raw.get("upper_bound_run_id") != cursor.get("upper_bound_run_id")
        or raw.get("last_scanned_run_id")
        != cursor.get("last_scanned_run_id")
        or raw.get("page_cap") != cursor.get("page_cap")
        or raw.get("pages_scanned") != cursor.get("pages_scanned")
        or raw.get("declared_total_count")
        != cursor.get("declared_total_count")
        or raw.get("queried_page") != cursor.get("queried_page")
        or raw.get("page_run_ids_sha256")
        != cursor.get("page_run_ids_sha256")
        or raw.get("cumulative_run_ids_sha256")
        != cursor.get("cumulative_run_ids_sha256")
        or raw.get("observed_unique_run_count")
        != cursor.get("observed_unique_run_count")
        or raw.get("inventory_consistent")
        != cursor.get("inventory_consistent")
        or raw.get("inventory_blocker") != cursor.get("inventory_blocker")
        or raw.get("candidate_set_sha256")
        != cursor.get("candidate_set_sha256")
        or raw.get("bound_successor_count")
        != cursor.get("bound_successor_count")
        or raw.get("scan_complete") != cursor.get("scan_complete")
        or raw.get("sealed_main_head_sha") != sealed_main
        or raw.get("observed_main_head_sha") != sealed_main
    ):
        raise OutboxBlock("cursor observation binding mismatch")
    return record, cursor


def _validate_ambiguity_observation(
    value: Any,
    *,
    blocker: str,
    intent: Mapping[str, Any],
    transports: Mapping[str, Any],
    acceptances: Mapping[str, Any],
    completions: Mapping[str, Any],
    child_recovery: Mapping[str, Any],
    retry_scan_cursors: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one blocker-specific immutable Authority observation.

    AMBIGUOUS_OR_DRIFT is never an evidence-free escape hatch.  Each allowed
    blocker has a closed schema and is checked against the exact current FIFO
    state again inside the terminal CAS planner.
    """
    raw = dict(_mapping(value, "outbox authority observation"))
    lane = _lane(intent.get("lane"))
    sequence = _sequence(intent.get("sequence"))
    fingerprint = _digest(intent.get("fingerprint"), "authority fingerprint")
    common = {
        "schema",
        "blocker",
        "lane",
        "sequence",
        "fingerprint",
        "verified",
        "productive_effect",
    }
    if (
        raw.get("schema") != AUTHORITY_OBSERVATION_SCHEMA
        or raw.get("blocker") != blocker
        or raw.get("lane") != lane
        or raw.get("sequence") != sequence
        or raw.get("fingerprint") != fingerprint
        or raw.get("verified") is not True
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("authority observation binding mismatch")

    if blocker == "OUTBOX_EVALUATOR_SUPERSEDED":
        expected_keys = common | {
            "sealed_main_head_sha",
            "observed_main_head_sha",
        }
        sealed_main = _sha(
            _mapping(intent.get("payload"), "authority intent payload").get(
                "main_head_sha"
            ),
            "sealed evaluator main",
        )
        observed_main = _sha(
            raw.get("observed_main_head_sha"), "observed evaluator main"
        )
        if (
            set(raw) != expected_keys
            or raw.get("sealed_main_head_sha") != sealed_main
            or observed_main == sealed_main
        ):
            raise OutboxBlock("evaluator supersession observation mismatch")
    elif blocker == "OUTBOX_SUBJECT_SUPERSEDED":
        expected_keys = common | {
            "sealed_subject_sha256",
            "observed_subject",
            "observed_subject_sha256",
        }
        sealed_subject = dict(
            _mapping(
                _mapping(intent.get("payload"), "authority intent payload").get(
                    "subject"
                ),
                "sealed authority subject",
            )
        )
        observed_subject = dict(
            _mapping(raw.get("observed_subject"), "observed authority subject")
        )
        _validate_observed_subject_shape(sealed_subject, observed_subject)
        if (
            set(raw) != expected_keys
            or observed_subject == sealed_subject
            or raw.get("sealed_subject_sha256") != digest(sealed_subject)
            or raw.get("observed_subject_sha256") != digest(observed_subject)
        ):
            raise OutboxBlock("subject supersession observation mismatch")
    elif blocker == "OUTBOX_TARGET_WORKFLOW_SUPERSEDED":
        expected_keys = common | {
            "sealed_target",
            "sealed_target_sha256",
            "observed_target",
            "observed_target_sha256",
            "sealed_main_head_sha",
            "observed_main_head_sha",
        }
        payload = _mapping(intent.get("payload"), "target observation payload")
        sealed_target = dict(
            _mapping(payload.get("target"), "sealed workflow target")
        )
        observed_target = dict(
            _mapping(raw.get("observed_target"), "observed workflow target")
        )
        sealed_main = _sha(
            payload.get("main_head_sha"), "target observation sealed main"
        )
        target_keys = {"workflow_id", "workflow_path", "event"}
        if (
            set(raw) != expected_keys
            or raw.get("sealed_target") != sealed_target
            or raw.get("sealed_target_sha256") != digest(sealed_target)
            or set(observed_target) != target_keys
            or isinstance(observed_target.get("workflow_id"), bool)
            or not isinstance(observed_target.get("workflow_id"), int)
            or observed_target.get("workflow_id") < 1
            or not isinstance(observed_target.get("workflow_path"), str)
            or re.fullmatch(
                r"\.github/workflows/[A-Za-z0-9_.-]+\.yml",
                observed_target.get("workflow_path", ""),
            )
            is None
            or not isinstance(observed_target.get("event"), str)
            or not observed_target.get("event")
            or observed_target == sealed_target
            or raw.get("observed_target_sha256") != digest(observed_target)
            or raw.get("sealed_main_head_sha") != sealed_main
            or raw.get("observed_main_head_sha") != sealed_main
        ):
            raise OutboxBlock("target workflow supersession observation mismatch")
    elif blocker == "SOURCE_ATTEMPT_1_ACTION_REQUIRED":
        expected_keys = common | {
            "transport_attempt",
            "intent_sha256",
            "acceptance_sha256",
            "accepted_child_sha256",
            "observed_child",
            "observed_child_sha256",
            "jobs_total_count",
            "jobs_set_sha256",
            "jobs_pages_scanned",
            "jobs_page_cap",
            "jobs_scan_complete",
            "admission_receipt",
            "admission_receipt_sha256",
            "sealed_main_head_sha",
            "observed_main_head_sha",
            "sealed_subject_sha256",
            "observed_subject",
            "observed_subject_sha256",
            "observation_started_at",
            "observation_completed_at",
        }
        payload = _mapping(intent.get("payload"), "Admission intent payload")
        sealed_main = _sha(
            payload.get("main_head_sha"), "Admission sealed evaluator"
        )
        sealed_subject = dict(
            _mapping(payload.get("subject"), "Admission sealed subject")
        )
        observed_subject = dict(
            _mapping(raw.get("observed_subject"), "Admission observed subject")
        )
        acceptance = acceptances.get("1")
        observed_child = (
            _validate_observed_child_for_acceptance(
                raw.get("observed_child"),
                intent=intent,
                acceptance=acceptance,
                transport_attempt=1,
            )
            if isinstance(acceptance, Mapping)
            else {}
        )
        receipt = _validate_admission_action_required_receipt(
            raw.get("admission_receipt"), observed_child=observed_child
        )
        pages = raw.get("jobs_pages_scanned")
        cap = raw.get("jobs_page_cap")
        timestamp = re.compile(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
        )
        started = raw.get("observation_started_at")
        completed = raw.get("observation_completed_at")
        if (
            lane
            not in {"exact-review-dispatch", "mesh-review-successor-dispatch"}
            or set(raw) != expected_keys
            or set(transports) != {"1"}
            or set(acceptances) != {"1"}
            or completions
            or child_recovery
            or raw.get("transport_attempt") != 1
            or raw.get("intent_sha256") != digest(dict(intent))
            or raw.get("acceptance_sha256") != digest(dict(acceptance))
            or raw.get("accepted_child_sha256")
            != acceptance.get("child_sha256")
            or raw.get("observed_child_sha256") != digest(observed_child)
            or observed_child.get("run_attempt") != 1
            or observed_child.get("status") != "completed"
            or observed_child.get("conclusion") != "action_required"
            or raw.get("jobs_total_count") != 0
            or raw.get("jobs_set_sha256") != digest([])
            or pages != 1
            or isinstance(cap, bool)
            or not isinstance(cap, int)
            or not (1 <= cap <= 100)
            or raw.get("jobs_scan_complete") is not True
            or raw.get("admission_receipt_sha256") != digest(receipt)
            or raw.get("sealed_main_head_sha") != sealed_main
            or raw.get("observed_main_head_sha") != sealed_main
            or raw.get("sealed_subject_sha256") != digest(sealed_subject)
            or observed_subject != sealed_subject
            or raw.get("observed_subject_sha256") != digest(observed_subject)
            or not isinstance(started, str)
            or timestamp.fullmatch(started) is None
            or not isinstance(completed, str)
            or timestamp.fullmatch(completed) is None
            or started > completed
        ):
            raise OutboxBlock("Admission action-required observation mismatch")
    elif blocker == "BOUND_EVIDENCE_AMBIGUOUS":
        candidates = raw.get("candidate_sha256s")
        if lane in {"exact-head-dispatch", "exact-review-dispatch"}:
            expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS) | {
                "candidate_sha256s"
            }
            _record, cursor = _validate_cursor_observation_binding(
                raw,
                intent=intent,
                retry_scan_cursors=retry_scan_cursors,
                allowed_states=frozenset({"COMPLETE_SUCCESSOR_OBSERVED"}),
            )
            expected_candidates = sorted(
                digest(dict(item))
                for item in cursor.get("candidate_locators", [])
            )
            if (
                set(raw) != expected_keys
                or cursor.get("scan_complete") is not True
                or not isinstance(candidates, list)
                or not (2 <= len(candidates) <= 8)
                or cursor.get("bound_successor_count") != len(candidates)
                or candidates != expected_candidates
            ):
                raise OutboxBlock(
                    "cursor-bound evidence ambiguity observation mismatch"
                )
        elif lane == "mesh-review-successor-dispatch":
            raise OutboxBlock(
                "Mesh ambiguity requires its lane-specific cursor-bound blocker"
            )
        else:
            expected_keys = common | {
                "candidate_sha256s",
                "scan_complete",
            }
            if (
                set(raw) != expected_keys
                or raw.get("scan_complete") is not True
                or not isinstance(candidates, list)
                or not (2 <= len(candidates) <= 8)
                or candidates != sorted(set(candidates))
                or any(HEX64.fullmatch(str(item)) is None for item in candidates)
            ):
                raise OutboxBlock("bound-evidence ambiguity observation mismatch")
    elif blocker == "BOUND_EVIDENCE_AMBIGUITY_SET_EXCEEDED":
        expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS) | {
            "candidate_count"
        }
        count = raw.get("candidate_count")
        record, cursor = _validate_cursor_observation_binding(
            raw,
            intent=intent,
            retry_scan_cursors=retry_scan_cursors,
            allowed_states=frozenset(
                {
                    "COMPLETE_SUCCESSOR_OBSERVED",
                    "AMBIGUITY_SET_EXCEEDED_AUTHORITY",
                }
            ),
        )
        if (
            lane not in {"exact-head-dispatch", "exact-review-dispatch"}
            or set(raw) != expected_keys
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 9
            or count != cursor.get("bound_successor_count")
            or (
                record.get("state") == "COMPLETE_SUCCESSOR_OBSERVED"
                and cursor.get("scan_complete") is not True
            )
        ):
            raise OutboxBlock("bound-evidence ambiguity-set observation mismatch")
    elif blocker == "MESH_REVIEW_TRANSPORT_CHILD_AMBIGUOUS":
        expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS) | {
            "candidate_sha256s"
        }
        candidates = raw.get("candidate_sha256s")
        _record, cursor = _validate_cursor_observation_binding(
            raw,
            intent=intent,
            retry_scan_cursors=retry_scan_cursors,
            allowed_states=frozenset({"COMPLETE_SUCCESSOR_OBSERVED"}),
            allowed_lanes=frozenset({"mesh-review-successor-dispatch"}),
        )
        expected_candidates = sorted(
            digest(dict(item)) for item in cursor.get("candidate_locators", [])
        )
        if (
            lane != "mesh-review-successor-dispatch"
            or set(raw) != expected_keys
            or raw.get("transport_attempt") != 1
            or cursor.get("scan_complete") is not True
            or not isinstance(candidates, list)
            or not (2 <= len(candidates) <= 8)
            or cursor.get("bound_successor_count") != len(candidates)
            or candidates != expected_candidates
        ):
            raise OutboxBlock("Mesh cursor-bound child ambiguity mismatch")
    elif blocker == "MESH_REVIEW_TRANSPORT_CHILD_SET_EXCEEDED":
        expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS) | {
            "candidate_count"
        }
        count = raw.get("candidate_count")
        record, cursor = _validate_cursor_observation_binding(
            raw,
            intent=intent,
            retry_scan_cursors=retry_scan_cursors,
            allowed_states=frozenset(
                {
                    "COMPLETE_SUCCESSOR_OBSERVED",
                    "AMBIGUITY_SET_EXCEEDED_AUTHORITY",
                }
            ),
            allowed_lanes=frozenset({"mesh-review-successor-dispatch"}),
        )
        if (
            lane != "mesh-review-successor-dispatch"
            or set(raw) != expected_keys
            or raw.get("transport_attempt") != 1
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 9
            or count != cursor.get("bound_successor_count")
            or (
                record.get("state") == "COMPLETE_SUCCESSOR_OBSERVED"
                and cursor.get("scan_complete") is not True
            )
        ):
            raise OutboxBlock("Mesh cursor-bound child-set observation mismatch")
    elif blocker in TRANSPORT_ABSENCE_BLOCKERS:
        observed_attempts = sorted(int(item) for item in transports)
        latest_attempt = observed_attempts[-1] if observed_attempts else None
        latest_transport = transports.get(str(latest_attempt))
        if blocker in {
            "REPEATED_EXACT_HEAD_TRANSPORT_UNACKNOWLEDGED",
            "REPEATED_EXACT_REVIEW_TRANSPORT_UNACKNOWLEDGED",
        }:
            expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS) | {
                "transport_request_sha256"
            }
            _record, cursor = _validate_cursor_observation_binding(
                raw,
                intent=intent,
                retry_scan_cursors=retry_scan_cursors,
                allowed_states=frozenset({"COMPLETE_ZERO_SUCCESSOR"}),
            )
            if (
                set(raw) != expected_keys
                or observed_attempts != [1]
                or latest_attempt != 1
                or raw.get("transport_attempt") != 1
                or not isinstance(latest_transport, Mapping)
                or raw.get("transport_request_sha256")
                != latest_transport.get("request_sha256")
                or cursor.get("scan_complete") is not True
                or cursor.get("bound_successor_count") != 0
                or acceptances
                or completions
            ):
                raise OutboxBlock(
                    "cursor-bound unacknowledged transport observation mismatch"
                )
        elif blocker == "REPEATED_MESH_REVIEW_TRANSPORT_UNACKNOWLEDGED":
            expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS) | {
                "transport_request_sha256"
            }
            _record, cursor = _validate_cursor_observation_binding(
                raw,
                intent=intent,
                retry_scan_cursors=retry_scan_cursors,
                allowed_states=frozenset({"COMPLETE_ZERO_SUCCESSOR"}),
                allowed_lanes=frozenset({"mesh-review-successor-dispatch"}),
            )
            if (
                set(raw) != expected_keys
                or observed_attempts != [1]
                or latest_attempt != 1
                or raw.get("transport_attempt") != 1
                or not isinstance(latest_transport, Mapping)
                or raw.get("transport_request_sha256")
                != latest_transport.get("request_sha256")
                or cursor.get("scan_complete") is not True
                or cursor.get("bound_successor_count") != 0
                or acceptances
                or completions
            ):
                raise OutboxBlock(
                    "Mesh cursor-bound unacknowledged transport observation mismatch"
                )
        else:
            expected_keys = common | {
                "transport_attempt",
                "transport_request_sha256",
                "scan_complete",
                "bound_successor_count",
            }
            if (
                set(raw) != expected_keys
                or observed_attempts != [1]
                or latest_attempt != 1
                or raw.get("transport_attempt") != latest_attempt
                or not isinstance(latest_transport, Mapping)
                or raw.get("transport_request_sha256")
                != latest_transport.get("request_sha256")
                or raw.get("scan_complete") is not True
                or raw.get("bound_successor_count") != 0
                or acceptances
                or completions
            ):
                raise OutboxBlock("unacknowledged transport observation mismatch")
    elif blocker == "REPEATED_EXACT_HEAD_RESULT_NOT_PERSISTED":
        expected_keys = common | {
            "transport_attempt",
            "accepted_child_sha256",
            "observed_child",
            "observed_child_sha256",
            "same_run_result",
            "completion_present",
            "business_receipt_present",
            "scan_complete",
        }
        observed_attempts = sorted(int(item) for item in acceptances)
        latest_attempt = observed_attempts[-1] if observed_attempts else None
        acceptance = acceptances.get(str(latest_attempt))
        observed_child = (
            _validate_observed_child_for_acceptance(
                raw.get("observed_child"),
                intent=intent,
                acceptance=acceptance,
                transport_attempt=latest_attempt,
                same_run_result=raw.get("same_run_result") is True,
            )
            if isinstance(acceptance, Mapping) and latest_attempt in {1, 2}
            else {}
        )
        if (
            lane != "exact-head-dispatch"
            or set(raw) != expected_keys
            or latest_attempt not in {1, 2}
            or raw.get("transport_attempt") != latest_attempt
            or raw.get("accepted_child_sha256")
            != acceptance.get("child_sha256")
            or raw.get("observed_child_sha256") != digest(observed_child)
            or not isinstance(raw.get("same_run_result"), bool)
        ):
            raise OutboxBlock("unpersisted exact result observation mismatch")
        if (
            observed_child.get("conclusion") != "success"
            or raw.get("completion_present") is not False
            or str(latest_attempt) in completions
            or raw.get("business_receipt_present") is not False
            or raw.get("scan_complete") is not True
        ):
            raise OutboxBlock("unpersisted exact result observation mismatch")
    elif blocker == "EXACT_HEAD_COMPLETION_EVIDENCE_MISSING":
        expected_keys = common | {
            "transport_attempt",
            "accepted_child_sha256",
            "observed_child",
            "observed_child_sha256",
            "same_run_result",
            "jobs_total_count",
            "expected_artifact_name",
            "evidence_classification",
            "artifact_count",
            "artifact_set_sha256",
            "scan_complete",
        }
        observed_attempts = sorted(int(item) for item in acceptances)
        latest_attempt = observed_attempts[-1] if observed_attempts else None
        acceptance = acceptances.get(str(latest_attempt))
        observed_child = (
            _validate_observed_child_for_acceptance(
                raw.get("observed_child"),
                intent=intent,
                acceptance=acceptance,
                transport_attempt=latest_attempt,
                same_run_result=raw.get("same_run_result") is True,
            )
            if isinstance(acceptance, Mapping) and latest_attempt in {1, 2}
            else {}
        )
        jobs_total = raw.get("jobs_total_count")
        artifact_count = raw.get("artifact_count")
        classification = raw.get("evidence_classification")
        expected_artifact = (
            f"qikvrt-exact-head-business-result-{observed_child.get('run_id')}-"
            f"{observed_child.get('run_attempt')}"
        )
        if (
            lane != "exact-head-dispatch"
            or set(raw) != expected_keys
            or latest_attempt not in {1, 2}
            or raw.get("transport_attempt") != latest_attempt
            or not isinstance(acceptance, Mapping)
            or raw.get("accepted_child_sha256")
            != acceptance.get("child_sha256")
            or raw.get("observed_child_sha256") != digest(observed_child)
            or not isinstance(raw.get("same_run_result"), bool)
            or isinstance(jobs_total, bool)
            or not isinstance(jobs_total, int)
            or jobs_total < 0
            or raw.get("expected_artifact_name") != expected_artifact
            or classification
            not in {
                "MISSING_ARTIFACT",
                "DUPLICATE_ARTIFACTS",
                "ARCHIVE_INVALID",
                "PAYLOAD_INVALID",
                "JOB_EVIDENCE_INVALID",
            }
            or isinstance(artifact_count, bool)
            or not isinstance(artifact_count, int)
            or artifact_count < 0
            or (
                classification == "MISSING_ARTIFACT" and artifact_count != 0
            )
            or (
                classification == "DUPLICATE_ARTIFACTS" and artifact_count < 2
            )
            or (
                classification
                in {"ARCHIVE_INVALID", "PAYLOAD_INVALID"}
                and artifact_count != 1
            )
            or (
                classification == "JOB_EVIDENCE_INVALID"
                and artifact_count not in {0, 1}
            )
            or HEX64.fullmatch(str(raw.get("artifact_set_sha256"))) is None
            or raw.get("scan_complete") is not True
            or str(latest_attempt) in completions
        ):
            raise OutboxBlock("exact-head missing evidence observation mismatch")
    elif blocker == "RECOVERY_QUERY_BOUND_EXCEEDED":
        expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS)
        _record, cursor = _validate_cursor_observation_binding(
            raw,
            intent=intent,
            retry_scan_cursors=retry_scan_cursors,
            allowed_states=frozenset({"SCAN_BOUND_EXCEEDED_AUTHORITY"}),
        )
        if (
            lane not in {"exact-head-dispatch", "exact-review-dispatch"}
            or set(raw) != expected_keys
            or cursor.get("pages_scanned") != cursor.get("page_cap")
            or cursor.get("scan_complete") is not False
        ):
            raise OutboxBlock("recovery query bound observation mismatch")
    elif blocker == "RECOVERY_QUERY_INVENTORY_INCONSISTENT":
        expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS)
        _record, cursor = _validate_cursor_observation_binding(
            raw,
            intent=intent,
            retry_scan_cursors=retry_scan_cursors,
            allowed_states=frozenset(
                {"SCAN_INVENTORY_INCONSISTENT_AUTHORITY"}
            ),
        )
        if (
            lane not in {"exact-head-dispatch", "exact-review-dispatch"}
            or set(raw) != expected_keys
            or cursor.get("inventory_consistent") is not False
            or cursor.get("inventory_blocker")
            not in RETRY_SCAN_INVENTORY_BLOCKERS
            or cursor.get("scan_complete") is not False
        ):
            raise OutboxBlock(
                "recovery query inventory observation mismatch"
            )
    elif blocker == "MESH_REVIEW_RECOVERY_QUERY_BOUND_EXCEEDED":
        expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS)
        _record, cursor = _validate_cursor_observation_binding(
            raw,
            intent=intent,
            retry_scan_cursors=retry_scan_cursors,
            allowed_states=frozenset({"SCAN_BOUND_EXCEEDED_AUTHORITY"}),
            allowed_lanes=frozenset({"mesh-review-successor-dispatch"}),
        )
        if (
            lane != "mesh-review-successor-dispatch"
            or set(raw) != expected_keys
            or raw.get("transport_attempt") != 1
            or cursor.get("pages_scanned") != cursor.get("page_cap")
            or cursor.get("scan_complete") is not False
        ):
            raise OutboxBlock("Mesh recovery query bound observation mismatch")
    elif blocker == "MESH_REVIEW_RECOVERY_QUERY_INVENTORY_INCONSISTENT":
        expected_keys = common | set(EXACT_CURSOR_OBSERVATION_KEYS)
        _record, cursor = _validate_cursor_observation_binding(
            raw,
            intent=intent,
            retry_scan_cursors=retry_scan_cursors,
            allowed_states=frozenset(
                {"SCAN_INVENTORY_INCONSISTENT_AUTHORITY"}
            ),
            allowed_lanes=frozenset({"mesh-review-successor-dispatch"}),
        )
        if (
            lane != "mesh-review-successor-dispatch"
            or set(raw) != expected_keys
            or raw.get("transport_attempt") != 1
            or cursor.get("inventory_consistent") is not False
            or cursor.get("inventory_blocker")
            not in RETRY_SCAN_INVENTORY_BLOCKERS
            or cursor.get("scan_complete") is not False
        ):
            raise OutboxBlock(
                "Mesh recovery inventory observation mismatch"
            )
    elif blocker == "EXACT_REVIEW_COMPLETION_EVIDENCE_MISSING":
        expected_keys = common | {
            "transport_attempt",
            "accepted_child_sha256",
            "observed_child",
            "observed_child_sha256",
            "jobs_total_count",
            "expected_artifact_name",
            "evidence_classification",
            "artifact_count",
            "artifact_set_sha256",
            "scan_complete",
        }
        observed_attempts = sorted(int(item) for item in acceptances)
        latest_attempt = observed_attempts[-1] if observed_attempts else None
        acceptance = acceptances.get(str(latest_attempt))
        child = (
            _validate_observed_child_for_acceptance(
                raw.get("observed_child"),
                intent=intent,
                acceptance=acceptance,
                transport_attempt=latest_attempt,
            )
            if isinstance(acceptance, Mapping) and latest_attempt in {1, 2}
            else {}
        )
        expected_artifact = (
            f"qikvrt-requested-review-completion-{child.get('run_id')}-"
            f"attempt-{child.get('run_attempt')}"
        )
        jobs_total = raw.get("jobs_total_count")
        artifact_count = raw.get("artifact_count")
        classification = raw.get("evidence_classification")
        if (
            lane != "exact-review-dispatch"
            or set(raw) != expected_keys
            or latest_attempt not in {1, 2}
            or raw.get("transport_attempt") != latest_attempt
            or not isinstance(acceptance, Mapping)
            or raw.get("accepted_child_sha256")
            != acceptance.get("child_sha256")
            or raw.get("observed_child_sha256") != digest(child)
            or isinstance(jobs_total, bool)
            or not isinstance(jobs_total, int)
            or jobs_total < 0
            or raw.get("expected_artifact_name") != expected_artifact
            or classification
            not in {
                "MISSING_ARTIFACT",
                "DUPLICATE_ARTIFACTS",
                "ARCHIVE_INVALID",
                "PAYLOAD_INVALID",
                "JOB_EVIDENCE_INVALID",
            }
            or isinstance(artifact_count, bool)
            or not isinstance(artifact_count, int)
            or artifact_count < 0
            or (
                classification == "MISSING_ARTIFACT" and artifact_count != 0
            )
            or (
                classification == "DUPLICATE_ARTIFACTS" and artifact_count < 2
            )
            or (
                classification in {"ARCHIVE_INVALID", "PAYLOAD_INVALID"}
                and artifact_count != 1
            )
            or (
                classification == "JOB_EVIDENCE_INVALID"
                and artifact_count not in {0, 1}
            )
            or HEX64.fullmatch(str(raw.get("artifact_set_sha256"))) is None
            or raw.get("scan_complete") is not True
            or str(latest_attempt) in completions
        ):
            raise OutboxBlock("exact-review missing evidence observation mismatch")
    elif blocker == "EXACT_REVIEW_BUSINESS_EVIDENCE_MISSING":
        expected_keys = common | {
            "transport_attempt",
            "accepted_child_sha256",
            "observed_child",
            "observed_child_sha256",
            "jobs_total_count",
            "completion_envelope_artifact_name",
            "completion_envelope_artifact_count",
            "expected_business_artifact_prefix",
            "expected_business_artifact_suffix",
            "business_evidence_classification",
            "business_artifact_count",
            "business_artifact_set_sha256",
            "scan_complete",
        }
        observed_attempts = sorted(int(item) for item in acceptances)
        latest_attempt = observed_attempts[-1] if observed_attempts else None
        acceptance = acceptances.get(str(latest_attempt))
        child = (
            _validate_observed_child_for_acceptance(
                raw.get("observed_child"),
                intent=intent,
                acceptance=acceptance,
                transport_attempt=latest_attempt,
            )
            if isinstance(acceptance, Mapping) and latest_attempt in {1, 2}
            else {}
        )
        payload = _mapping(intent.get("payload"), "business evidence payload")
        inputs = _mapping(
            _mapping(payload.get("request"), "business evidence request").get(
                "inputs"
            ),
            "business evidence inputs",
        )
        completion_name = (
            f"qikvrt-requested-review-completion-{child.get('run_id')}-"
            f"attempt-{child.get('run_attempt')}"
        )
        business_prefix = (
            f"qikvrt-mesh-review-pr-{inputs.get('pr')}-"
            f"{inputs.get('head')}-"
        )
        business_suffix = (
            f"-run-{child.get('run_id')}-attempt-{child.get('run_attempt')}"
        )
        jobs_total = raw.get("jobs_total_count")
        artifact_count = raw.get("business_artifact_count")
        classification = raw.get("business_evidence_classification")
        if (
            lane != "exact-review-dispatch"
            or set(raw) != expected_keys
            or latest_attempt not in {1, 2}
            or raw.get("transport_attempt") != latest_attempt
            or not isinstance(acceptance, Mapping)
            or child.get("conclusion") != "success"
            or raw.get("accepted_child_sha256")
            != acceptance.get("child_sha256")
            or raw.get("observed_child_sha256") != digest(child)
            or isinstance(jobs_total, bool)
            or not isinstance(jobs_total, int)
            or jobs_total < 1
            or raw.get("completion_envelope_artifact_name") != completion_name
            or raw.get("completion_envelope_artifact_count") != 1
            or raw.get("expected_business_artifact_prefix") != business_prefix
            or raw.get("expected_business_artifact_suffix") != business_suffix
            or classification
            not in {
                "MISSING_ARTIFACT",
                "DUPLICATE_ARTIFACTS",
                "ARCHIVE_INVALID",
                "PAYLOAD_INVALID",
            }
            or isinstance(artifact_count, bool)
            or not isinstance(artifact_count, int)
            or artifact_count < 0
            or (
                classification == "MISSING_ARTIFACT" and artifact_count != 0
            )
            or (
                classification == "DUPLICATE_ARTIFACTS" and artifact_count < 2
            )
            or (
                classification in {"ARCHIVE_INVALID", "PAYLOAD_INVALID"}
                and artifact_count != 1
            )
            or HEX64.fullmatch(
                str(raw.get("business_artifact_set_sha256"))
            )
            is None
            or raw.get("scan_complete") is not True
            or str(latest_attempt) in completions
        ):
            raise OutboxBlock("exact-review missing business evidence mismatch")
    elif blocker == "MESH_REVIEW_COMPLETION_EVIDENCE_MISSING":
        selector_keys = {
            "transport_attempt",
            "child_recovery",
            "accepted_child_sha256",
            "observed_child",
            "observed_child_sha256",
        }
        expected_keys = common | selector_keys | set(
            MESH_COMPLETION_INVENTORY_KEYS
        ) | {
            "expected_artifact_name",
            "completion_artifact_count",
            "completion_artifact_set_sha256",
            "evidence_classification",
        }
        _acceptance, child = _validate_mesh_completion_observation_context(
            raw,
            intent=intent,
            acceptances=acceptances,
            completions=completions,
            child_recovery=child_recovery,
        )
        _validate_complete_mesh_inventory(raw)
        count = raw.get("completion_artifact_count")
        classification = raw.get("evidence_classification")
        expected_name = (
            f"qikvrt-requested-review-completion-{child.get('run_id')}-"
            f"attempt-{child.get('run_attempt')}"
        )
        if (
            lane != "mesh-review-successor-dispatch"
            or set(raw) != expected_keys
            or raw.get("expected_artifact_name") != expected_name
            or classification
            not in {
                "MISSING_ARTIFACT",
                "DUPLICATE_ARTIFACTS",
                "ARCHIVE_INVALID",
                "PAYLOAD_INVALID",
                "JOB_EVIDENCE_INVALID",
            }
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            or count > raw.get("artifacts_total_count")
            or (classification == "MISSING_ARTIFACT" and count != 0)
            or (classification == "DUPLICATE_ARTIFACTS" and count < 2)
            or (
                classification
                in {"ARCHIVE_INVALID", "PAYLOAD_INVALID", "JOB_EVIDENCE_INVALID"}
                and count != 1
            )
            or HEX64.fullmatch(
                str(raw.get("completion_artifact_set_sha256"))
            )
            is None
        ):
            raise OutboxBlock("Mesh completion evidence observation mismatch")
    elif blocker == "MESH_REVIEW_BUSINESS_EVIDENCE_MISSING":
        selector_keys = {
            "transport_attempt",
            "child_recovery",
            "accepted_child_sha256",
            "observed_child",
            "observed_child_sha256",
        }
        expected_keys = common | selector_keys | set(
            MESH_COMPLETION_INVENTORY_KEYS
        ) | {
            "completion_envelope_artifact_name",
            "completion_envelope_artifact_count",
            "completion_envelope_artifact_set_sha256",
            "expected_business_artifact_prefix",
            "expected_business_artifact_suffix",
            "business_artifact_count",
            "business_artifact_set_sha256",
            "business_evidence_classification",
        }
        _acceptance, child = _validate_mesh_completion_observation_context(
            raw,
            intent=intent,
            acceptances=acceptances,
            completions=completions,
            child_recovery=child_recovery,
        )
        _validate_complete_mesh_inventory(raw)
        payload = _mapping(intent.get("payload"), "Mesh business evidence payload")
        subject = _mapping(payload.get("subject"), "Mesh business evidence subject")
        queue = _mapping(
            subject.get("queue_intent"), "Mesh business evidence queue intent"
        )
        completion_name = (
            f"qikvrt-requested-review-completion-{child.get('run_id')}-"
            f"attempt-{child.get('run_attempt')}"
        )
        business_prefix = (
            f"qikvrt-mesh-review-pr-{queue.get('pr_number')}-"
            f"{queue.get('head_sha')}-"
        )
        business_suffix = (
            f"-run-{child.get('run_id')}-attempt-{child.get('run_attempt')}"
        )
        count = raw.get("business_artifact_count")
        classification = raw.get("business_evidence_classification")
        if (
            lane != "mesh-review-successor-dispatch"
            or set(raw) != expected_keys
            or child.get("conclusion") != "success"
            or raw.get("completion_envelope_artifact_name") != completion_name
            or raw.get("completion_envelope_artifact_count") != 1
            or HEX64.fullmatch(
                str(raw.get("completion_envelope_artifact_set_sha256"))
            )
            is None
            or raw.get("expected_business_artifact_prefix") != business_prefix
            or raw.get("expected_business_artifact_suffix") != business_suffix
            or classification
            not in {
                "MISSING_ARTIFACT",
                "DUPLICATE_ARTIFACTS",
                "ARCHIVE_INVALID",
                "PAYLOAD_INVALID",
            }
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            or count > raw.get("artifacts_total_count")
            or (classification == "MISSING_ARTIFACT" and count != 0)
            or (classification == "DUPLICATE_ARTIFACTS" and count < 2)
            or (
                classification in {"ARCHIVE_INVALID", "PAYLOAD_INVALID"}
                and count != 1
            )
            or HEX64.fullmatch(str(raw.get("business_artifact_set_sha256")))
            is None
        ):
            raise OutboxBlock("Mesh business evidence observation mismatch")
    elif blocker == "MESH_REVIEW_COMPLETION_QUERY_BOUND_EXCEEDED":
        selector_keys = {
            "transport_attempt",
            "child_recovery",
            "accepted_child_sha256",
            "observed_child",
            "observed_child_sha256",
        }
        expected_keys = common | selector_keys | {
            "query_kind",
            "jobs_declared_total_count",
            "jobs_observed_count",
            "jobs_set_sha256",
            "jobs_pages_scanned",
            "jobs_page_cap",
            "jobs_scan_complete",
            "artifacts_declared_total_count",
            "artifacts_observed_count",
            "artifact_inventory_sha256",
            "artifacts_pages_scanned",
            "artifacts_page_cap",
            "artifacts_scan_complete",
            "observation_started_at",
            "observation_completed_at",
        }
        _validate_mesh_completion_observation_context(
            raw,
            intent=intent,
            acceptances=acceptances,
            completions=completions,
            child_recovery=child_recovery,
        )
        _validate_bounded_mesh_inventory(raw)
        if lane != "mesh-review-successor-dispatch" or set(raw) != expected_keys:
            raise OutboxBlock("Mesh completion query-bound observation mismatch")
    else:
        raise OutboxBlock("ambiguity blocker lacks an exact observation schema")
    return raw


def _validate_authority_observation_for_item(
    value: Any,
    *,
    blocker: str,
    intent: Mapping[str, Any],
    transports: Mapping[str, Any],
    acceptances: Mapping[str, Any],
    completions: Mapping[str, Any],
    child_recovery: Mapping[str, Any],
    retry_scan_cursors: Mapping[str, Any],
    late_acceptance_conflict: Any,
) -> dict[str, Any]:
    """Validate one immutable API observation against the exact ledger state.

    Absence and ambiguity facts are never accepted only because terminal
    evidence repeats them.  A trusted observer first stores the exact API
    observation plus its artifact provenance; every later read and terminal
    CAS revalidates the observation against the then-current FIFO state.
    """
    raw = dict(_mapping(value, "stored authority observation"))
    schema = raw.get("schema")
    lane = _lane(intent.get("lane"))
    sequence = _sequence(intent.get("sequence"))
    fingerprint = _digest(
        intent.get("fingerprint"), "stored authority fingerprint"
    )

    if schema == AUTHORITY_OBSERVATION_SCHEMA:
        return _validate_ambiguity_observation(
            raw,
            blocker=blocker,
            intent=intent,
            transports=transports,
            acceptances=acceptances,
            completions=completions,
            child_recovery=child_recovery,
            retry_scan_cursors=retry_scan_cursors,
        )

    common = {
        "schema",
        "blocker",
        "lane",
        "sequence",
        "fingerprint",
        "verified",
        "productive_effect",
    }
    if (
        raw.get("blocker") != blocker
        or raw.get("lane") != lane
        or raw.get("sequence") != sequence
        or raw.get("fingerprint") != fingerprint
        or raw.get("verified") is not True
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("stored authority observation binding mismatch")

    if schema == CHILD_RERUN_OBSERVATION_SCHEMA:
        expected_keys = common | {
            "transport_attempt",
            "target_run_id",
            "target_run_attempt",
            "target_attempt_one_child",
            "target_attempt_one_child_sha256",
            "preparation_actor",
            "preparation_actor_sha256",
            "query_window_start",
            "query_window_end",
            "observation_started_at",
            "observation_completed_at",
            "observed_run_attempt",
            "scan_complete",
            "successor_present",
        }
        transport_attempt = raw.get("transport_attempt")
        recovery_state = child_recovery.get(str(transport_attempt))
        rerun = (
            recovery_state.get("rerun")
            if isinstance(recovery_state, Mapping)
            else None
        )
        recovered_acceptance = (
            recovery_state.get("acceptance")
            if isinstance(recovery_state, Mapping)
            else None
        )
        retry = (
            _mapping(rerun.get("retry_evidence"), "child-rerun stored retry")
            if isinstance(rerun, Mapping)
            else {}
        )
        target_child = dict(
            _mapping(
                raw.get("target_attempt_one_child"),
                "child-rerun target attempt-one child",
            )
        )
        stored_target = (
            dict(
                _mapping(
                    retry.get("observed_terminal_child"),
                    "child-rerun stored target child",
                )
            )
            if retry
            else {}
        )
        actor = dict(
            _mapping(raw.get("preparation_actor"), "child-rerun preparation actor")
        )
        actor_keys = {
            "run_id",
            "run_attempt",
            "status",
            "conclusion",
            "created_at",
            "updated_at",
        }
        timestamp = re.compile(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
        )
        query_start = raw.get("query_window_start")
        query_end = raw.get("query_window_end")
        observation_start = raw.get("observation_started_at")
        observation_end = raw.get("observation_completed_at")
        if (
            blocker != "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED"
            or set(raw) != expected_keys
            or transport_attempt != 1
            or not isinstance(rerun, Mapping)
            or recovered_acceptance is not None
            or raw.get("target_run_id") != rerun.get("target_run_id")
            or raw.get("target_run_attempt") != 2
            or target_child != stored_target
            or raw.get("target_attempt_one_child_sha256") != digest(target_child)
            or set(actor) != actor_keys
            or actor.get("run_id") != rerun.get("actor_run_id")
            or actor.get("run_attempt") != rerun.get("actor_run_attempt")
            or actor.get("status") != "completed"
            or actor.get("conclusion") not in TERMINAL_RUN_CONCLUSIONS
            or raw.get("preparation_actor_sha256") != digest(actor)
            or any(
                not isinstance(value, str) or timestamp.fullmatch(value) is None
                for value in (
                    actor.get("created_at"),
                    actor.get("updated_at"),
                    query_start,
                    query_end,
                    observation_start,
                    observation_end,
                )
            )
            or actor.get("created_at") > actor.get("updated_at")
            or query_start > actor.get("created_at")
            or query_end != observation_start
            or observation_start <= actor.get("updated_at")
            or observation_start > observation_end
            or raw.get("observed_run_attempt") != 1
            or raw.get("scan_complete") is not True
            or raw.get("successor_present") is not False
        ):
            raise OutboxBlock("child-rerun absence observation mismatch")
        return raw

    if schema == RERUN_TRANSPORT_OBSERVATION_SCHEMA:
        expected_keys = common | {
            "run_id",
            "observed_run_attempt",
            "target_run_attempt",
            "transport_effect_observed",
            "scan_complete",
        }
        request = _mapping(
            _mapping(intent.get("payload"), "rerun observation payload").get(
                "request"
            ),
            "rerun observation request",
        )
        if (
            lane != "reconciler-rerun"
            or blocker
            not in COMMON_EXHAUSTION_BLOCKERS[
                "ONE_SHOT_RERUN_TRANSPORT_AMBIGUOUS"
            ]
            or set(raw) != expected_keys
            or set(transports) != {"1"}
            or acceptances
            or completions
            or raw.get("run_id") != request.get("reconciler_run_id")
            or raw.get("observed_run_attempt") != 1
            or raw.get("target_run_attempt") != 2
            or raw.get("transport_effect_observed") is not False
            or raw.get("scan_complete") is not True
        ):
            raise OutboxBlock("one-shot rerun absence observation mismatch")
        return raw

    if schema == LATE_ACCEPTANCE_A2_OBSERVATION_SCHEMA:
        expected_keys = common | {
            "transport_attempt",
            "transport_request_sha256",
            "acceptance_present",
            "completion_present",
            "scan_complete",
        }
        attempt_two_transport = transports.get("2")
        if (
            blocker
            != "LATE_ATTEMPT_1_ACCEPTANCE_AFTER_ATTEMPT_2_SEALED"
            or set(raw) != expected_keys
            or not isinstance(late_acceptance_conflict, Mapping)
            or set(transports) != {"1", "2"}
            or acceptances
            or completions
            or not isinstance(attempt_two_transport, Mapping)
            or raw.get("transport_attempt") != 2
            or raw.get("transport_request_sha256")
            != attempt_two_transport.get("request_sha256")
            or raw.get("acceptance_present") is not False
            or raw.get("completion_present") is not False
            or raw.get("scan_complete") is not True
        ):
            raise OutboxBlock("late acceptance absence observation mismatch")
        return raw

    raise OutboxBlock("stored authority observation schema is not authorized")


def _normalize_authority_observer(
    value: Any,
    *,
    intent: Mapping[str, Any],
    expected_workflow_sha: str | None = None,
    blocker: str | None = None,
) -> dict[str, Any]:
    raw = _mapping(value, "outbox authority observer")
    producer = {
        "workflow_path": raw.get("workflow_path"),
        "workflow_sha": _sha(
            raw.get("workflow_sha"), "authority observer workflow sha"
        ),
        "workflow_id": _positive_int(
            raw.get("workflow_id"), "authority observer workflow id"
        ),
        "run_id": _positive_int(raw.get("run_id"), "authority observer run id"),
        "run_attempt": _positive_int(
            raw.get("run_attempt"), "authority observer run attempt"
        ),
        "event": raw.get("event"),
    }
    payload = _mapping(intent.get("payload"), "authority observer intent payload")
    expected_sha = (
        _sha(expected_workflow_sha, "authority observer expected workflow sha")
        if expected_workflow_sha is not None
        else payload.get("main_head_sha")
    )
    lane = _lane(intent.get("lane"))
    path = producer["workflow_path"]
    event = producer["event"]
    ordinary_observer = (
        lane != "mesh-review-successor-dispatch"
        and event in {"schedule", "workflow_run", "workflow_dispatch"}
        and (
            (
                path
                == ".github/workflows/qikvrt_autonomous_pr_head_continuation.yml"
                and blocker != "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
            )
            or (
                lane == "exact-review-dispatch"
                and path
                == ".github/workflows/qikvrt_review_admission_recovery.yml"
                and blocker in ADMISSION_AUTHORITY_OBSERVATION_BLOCKERS
            )
        )
    )
    mesh_completion_observer = (
        lane == "mesh-review-successor-dispatch"
        and blocker not in ADMISSION_AUTHORITY_OBSERVATION_BLOCKERS
        and path in MESH_AUTHORITY_OBSERVER_EVENTS
        and event in MESH_AUTHORITY_OBSERVER_EVENTS[path]
    )
    mesh_child_rerun_observer = (
        lane == "mesh-review-successor-dispatch"
        and blocker in ADMISSION_AUTHORITY_OBSERVATION_BLOCKERS
        and path in MESH_CHILD_RERUN_AUTHORITY_OBSERVER_EVENTS
        and event in MESH_CHILD_RERUN_AUTHORITY_OBSERVER_EVENTS[path]
    )
    if (
        set(raw) != set(producer)
        or not (
            ordinary_observer
            or mesh_completion_observer
            or mesh_child_rerun_observer
        )
        or producer["workflow_sha"] != expected_sha
    ):
        raise OutboxBlock("authority observer provenance mismatch")
    return producer


def validate_authority_observation_record(
    value: Any, *, intent: Mapping[str, Any]
) -> dict[str, Any]:
    raw = dict(_mapping(value, "outbox authority observation record"))
    lane = _lane(intent.get("lane"))
    sequence = _sequence(intent.get("sequence"))
    fingerprint = _digest(intent.get("fingerprint"), "authority record fingerprint")
    observation = dict(
        _mapping(raw.get("observation"), "stored authority observation")
    )
    blocker = observation.get("blocker")
    allowed = COMMON_EXHAUSTION_BLOCKERS["AMBIGUOUS_OR_DRIFT"] | (
        LANE_EXHAUSTION_BLOCKERS.get(lane, {}).get(
            "AMBIGUOUS_OR_DRIFT", frozenset()
        )
    ) | COMMON_EXHAUSTION_BLOCKERS["CHILD_RERUN_EXHAUSTED"] | (
        COMMON_EXHAUSTION_BLOCKERS["ONE_SHOT_RERUN_TRANSPORT_AMBIGUOUS"]
    )
    _technical_code(blocker, "stored authority blocker", allowed)
    expected_workflow_sha = None
    if blocker == "OUTBOX_EVALUATOR_SUPERSEDED":
        expected_workflow_sha = observation.get("observed_main_head_sha")
    producer = _normalize_authority_observer(
        raw.get("producer"),
        intent=intent,
        expected_workflow_sha=expected_workflow_sha,
        blocker=blocker,
    )
    observation_sha = digest(observation)
    artifact = validate_artifact(
        raw.get("artifact"),
        payload_sha256=sha256_bytes(canonical_bytes(observation)),
        producer=producer,
    )
    expected_name = (
        f"qikvrt-outbox-authority-observation-{lane}-{sequence}-{blocker}-"
        f"run-{producer['run_id']}-attempt-{producer['run_attempt']}"
    )
    if (
        set(raw)
        != {
            "schema",
            "lane",
            "sequence",
            "fingerprint",
            "blocker",
            "observation",
            "observation_sha256",
            "producer",
            "artifact",
            "state",
            "productive_effect",
        }
        or raw.get("schema") != AUTHORITY_OBSERVATION_RECORD_SCHEMA
        or raw.get("lane") != lane
        or raw.get("sequence") != sequence
        or raw.get("fingerprint") != fingerprint
        or raw.get("blocker") != blocker
        or observation.get("lane") != lane
        or observation.get("sequence") != sequence
        or observation.get("fingerprint") != fingerprint
        or raw.get("observation_sha256") != observation_sha
        or artifact.get("name") != expected_name
        or raw.get("state") != "IMMUTABLE_API_OBSERVATION"
        or raw.get("productive_effect") is not False
    ):
        raise OutboxBlock("authority observation record binding mismatch")
    return {
        "schema": AUTHORITY_OBSERVATION_RECORD_SCHEMA,
        "lane": lane,
        "sequence": sequence,
        "fingerprint": fingerprint,
        "blocker": blocker,
        "observation": observation,
        "observation_sha256": observation_sha,
        "producer": producer,
        "artifact": artifact,
        "state": "IMMUTABLE_API_OBSERVATION",
        "productive_effect": False,
    }


def _validate_recovery_bound_cursor_snapshot(
    backend: LedgerBackend,
    observation: Mapping[str, Any],
) -> None:
    """Reopen the exact cursor commit named by a capped-scan observation."""
    if observation.get("blocker") not in CURSOR_BOUND_BLOCKERS:
        return
    lane = _lane(observation.get("lane"))
    if lane not in {
        "exact-head-dispatch",
        "exact-review-dispatch",
        "mesh-review-successor-dispatch",
    }:
        return
    sequence = _sequence(observation.get("sequence"))
    attempt = observation.get("transport_attempt")
    if attempt not in {1, 2}:
        raise OutboxBlock("recovery query bound cursor attempt is invalid")
    ref = observation.get("retry_scan_cursor_ledger_ref")
    head = _sha(
        observation.get("retry_scan_cursor_ledger_head"),
        "recovery query bound cursor ledger head",
    )
    if ref != ledger_ref(lane):
        raise OutboxBlock("recovery query bound cursor ledger ref mismatch")
    snapshot = _read_next_at(backend, head, lane)
    persisted = _mapping(
        _mapping(
            snapshot.get("retry_scan_cursor"),
            "recovery query bound snapshot cursors",
        ).get(str(attempt)),
        "recovery query bound snapshot cursor",
    )
    if (
        snapshot.get("state") != "PENDING"
        or snapshot.get("sequence") != sequence
        or snapshot.get("fingerprint") != observation.get("fingerprint")
        or snapshot.get("ledger_ref") != ref
        or snapshot.get("ledger_head") != head
        or persisted.get("state")
        != observation.get("retry_scan_cursor_state")
        or digest(dict(persisted))
        != observation.get("retry_scan_cursor_record_sha256")
        or backend.get_main_head() != observation.get("observed_main_head_sha")
    ):
        raise OutboxBlock("recovery query bound cursor snapshot mismatch")


def _bind_authority_observation_at(
    backend: LedgerBackend,
    head: str,
    next_item: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Load only the content-addressed observation selected by evidence.

    Observation records are deliberately not represented by one mutable or
    first-writer-wins per-sequence slot.  A crash-replayed observation and a
    later state-specific observation may coexist; terminal evidence selects
    exactly one immutable record by digest at the same ledger snapshot used
    for all other terminal predicates.
    """
    item = dict(next_item)
    exhaustion = evidence.get("exhaustion")
    if not isinstance(exhaustion, Mapping):
        item["authority_observation"] = None
        return item
    raw_record_sha = exhaustion.get("authority_observation_sha256")
    if raw_record_sha is None:
        item["authority_observation"] = None
        return item
    record_sha = _digest(
        raw_record_sha, "terminal Authority observation record digest"
    )
    intent = _mapping(item.get("intent"), "Authority observation intent")
    lane = _lane(intent.get("lane"))
    sequence = _sequence(intent.get("sequence"))
    raw_record = _read_json(
        backend,
        _sha(head, "Authority observation ledger head"),
        authority_observation_path(lane, sequence, record_sha),
    )
    record = validate_authority_observation_record(raw_record, intent=intent)
    if digest(record) != record_sha:
        raise OutboxBlock(
            "terminal Authority observation content address mismatch"
        )
    _validate_recovery_bound_cursor_snapshot(
        backend, _mapping(record.get("observation"), "terminal observation")
    )
    item["authority_observation"] = record
    return item


def record_authority_observation(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    observation: Mapping[str, Any],
    producer: Mapping[str, Any],
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    lane = _lane(lane)
    sequence = _sequence(sequence)
    current = read_next(backend, lane)
    if current.get("state") != "PENDING" or current.get("sequence") != sequence:
        raise OutboxBlock("authority observation is not for current FIFO item")
    intent = _mapping(current.get("intent"), "authority observation intent")
    blocker = str(observation.get("blocker"))
    normalized_observation = _validate_authority_observation_for_item(
        observation,
        blocker=blocker,
        intent=intent,
        transports=_mapping(current.get("transport"), "authority transports"),
        acceptances=_mapping(current.get("acceptance"), "authority acceptances"),
        completions=_mapping(current.get("completion"), "authority completions"),
        child_recovery=_mapping(
            current.get("child_recovery"), "authority child recovery"
        ),
        retry_scan_cursors=_mapping(
            current.get("retry_scan_cursor"), "authority retry scan cursors"
        ),
        late_acceptance_conflict=current.get("late_acceptance_conflict"),
    )
    if (
        blocker == "OUTBOX_EVALUATOR_SUPERSEDED"
        and backend.get_main_head()
        != normalized_observation.get("observed_main_head_sha")
    ):
        raise OutboxBlock("evaluator supersession is not the exact live main")
    if (
        blocker == "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
        and backend.get_main_head()
        != normalized_observation.get("observed_main_head_sha")
    ):
        raise OutboxBlock("Authority observation is not bound to exact live main")
    _validate_recovery_bound_cursor_snapshot(backend, normalized_observation)
    expected_workflow_sha = None
    if blocker == "OUTBOX_EVALUATOR_SUPERSEDED":
        expected_workflow_sha = normalized_observation.get(
            "observed_main_head_sha"
        )
    normalized_producer = _normalize_authority_observer(
        producer,
        intent=intent,
        expected_workflow_sha=expected_workflow_sha,
        blocker=blocker,
    )
    record = validate_authority_observation_record(
        {
            "schema": AUTHORITY_OBSERVATION_RECORD_SCHEMA,
            "lane": lane,
            "sequence": sequence,
            "fingerprint": intent["fingerprint"],
            "blocker": blocker,
            "observation": normalized_observation,
            "observation_sha256": digest(normalized_observation),
            "producer": normalized_producer,
            "artifact": artifact,
            "state": "IMMUTABLE_API_OBSERVATION",
            "productive_effect": False,
        },
        intent=intent,
    )

    def validate_current(current_value: Mapping[str, Any]) -> None:
        current_intent = _mapping(
            current_value.get("intent"), "authority CAS intent"
        )
        if current_intent.get("fingerprint") != intent.get("fingerprint"):
            raise OutboxBlock("authority intent changed during CAS")
        if (
            blocker == "OUTBOX_EVALUATOR_SUPERSEDED"
            and backend.get_main_head()
            != normalized_observation.get("observed_main_head_sha")
        ):
            raise OutboxBlock(
                "evaluator supersession main changed during observation CAS"
            )
        if (
            blocker == "SOURCE_ATTEMPT_1_ACTION_REQUIRED"
            and backend.get_main_head()
            != normalized_observation.get("observed_main_head_sha")
        ):
            raise OutboxBlock(
                "Authority observation main changed during observation CAS"
            )
        _validate_recovery_bound_cursor_snapshot(
            backend, normalized_observation
        )
        _validate_authority_observation_for_item(
            normalized_observation,
            blocker=blocker,
            intent=current_intent,
            transports=_mapping(
                current_value.get("transport"), "authority CAS transports"
            ),
            acceptances=_mapping(
                current_value.get("acceptance"), "authority CAS acceptances"
            ),
            completions=_mapping(
                current_value.get("completion"), "authority CAS completions"
            ),
            child_recovery=_mapping(
                current_value.get("child_recovery"),
                "authority CAS child recovery",
            ),
            retry_scan_cursors=_mapping(
                current_value.get("retry_scan_cursor"),
                "authority CAS retry scan cursors",
            ),
            late_acceptance_conflict=current_value.get(
                "late_acceptance_conflict"
            ),
        )

    record_sha = digest(record)
    path = authority_observation_path(lane, sequence, record_sha)
    persisted = _append_immutable_record(
        backend,
        lane=lane,
        sequence=sequence,
        path=path,
        record=record,
        message=f"Record {lane} Authority observation {sequence}",
        validate_current=validate_current,
    )
    return {
        "schema": AUTHORITY_OBSERVATION_RECEIPT_SCHEMA,
        "state": "IMMUTABLE_API_OBSERVATION_PERSISTED",
        "record": record,
        "record_sha256": record_sha,
        "record_path": path,
        "ledger_ref": persisted["ledger_ref"],
        "ledger_head": persisted["ledger_head"],
        "cas": persisted["cas"],
        "productive_effect": False,
    }


def validate_terminal_evidence(
    value: Any,
    *,
    next_item: Mapping[str, Any],
) -> dict[str, Any]:
    raw = dict(_mapping(value, "outbox terminal evidence"))
    allowed_top = {
        "schema",
        "d0",
        "state",
        "reason",
        "business_receipt",
        "exhaustion",
        "continuation",
        "completion_claims",
        "productive_effect",
        "effect_ack",
    }
    if set(raw) - allowed_top:
        raise OutboxBlock("outbox terminal evidence key set is not authorized")
    if raw.get("schema") != TERMINAL_EVIDENCE_SCHEMA:
        raise OutboxBlock("outbox terminal evidence schema mismatch")
    if raw.get("completion_claims") != empty_completion_claims():
        raise OutboxBlock("outbox terminal completion claims must all be false")
    if "effect_ack" in raw and raw.get("effect_ack") != "NOT_REQUIRED":
        raise OutboxBlock("outbox terminal effect acknowledgement is invalid")
    _reject_recursive_completion_claims(raw)
    if "continuation" in raw:
        raw["continuation"] = _validate_terminal_continuation(raw["continuation"])
    intent = _mapping(next_item.get("intent"), "terminal intent")
    lane = _lane(intent.get("lane"))
    sequence = _sequence(intent.get("sequence"))
    fingerprint = _digest(intent.get("fingerprint"), "terminal fingerprint")
    transports = _mapping(next_item.get("transport"), "terminal transports")
    acceptances = _mapping(next_item.get("acceptance"), "terminal acceptances")
    completions = _mapping(next_item.get("completion"), "terminal completions")
    child_recovery = _mapping(
        next_item.get("child_recovery"), "terminal child recovery"
    )
    retry_scan_cursors = _mapping(
        next_item.get("retry_scan_cursor"), "terminal retry scan cursors"
    )
    same_run_results = _mapping(
        next_item.get("same_run_result"), "terminal same-run results"
    )
    late_acceptance_conflict = next_item.get("late_acceptance_conflict")
    authority_observation_record = next_item.get("authority_observation")
    d0 = raw.get("d0")
    if raw.get("productive_effect") is not False:
        raise OutboxBlock("outbox terminal record cannot claim a productive effect")
    if d0 == 2:
        if late_acceptance_conflict is not None:
            raise OutboxBlock(
                "late attempt-one acceptance conflict forbids business success"
            )
        if any(
            isinstance(value, Mapping)
            and value.get("d0") == 3
            and isinstance(value.get("child"), Mapping)
            and value["child"].get("conclusion") not in {None, "success"}
            for value in same_run_results.values()
        ):
            raise OutboxBlock(
                "later exact same-run adverse result supersedes D0=2"
            )
        if raw.get("state") not in {"CONTINUE", "CURRENT", "REOBSERVE"}:
            raise OutboxBlock("D0=2 terminal state is invalid")
        if "exhaustion" in raw:
            raise OutboxBlock("D0=2 terminal cannot carry exhaustion evidence")
        if not transports:
            raise OutboxBlock("D0=2 terminal requires an exact transport")
        receipt = _mapping(raw.get("business_receipt"), "outbox business receipt")
        receipt_attempt = receipt.get("attempt")
        original_acceptance = acceptances.get(str(receipt_attempt))
        original_completion = completions.get(str(receipt_attempt))
        recovery_state = child_recovery.get(str(receipt_attempt))
        recovered_acceptance = (
            recovery_state.get("acceptance")
            if isinstance(recovery_state, Mapping)
            else None
        )
        recovered_completion = (
            recovery_state.get("completion")
            if isinstance(recovery_state, Mapping)
            else None
        )
        use_recovery = receipt.get("child_recovery") is True
        use_same_run = receipt.get("same_run_result") is True
        if use_recovery and use_same_run:
            raise OutboxBlock("business receipt cannot mix two recovery modes")
        acceptance = recovered_acceptance if use_recovery else original_acceptance
        completion = (
            same_run_results.get(str(receipt_attempt))
            if use_same_run
            else (recovered_completion if use_recovery else original_completion)
        )
        completed_child = (
            _mapping(completion.get("child"), "business completed child")
            if isinstance(completion, Mapping)
            else {}
        )
        receipt_artifact = receipt.get("artifact")
        artifact = (
            _mapping(receipt_artifact, "business receipt artifact")
            if isinstance(receipt_artifact, Mapping)
            else {}
        )
        completion_evidence = (
            _mapping(completion.get("evidence"), "business completion evidence")
            if isinstance(completion, Mapping)
            else {}
        )
        expected_artifact_name = None
        if lane in {"ruleset-dispatch", "reconciler-rerun"} and completed_child:
            expected_artifact_name = (
                "qikvrt-main-ruleset-receipt-"
                f"{completed_child.get('run_id')}-{completed_child.get('run_attempt')}"
            )
        receipt_keys = {
            "schema",
            "lane",
            "sequence",
            "fingerprint",
            "outcome",
            "attempt",
            "run_id",
            "run_attempt",
            "workflow_id",
            "workflow_path",
            "head_sha",
            "locator_child_sha256",
            "child_sha256",
            "child_recovery",
            "same_run_result",
            "artifact",
            "completion_evidence_sha256",
            "evidence_sha256",
            "verified",
            "productive_effect",
        }
        artifact_keys = {
            "id",
            "name",
            "archive_sha256",
            "payload_sha256",
            "producer_run_id",
            "producer_run_attempt",
            "verified",
        }
        if (
            set(receipt) != receipt_keys
            or set(artifact) != artifact_keys
            or receipt.get("schema") != BUSINESS_RECEIPT_SCHEMA
            or receipt.get("lane") != lane
            or receipt.get("sequence") != sequence
            or receipt.get("fingerprint") != fingerprint
            or receipt.get("outcome") not in BUSINESS_OUTCOMES[lane]
            or receipt_attempt != 1
            or str(receipt_attempt) not in transports
            or not isinstance(acceptance, Mapping)
            or not isinstance(completion, Mapping)
            or receipt.get("run_id") is None
            or receipt.get("run_attempt") is None
            or receipt.get("run_id") != completed_child.get("run_id")
            or receipt.get("run_attempt") != completed_child.get("run_attempt")
            or receipt.get("workflow_id") != completed_child.get("workflow_id")
            or receipt.get("workflow_path") != completed_child.get("workflow_path")
            or receipt.get("head_sha") != completed_child.get("head_sha")
            or receipt.get("locator_child_sha256")
            != acceptance.get("child_sha256")
            or receipt.get("child_sha256") != completion.get("child_sha256")
            or receipt.get("child_recovery") is not use_recovery
            or receipt.get("same_run_result") is not use_same_run
            or completed_child.get("status") != "completed"
            or completed_child.get("conclusion") != "success"
            or not artifact
            or isinstance(artifact.get("id"), bool)
            or not isinstance(artifact.get("id"), int)
            or artifact.get("id", 0) < 1
            or not isinstance(artifact.get("name"), str)
            or not artifact.get("name")
            or (
                expected_artifact_name is not None
                and artifact.get("name") != expected_artifact_name
            )
            or HEX64.fullmatch(
                str(artifact.get("archive_sha256", "")).removeprefix("sha256:")
            )
            is None
            or HEX64.fullmatch(str(artifact.get("payload_sha256"))) is None
            or artifact.get("producer_run_id") != completed_child.get("run_id")
            or artifact.get("producer_run_attempt")
            != completed_child.get("run_attempt")
            or artifact.get("verified") is not True
            or artifact != completion_evidence.get("artifact")
            or receipt.get("completion_evidence_sha256")
            != completion.get("evidence_sha256")
            or receipt.get("evidence_sha256") != digest(dict(artifact))
            or receipt.get("verified") is not True
            or receipt.get("productive_effect") is not False
        ):
            raise OutboxBlock("D0=2 business receipt binding mismatch")
        if "reason" in raw:
            _technical_code(
                raw.get("reason"),
                "D0=2 terminal reason",
                D0_2_TECHNICAL_REASONS[lane],
            )
        _positive_int(receipt.get("run_id"), "business receipt run id")
        _positive_int(receipt.get("run_attempt"), "business receipt run attempt")
    elif d0 == 3:
        if raw.get("state") != "REQUEST_AUTHORITY":
            raise OutboxBlock("D0=3 terminal state is invalid")
        if "business_receipt" in raw:
            raise OutboxBlock("D0=3 terminal cannot carry a business receipt")
        exhaustion = _mapping(raw.get("exhaustion"), "outbox exhaustion evidence")
        attempts = exhaustion.get("attempts")
        if not isinstance(attempts, list) or any(
            isinstance(item, bool) or item != 1 for item in attempts
        ):
            raise OutboxBlock("outbox exhausted-attempt list is invalid")
        observed_attempts = sorted(int(item) for item in transports)
        mode = exhaustion.get("mode")
        common_exhaustion_keys = {
            "schema",
            "lane",
            "sequence",
            "fingerprint",
            "mode",
            "attempts",
            "first_blocker",
            "verified",
            "productive_effect",
        }
        mode_keys = {
            "CHILD_RESULT_ADVERSE": {
                "transport_attempt",
                "successor",
                "successor_sha256",
                "completion_evidence_sha256",
            },
            "ONE_SHOT_RERUN_EXHAUSTED": {
                "target_run_attempt",
                "successor",
                "successor_sha256",
            },
            "ONE_SHOT_RERUN_TRANSPORT_AMBIGUOUS": {
                "authority_observation_sha256",
                "observation_sha256",
            },
            "CHILD_RERUN_EXHAUSTED": {
                "transport_attempt",
                "target_run_id",
                "target_run_attempt",
                "successor",
                "successor_sha256",
                "completion_evidence_sha256",
                "authority_observation_sha256",
                "observation_sha256",
            },
            "SAME_RUN_RESULT_ADVERSE": {
                "transport_attempt",
                "successor",
                "successor_sha256",
            },
            "AMBIGUOUS_OR_DRIFT": {
                "authority_observation_sha256",
                "late_acceptance_conflict_sha256",
                "observation_sha256",
            },
        }
        if mode not in mode_keys or set(exhaustion) - (
            common_exhaustion_keys | mode_keys[mode]
        ):
            raise OutboxBlock("outbox exhaustion evidence key set is not authorized")
        successful_completions = [
            value
            for value in completions.values()
            if isinstance(value, Mapping)
            and isinstance(value.get("child"), Mapping)
            and value["child"].get("conclusion") == "success"
        ]
        successful_recovered_completions = [
            recovery.get("completion")
            for recovery in child_recovery.values()
            if isinstance(recovery, Mapping)
            and isinstance(recovery.get("completion"), Mapping)
            and isinstance(recovery["completion"].get("child"), Mapping)
            and recovery["completion"]["child"].get("conclusion") == "success"
        ]
        successful_same_run_results = [
            value
            for value in same_run_results.values()
            if isinstance(value, Mapping)
            and value.get("d0") == 2
            and isinstance(value.get("child"), Mapping)
            and value["child"].get("conclusion") == "success"
        ]
        if (
            successful_completions
            or successful_recovered_completions
            or successful_same_run_results
        ) and mode != "SAME_RUN_RESULT_ADVERSE" and not (
            mode == "AMBIGUOUS_OR_DRIFT"
            and late_acceptance_conflict is not None
        ):
            raise OutboxBlock(
                "exact successful completion has precedence over D0=3 ambiguity"
            )
        allowed_blockers = COMMON_EXHAUSTION_BLOCKERS.get(mode, frozenset()) | (
            LANE_EXHAUSTION_BLOCKERS.get(lane, {}).get(mode, frozenset())
        )
        blocker = _technical_code(
            exhaustion.get("first_blocker"),
            "D0=3 exhaustion blocker",
            allowed_blockers,
        )
        if mode == "CHILD_RESULT_ADVERSE":
            transport_attempt = exhaustion.get("transport_attempt")
            accepted = acceptances.get(str(transport_attempt))
            completion = completions.get(str(transport_attempt))
            completed_child = (
                _mapping(completion.get("child"), "adverse completed child")
                if isinstance(completion, Mapping)
                else {}
            )
            if lane == "reconciler-rerun":
                expected_attempt = 1
                expected_attempts = [1]
                expected_acceptances = {"1"}
            else:
                expected_attempt = 1
                expected_attempts = [1]
                expected_acceptances = {"1"}
            if (
                transport_attempt != expected_attempt
                or attempts != expected_attempts
                or observed_attempts != expected_attempts
                or set(acceptances) != expected_acceptances
                or not isinstance(accepted, Mapping)
                or not isinstance(completion, Mapping)
                or not completed_child
                or completed_child.get("status") != "completed"
                or completed_child.get("conclusion") in {None, "success"}
                or exhaustion.get("successor") != completed_child
                or exhaustion.get("successor_sha256")
                != completion.get("child_sha256")
                or exhaustion.get("completion_evidence_sha256")
                != completion.get("evidence_sha256")
            ):
                raise OutboxBlock(
                    "child-result adverse exhaustion lacks exact completed evidence"
                )
        elif mode == "ONE_SHOT_RERUN_EXHAUSTED":
            accepted = acceptances.get("1")
            completion = completions.get("1")
            completed_child = (
                _mapping(completion.get("child"), "one-shot rerun successor")
                if isinstance(completion, Mapping)
                else {}
            )
            if (
                lane != "reconciler-rerun"
                or attempts != [1]
                or observed_attempts != [1]
                or exhaustion.get("target_run_attempt") != 2
                or not isinstance(accepted, Mapping)
                or not completed_child
                or completed_child.get("run_attempt") != 2
                or completed_child.get("status") != "completed"
                or completed_child.get("conclusion") in {None, "success"}
                or exhaustion.get("successor") != completed_child
                or exhaustion.get("successor_sha256")
                != completion.get("child_sha256")
            ):
                raise OutboxBlock(
                    "one-shot rerun exhaustion requires only exact rerun attempt two"
                )
        elif mode == "ONE_SHOT_RERUN_TRANSPORT_AMBIGUOUS":
            record = _mapping(
                authority_observation_record,
                "stored one-shot Authority observation record",
            )
            observation = _validate_authority_observation_for_item(
                record.get("observation"),
                blocker=blocker,
                intent=intent,
                transports=transports,
                acceptances=acceptances,
                completions=completions,
                child_recovery=child_recovery,
                retry_scan_cursors=retry_scan_cursors,
                late_acceptance_conflict=late_acceptance_conflict,
            )
            if (
                lane != "reconciler-rerun"
                or attempts != [1]
                or observed_attempts != [1]
                or acceptances
                or record.get("blocker") != blocker
                or exhaustion.get("authority_observation_sha256")
                != digest(dict(record))
                or exhaustion.get("observation_sha256")
                != digest(observation)
            ):
                raise OutboxBlock(
                    "one-shot ambiguous HOLD must prove no observed rerun effect"
                )
        elif mode == "CHILD_RERUN_EXHAUSTED":
            transport_attempt = exhaustion.get("transport_attempt")
            recovery_state = child_recovery.get(str(transport_attempt))
            rerun = (
                recovery_state.get("rerun")
                if isinstance(recovery_state, Mapping)
                else None
            )
            recovered_acceptance = (
                recovery_state.get("acceptance")
                if isinstance(recovery_state, Mapping)
                else None
            )
            recovered_completion = (
                recovery_state.get("completion")
                if isinstance(recovery_state, Mapping)
                else None
            )
            successor = exhaustion.get("successor")
            successor_digest = exhaustion.get("successor_sha256")
            if (
                attempts != observed_attempts
                or transport_attempt != 1
                or transport_attempt not in observed_attempts
                or not isinstance(rerun, Mapping)
                or rerun.get("target_run_attempt") != 2
                or exhaustion.get("target_run_id") != rerun.get("target_run_id")
                or exhaustion.get("target_run_attempt") != 2
            ):
                raise OutboxBlock(
                    "child-rerun exhaustion requires exact recovery record"
                )
            if recovered_acceptance is not None:
                recovered_child = _mapping(
                    recovered_completion.get("child"),
                    "child-rerun exhausted successor",
                ) if isinstance(recovered_completion, Mapping) else {}
                if (
                    not isinstance(recovered_completion, Mapping)
                    or not recovered_child
                    or recovered_child.get("status") != "completed"
                    or recovered_child.get("conclusion") in {None, "success"}
                    or recovered_child.get("run_attempt") != 2
                    or successor != recovered_child
                    or successor_digest != recovered_completion.get("child_sha256")
                    or exhaustion.get("completion_evidence_sha256")
                    != recovered_completion.get("evidence_sha256")
                ):
                    raise OutboxBlock(
                        "child-rerun exhausted successor binding mismatch"
                    )
            else:
                record = _mapping(
                    authority_observation_record,
                    "stored child-rerun Authority observation record",
                )
                observation = _validate_authority_observation_for_item(
                    record.get("observation"),
                    blocker=blocker,
                    intent=intent,
                    transports=transports,
                    acceptances=acceptances,
                    completions=completions,
                    child_recovery=child_recovery,
                    retry_scan_cursors=retry_scan_cursors,
                    late_acceptance_conflict=late_acceptance_conflict,
                )
                if (
                    blocker != "CHILD_RERUN_ATTEMPT_2_NOT_OBSERVED"
                    or successor is not None
                    or successor_digest is not None
                    or "completion_evidence_sha256" in exhaustion
                    or record.get("blocker") != blocker
                    or exhaustion.get("authority_observation_sha256")
                    != digest(dict(record))
                    or exhaustion.get("observation_sha256")
                    != digest(observation)
                ):
                    raise OutboxBlock(
                        "child-rerun orphan exhaustion lacks exact observation"
                    )
        elif mode == "SAME_RUN_RESULT_ADVERSE":
            transport_attempt = exhaustion.get("transport_attempt")
            observed = same_run_results.get(str(transport_attempt))
            observed_child = (
                _mapping(observed.get("child"), "same-run adverse child")
                if isinstance(observed, Mapping)
                else {}
            )
            if (
                lane != "exact-head-dispatch"
                or attempts != observed_attempts
                or transport_attempt not in observed_attempts
                or not observed_child
                or observed.get("d0") != 3
                or observed_child.get("status") != "completed"
                or observed_child.get("conclusion") in {None, "success"}
                or exhaustion.get("successor") != observed_child
                or exhaustion.get("successor_sha256")
                != observed.get("child_sha256")
            ):
                raise OutboxBlock("same-run adverse exhaustion binding mismatch")
        elif mode == "AMBIGUOUS_OR_DRIFT":
            if attempts != observed_attempts:
                raise OutboxBlock("authority evidence attempt set differs from ledger")
        else:
            raise OutboxBlock("outbox exhaustion mode is invalid")
        if (
            exhaustion.get("schema") != EXHAUSTION_SCHEMA
            or exhaustion.get("lane") != lane
            or exhaustion.get("sequence") != sequence
            or exhaustion.get("fingerprint") != fingerprint
            or exhaustion.get("verified") is not True
            or exhaustion.get("productive_effect") is not False
        ):
            raise OutboxBlock("D0=3 exhaustion evidence binding mismatch")
        late_conflict_code = (
            "LATE_ATTEMPT_1_ACCEPTANCE_AFTER_ATTEMPT_2_SEALED"
        )
        if late_acceptance_conflict is not None:
            if (
                mode != "AMBIGUOUS_OR_DRIFT"
                or blocker != late_conflict_code
                or attempts != [1, 2]
                or observed_attempts != [1, 2]
                or exhaustion.get("late_acceptance_conflict_sha256")
                != digest(dict(late_acceptance_conflict))
            ):
                raise OutboxBlock(
                    "late acceptance conflict requires exact immutable conflict "
                    "and attempt-two ambiguity terminalization"
                )
            if "2" in acceptances:
                if (
                    set(acceptances) != {"2"}
                    or "authority_observation_sha256" in exhaustion
                    or "observation_sha256" in exhaustion
                ):
                    raise OutboxBlock(
                        "late acceptance conflict exact adoption is ambiguous"
                    )
            else:
                record = _mapping(
                    authority_observation_record,
                    "stored late-acceptance Authority observation record",
                )
                observation = _validate_authority_observation_for_item(
                    record.get("observation"),
                    blocker=blocker,
                    intent=intent,
                    transports=transports,
                    acceptances=acceptances,
                    completions=completions,
                    child_recovery=child_recovery,
                    retry_scan_cursors=retry_scan_cursors,
                    late_acceptance_conflict=late_acceptance_conflict,
                )
                if (
                    record.get("blocker") != blocker
                    or exhaustion.get("authority_observation_sha256")
                    != digest(dict(record))
                    or exhaustion.get("observation_sha256")
                    != digest(observation)
                ):
                    raise OutboxBlock(
                        "late acceptance conflict without attempt-two adoption "
                        "requires exact absence observation"
                    )
        elif blocker == late_conflict_code:
            raise OutboxBlock("late acceptance blocker lacks immutable conflict")
        elif mode == "AMBIGUOUS_OR_DRIFT":
            record = _mapping(
                authority_observation_record,
                "stored Authority observation record",
            )
            if (
                record.get("blocker") != blocker
                or exhaustion.get("authority_observation_sha256")
                != digest(dict(record))
            ):
                raise OutboxBlock(
                    "authority terminal does not bind stored observation record"
                )
            observation = _validate_authority_observation_for_item(
                record.get("observation"),
                blocker=blocker,
                intent=intent,
                transports=transports,
                acceptances=acceptances,
                completions=completions,
                child_recovery=child_recovery,
                retry_scan_cursors=retry_scan_cursors,
                late_acceptance_conflict=late_acceptance_conflict,
            )
            if exhaustion.get("observation_sha256") != digest(observation):
                raise OutboxBlock("authority observation digest mismatch")
        if "reason" in raw and _technical_code(
            raw.get("reason"), "D0=3 terminal reason", allowed_blockers
        ) != blocker:
            raise OutboxBlock("D0=3 reason differs from exact exhaustion blocker")
    else:
        raise OutboxBlock("outbox terminal evidence must be D0=2 or D0=3")
    return raw


def terminalize(
    backend: LedgerBackend,
    *,
    lane: str,
    sequence: int,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    lane = _lane(lane)
    sequence = _sequence(sequence)
    current = read_next(backend, lane)
    if current.get("state") != "PENDING" or current.get("sequence") != sequence:
        # Idempotent replay after an exact terminal is handled inside the CAS
        # planner.  A different live FIFO item must never lend its evidence.
        head = backend.get_ledger_head(lane)
        if head is None:
            raise OutboxBlock("outbox ledger ref disappeared")
        existing = _read_json(
            backend, head, terminal_path(lane, sequence), required=False
        )
        if existing is None:
            raise OutboxBlock("only the current FIFO item can be terminalized")
        evidence_value = dict(_mapping(evidence, "outbox terminal evidence"))
    else:
        evidence_mapping = _mapping(evidence, "outbox terminal evidence")
        current_with_observation = _bind_authority_observation_at(
            backend,
            _sha(current.get("ledger_head"), "terminal read snapshot"),
            current,
            evidence_mapping,
        )
        evidence_value = validate_terminal_evidence(
            evidence_mapping, next_item=current_with_observation
        )
    terminal: dict[str, Any] = {}

    def plan_at(parent: str) -> Mapping[str, bytes] | None:
        nonlocal terminal
        meta = validate_meta(_read_json(backend, parent, meta_path(lane)), lane)
        path = terminal_path(lane, sequence)
        existing = _read_json(backend, parent, path, required=False)
        if existing is not None:
            if meta["drain_seq"] <= sequence:
                raise OutboxBlock("terminal exists without an advanced drain cursor")
            terminal = dict(existing)
            expected_sha = digest(evidence_value)
            if terminal.get("evidence_sha256") != expected_sha:
                raise OutboxBlock("immutable outbox terminal collision")
            return None
        if meta["drain_seq"] != sequence:
            raise OutboxBlock("only the current FIFO item can be terminalized")
        current = _read_next_at(backend, parent, lane)
        current = _bind_authority_observation_at(
            backend, parent, current, evidence_value
        )
        # All absence, completion-precedence, and transport predicates are
        # state-dependent.  Revalidate them against every CAS parent so a
        # concurrent acceptance/completion can never be overwritten by stale
        # terminal evidence after a non-fast-forward retry.
        current_evidence = validate_terminal_evidence(
            evidence_value, next_item=current
        )
        intent = _mapping(current.get("intent"), "terminal intent")
        if current_evidence.get("d0") == 2:
            sealed_main = _sha(
                _mapping(intent.get("payload"), "terminal intent payload").get(
                    "main_head_sha"
                ),
                "terminal sealed main",
            )
            if backend.get_main_head() != sealed_main:
                raise OutboxBlock(
                    "OUTBOX_EVALUATOR_SUPERSEDED: D0=2 terminal main drifted"
                )
        elif (
            _mapping(
                current_evidence.get("exhaustion"),
                "terminal recovery-bound exhaustion",
            ).get("first_blocker")
            in MAIN_BOUND_AUTHORITY_BLOCKERS
        ):
            sealed_main = _sha(
                _mapping(intent.get("payload"), "terminal intent payload").get(
                    "main_head_sha"
                ),
                "terminal sealed main",
            )
            if backend.get_main_head() != sealed_main:
                raise OutboxBlock(
                    "OUTBOX_EVALUATOR_SUPERSEDED: capped-scan terminal main drifted"
                )
        terminal = {
            "schema": TERMINAL_SCHEMA,
            "lane": lane,
            "sequence": sequence,
            "fingerprint": intent["fingerprint"],
            "state": "TERMINAL",
            "d0": current_evidence["d0"],
            "evidence_sha256": digest(current_evidence),
            "evidence": current_evidence,
            "productive_effect": False,
        }
        next_meta = {**meta, "drain_seq": sequence + 1}
        return {
            path: canonical_bytes(terminal),
            meta_path(lane): canonical_bytes(next_meta),
        }

    expected_evidence_sha = digest(evidence_value)

    def verify_at(head: str) -> bool:
        value = _read_json(
            backend, head, terminal_path(lane, sequence), required=False
        )
        if value is None or value.get("evidence_sha256") != expected_evidence_sha:
            return False
        meta = validate_meta(_read_json(backend, head, meta_path(lane)), lane)
        return meta["drain_seq"] > sequence

    cas = bounded_ff_cas(
        backend,
        lane=lane,
        plan_at=plan_at,
        build_message=f"Terminalize {lane} outbox item {sequence}",
        verify_at=verify_at,
    )
    return {
        **terminal,
        "ledger_ref": ledger_ref(lane),
        "ledger_head": cas["head"],
        "cas": cas,
    }


def _load_json(path: pathlib.Path, label: str) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OutboxBlock(f"{label} could not be read: {exc}") from exc


def _write_result(value: Mapping[str, Any], receipt: pathlib.Path | None) -> None:
    raw = canonical_bytes(value)
    if receipt is not None:
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_bytes(raw)
    sys.stdout.buffer.write(raw)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--receipt", type=pathlib.Path)
    subparsers = parser.add_subparsers(dest="command", required=True)

    enqueue_parser = subparsers.add_parser("enqueue")
    enqueue_parser.add_argument("--lane", required=True, choices=LANES)
    enqueue_parser.add_argument("--payload", required=True, type=pathlib.Path)
    enqueue_parser.add_argument("--artifact-id", required=True, type=int)
    enqueue_parser.add_argument("--artifact-name", required=True)
    enqueue_parser.add_argument("--artifact-digest", required=True)

    next_parser = subparsers.add_parser("next")
    next_parser.add_argument("--lane", required=True, choices=LANES)

    lookup_parser = subparsers.add_parser("lookup")
    lookup_parser.add_argument("--lane", required=True, choices=LANES)
    lookup_parser.add_argument("--sequence", required=True, type=int)
    lookup_parser.add_argument("--fingerprint", required=True)

    lookup_fingerprint_parser = subparsers.add_parser("lookup-fingerprint")
    lookup_fingerprint_parser.add_argument(
        "--lane", required=True, choices=LANES
    )
    lookup_fingerprint_parser.add_argument("--fingerprint", required=True)

    authority_parser = subparsers.add_parser("verify-authority")
    authority_parser.add_argument("--lane", required=True, choices=LANES)

    transport_parser = subparsers.add_parser("prepare-transport")
    transport_parser.add_argument("--lane", required=True, choices=LANES)
    transport_parser.add_argument("--sequence", required=True, type=int)
    transport_parser.add_argument("--attempt", required=True, type=int, choices=(1,))
    transport_parser.add_argument("--request", required=True, type=pathlib.Path)
    transport_parser.add_argument("--actor-run-id", required=True, type=int)
    transport_parser.add_argument("--actor-run-attempt", required=True, type=int)
    transport_parser.add_argument("--retry-evidence", type=pathlib.Path)
    transport_parser.add_argument("--witness-run-id", type=int)
    transport_parser.add_argument("--witness-run-attempt", type=int)

    acceptance_parser = subparsers.add_parser("accept")
    acceptance_parser.add_argument("--lane", required=True, choices=LANES)
    acceptance_parser.add_argument("--sequence", required=True, type=int)
    acceptance_parser.add_argument("--attempt", required=True, type=int, choices=(1,))
    acceptance_parser.add_argument("--child", required=True, type=pathlib.Path)

    completion_parser = subparsers.add_parser("complete")
    completion_parser.add_argument("--lane", required=True, choices=LANES)
    completion_parser.add_argument("--sequence", required=True, type=int)
    completion_parser.add_argument("--attempt", required=True, type=int, choices=(1,))
    completion_parser.add_argument("--child", required=True, type=pathlib.Path)
    completion_parser.add_argument("--evidence", required=True, type=pathlib.Path)
    completion_parser.add_argument("--child-recovery", action="store_true")

    same_run_parser = subparsers.add_parser("observe-same-run-result")
    same_run_parser.add_argument("--lane", required=True, choices=LANES)
    same_run_parser.add_argument("--sequence", required=True, type=int)
    same_run_parser.add_argument("--fingerprint", required=True)
    same_run_parser.add_argument(
        "--transport-attempt", required=True, type=int, choices=(1,)
    )
    same_run_parser.add_argument("--child", required=True, type=pathlib.Path)
    same_run_parser.add_argument("--evidence", required=True, type=pathlib.Path)

    child_rerun_parser = subparsers.add_parser("prepare-child-rerun")
    child_rerun_parser.add_argument("--lane", required=True, choices=LANES)
    child_rerun_parser.add_argument("--sequence", required=True, type=int)
    child_rerun_parser.add_argument(
        "--transport-attempt", required=True, type=int, choices=(1,)
    )
    child_rerun_parser.add_argument(
        "--retry-evidence", required=True, type=pathlib.Path
    )
    child_rerun_parser.add_argument("--actor-run-id", required=True, type=int)
    child_rerun_parser.add_argument("--actor-run-attempt", required=True, type=int)

    child_rerun_acceptance_parser = subparsers.add_parser("accept-child-rerun")
    child_rerun_acceptance_parser.add_argument(
        "--lane", required=True, choices=LANES
    )
    child_rerun_acceptance_parser.add_argument(
        "--sequence", required=True, type=int
    )
    child_rerun_acceptance_parser.add_argument(
        "--transport-attempt", required=True, type=int, choices=(1,)
    )
    child_rerun_acceptance_parser.add_argument(
        "--child", required=True, type=pathlib.Path
    )

    retry_cursor_parser = subparsers.add_parser("record-retry-scan-cursor")
    retry_cursor_parser.add_argument("--lane", required=True, choices=LANES)
    retry_cursor_parser.add_argument("--sequence", required=True, type=int)
    retry_cursor_parser.add_argument("--cursor", required=True, type=pathlib.Path)
    retry_cursor_parser.add_argument("--artifact-id", required=True, type=int)
    retry_cursor_parser.add_argument("--artifact-name", required=True)
    retry_cursor_parser.add_argument("--artifact-digest", required=True)

    observation_parser = subparsers.add_parser("record-observation")
    observation_parser.add_argument("--lane", required=True, choices=LANES)
    observation_parser.add_argument("--sequence", required=True, type=int)
    observation_parser.add_argument(
        "--observation", required=True, type=pathlib.Path
    )
    observation_parser.add_argument("--producer", required=True, type=pathlib.Path)
    observation_parser.add_argument("--artifact-id", required=True, type=int)
    observation_parser.add_argument("--artifact-name", required=True)
    observation_parser.add_argument("--artifact-digest", required=True)

    terminal_parser = subparsers.add_parser("terminalize")
    terminal_parser.add_argument("--lane", required=True, choices=LANES)
    terminal_parser.add_argument("--sequence", required=True, type=int)
    terminal_parser.add_argument("--evidence", required=True, type=pathlib.Path)

    args = parser.parse_args(argv)
    try:
        repository = _repository(args.repository)
        read_only = args.command in {
            "next",
            "lookup",
            "lookup-fingerprint",
            "verify-authority",
        }
        token = (
            auditor_token_from_environment()
            if read_only
            else writer_token_from_environment()
        )
        # Public, non-secret identity input required by both readback scopes.
        writer_actor_id_from_environment()
        backend = GitHubLedgerBackend(repository, token)
        if args.command == "verify-authority":
            ledger_head = ensure_initialized(backend, args.lane)
            authority = backend.last_authority_readback
            if not isinstance(authority, Mapping):
                raise OutboxBlock(
                    "AUTHORITY_OUTBOX_LEDGER_ENVIRONMENT_NOT_VERIFIED: "
                    "effect-local readback receipt is absent"
                )
            result = {
                **dict(authority),
                "ledger_ref": ledger_ref(args.lane),
                "ledger_head": ledger_head,
                "ledger_protection_verified": True,
            }
        elif args.command == "enqueue":
            payload = validate_payload(_load_json(args.payload, "outbox payload"), lane=args.lane)
            payload_sha = sha256_bytes(canonical_bytes(payload))
            result = append_intent(
                backend,
                payload=payload,
                artifact={
                    "id": args.artifact_id,
                    "name": args.artifact_name,
                    "archive_sha256": args.artifact_digest,
                    "payload_sha256": payload_sha,
                    "producer_run_id": payload["producer"]["run_id"],
                    "producer_run_attempt": payload["producer"]["run_attempt"],
                    "producer_workflow_id": payload["producer"]["workflow_id"],
                },
            )
        elif args.command == "next":
            result = read_next(backend, args.lane)
        elif args.command == "lookup":
            result = lookup(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                fingerprint=args.fingerprint,
            )
        elif args.command == "lookup-fingerprint":
            result = lookup_fingerprint(
                backend,
                lane=args.lane,
                fingerprint=args.fingerprint,
            )
        elif args.command == "prepare-transport":
            result = prepare_transport(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                attempt=args.attempt,
                request=_load_json(args.request, "transport request"),
                actor_run_id=args.actor_run_id,
                actor_run_attempt=args.actor_run_attempt,
                retry_evidence=(
                    _load_json(args.retry_evidence, "retry evidence")
                    if args.retry_evidence is not None
                    else None
                ),
                witness_run_id=args.witness_run_id,
                witness_run_attempt=args.witness_run_attempt,
            )
        elif args.command == "accept":
            result = record_acceptance(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                attempt=args.attempt,
                child=_load_json(args.child, "accepted child"),
            )
        elif args.command == "complete":
            result = record_completion(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                attempt=args.attempt,
                child=_load_json(args.child, "completed child"),
                evidence=_load_json(args.evidence, "completion evidence"),
                child_recovery=args.child_recovery,
            )
        elif args.command == "observe-same-run-result":
            result = record_same_run_result(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                fingerprint=args.fingerprint,
                transport_attempt=args.transport_attempt,
                child=_load_json(args.child, "same-run completed child"),
                evidence=_load_json(args.evidence, "same-run completion evidence"),
            )
        elif args.command == "prepare-child-rerun":
            result = prepare_child_rerun(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                transport_attempt=args.transport_attempt,
                retry_evidence=_load_json(
                    args.retry_evidence, "child-rerun retry evidence"
                ),
                actor_run_id=args.actor_run_id,
                actor_run_attempt=args.actor_run_attempt,
            )
        elif args.command == "accept-child-rerun":
            result = record_child_rerun_acceptance(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                transport_attempt=args.transport_attempt,
                child=_load_json(args.child, "recovered child"),
            )
        elif args.command == "record-retry-scan-cursor":
            cursor = _load_json(args.cursor, "retry scan cursor")
            cursor_producer = _mapping(
                cursor.get("observation_producer"),
                "retry scan cursor producer",
            )
            result = record_retry_scan_cursor(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                cursor=cursor,
                artifact={
                    "id": args.artifact_id,
                    "name": args.artifact_name,
                    "archive_sha256": args.artifact_digest,
                    "payload_sha256": sha256_bytes(canonical_bytes(cursor)),
                    "producer_run_id": cursor_producer["run_id"],
                    "producer_run_attempt": cursor_producer["run_attempt"],
                    "producer_workflow_id": cursor_producer["workflow_id"],
                },
            )
        elif args.command == "record-observation":
            observation = _load_json(
                args.observation, "Authority API observation"
            )
            producer = _load_json(args.producer, "Authority observer producer")
            result = record_authority_observation(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                observation=observation,
                producer=producer,
                artifact={
                    "id": args.artifact_id,
                    "name": args.artifact_name,
                    "archive_sha256": args.artifact_digest,
                    "payload_sha256": sha256_bytes(
                        canonical_bytes(observation)
                    ),
                    "producer_run_id": producer["run_id"],
                    "producer_run_attempt": producer["run_attempt"],
                    "producer_workflow_id": producer["workflow_id"],
                },
            )
        elif args.command == "terminalize":
            result = terminalize(
                backend,
                lane=args.lane,
                sequence=args.sequence,
                evidence=_load_json(args.evidence, "terminal evidence"),
            )
        else:  # pragma: no cover - argparse enforces the command set.
            raise OutboxBlock("outbox command is invalid")
    except (OSError, ValueError, OutboxBlock) as exc:
        _write_result(
            {
                "schema": "qikvrt_ruleset_outbox_command_v1",
                "state": "HOLD",
                "d0": 3,
                "action": "NONE",
                "first_blocker": str(exc),
                "productive_effect": False,
            },
            args.receipt,
        )
        return 3
    _write_result(result, args.receipt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
