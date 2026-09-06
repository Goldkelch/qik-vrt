#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic, fail-closed Mesh repository review core.

The trusted-main workflow supplies an exact candidate snapshot plus the full
``git diff --binary --full-index`` byte stream. This module performs bounded
static invariant review, binds the result to base/head/tree/scope/diff and
derives exactly one causal D0 continuation. It never writes GitHub or Git.

The result is deliberately not an independent Code-Owner approval and always
remains ``HOLD_UNVERIFIED``. Repository metadata and the append-only Mesh
review ledger are projections owned by the workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.parse
from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Any

REVIEW_DIFF_CHUNK_BYTES = 1024 * 1024
REVIEW_DIFF_TRANSPORT_SCHEMA = "qikvrt_mesh_review_diff_transport_v1"
REVIEW_DIFF_TRANSPORT_DELIVERY = "SEQUENTIAL_EXACT_PACKET_ORDER"
SUCCESS = {"success"}
NON_ADVERSE = {"success", "skipped"}
NON_GATE_OBSERVER_PATHS = {
    "QIKVRT live status watch": ".github/workflows/qikvrt_live_status_watch.yml",
}
LEDGER_REF = "refs/heads/qikvrt/mesh-review-ledger-v1"
LEDGER_ROOT = "state/mesh/reviews"
REVIEW_QUEUE_ROOT = "state/mesh/review-queue"
REVIEW_QUEUE_ACK_ROOT = "state/mesh/review-queue-acks"
TRUSTED_EVALUATOR_PATH = "tools/qikvrt_requested_review_executor.py"
TRUSTED_WORKFLOW_PATH = ".github/workflows/qikvrt_requested_review_executor.yml"
REVIEW_MARKER = "qikvrt-mesh-review:v1"
LIVE_STATUS_MARKER = "qikvrt-live-status-watch"
TRUSTED_AUTOMATION_DISCUSSION_PREFIXES = (
    f"<!-- {REVIEW_MARKER} ",
    f"<!-- {LIVE_STATUS_MARKER} -->",
)
ACTIVE_WRITER_STATES = ("queued", "in_progress", "waiting", "requested", "pending")
REVIEW_SELECTION_SCHEMA = "qikvrt_requested_review_selection_v1"
REVIEW_INTAKE_SCHEMA = "qikvrt_review_intake_v1"
REVIEW_PRIORITY_POLICY_PATH = "policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json"
REVIEW_PRIORITY_POLICY_SCHEMA = "qikvrt_requested_review_and_issue_lifecycle_policy_v1"
REF_RECONCILIATION_DELAYS_SECONDS = (0.25, 1.0, 2.0, 4.0, 8.0)
VALID_FILE_STATES = {
    "added",
    "changed",
    "copied",
    "modified",
    "removed",
    "renamed",
    "unchanged",
}

# These receipt fields are the complete, explicit projection of workflow/run
# progress.  Historical ledger admission removes only these known fields.  An
# unknown future field therefore remains part of the causal binding and fails
# closed until it is deliberately classified here.
REOBSERVATION_PROGRESS_FIELDS = frozenset({
    "state",
    "mesh_disposition",
    "first_blocker",
    "detail",
    # Trusted-main tip is observation progress, not immutable candidate identity.
    # Reobservation still must fail closed if the decision input moves, because
    # the current main head is a causal input to the review policy itself.
    "current_main_sha",
    "current_main_tree_sha",
    "evidence_fingerprint",
    "ledger_path",
    "ledger_diff_path",
    "diff_transport",
    "findings",
    "latest_workflows",
    "active_writers_observed",
    "derived_action",
    "receipt_payload_sha256",
})
REOBSERVATION_DECISION_INPUT_FIELDS = frozenset({
    "current_main_sha",
    "current_main_tree_sha",
})
REPOSITORY_FEEDBACK_PROGRESS_FIELDS = frozenset({
    "receipt_path",
    "diff_path",
    "diff_transport",
})


class ReviewSnapshotError(ValueError):
    """The trusted observation envelope is malformed."""


class ReviewObservationError(RuntimeError):
    """The repository could not be observed as one stable exact subject."""


def _sha(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or len(value) != 40:
        raise ReviewSnapshotError(f"{label} is not a Git SHA-1")
    if any(ch not in "0123456789abcdef" for ch in value):
        raise ReviewSnapshotError(f"{label} is not lowercase hexadecimal")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ReviewSnapshotError(f"{label} is not a SHA-256 digest")
    if any(ch not in "0123456789abcdef" for ch in value):
        raise ReviewSnapshotError(f"{label} is not lowercase hexadecimal")
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _historical_receipt_binding(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Return every causal field except the enumerated progress projection.

    This is intentionally subtraction-based.  Adding a new receipt field does
    not silently make it history-safe: it is bound automatically unless the
    field is explicitly classified as workflow progress above.
    """
    result: dict[str, Any] = {}
    for field, value in receipt.items():
        if field in REOBSERVATION_PROGRESS_FIELDS:
            continue
        if field == "repository_feedback" and isinstance(value, Mapping):
            result[field] = {
                key: nested
                for key, nested in value.items()
                if key not in REPOSITORY_FEEDBACK_PROGRESS_FIELDS
            }
        else:
            result[field] = value
    return result


def review_queue_intent(
    receipt: Mapping[str, Any],
    predecessor_fingerprint: str,
) -> tuple[str, dict[str, Any]]:
    """Create one immutable, content-addressed recursive review work unit."""
    predecessor = _sha256(predecessor_fingerprint, "predecessor fingerprint")
    repository = receipt.get("repository")
    pr_number = receipt.get("pr_number")
    head = _sha(receipt.get("head_sha"), "queue head_sha")
    tree = _sha(receipt.get("tree_sha"), "queue tree_sha")
    base = _sha(receipt.get("base_sha"), "queue base_sha")
    fingerprint = _sha256(
        receipt.get("evidence_fingerprint"),
        "queue successor fingerprint",
    )
    receipt_path = receipt.get("ledger_path")
    diff_path = receipt.get("ledger_diff_path")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise ReviewSnapshotError("queue repository is invalid")
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number < 1:
        raise ReviewSnapshotError("queue pull request number is invalid")
    if not isinstance(receipt_path, str) or not isinstance(diff_path, str):
        raise ReviewSnapshotError("queue evidence paths are invalid")
    path = f"{REVIEW_QUEUE_ROOT}/pr-{pr_number}/{head}/{fingerprint}.json"
    return path, {
        "schema": "qikvrt_mesh_review_queue_intent_v1",
        "work_unit_id": f"pr-{pr_number}/{head}/{fingerprint}",
        "repository": repository,
        "pr_number": pr_number,
        "head_sha": head,
        "tree_sha": tree,
        "base_sha": base,
        "predecessor_fingerprint": predecessor,
        "successor_fingerprint": fingerprint,
        "receipt_path": receipt_path,
        "diff_path": diff_path,
        "state": "QUEUED_RECURSIVE_REOBSERVATION",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }


def review_queue_ack(
    repository: str,
    pr_number: int,
    head_sha: str,
    predecessor_fingerprint: str,
    successor_fingerprint: str,
) -> tuple[str, dict[str, Any]]:
    """Bind completion of one work unit to the observed successor receipt."""
    head = _sha(head_sha, "queue acknowledgement head_sha")
    predecessor = _sha256(predecessor_fingerprint, "ack predecessor fingerprint")
    successor = _sha256(successor_fingerprint, "ack successor fingerprint")
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise ReviewSnapshotError("queue acknowledgement repository is invalid")
    if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number < 1:
        raise ReviewSnapshotError("queue acknowledgement PR number is invalid")
    path = f"{REVIEW_QUEUE_ACK_ROOT}/pr-{pr_number}/{head}/{predecessor}.json"
    return path, {
        "schema": "qikvrt_mesh_review_queue_ack_v1",
        "work_unit_id": f"pr-{pr_number}/{head}/{predecessor}",
        "repository": repository,
        "pr_number": pr_number,
        "head_sha": head,
        "predecessor_fingerprint": predecessor,
        "successor_fingerprint": successor,
        "state": "SUPERSEDED_BY_CAUSAL_REOBSERVATION",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }


def _pretty_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")


def build_diff_transport(diff: bytes, base_path: str) -> dict[str, Any]:
    """Describe an exact diff as ordered, content-addressed 1 MiB packets.

    The packets are a transport representation only: the receipt remains bound
    to the complete canonical diff digest and byte count.  A consumer must
    reject missing, reordered, altered, or surplus packets.
    """
    if not isinstance(diff, bytes) or not diff:
        raise ReviewSnapshotError("diff transport requires non-empty bytes")
    if not isinstance(base_path, str) or not base_path:
        raise ReviewSnapshotError("diff transport base path is missing")
    chunks = []
    for index, offset in enumerate(range(0, len(diff), REVIEW_DIFF_CHUNK_BYTES)):
        packet = diff[offset : offset + REVIEW_DIFF_CHUNK_BYTES]
        chunks.append({
            "index": index,
            "offset": offset,
            "bytes": len(packet),
            "sha256": hashlib.sha256(packet).hexdigest(),
            "path": f"{base_path}.chunks/{index:08d}.bin",
        })
    transport: dict[str, Any] = {
        "schema": REVIEW_DIFF_TRANSPORT_SCHEMA,
        "packet_bytes": REVIEW_DIFF_CHUNK_BYTES,
        "packet_count": len(chunks),
        "total_bytes": len(diff),
        "sha256": hashlib.sha256(diff).hexdigest(),
        "manifest_path": f"{base_path}.chunks.json",
        "packets": chunks,
        "delivery": REVIEW_DIFF_TRANSPORT_DELIVERY,
    }
    # The manifest digest is deliberately computed over the canonical manifest
    # projection without this self-referential field.  The receipt seals the
    # resulting transport object; the ledger stores the exact pretty-JSON
    # manifest bytes and reconstructs every packet before accepting it.
    transport["manifest_sha256"] = _canonical_sha256(transport)
    return transport


def reassemble_diff_transport(transport: Mapping[str, Any], packets: Sequence[bytes]) -> bytes:
    """Fail closed unless packets reproduce the complete declared diff."""
    if not isinstance(transport, Mapping) or transport.get("schema") != REVIEW_DIFF_TRANSPORT_SCHEMA:
        raise ReviewSnapshotError("diff transport schema is invalid")
    required_fields = {
        "schema",
        "packet_bytes",
        "packet_count",
        "total_bytes",
        "sha256",
        "manifest_path",
        "packets",
        "delivery",
        "manifest_sha256",
    }
    if set(transport) != required_fields:
        raise ReviewSnapshotError("diff transport manifest fields are invalid")
    if transport.get("packet_bytes") != REVIEW_DIFF_CHUNK_BYTES:
        raise ReviewSnapshotError("diff transport packet bound is invalid")
    if transport.get("delivery") != REVIEW_DIFF_TRANSPORT_DELIVERY:
        raise ReviewSnapshotError("diff transport delivery contract is invalid")
    total_bytes = transport.get("total_bytes")
    packet_count = transport.get("packet_count")
    if (
        isinstance(total_bytes, bool)
        or not isinstance(total_bytes, int)
        or total_bytes < 1
        or isinstance(packet_count, bool)
        or not isinstance(packet_count, int)
        or packet_count < 1
    ):
        raise ReviewSnapshotError("diff transport size declaration is invalid")
    _sha256(transport.get("sha256"), "diff transport digest")
    manifest_path = transport.get("manifest_path")
    if not isinstance(manifest_path, str) or not manifest_path.endswith(".chunks.json"):
        raise ReviewSnapshotError("diff transport manifest path is invalid")
    manifest_projection = dict(transport)
    manifest_sha256 = manifest_projection.pop("manifest_sha256")
    if (
        not isinstance(manifest_sha256, str)
        or manifest_sha256 != _canonical_sha256(manifest_projection)
    ):
        raise ReviewSnapshotError("diff transport manifest digest mismatch")
    declared = transport.get("packets")
    if (
        not isinstance(declared, list)
        or len(declared) != packet_count
        or len(declared) != len(packets)
        or not declared
    ):
        raise ReviewSnapshotError("diff transport packet count is invalid")
    base_path = manifest_path[: -len(".chunks.json")]
    materialized: list[bytes] = []
    for index, (item, packet) in enumerate(zip(declared, packets)):
        if (
            not isinstance(item, Mapping)
            or set(item) != {"index", "offset", "bytes", "sha256", "path"}
            or not isinstance(packet, bytes)
        ):
            raise ReviewSnapshotError("diff transport packet is invalid")
        offset = sum(len(value) for value in materialized)
        remaining = total_bytes - offset
        expected_size = min(REVIEW_DIFF_CHUNK_BYTES, remaining)
        if (
            item.get("index") != index
            or item.get("offset") != offset
            or item.get("path") != f"{base_path}.chunks/{index:08d}.bin"
            or item.get("bytes") != expected_size
        ):
            raise ReviewSnapshotError("diff transport packet order is invalid")
        if item.get("bytes") != len(packet) or item.get("sha256") != hashlib.sha256(packet).hexdigest():
            raise ReviewSnapshotError("diff transport packet digest mismatch")
        materialized.append(packet)
    complete = b"".join(materialized)
    if total_bytes != len(complete) or transport.get("sha256") != hashlib.sha256(complete).hexdigest():
        raise ReviewSnapshotError("diff transport completion digest mismatch")
    return complete


def prepare_diff_transport_ledger_entries(
    transport: Mapping[str, Any],
    diff: bytes,
    ledger_manifest_path: str,
) -> tuple[bytes, list[bytes]]:
    """Return only a ledger-bound, exactly reconstructible packet sequence.

    A receipt may name exactly one manifest path in the append-only ledger.  It
    is not sufficient for a different, valid-looking manifest to reconstruct
    the same bytes: that would leave receipt-to-ledger path identity
    unverified.  This helper is shared by the workflow writer and its tests so
    every write path validates the same envelope before creating blobs.
    """
    if not isinstance(diff, bytes) or not diff:
        raise ReviewSnapshotError("ledger diff bytes are unavailable")
    if not isinstance(ledger_manifest_path, str) or not ledger_manifest_path:
        raise ReviewSnapshotError("ledger manifest path is invalid")
    if not isinstance(transport, Mapping):
        raise ReviewSnapshotError("ledger diff transport is invalid")
    if transport.get("manifest_path") != ledger_manifest_path:
        raise ReviewSnapshotError("diff transport manifest path does not bind the ledger path")
    declared = transport.get("packets")
    if not isinstance(declared, list):
        raise ReviewSnapshotError("diff transport packets are unavailable")
    packets: list[bytes] = []
    for item in declared:
        if not isinstance(item, Mapping):
            raise ReviewSnapshotError("diff transport packet is invalid")
        offset = item.get("offset")
        size = item.get("bytes")
        if (
            isinstance(offset, bool)
            or not isinstance(offset, int)
            or offset < 0
            or isinstance(size, bool)
            or not isinstance(size, int)
            or size < 1
        ):
            raise ReviewSnapshotError("diff transport packet range is invalid")
        packets.append(diff[offset : offset + size])
    if reassemble_diff_transport(transport, packets) != diff:
        raise ReviewSnapshotError("diff transport reconstruction mismatch")
    return _pretty_json_bytes(dict(transport)), packets


def latest_status_matches_projection(
    statuses: Iterable[Mapping[str, Any]],
    context: str,
    state: str,
    evidence_fingerprint: str,
) -> bool:
    """Return true only when the latest status in a context is the projection."""
    if not isinstance(context, str) or not context:
        raise ReviewSnapshotError("status context is missing")
    if not isinstance(state, str) or not state:
        raise ReviewSnapshotError("status state is missing")
    _sha256(evidence_fingerprint, "status evidence fingerprint")
    matching: list[Mapping[str, Any]] = []
    for status in statuses:
        if not isinstance(status, Mapping):
            raise ReviewSnapshotError("commit status must be an object")
        if status.get("context") == context:
            matching.append(status)
    if not matching:
        return False

    def key(status: Mapping[str, Any]) -> tuple[str, int]:
        identifier = status.get("id")
        timestamp = status.get("updated_at") or status.get("created_at")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier < 1:
            raise ReviewSnapshotError("commit status id is invalid")
        if not isinstance(timestamp, str) or not timestamp:
            raise ReviewSnapshotError("commit status timestamp is missing")
        return timestamp, identifier

    latest = max(matching, key=key)
    match = re.search(r"\bfp=([0-9a-f]{64})\b", latest.get("description") or "")
    return (
        latest.get("state") == state
        and match is not None
        and match.group(1) == evidence_fingerprint
    )


def plan_ledger_update(
    receipt_bytes: bytes,
    diff_bytes: bytes,
    ledger_head: str | None,
    existing_receipt: bytes | None,
    existing_diff: bytes | None,
) -> dict[str, Any]:
    """Plan one append-only ledger transition without performing an effect."""
    if not isinstance(receipt_bytes, bytes) or not receipt_bytes:
        raise ReviewSnapshotError("ledger receipt bytes are unavailable")
    if not isinstance(diff_bytes, bytes) or not diff_bytes:
        raise ReviewSnapshotError("ledger diff bytes are unavailable")
    if ledger_head is None:
        if existing_receipt is not None or existing_diff is not None:
            raise ReviewSnapshotError("root ledger plan has unexpected existing bytes")
        action = "INITIALIZE_ORPHAN_ROOT"
        blocker = None
    else:
        _sha(ledger_head, "ledger_head")
        if existing_receipt is None and existing_diff is None:
            action = "APPEND_FAST_FORWARD"
            blocker = None
        elif existing_receipt == receipt_bytes and existing_diff == diff_bytes:
            action = "NOOP_IDENTICAL_RECEIPT"
            blocker = None
        else:
            action = "HOLD"
            blocker = "APPEND_ONLY_LEDGER_PATH_COLLISION"
    return {
        "schema": "qikvrt_mesh_review_ledger_plan_v1",
        "state": "HOLD_UNVERIFIED",
        "action": action,
        "parent": ledger_head,
        "force": False,
        "first_blocker": blocker,
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }


def exact_ref_sha(value: Mapping[str, Any] | None, expected_ref: str) -> str | None:
    """Return one exact Git commit ref target, preserving 404 as ``None``."""
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise ReviewSnapshotError("Git ref readback is not an object")
    if value.get("ref") != expected_ref:
        raise ReviewSnapshotError("Git ref readback identity differs")
    target = value.get("object")
    if not isinstance(target, Mapping) or target.get("type") != "commit":
        raise ReviewSnapshotError("Git ref readback target is not a commit")
    return _sha(target.get("sha"), "Git ref readback target")


def reconcile_ref_readback(
    fetch_ref: Callable[[], Mapping[str, Any] | None],
    expected_ref: str,
    expected_old_sha: str | None,
    attempted_commit: str,
    *,
    delays: Sequence[float] = REF_RECONCILIATION_DELAYS_SECONDS,
    sleeper: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Reobserve one mutation by GET only, retrying only its known-old state.

    The caller performs at most one POST/PATCH.  An exact target is accepted;
    404 during create or the exact expected-old SHA during fast-forward may be
    transient and is reobserved within the fixed bound.  Any other visible
    target or malformed response fails closed immediately.
    """
    if not isinstance(expected_ref, str) or not expected_ref.startswith("refs/"):
        raise ReviewSnapshotError("expected Git ref identity is invalid")
    old_sha = _sha(expected_old_sha, "expected_old_sha", nullable=True)
    commit_sha = _sha(attempted_commit, "attempted_commit")
    if not isinstance(delays, Sequence) or isinstance(delays, (str, bytes)):
        raise ReviewSnapshotError("ref reconciliation delays are invalid")
    normalized_delays: list[float] = []
    for delay in delays:
        if isinstance(delay, bool) or not isinstance(delay, (int, float)) or delay < 0:
            raise ReviewSnapshotError("ref reconciliation delay is invalid")
        normalized_delays.append(float(delay))

    result = {
        "schema": "qikvrt_git_ref_reconciliation_v1",
        "state": "HOLD_UNVERIFIED",
        "exact": False,
        "expected_ref": expected_ref,
        "expected_old_sha": old_sha,
        "attempted_commit": commit_sha,
        "observed_shas": [],
        "first_blocker": None,
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }
    for attempt in range(len(normalized_delays) + 1):
        try:
            observed = exact_ref_sha(fetch_ref(), expected_ref)
        except ReviewSnapshotError as exc:
            result.update(
                state="HOLD_MALFORMED_READBACK",
                first_blocker=f"GIT_REF_READBACK_MALFORMED: {exc}",
            )
            return result
        result["observed_shas"].append(observed)
        if observed == commit_sha:
            result.update(state="EXACT", exact=True)
            return result
        if observed != old_sha:
            result.update(
                state="HOLD_DIVERGED_READBACK",
                first_blocker="GIT_REF_READBACK_DIVERGED",
            )
            return result
        if attempt < len(normalized_delays):
            sleeper(normalized_delays[attempt])
    result.update(
        state="HOLD_STALE_READBACK",
        first_blocker="GIT_REF_READBACK_STALE",
    )
    return result


def _run_key(run: Mapping[str, Any]) -> tuple[int, int, int]:
    values: list[int] = []
    for field, default in (("run_number", -1), ("run_attempt", 1), ("id", -1)):
        value = run.get(field, default)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ReviewSnapshotError(f"workflow {field} must be an integer")
        values.append(value)
    return values[0], values[1], values[2]


def _workflow_identity(run: Mapping[str, Any]) -> tuple[int, str, str, str]:
    """Return the stable repository identity of one workflow run."""
    workflow_id = run.get("workflow_id")
    path = run.get("path")
    event = run.get("event")
    name = run.get("name")
    if (
        isinstance(workflow_id, bool)
        or not isinstance(workflow_id, int)
        or workflow_id < 1
    ):
        raise ReviewSnapshotError("workflow workflow_id must be positive")
    if not isinstance(path, str) or not path:
        raise ReviewSnapshotError("workflow path is missing")
    if not isinstance(event, str) or not event:
        raise ReviewSnapshotError("workflow event is missing")
    if not isinstance(name, str) or not name:
        raise ReviewSnapshotError("workflow run name is missing")
    return workflow_id, path, event, name


def collapse_latest(
    runs: Sequence[Mapping[str, Any]],
) -> dict[tuple[int, str, str, str], Mapping[str, Any]]:
    """Collapse retries by stable workflow identity, never by display name."""
    by_identity: dict[tuple[int, str, str, str], Mapping[str, Any]] = {}
    for run in runs:
        if not isinstance(run, Mapping):
            raise ReviewSnapshotError("workflow run must be an object")
        identity = _workflow_identity(run)
        current = by_identity.get(identity)
        if current is None or _run_key(run) > _run_key(current):
            by_identity[identity] = run
        elif _run_key(run) == _run_key(current) and dict(run) != dict(current):
            raise ReviewSnapshotError(
                f"ambiguous duplicate workflow run: {identity[3]}"
            )

    return dict(sorted(by_identity.items()))


def _canonical_jobs(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Validate and deterministically project every job in one workflow run."""
    raw = run.get("jobs")
    if not isinstance(raw, list):
        raise ReviewSnapshotError("workflow jobs must be a list")
    jobs: list[dict[str, Any]] = []
    seen: set[int] = set()
    for index, job in enumerate(raw):
        if not isinstance(job, Mapping):
            raise ReviewSnapshotError(f"workflow jobs[{index}] must be an object")
        identifier = job.get("id")
        status = job.get("status")
        conclusion = job.get("conclusion")
        if isinstance(identifier, bool) or not isinstance(identifier, int) or identifier < 1:
            raise ReviewSnapshotError(f"workflow jobs[{index}].id must be positive")
        if identifier in seen:
            raise ReviewSnapshotError(f"duplicate workflow job id: {identifier}")
        if not isinstance(status, str) or not status:
            raise ReviewSnapshotError(f"workflow jobs[{index}].status is missing")
        if conclusion is not None and (
            not isinstance(conclusion, str) or not conclusion
        ):
            raise ReviewSnapshotError(
                f"workflow jobs[{index}].conclusion is invalid"
            )
        seen.add(identifier)
        jobs.append(
            {
                "id": identifier,
                "status": status,
                "conclusion": conclusion,
            }
        )
    jobs.sort(key=lambda item: item["id"])
    declared_total = run.get("jobs_total")
    if (
        isinstance(declared_total, bool)
        or not isinstance(declared_total, int)
        or declared_total < 0
    ):
        raise ReviewSnapshotError("workflow jobs_total must be non-negative")
    if declared_total != len(jobs):
        raise ReviewSnapshotError(
            f"workflow jobs_total {declared_total} != projected jobs {len(jobs)}"
        )
    return jobs


def canonical_scope(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = snapshot.get("changed_files")
    if not isinstance(raw, list):
        raise ReviewSnapshotError("changed_files must be a list")
    scope: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ReviewSnapshotError(f"changed_files[{index}] must be an object")
        path = item.get("path")
        if (
            not isinstance(path, str)
            or not path
            or "\x00" in path
            or "\n" in path
            or "\r" in path
        ):
            raise ReviewSnapshotError(f"changed_files[{index}].path is invalid")
        if path in seen:
            raise ReviewSnapshotError(f"duplicate changed path: {path}")
        seen.add(path)
        status = item.get("status")
        if status not in VALID_FILE_STATES:
            raise ReviewSnapshotError(f"unsupported file status for {path}: {status!r}")
        previous_path = item.get("previous_path")
        if previous_path is not None and (
            not isinstance(previous_path, str)
            or not previous_path
            or "\x00" in previous_path
            or "\n" in previous_path
            or "\r" in previous_path
        ):
            raise ReviewSnapshotError(f"previous path is invalid for {path}")
        scope.append(
            {
                "path": path,
                "previous_path": previous_path,
                "status": status,
                "base_blob_sha": _sha(
                    item.get("base_blob_sha"),
                    f"base blob for {path}",
                    nullable=True,
                ),
                "head_blob_sha": _sha(
                    item.get("head_blob_sha"),
                    f"head blob for {path}",
                    nullable=True,
                ),
            }
        )
    scope.sort(key=lambda item: (item["path"], item.get("previous_path") or ""))
    paths = snapshot.get("changed_paths")
    if paths is not None:
        if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
            raise ReviewSnapshotError("changed_paths must be a string list")
        if sorted(paths) != [item["path"] for item in scope]:
            raise ReviewSnapshotError("changed_paths and changed_files scope disagree")
    return scope


def canonical_scope_digest(scope: Sequence[Mapping[str, Any]]) -> str:
    return _canonical_sha256(list(scope))


def _threads(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = snapshot.get("review_threads", [])
    if not isinstance(raw, list):
        raise ReviewSnapshotError("review_threads must be a list")
    result: list[dict[str, Any]] = []
    for index, thread in enumerate(raw):
        if not isinstance(thread, Mapping):
            raise ReviewSnapshotError(f"review_threads[{index}] must be an object")
        identifier = thread.get("id")
        resolved = thread.get("is_resolved")
        body_sha256 = thread.get("body_sha256")
        if not isinstance(identifier, str) or not identifier:
            raise ReviewSnapshotError("review thread id is missing")
        if not isinstance(resolved, bool):
            raise ReviewSnapshotError("review thread resolution must be boolean")
        if body_sha256 is not None:
            _sha256(body_sha256, "review thread body_sha256")
        result.append(
            {
                "id": identifier,
                "is_resolved": resolved,
                "body_sha256": body_sha256,
            }
        )
    result.sort(key=lambda item: item["id"])
    declared = snapshot.get("unresolved_review_threads")
    unresolved = sum(1 for item in result if not item["is_resolved"])
    if declared is not None:
        if isinstance(declared, bool) or not isinstance(declared, int) or declared < 0:
            raise ReviewSnapshotError("unresolved_review_threads must be non-negative")
        if declared != unresolved:
            raise ReviewSnapshotError("review thread count disagrees with review_threads")
    return result


def _active_writers(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = snapshot.get("active_writers", [])
    if not isinstance(raw, list):
        raise ReviewSnapshotError("active_writers must be a list")
    result: list[dict[str, Any]] = []
    for writer in raw:
        if not isinstance(writer, Mapping):
            raise ReviewSnapshotError("active writer must be an object")
        run_id = writer.get("id")
        name = writer.get("name")
        status = writer.get("status")
        if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id < 1:
            raise ReviewSnapshotError("active writer id must be a positive integer")
        if not isinstance(name, str) or not name:
            raise ReviewSnapshotError("active writer name is missing")
        if status not in ACTIVE_WRITER_STATES:
            raise ReviewSnapshotError("active writer status is not active")
        result.append(
            {
                "id": run_id,
                "name": name,
                "status": status,
                "head_sha": writer.get("head_sha"),
                "workflow_id": writer.get("workflow_id"),
                "path": writer.get("path"),
                "event": writer.get("event"),
                "run_number": writer.get("run_number"),
                "run_attempt": writer.get("run_attempt"),
            }
        )
    result.sort(key=lambda item: (item["name"], item["id"]))
    return result


def _string_list(snapshot: Mapping[str, Any], field: str) -> list[str]:
    raw = snapshot.get(field, [])
    if not isinstance(raw, list) or not all(isinstance(value, str) and value for value in raw):
        raise ReviewSnapshotError(f"{field} must be a string list")
    if len(set(raw)) != len(raw):
        raise ReviewSnapshotError(f"{field} must not contain duplicates")
    return sorted(raw)


def _optional_text(value: Any, label: str) -> str | None:
    """Normalize one optional, non-control-character text value."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ReviewSnapshotError(f"{label} must be a string or null")
    normalized = value.strip()
    if not normalized or any(ord(character) < 32 for character in normalized):
        raise ReviewSnapshotError(f"{label} is invalid")
    return normalized


def _optional_sha256(value: Any, label: str) -> str | None:
    """Normalize one optional SHA-256 binding."""
    if value is None or value == "":
        return None
    return _sha256(value, label)


def _review_priority_policy() -> tuple[dict[str, Any], str]:
    """Load the versioned, trusted-main review-intake classification policy."""
    path = pathlib.Path(__file__).resolve().parents[1] / REVIEW_PRIORITY_POLICY_PATH
    try:
        raw = path.read_bytes()
        policy = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewSnapshotError(f"review priority policy is unavailable: {exc}") from exc
    if not isinstance(policy, dict):
        raise ReviewSnapshotError("review priority policy must be an object")
    if policy.get("schema") != REVIEW_PRIORITY_POLICY_SCHEMA:
        raise ReviewSnapshotError("review priority policy schema is invalid")
    if policy.get("policy_id") != "QIKVRT-REQUESTED-REVIEW-AND-ISSUE-LIFECYCLE-V1":
        raise ReviewSnapshotError("review priority policy id is invalid")
    intake_policy = policy.get("review_intake_priority")
    if not isinstance(intake_policy, Mapping):
        raise ReviewSnapshotError("review intake priority policy is missing")
    roles = intake_policy.get("principal_roles")
    labels = intake_policy.get("reason_labels")
    classes = intake_policy.get("priority_classes")
    if not isinstance(roles, Mapping) or not isinstance(labels, Mapping) or not isinstance(classes, list):
        raise ReviewSnapshotError("review priority policy shape is invalid")
    expected_classes = {
        "P0_SECURITY_OR_INTEGRITY": 0,
        "P1_PRODUCT_OWNER_TO_REQUIRED_CODE_OWNER": 1,
        "P2_REQUIRED_CODE_OWNER_REQUEST": 2,
        "P3_EXPLICIT_REVIEW_REQUEST": 3,
        "P4_AUTOMATIC_ELIGIBLE_EVENT": 4,
    }
    observed_classes: dict[str, int] = {}
    for item in classes:
        if not isinstance(item, Mapping):
            raise ReviewSnapshotError("review priority class must be an object")
        name = item.get("class")
        rank = item.get("rank")
        if (
            not isinstance(name, str)
            or isinstance(rank, bool)
            or not isinstance(rank, int)
        ):
            raise ReviewSnapshotError("review priority class is invalid")
        if name in observed_classes:
            raise ReviewSnapshotError("review priority class is duplicated")
        observed_classes[name] = rank
    if observed_classes != expected_classes:
        raise ReviewSnapshotError("review priority policy class mapping is invalid")
    for role in ("PRODUCT_OWNER", "REQUIRED_CODE_OWNER"):
        values = roles.get(role)
        if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
            raise ReviewSnapshotError(f"review priority role {role} is invalid")
    if not all(isinstance(label, str) and isinstance(reason, str) for label, reason in labels.items()):
        raise ReviewSnapshotError("review priority reason labels are invalid")
    return dict(intake_policy), hashlib.sha256(raw).hexdigest()


def _principal_role(login: str | None, policy: Mapping[str, Any]) -> str:
    if login is None:
        return "NONE"
    roles = policy["principal_roles"]
    normalized = login.casefold()
    for role in ("PRODUCT_OWNER", "REQUIRED_CODE_OWNER"):
        if any(
            isinstance(candidate, str) and candidate.casefold() == normalized
            for candidate in roles[role]
        ):
            return role
    return "OTHER"


def _review_intake(
    event_context: Mapping[str, Any] | None,
    observed_labels: Sequence[str],
    observed_reviewers: Sequence[str] = (),
    observed_teams: Sequence[str] = (),
) -> dict[str, Any]:
    """Derive the sole canonical priority classification for one exact event.

    GitHub Actions does not expose a native delivery id or a priority queue.  It
    can bind the event fields and classify them, but it must not claim that it
    ordered multiple independent deliveries.  A provisioned GitHub App broker
    is the only permitted owner of that cross-event ordering.
    """
    if event_context is None:
        event_context = {}
    if not isinstance(event_context, Mapping):
        raise ReviewSnapshotError("review event context must be an object")
    policy, policy_sha256 = _review_priority_policy()
    event_name = _optional_text(event_context.get("event_name"), "review event name") or "UNKNOWN"
    event_action = _optional_text(event_context.get("event_action"), "review event action") or ""
    event_payload_sha256 = _optional_sha256(
        event_context.get("event_payload_sha256"),
        "review event payload sha256",
    )
    event_actor = _optional_text(event_context.get("event_actor"), "review event actor")
    requested_reviewer = _optional_text(
        event_context.get("requested_reviewer"),
        "requested reviewer",
    )
    requested_team = _optional_text(
        event_context.get("requested_team"),
        "requested reviewer team",
    )
    predecessor_successor_fingerprint = _optional_sha256(
        event_context.get("predecessor_successor_fingerprint"),
        "predecessor successor fingerprint",
    )
    source = _optional_text(event_context.get("source"), "review event source") or "UNSPECIFIED"
    native_delivery_identity = (
        _optional_text(event_context.get("native_delivery_identity"), "native delivery identity")
        or "UNAVAILABLE_TO_GITHUB_ACTIONS"
    )
    if requested_reviewer is not None and requested_team is not None:
        raise ReviewSnapshotError("review event cannot name both a user and a team target")
    if event_action == "review_requested" and requested_reviewer is None and requested_team is None:
        raise ReviewSnapshotError("review_requested event lacks a reviewer or team target")

    normalized_labels: list[str] = []
    for label in observed_labels:
        normalized_label = _optional_text(label, "pull request label")
        if normalized_label is None:
            raise ReviewSnapshotError("pull request labels contain an empty value")
        normalized_labels.append(normalized_label)
    labels = sorted(set(normalized_labels))
    reason_mapping = policy["reason_labels"]
    matched_labels = [label for label in labels if label in reason_mapping]
    if len(matched_labels) > 1:
        reason = "AMBIGUOUS"
        reason_label = None
        reason_state = "AMBIGUOUS_FAIL_CLOSED"
    elif matched_labels:
        reason_label = matched_labels[0]
        reason = reason_mapping[reason_label]
        reason_state = "DECLARED_LABEL"
    else:
        reason = "UNSPECIFIED"
        reason_label = None
        reason_state = "UNSPECIFIED"

    requester_role = _principal_role(event_actor, policy)
    requested_reviewer_role = _principal_role(requested_reviewer, policy)
    requested_target_observed: bool | None = None
    if event_action == "review_requested":
        requested_target_observed = (
            any(
                candidate.casefold() == requested_reviewer.casefold()
                for candidate in observed_reviewers
            )
            if requested_reviewer is not None
            else requested_team in observed_teams
        )
        if (
            reason == "SECURITY_OR_INTEGRITY"
            and requester_role in {"PRODUCT_OWNER", "REQUIRED_CODE_OWNER"}
        ):
            priority_class = "P0_SECURITY_OR_INTEGRITY"
        elif (
            requester_role == "PRODUCT_OWNER"
            and requested_reviewer_role == "REQUIRED_CODE_OWNER"
        ):
            priority_class = "P1_PRODUCT_OWNER_TO_REQUIRED_CODE_OWNER"
        elif requested_reviewer_role == "REQUIRED_CODE_OWNER":
            priority_class = "P2_REQUIRED_CODE_OWNER_REQUEST"
        else:
            priority_class = "P3_EXPLICIT_REVIEW_REQUEST"
        request_state = (
            "ACTIVE_EXPLICIT_REQUEST"
            if requested_target_observed
            else "STALE_EXPLICIT_REQUEST"
        )
    else:
        priority_class = "P4_AUTOMATIC_ELIGIBLE_EVENT"
        request_state = (
            "REMOVED_REQUEST_REOBSERVATION_ONLY"
            if event_action == "review_request_removed"
            else "AUTOMATIC_ELIGIBLE_REOBSERVATION"
        )
    ranks = {item["class"]: item["rank"] for item in policy["priority_classes"]}
    return {
        "schema": REVIEW_INTAKE_SCHEMA,
        "policy_id": "QIKVRT-REQUESTED-REVIEW-AND-ISSUE-LIFECYCLE-V1",
        "policy_sha256": policy_sha256,
        "source": source,
        "event_name": event_name,
        "event_action": event_action,
        "event_payload_sha256": event_payload_sha256,
        "event_actor": event_actor,
        "requested_reviewer": requested_reviewer,
        "requested_team": requested_team,
        "predecessor_successor_fingerprint": predecessor_successor_fingerprint,
        "requester_role": requester_role,
        "requested_reviewer_role": requested_reviewer_role,
        "requested_target_observed": requested_target_observed,
        "request_state": request_state,
        "reason": reason,
        "reason_label": reason_label,
        "reason_labels": matched_labels,
        "reason_state": reason_state,
        "priority_class": priority_class,
        "priority_rank": ranks[priority_class],
        "cross_event_ordering": "GITHUB_ACTIONS_NO_CROSS_EVENT_PRIORITY_GUARANTEE",
        "native_delivery_identity": native_delivery_identity,
    }


def _canonical_review_intake(value: Any) -> dict[str, Any]:
    """Validate a receipt-bound review intake against current trusted policy."""
    if value is None:
        return _review_intake({}, [])
    if not isinstance(value, Mapping):
        raise ReviewSnapshotError("review_intake must be an object")
    required = {
        "schema",
        "policy_id",
        "policy_sha256",
        "source",
        "event_name",
        "event_action",
        "event_payload_sha256",
        "event_actor",
        "requested_reviewer",
        "requested_team",
        "predecessor_successor_fingerprint",
        "requester_role",
        "requested_reviewer_role",
        "requested_target_observed",
        "request_state",
        "reason",
        "reason_label",
        "reason_labels",
        "reason_state",
        "priority_class",
        "priority_rank",
        "cross_event_ordering",
        "native_delivery_identity",
    }
    if set(value) != required:
        raise ReviewSnapshotError("review_intake fields are invalid")
    policy, policy_sha256 = _review_priority_policy()
    if (
        value.get("schema") != REVIEW_INTAKE_SCHEMA
        or value.get("policy_id") != "QIKVRT-REQUESTED-REVIEW-AND-ISSUE-LIFECYCLE-V1"
        or value.get("policy_sha256") != policy_sha256
    ):
        raise ReviewSnapshotError("review_intake policy binding drifted")
    normalized: dict[str, Any] = {}
    for field in (
        "source",
        "event_name",
        "event_action",
        "event_actor",
        "requested_reviewer",
        "requested_team",
        "reason_label",
        "native_delivery_identity",
    ):
        normalized[field] = _optional_text(value.get(field), f"review_intake {field}")
    normalized["event_payload_sha256"] = _optional_sha256(
        value.get("event_payload_sha256"),
        "review_intake event_payload_sha256",
    )
    normalized["predecessor_successor_fingerprint"] = _optional_sha256(
        value.get("predecessor_successor_fingerprint"),
        "review_intake predecessor_successor_fingerprint",
    )
    raw_reason_labels = value.get("reason_labels")
    if (
        not isinstance(raw_reason_labels, list)
        or not all(isinstance(label, str) and label for label in raw_reason_labels)
        or raw_reason_labels != sorted(set(raw_reason_labels))
    ):
        raise ReviewSnapshotError("review_intake reason_labels are invalid")
    for field in (
        "requester_role",
        "requested_reviewer_role",
        "request_state",
        "reason",
        "reason_state",
        "priority_class",
        "cross_event_ordering",
    ):
        text = _optional_text(value.get(field), f"review_intake {field}")
        if text is None:
            raise ReviewSnapshotError(f"review_intake {field} is missing")
        normalized[field] = text
    rank = value.get("priority_rank")
    if isinstance(rank, bool) or not isinstance(rank, int):
        raise ReviewSnapshotError("review_intake priority_rank is invalid")
    ranks = {item["class"]: item["rank"] for item in policy["priority_classes"]}
    if ranks.get(normalized["priority_class"]) != rank:
        raise ReviewSnapshotError("review_intake priority class and rank disagree")
    if normalized["cross_event_ordering"] != "GITHUB_ACTIONS_NO_CROSS_EVENT_PRIORITY_GUARANTEE":
        raise ReviewSnapshotError("review_intake cross-event ordering claim is invalid")
    if normalized["event_action"] == "review_requested" and (
        normalized["requested_reviewer"] is None and normalized["requested_team"] is None
    ):
        raise ReviewSnapshotError("review_intake requested review lacks target")
    target_observed = value.get("requested_target_observed")
    if target_observed is not None and not isinstance(target_observed, bool):
        raise ReviewSnapshotError("review_intake requested_target_observed is invalid")
    if normalized["event_action"] == "review_requested" and not isinstance(target_observed, bool):
        raise ReviewSnapshotError("review_intake requested review target observation is missing")
    if normalized["event_action"] != "review_requested" and target_observed is not None:
        raise ReviewSnapshotError("review_intake non-request event target observation is invalid")
    expected = _review_intake(
        {
            field: normalized[field]
            for field in (
                "source",
                "event_name",
                "event_action",
                "event_payload_sha256",
                "event_actor",
                "requested_reviewer",
                "requested_team",
                "predecessor_successor_fingerprint",
                "native_delivery_identity",
            )
        },
        raw_reason_labels,
        [normalized["requested_reviewer"]] if target_observed and normalized["requested_reviewer"] else [],
        [normalized["requested_team"]] if target_observed and normalized["requested_team"] else [],
    )
    if dict(value) != expected:
        raise ReviewSnapshotError("review_intake does not match deterministic priority policy")
    return expected


def _event_context_from_review_intake(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Reuse a sealed receipt's raw event fields for exact reobservation."""
    value = receipt.get("review_intake")
    if not isinstance(value, Mapping):
        return {}
    return {
        field: value.get(field)
        for field in (
            "source",
            "event_name",
            "event_action",
            "event_payload_sha256",
            "event_actor",
            "requested_reviewer",
            "requested_team",
            "predecessor_successor_fingerprint",
            "native_delivery_identity",
        )
    }


def _discussion_items(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = snapshot.get("discussion_items", [])
    if not isinstance(raw, list):
        raise ReviewSnapshotError("discussion_items must be a list")
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            raise ReviewSnapshotError("discussion item must be an object")
        kind = item.get("kind")
        identifier = item.get("id")
        updated_at = item.get("updated_at")
        if not isinstance(kind, str) or not kind:
            raise ReviewSnapshotError("discussion item kind is missing")
        if not isinstance(identifier, str) or not identifier:
            raise ReviewSnapshotError("discussion item id is missing")
        if not isinstance(updated_at, str) or not updated_at:
            raise ReviewSnapshotError("discussion item updated_at is missing")
        body_sha256 = _sha256(item.get("body_sha256"), "discussion body_sha256")
        key = (kind, identifier)
        if key in seen:
            raise ReviewSnapshotError(f"duplicate discussion item: {kind}/{identifier}")
        seen.add(key)
        result.append(
            {
                "kind": kind,
                "id": identifier,
                "author": item.get("author"),
                "author_association": item.get("author_association"),
                "state": item.get("state"),
                "commit_id": item.get("commit_id"),
                "updated_at": updated_at,
                "body_sha256": body_sha256,
            }
        )
    result.sort(key=lambda item: (item["kind"], item["id"]))
    return result


def _gate_projection(
    latest: Mapping[tuple[int, str, str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for identity, run in sorted(latest.items(), key=lambda item: item[0]):
        workflow_id, path, event, name = identity
        projected.append({
            "id": run.get("id"),
            "name": name,
            "workflow_id": run.get("workflow_id"),
            "path": run.get("path"),
            "event": run.get("event"),
            "jobs_total": run.get("jobs_total"),
            "jobs": _canonical_jobs(run),
            "run_number": _run_key(run)[0],
            "run_attempt": _run_key(run)[1],
            "head_sha": run.get("head_sha"),
            "status": run.get("status"),
            "conclusion": run.get("conclusion"),
        })
    return projected


def _required_gate_binding(
    snapshot: Mapping[str, Any],
) -> tuple[list[str], dict[str, str], dict[str, int], dict[str, str]]:
    required = snapshot.get("required_gates")
    if not isinstance(required, list) or not required or not all(
        isinstance(name, str) and name for name in required
    ):
        raise ReviewSnapshotError("required_gates must be a non-empty string list")
    if len(set(required)) != len(required):
        raise ReviewSnapshotError("required_gates must not contain duplicates")
    raw_paths = snapshot.get("required_gate_paths")
    if not isinstance(raw_paths, Mapping) or set(raw_paths) != set(required):
        raise ReviewSnapshotError("required_gate_paths must bind every required gate exactly once")
    raw_ids = snapshot.get("required_gate_workflow_ids")
    raw_events = snapshot.get("required_gate_events")
    if not isinstance(raw_ids, Mapping) or set(raw_ids) != set(required):
        raise ReviewSnapshotError("required_gate_workflow_ids must bind every required gate")
    if not isinstance(raw_events, Mapping) or set(raw_events) != set(required):
        raise ReviewSnapshotError("required_gate_events must bind every required gate")
    paths: dict[str, str] = {}
    workflow_ids: dict[str, int] = {}
    events: dict[str, str] = {}
    for name in required:
        path = raw_paths.get(name)
        if (
            not isinstance(path, str)
            or not path.startswith(".github/workflows/")
            or path.endswith("/")
            or "\x00" in path
            or "\n" in path
            or "\r" in path
            or "/../" in f"/{path}/"
        ):
            raise ReviewSnapshotError(f"required workflow path is invalid: {name}")
        paths[name] = path
        workflow_id = raw_ids.get(name)
        event = raw_events.get(name)
        if isinstance(workflow_id, bool) or not isinstance(workflow_id, int) or workflow_id < 1:
            raise ReviewSnapshotError(f"required workflow id is invalid: {name}")
        if event != "pull_request":
            raise ReviewSnapshotError(f"required workflow event is invalid: {name}")
        workflow_ids[name] = workflow_id
        events[name] = event
    return list(required), paths, workflow_ids, events


def _evidence_fingerprint(
    snapshot: Mapping[str, Any],
    scope: Sequence[Mapping[str, Any]],
    scope_sha256: str,
    observed_diff_sha256: str,
    diff_bytes: int,
    threads: Sequence[Mapping[str, Any]],
    latest: Mapping[str, Mapping[str, Any]],
    writers: Sequence[Mapping[str, Any]],
    required_gate_paths: Mapping[str, str],
) -> str:
    payload = {
        "fingerprint_schema": "qikvrt_mesh_review_evidence_fingerprint_v4",
        "trusted_evaluator_blob_sha": snapshot.get("trusted_evaluator_blob_sha"),
        "trusted_workflow_blob_sha": snapshot.get("trusted_workflow_blob_sha"),
        "repository": snapshot.get("repository"),
        "repository_role": snapshot.get("repository_role"),
        "pr_number": snapshot.get("pr_number"),
        "pr_state": snapshot.get("pr_state"),
        "pr_title_sha256": snapshot.get("pr_title_sha256"),
        "pr_body_sha256": snapshot.get("pr_body_sha256"),
        "head_repository": snapshot.get("head_repository"),
        "base_ref": snapshot.get("base_ref", "main"),
        "draft": snapshot.get("draft"),
        "current_main_sha": snapshot.get("current_main_sha"),
        "current_main_tree_sha": snapshot.get("current_main_tree_sha"),
        "base_sha": snapshot.get("base_sha"),
        "base_tree_sha": snapshot.get("base_tree_sha"),
        "head_sha": snapshot.get("head_sha"),
        "observed_head_sha": snapshot.get("observed_head_sha"),
        "tree_sha": snapshot.get("tree_sha"),
        "observed_tree_sha": snapshot.get("observed_tree_sha"),
        "scope": list(scope),
        "scope_sha256": scope_sha256,
        "declared_scope_sha256": snapshot.get("scope_sha256"),
        "diff_sha256": observed_diff_sha256,
        "diff_bytes": diff_bytes,
        "declared_diff_sha256": snapshot.get("diff_sha256"),
        "declared_diff_bytes": snapshot.get("diff_bytes"),
        "diff_complete": snapshot.get("diff_complete"),
        "requested_reviewers": sorted(snapshot.get("requested_reviewers", [])),
        "requested_team_reviewers": sorted(snapshot.get("requested_team_reviewers", [])),
        "review_intake": snapshot.get("review_intake"),
        "discussion": list(threads),
        "discussion_items": snapshot.get("discussion_items", []),
        "required_gates": snapshot.get("required_gates"),
        "required_gate_paths": dict(sorted(required_gate_paths.items())),
        "required_gate_workflow_ids": snapshot.get("required_gate_workflow_ids"),
        "required_gate_events": snapshot.get("required_gate_events"),
        "latest_workflows": _gate_projection(latest),
        "active_writers": list(writers),
    }
    return _canonical_sha256(payload)


def _finding(
    finding_id: str,
    severity: str,
    detail: str,
    *,
    path: str | None = None,
    line: int | None = None,
    evidence_sha256: str | None = None,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "detail": detail,
        "path": path,
        "line": line,
        "evidence_sha256": evidence_sha256,
    }


def _scan_added_lines(diff_bytes: bytes) -> list[dict[str, Any]]:
    """Apply small, explicit invariant checks to exact added diff lines."""
    text = diff_bytes.decode("utf-8", errors="surrogateescape")
    findings: list[dict[str, Any]] = []
    current_path: str | None = None
    new_line: int | None = None
    hunk = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    write_permission = re.compile(
        r"^\s*(?:actions|checks|contents|deployments|id-token|issues|packages|pages|"
        r"pull-requests|security-events|statuses):\s*write\s*(?:#.*)?$"
    )
    completion_claim = re.compile(
        r"[\"']?(?:PASS|FINAL_PASS|EFFECT_ACK_DONE)[\"']?\s*[:=]\s*(?:true|True)\b"
    )
    stale_transfer = re.compile(
        r"(?:predecessor_evidence_transfer\s*[:=]\s*(?:true|True)|"
        r"no_predecessor_gate_inheritance\s*[:=]\s*(?:false|False))"
    )
    destructive_git = re.compile(
        r"\bgit\s+(?:push\b[^\n]*(?:--force(?:-with-lease)?|-f\b)|reset\s+--hard\b)"
    )

    for raw in text.splitlines():
        if raw.startswith("+++ b/"):
            current_path = raw[6:]
            continue
        match = hunk.match(raw)
        if match:
            new_line = int(match.group(1))
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            content = raw[1:]
            line = new_line
            digest = hashlib.sha256(content.encode("utf-8", errors="surrogateescape")).hexdigest()
            stripped = content.lstrip()
            if stripped == "<<<<<<<" or stripped.startswith("<<<<<<< ") or stripped == ">>>>>>>" or stripped.startswith(">>>>>>> "):
                findings.append(
                    _finding(
                        "MESH_DIFF_CONFLICT_MARKER",
                        "BLOCK",
                        "added line contains an unresolved merge-conflict marker",
                        path=current_path,
                        line=line,
                        evidence_sha256=digest,
                    )
                )
            if current_path and current_path.startswith(".github/workflows/") and write_permission.match(content):
                findings.append(
                    _finding(
                        "MESH_WORKFLOW_PERMISSION_WIDENING",
                        "AUTHORITY_REQUIRED",
                        "workflow diff adds a write permission and requires exact-scope authority review",
                        path=current_path,
                        line=line,
                        evidence_sha256=digest,
                    )
                )
            if completion_claim.search(content):
                findings.append(
                    _finding(
                        "MESH_COMPLETION_AUTHORITY_REQUIRED",
                        "AUTHORITY_REQUIRED",
                        "diff adds a positive completion claim that the Mesh review cannot authorize",
                        path=current_path,
                        line=line,
                        evidence_sha256=digest,
                    )
                )
            if stale_transfer.search(content):
                findings.append(
                    _finding(
                        "MESH_STALE_PREDECESSOR_EVIDENCE_TRANSFER",
                        "BLOCK",
                        "diff enables predecessor evidence transfer or disables non-inheritance",
                        path=current_path,
                        line=line,
                        evidence_sha256=digest,
                    )
                )
            if (
                current_path
                and current_path.startswith((".github/workflows/", "tools/", "scripts/"))
                and destructive_git.search(content)
            ):
                findings.append(
                    _finding(
                        "MESH_HISTORY_REWRITE_COMMAND",
                        "BLOCK",
                        "executable repository path adds a history-rewriting Git command",
                        path=current_path,
                        line=line,
                        evidence_sha256=digest,
                    )
                )
            if new_line is not None:
                new_line += 1
        elif raw.startswith("-") and not raw.startswith("---"):
            continue
        elif new_line is not None and not raw.startswith("\\"):
            new_line += 1
    return findings


def _derived_action(state: str, blocker: str | None) -> dict[str, Any]:
    if state == "APPROVE":
        return {
            "d0": 3,
            "state": "REQUEST_AUTHORITY",
            "next_action": "REQUEST_EXACT_HEAD_CODE_OWNER_REOBSERVATION",
            "productive_effect": False,
            "effect_ack": "HOLD_UNVERIFIED",
        }
    if blocker in {
        "BASE_DRIFT",
        "BASE_TREE_DRIFT",
        "HEAD_DRIFT",
        "TREE_DRIFT",
        "SCOPE_DIGEST_MISMATCH",
        "REQUIRED_GATE_MISSING",
        "UNTRUSTED_GATE_BINDING",
        "ZERO_JOB_GATE",
        "ZERO_EXECUTED_JOB_GATE",
        "REVIEW_BYTES_UNAVAILABLE",
        "REVIEW_REASON_AMBIGUOUS",
        "REVIEW_REQUEST_STALE",
        "DIFF_INCOMPLETE",
        "DIFF_DIGEST_MISMATCH",
        "EMPTY_SCOPE",
    }:
        return {
            "d0": 2,
            "state": "REOBSERVE",
            "next_action": "REOBSERVE_EXACT_HEAD_REVIEW_EVIDENCE",
            "productive_effect": False,
            "effect_ack": "HOLD_UNVERIFIED",
        }
    if blocker in {
        "MESH_WORKFLOW_PERMISSION_WIDENING",
        "MESH_COMPLETION_AUTHORITY_REQUIRED",
    }:
        return {
            "d0": 3,
            "state": "REQUEST_AUTHORITY",
            "next_action": "REQUEST_EXACT_SCOPE_AUTHORITY_REVIEW",
            "productive_effect": False,
            "effect_ack": "HOLD_UNVERIFIED",
        }
    next_action = {
        "DRAFT": "REQUEST_HISTORY_PRESERVING_READY_RECLASSIFICATION_AUTHORITY",
        "COMPETING_WRITER_ACTIVE": "WAIT_FOR_SINGLE_WRITER_LEASE",
        "REQUIRED_GATE_NOT_TERMINAL": "WAIT_FOR_EXACT_HEAD_GATE",
        "APPLICABLE_GATE_NOT_TERMINAL": "WAIT_FOR_EXACT_HEAD_GATE",
        "UNRESOLVED_REVIEW_THREADS": "RESOLVE_REVIEW_THREADS",
        "REQUIRED_GATE_FAILED": "REPAIR_FIRST_FAILED_EXACT_HEAD_GATE",
        "APPLICABLE_GATE_FAILED": "REPAIR_FIRST_FAILED_EXACT_HEAD_GATE",
    }.get(blocker, "REPAIR_FIRST_DETERMINISTIC_REVIEW_BLOCKER")
    return {
        "d0": 1,
        "state": "HOLD",
        "next_action": next_action,
        "productive_effect": False,
        "effect_ack": "HOLD_UNVERIFIED",
    }


def _seal(result: dict[str, Any]) -> dict[str, Any]:
    payload = dict(result)
    payload.pop("receipt_payload_sha256", None)
    result["receipt_payload_sha256"] = _canonical_sha256(payload)
    return result


def _result(
    snapshot: Mapping[str, Any],
    state: str,
    blocker: str | None,
    detail: str,
    *,
    scope: Sequence[Mapping[str, Any]] = (),
    scope_sha256: str | None = None,
    diff_sha256: str | None = None,
    diff_bytes: int | None = None,
    fingerprint: str | None = None,
    diff_transport: Mapping[str, Any] | None = None,
    findings: Sequence[Mapping[str, Any]] = (),
    latest: Mapping[tuple[int, str, str, str], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    pr_number = snapshot.get("pr_number")
    head = snapshot.get("head_sha")
    ledger_path = None
    diff_path = None
    if isinstance(pr_number, int) and isinstance(head, str) and fingerprint:
        base_path = f"{LEDGER_ROOT}/pr-{pr_number}/{head}/{fingerprint}"
        ledger_path = f"{base_path}.json"
        diff_path = f"{base_path}.chunks.json"
    result: dict[str, Any] = {
        "schema": "qikvrt_mesh_repository_review_receipt_v1",
        "review_kind": "MESH_REPOSITORY_SELF_REVIEW",
        "state": state,
        "mesh_disposition": state,
        "first_blocker": blocker,
        "detail": detail,
        "repository": snapshot.get("repository"),
        "repository_role": snapshot.get("repository_role"),
        "pr_number": pr_number,
        "pr_state": snapshot.get("pr_state"),
        "pr_title_sha256": snapshot.get("pr_title_sha256"),
        "pr_body_sha256": snapshot.get("pr_body_sha256"),
        "head_repository": snapshot.get("head_repository"),
        "draft": snapshot.get("draft"),
        "trusted_evaluator_blob_sha": snapshot.get("trusted_evaluator_blob_sha"),
        "trusted_workflow_blob_sha": snapshot.get("trusted_workflow_blob_sha"),
        "base_ref": snapshot.get("base_ref", "main"),
        "current_main_sha": snapshot.get("current_main_sha"),
        "current_main_tree_sha": snapshot.get("current_main_tree_sha"),
        "base_sha": snapshot.get("base_sha"),
        "base_tree_sha": snapshot.get("base_tree_sha"),
        "head_sha": head,
        "tree_sha": snapshot.get("tree_sha"),
        "reviewed_scope": list(scope),
        "scope_sha256": scope_sha256,
        "diff_sha256": diff_sha256,
        "diff_bytes": diff_bytes,
        "evidence_fingerprint": fingerprint,
        "ledger_path": ledger_path,
        "ledger_diff_path": diff_path,
        "diff_transport": dict(diff_transport) if isinstance(diff_transport, Mapping) else None,
        "findings": [dict(finding) for finding in findings],
        "discussion_sha256": _canonical_sha256({
            "review_threads": snapshot.get("review_threads", []),
            "discussion_items": snapshot.get("discussion_items", []),
        }),
        "requested_reviewers_observed": list(snapshot.get("requested_reviewers", [])) if isinstance(snapshot.get("requested_reviewers"), list) else [],
        "requested_team_reviewers_observed": list(snapshot.get("requested_team_reviewers", [])) if isinstance(snapshot.get("requested_team_reviewers"), list) else [],
        "active_writers_observed": list(snapshot.get("active_writers", [])) if isinstance(snapshot.get("active_writers"), list) else [],
        "review_intake": dict(snapshot.get("review_intake", {})) if isinstance(snapshot.get("review_intake"), Mapping) else {},
        "required_gate_paths": dict(snapshot.get("required_gate_paths", {})) if isinstance(snapshot.get("required_gate_paths"), Mapping) else {},
        "required_gate_workflow_ids": dict(snapshot.get("required_gate_workflow_ids", {})) if isinstance(snapshot.get("required_gate_workflow_ids"), Mapping) else {},
        "required_gate_events": dict(snapshot.get("required_gate_events", {})) if isinstance(snapshot.get("required_gate_events"), Mapping) else {},
        "platform_projection": {
            "actor": "github-actions[bot]",
            "review_event": "COMMENT",
            "state": "PENDING_REPOSITORY_PROJECTION",
            "independent_code_owner_approval": False,
        },
        "repository_feedback": {
            "ledger_ref": LEDGER_REF,
            "receipt_path": ledger_path,
            "diff_path": diff_path,
            "diff_transport": dict(diff_transport) if isinstance(diff_transport, Mapping) else None,
            "append_only": True,
            "candidate_branch_mutation": False,
            "status_context": "QIKVRT requested review execution",
            "consumers": [
                "QIKVRT required code-owner review",
                "QIK-VRT expected-head promotion executor",
            ],
        },
        "derived_action": _derived_action(state, blocker),
        "verification_state": "HOLD_UNVERIFIED",
        "ordinary_release": False,
        "external_effect": "NONE",
        "limitations": [
            "deterministic bounded invariant review is not exhaustive semantic verification",
            "repository Mesh identity does not establish reviewer independence or consensus",
            "independent exact-head Code-Owner authority remains a separate gate",
            "head tree scope diff or evidence drift invalidates this receipt for continuation",
        ],
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "INDEPENDENT_CODE_OWNER_APPROVAL": False,
            "MERGE": False,
        },
    }
    if latest is not None:
        result["latest_workflows"] = _gate_projection(latest)
    return _seal(result)


def evaluate(snapshot: Mapping[str, Any], diff: bytes | None = None) -> dict[str, Any]:
    """Evaluate one exact observation and return a sealed Mesh review receipt."""
    if not isinstance(snapshot, Mapping):
        raise ReviewSnapshotError("snapshot must be an object")
    snapshot = dict(snapshot)
    try:
        repository = snapshot.get("repository")
        pr_number = snapshot.get("pr_number")
        if not isinstance(repository, str) or repository.count("/") != 1:
            raise ReviewSnapshotError("repository is invalid")
        if isinstance(pr_number, bool) or not isinstance(pr_number, int) or pr_number < 1:
            raise ReviewSnapshotError("pr_number must be a positive integer")
        if snapshot.get("pr_state") != "open":
            raise ReviewSnapshotError("pull request is not open")
        _sha256(snapshot.get("pr_title_sha256"), "pr_title_sha256")
        _sha256(snapshot.get("pr_body_sha256"), "pr_body_sha256")
        if snapshot.get("head_repository") != repository:
            raise ReviewSnapshotError("pull request head repository is not role-local")
        if snapshot.get("base_ref", "main") != "main":
            raise ReviewSnapshotError("pull request base ref is not main")
        if not isinstance(snapshot.get("draft"), bool):
            raise ReviewSnapshotError("draft must be boolean")
        _sha(snapshot.get("trusted_evaluator_blob_sha"), "trusted_evaluator_blob_sha")
        _sha(snapshot.get("trusted_workflow_blob_sha"), "trusted_workflow_blob_sha")
        current_main = _sha(snapshot.get("current_main_sha"), "current_main_sha")
        current_main_tree = _sha(snapshot.get("current_main_tree_sha"), "current_main_tree_sha")
        base = _sha(snapshot.get("base_sha"), "base_sha")
        base_tree = _sha(snapshot.get("base_tree_sha"), "base_tree_sha")
        head = _sha(snapshot.get("head_sha"), "head_sha")
        observed_head = _sha(snapshot.get("observed_head_sha"), "observed_head_sha")
        tree = _sha(snapshot.get("tree_sha"), "tree_sha")
        observed_tree = _sha(snapshot.get("observed_tree_sha"), "observed_tree_sha")
        scope = canonical_scope(snapshot)
        observed_scope_digest = canonical_scope_digest(scope)
        threads = _threads(snapshot)
        discussion = _discussion_items(snapshot)
        reviewers = _string_list(snapshot, "requested_reviewers")
        teams = _string_list(snapshot, "requested_team_reviewers")
        intake = _canonical_review_intake(snapshot.get("review_intake"))
        writers = _active_writers(snapshot)
        required, required_gate_paths, required_gate_workflow_ids, required_gate_events = (
            _required_gate_binding(snapshot)
        )
        snapshot["discussion_items"] = discussion
        snapshot["review_threads"] = threads
        snapshot["requested_reviewers"] = reviewers
        snapshot["requested_team_reviewers"] = teams
        snapshot["active_writers"] = writers
        snapshot["review_intake"] = intake
        snapshot["required_gate_paths"] = required_gate_paths
        snapshot["required_gate_workflow_ids"] = required_gate_workflow_ids
        snapshot["required_gate_events"] = required_gate_events
        runs = snapshot.get("workflow_runs")
        if not isinstance(runs, list):
            raise ReviewSnapshotError("workflow_runs must be a list")
        latest = {}
        for name, run in collapse_latest(runs).items():
            normalized = dict(run)
            normalized["jobs"] = _canonical_jobs(run)
            normalized["jobs_total"] = len(normalized["jobs"])
            latest[name] = normalized
    except ReviewSnapshotError as exc:
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            "INVALID_REVIEW_SNAPSHOT",
            str(exc),
            findings=[_finding("INVALID_REVIEW_SNAPSHOT", "BLOCK", str(exc))],
        )

    if diff is None or not isinstance(diff, bytes):
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            "REVIEW_BYTES_UNAVAILABLE",
            "complete exact diff bytes are required",
            scope=scope,
            scope_sha256=observed_scope_digest,
            findings=[_finding("REVIEW_BYTES_UNAVAILABLE", "BLOCK", "complete exact diff bytes are required")],
            latest=latest,
        )

    actual_diff_sha256 = hashlib.sha256(diff).hexdigest()
    fingerprint = _evidence_fingerprint(
        snapshot,
        scope,
        observed_scope_digest,
        actual_diff_sha256,
        len(diff),
        threads,
        latest,
        writers,
        required_gate_paths,
    )
    common = {
        "scope": scope,
        "scope_sha256": observed_scope_digest,
        "diff_sha256": actual_diff_sha256,
        "diff_bytes": len(diff),
        "fingerprint": fingerprint,
        "diff_transport": build_diff_transport(
            diff,
            f"{LEDGER_ROOT}/pr-{snapshot['pr_number']}/{snapshot['head_sha']}/{fingerprint}",
        ) if diff else None,
        "latest": latest,
    }
    if intake["reason_state"] == "AMBIGUOUS_FAIL_CLOSED":
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            "REVIEW_REASON_AMBIGUOUS",
            "multiple declared review-reason labels prevent a deterministic priority classification",
            findings=[_finding("REVIEW_REASON_AMBIGUOUS", "BLOCK", "multiple review-reason labels are present")],
            **common,
        )
    if intake["request_state"] == "STALE_EXPLICIT_REQUEST":
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            "REVIEW_REQUEST_STALE",
            "the requested reviewer or team is no longer present at exact observation",
            findings=[_finding("REVIEW_REQUEST_STALE", "BLOCK", "review-request target drifted before exact observation")],
            **common,
        )
    if snapshot.get("diff_complete") is not True:
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            "DIFF_INCOMPLETE",
            "the exact diff producer did not attest complete bytes",
            findings=[_finding("DIFF_INCOMPLETE", "BLOCK", "exact diff completeness is not attested")],
            **common,
        )
    if not diff:
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            "REVIEW_BYTES_UNAVAILABLE",
            "exact diff is empty for a declared review scope",
            findings=[_finding("REVIEW_BYTES_UNAVAILABLE", "BLOCK", "exact diff is empty")],
            **common,
        )
    positive_findings = [
        _finding(
            "EXACT_SCOPE_BOUND",
            "INFO",
            f"{len(scope)} changed path(s) are blob-bound by canonical scope digest",
            evidence_sha256=observed_scope_digest,
        ),
        _finding(
            "EXACT_DIFF_BOUND",
            "INFO",
            f"complete binary/full-index diff contains {len(diff)} bytes",
            evidence_sha256=actual_diff_sha256,
        ),
    ]

    declared_scope = snapshot.get("scope_sha256")
    if declared_scope != observed_scope_digest:
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            "SCOPE_DIGEST_MISMATCH",
            f"declared scope digest {declared_scope!r} != observed {observed_scope_digest}",
            findings=positive_findings
            + [_finding("SCOPE_DIGEST_MISMATCH", "BLOCK", "declared and observed scope digests differ")],
            **common,
        )
    declared_diff = snapshot.get("diff_sha256")
    declared_bytes = snapshot.get("diff_bytes")
    if declared_diff != actual_diff_sha256 or declared_bytes != len(diff):
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            "DIFF_DIGEST_MISMATCH",
            "declared exact diff size or digest differs from supplied bytes",
            findings=positive_findings
            + [_finding("DIFF_DIGEST_MISMATCH", "BLOCK", "declared exact diff binding does not match supplied bytes")],
            **common,
        )

    if base != current_main:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "BASE_DRIFT", f"base {base} != current main {current_main}", findings=positive_findings, **common)
    if base_tree != current_main_tree:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "BASE_TREE_DRIFT", f"base tree {base_tree} != current main tree {current_main_tree}", findings=positive_findings, **common)
    if observed_head != head:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "HEAD_DRIFT", f"observed head {observed_head} != bound head {head}", findings=positive_findings, **common)
    if observed_tree != tree:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "TREE_DRIFT", f"observed tree {observed_tree} != bound tree {tree}", findings=positive_findings, **common)
    if not scope:
        return _result(snapshot, "COMMENT_WITH_BLOCKER", "EMPTY_SCOPE", "review has no changed paths", findings=positive_findings, **common)

    findings = positive_findings + _scan_added_lines(diff)
    blocking = next((finding for finding in findings if finding["severity"] == "BLOCK"), None)
    if blocking is not None:
        return _result(
            snapshot,
            "REQUEST_CHANGES",
            str(blocking["finding_id"]),
            str(blocking["detail"]),
            findings=findings,
            **common,
        )
    authority = next(
        (finding for finding in findings if finding["severity"] == "AUTHORITY_REQUIRED"),
        None,
    )
    if authority is not None:
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            str(authority["finding_id"]),
            str(authority["detail"]),
            findings=findings,
            **common,
        )

    if writers:
        return _result(
            snapshot,
            "WAIT",
            "COMPETING_WRITER_ACTIVE",
            f"{len(writers)} productive repository writer(s) are active",
            findings=findings
            + [_finding("COMPETING_WRITER_ACTIVE", "HOLD", "productive repository writer lease is active")],
            **common,
        )
    unresolved = sum(1 for thread in threads if not thread["is_resolved"])
    if unresolved:
        return _result(
            snapshot,
            "COMMENT_WITH_BLOCKER",
            "UNRESOLVED_REVIEW_THREADS",
            f"{unresolved} unresolved review thread(s)",
            findings=findings
            + [_finding("UNRESOLVED_REVIEW_THREADS", "BLOCK", f"{unresolved} unresolved review thread(s)")],
            **common,
        )

    for identity, run in sorted(latest.items()):
        name = identity[3]
        run_head = run.get("head_sha")
        if run_head != head:
            return _result(
                snapshot,
                "WAIT",
                "UNTRUSTED_GATE_BINDING",
                f"workflow {name} is bound to {run_head!r}, not {head}",
                findings=findings
                + [_finding("UNTRUSTED_GATE_BINDING", "HOLD", f"workflow {name} is not bound to the exact candidate head")],
                **common,
            )
        if run.get("event") != "pull_request":
            detail=f"workflow {name} is not a pull_request run"
            return _result(snapshot, "WAIT", "UNTRUSTED_GATE_BINDING", detail, findings=findings + [_finding("UNTRUSTED_GATE_BINDING", "HOLD", detail)], **common)
        workflow_id = run.get("workflow_id")
        jobs_total = run.get("jobs_total")
        if isinstance(workflow_id, bool) or not isinstance(workflow_id, int) or workflow_id < 1:
            detail=f"workflow {name} lacks a stable workflow identity"
            return _result(snapshot, "WAIT", "UNTRUSTED_GATE_BINDING", detail, findings=findings + [_finding("UNTRUSTED_GATE_BINDING", "HOLD", detail)], **common)
        if isinstance(jobs_total, bool) or not isinstance(jobs_total, int) or jobs_total < 1:
            detail=f"workflow {name} has no exact-head job evidence"
            return _result(snapshot, "WAIT", "ZERO_JOB_GATE", detail, findings=findings + [_finding("ZERO_JOB_GATE", "HOLD", detail)], **common)
    runs_by_name: dict[
        str,
        list[tuple[tuple[int, str, str, str], Mapping[str, Any]]],
    ] = {}
    for identity, run in sorted(latest.items()):
        runs_by_name.setdefault(identity[3], []).append((identity, run))

    required_identities: set[tuple[int, str, str, str]] = set()
    for gate in required:
        matches = runs_by_name.get(gate, [])
        if not matches:
            detail=f"required exact-head gate is absent: {gate}"
            return _result(snapshot, "WAIT", "REQUIRED_GATE_MISSING", detail, findings=findings + [_finding("REQUIRED_GATE_MISSING", "HOLD", detail)], **common)
        if len(matches) != 1:
            detail=(
                f"required workflow name is ambiguous across {len(matches)} "
                f"stable identities: {gate}"
            )
            return _result(
                snapshot,
                "WAIT",
                "UNTRUSTED_GATE_BINDING",
                detail,
                findings=findings
                + [_finding("UNTRUSTED_GATE_BINDING", "HOLD", detail)],
                **common,
            )
        identity, run = matches[0]
        required_identities.add(identity)
        if run.get("status") != "completed":
            detail=f"required exact-head gate is not terminal: {gate}"
            return _result(snapshot, "WAIT", "REQUIRED_GATE_NOT_TERMINAL", detail, findings=findings + [_finding("REQUIRED_GATE_NOT_TERMINAL", "HOLD", detail)], **common)
        if (
            run.get("path") != required_gate_paths[gate]
            or run.get("workflow_id") != required_gate_workflow_ids[gate]
            or run.get("event") != required_gate_events[gate]
        ):
            detail=(
                f"required workflow identity is untrusted: {gate}; "
                f"path={run.get('path')!r}; id={run.get('workflow_id')!r}; "
                f"event={run.get('event')!r}"
            )
            return _result(
                snapshot,
                "WAIT",
                "UNTRUSTED_GATE_BINDING",
                detail,
                findings=findings
                + [_finding("UNTRUSTED_GATE_BINDING", "HOLD", detail)],
                **common,
            )
        if run.get("conclusion") not in SUCCESS:
            detail=f"required exact-head gate failed: {gate}={run.get('conclusion')}"
            return _result(snapshot, "REQUEST_CHANGES", "REQUIRED_GATE_FAILED", detail, findings=findings + [_finding("REQUIRED_GATE_FAILED", "BLOCK", detail)], **common)
        if run.get("conclusion") == "success" and not any(
            job["status"] == "completed" and job["conclusion"] == "success"
            for job in run["jobs"]
        ):
            detail=f"required exact-head gate has no completed successful job: {gate}"
            return _result(snapshot, "WAIT", "ZERO_EXECUTED_JOB_GATE", detail, findings=findings + [_finding("ZERO_EXECUTED_JOB_GATE", "HOLD", detail)], **common)
    for identity, run in sorted(latest.items()):
        if identity in required_identities:
            continue
        name = identity[3]
        observer_path = NON_GATE_OBSERVER_PATHS.get(name)
        if observer_path is not None:
            if run.get("path") != observer_path:
                detail = (
                    f"non-gate observer identity is untrusted: {name}; "
                    f"path={run.get('path')!r}"
                )
                return _result(
                    snapshot,
                    "WAIT",
                    "UNTRUSTED_GATE_BINDING",
                    detail,
                    findings=findings
                    + [_finding("UNTRUSTED_GATE_BINDING", "HOLD", detail)],
                    **common,
                )
            detail = (
                "exact-subject non-gate observer retained as metadata only: "
                f"{name}={run.get('conclusion') or run.get('status')}"
            )
            findings.append(
                _finding("NON_GATE_OBSERVER_CLASSIFIED", "INFO", detail)
            )
            continue
        if run.get("status") != "completed":
            detail=f"applicable exact-head gate is not terminal: {name}"
            return _result(snapshot, "WAIT", "APPLICABLE_GATE_NOT_TERMINAL", detail, findings=findings + [_finding("APPLICABLE_GATE_NOT_TERMINAL", "HOLD", detail)], **common)
        if run.get("conclusion") not in NON_ADVERSE:
            detail=f"applicable exact-head gate is adverse: {name}={run.get('conclusion')}"
            return _result(snapshot, "REQUEST_CHANGES", "APPLICABLE_GATE_FAILED", detail, findings=findings + [_finding("APPLICABLE_GATE_FAILED", "BLOCK", detail)], **common)
        if run.get("conclusion") == "success" and not any(
            job["status"] == "completed" and job["conclusion"] == "success"
            for job in run["jobs"]
        ):
            detail=f"applicable exact-head gate has no completed successful job: {name}"
            return _result(snapshot, "WAIT", "ZERO_EXECUTED_JOB_GATE", detail, findings=findings + [_finding("ZERO_EXECUTED_JOB_GATE", "HOLD", detail)], **common)

    if snapshot.get("draft") is True:
        return _result(
            snapshot,
            "WAIT",
            "DRAFT",
            "candidate remains draft after trusted exact-head gates",
            findings=findings
            + [_finding("DRAFT", "HOLD", "candidate remains draft after trusted exact-head gates")],
            **common,
        )

    findings.append(
        _finding(
            "EXACT_HEAD_GATES_NON_ADVERSE",
            "INFO",
            "all observed required and applicable exact-head gates are terminal non-adverse",
        )
    )
    return _result(
        snapshot,
        "APPROVE",
        None,
        "exact diff and scope inspected; deterministic findings are non-adverse; independent Code-Owner authority remains separate",
        findings=findings,
        **common,
    )


def _run_json(command: Sequence[str], *, input_text: str | None = None) -> Any:
    completed = subprocess.run(
        list(command),
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        detail = completed.stderr.strip().replace("\n", " ")[:400]
        raise ReviewObservationError(f"command failed ({command[0]}): {detail}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ReviewObservationError(f"command returned invalid JSON ({command[0]})") from exc


def _gh_one(path: str) -> Any:
    return _run_json(("gh", "api", path))


def _gh_pages(path: str) -> list[Mapping[str, Any]]:
    pages = _run_json(("gh", "api", "--paginate", "--slurp", path))
    if not isinstance(pages, list):
        raise ReviewObservationError("paginated GitHub response is not a list")
    result: list[Mapping[str, Any]] = []
    for page in pages:
        if not isinstance(page, list):
            raise ReviewObservationError("paginated GitHub page is not a list")
        for item in page:
            if not isinstance(item, Mapping):
                raise ReviewObservationError("paginated GitHub item is not an object")
            result.append(item)
    return result


def _positive_integer(value: Any) -> int | None:
    """Return a positive integer subject identifier, otherwise ``None``."""
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


def _git_sha1(value: Any) -> str | None:
    if not isinstance(value, str) or len(value) != 40:
        return None
    if any(character not in "0123456789abcdef" for character in value):
        return None
    return value


def _selection_subject(pr: Mapping[str, Any]) -> dict[str, Any]:
    """Project only the fields used for actionable-subject diagnostics."""
    base = pr.get("base")
    head = pr.get("head")
    base_ref = base.get("ref") if isinstance(base, Mapping) else None
    head_sha = head.get("sha") if isinstance(head, Mapping) else None
    head_repo = head.get("repo") if isinstance(head, Mapping) else None
    return {
        "number": _positive_integer(pr.get("number")),
        "state": pr.get("state") if isinstance(pr.get("state"), str) else None,
        "base_ref": base_ref if isinstance(base_ref, str) else None,
        "head_sha": head_sha if isinstance(head_sha, str) else None,
        "head_repository": (
            head_repo.get("full_name")
            if isinstance(head_repo, Mapping)
            and isinstance(head_repo.get("full_name"), str)
            else None
        ),
    }


def _selection_result(
    state: str,
    selection_basis: str,
    *,
    first_blocker: str | None = None,
    pr_number: int | None = None,
    event_source: str | None = None,
    expected_head: str | None = None,
    subject: Mapping[str, Any] | None = None,
    eligibility_reasons: Sequence[str] = (),
    subject_count: int = 0,
    detail: str | None = None,
) -> dict[str, Any]:
    """Return one stable, non-effecting selector observation."""
    return {
        "schema": REVIEW_SELECTION_SCHEMA,
        "state": state,
        "pr_number": pr_number,
        "candidate_pr_number": pr_number if state == "CANDIDATE" else None,
        "selection_basis": selection_basis,
        "event_source": event_source,
        "expected_head": expected_head,
        "first_blocker": first_blocker,
        "detail": detail,
        "eligibility_reasons": list(eligibility_reasons),
        "subject_count": subject_count,
        "observed_subject": dict(subject) if subject is not None else None,
        "review_execution": state == "CANDIDATE",
        "review_observation_started": False,
        "external_effect": "NONE",
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }


def _eligible_review_subject(
    pr: Mapping[str, Any], repository: str, expected_number: int
) -> tuple[dict[str, Any], list[str]]:
    subject = _selection_subject(pr)
    reasons: list[str] = []
    if subject["number"] != expected_number:
        reasons.append("PULL_REQUEST_NUMBER_MISMATCH")
    if subject["state"] != "open":
        reasons.append("PULL_REQUEST_NOT_OPEN")
    if subject["base_ref"] != "main":
        reasons.append("PULL_REQUEST_BASE_NOT_MAIN")
    if subject["head_repository"] != repository:
        reasons.append("PULL_REQUEST_HEAD_NOT_ROLE_LOCAL")
    if _git_sha1(subject["head_sha"]) is None:
        reasons.append("PULL_REQUEST_HEAD_SHA_INVALID")
    return subject, reasons


def event_payload_pull_request(
    payload: Any,
    repository: str,
    expected_number: int,
    expected_head: str,
    event_name: str,
) -> Mapping[str, Any] | None:
    """Return one exact native PR-event subject, otherwise ``None``.

    This is a read-only fallback for an unavailable live PR GET. It
    accepts only GitHub-native pull-request events whose embedded
    object already binds the exact repository, PR number, open state,
    main base and expected head. Other event classes, malformed
    objects and any drift fail closed.
    """
    if event_name not in {"pull_request_target", "pull_request_review"}:
        return None
    if not isinstance(payload, Mapping):
        return None
    if _positive_integer(expected_number) is None:
        return None
    if _git_sha1(expected_head) is None:
        return None
    pull_request = payload.get("pull_request")
    if not isinstance(pull_request, Mapping):
        return None
    subject, reasons = _eligible_review_subject(
        pull_request,
        repository,
        expected_number,
    )
    if reasons or subject["head_sha"] != expected_head:
        return None
    return pull_request


def _workflow_run_pr_number(
    item: Mapping[str, Any], repository: str
) -> tuple[int | None, str | None]:
    """Require a workflow-run PR association to bind to this repository."""
    number = _positive_integer(item.get("number"))
    if number is None:
        return None, "MALFORMED_WORKFLOW_RUN_PULL_REQUESTS"
    url = item.get("url")
    if not isinstance(url, str) or not url:
        return None, "MALFORMED_WORKFLOW_RUN_PULL_REQUESTS"
    parsed = urllib.parse.urlparse(url)
    expected_path = f"/repos/{repository}/pulls/{number}"
    if parsed.scheme != "https" or parsed.netloc != "api.github.com":
        return None, "WORKFLOW_RUN_PULL_REQUEST_NOT_ROLE_LOCAL"
    if parsed.path != expected_path or parsed.query or parsed.fragment:
        return None, "WORKFLOW_RUN_PULL_REQUEST_NOT_ROLE_LOCAL"
    return number, None


def select_review_subject(
    *,
    repository: str,
    requested_pr: str,
    event_pr: str,
    event_name: str,
    expected_head: str,
    workflow_event: str,
    workflow_prs: Any,
    fetch_pull_request: Callable[[int], Mapping[str, Any]],
) -> dict[str, Any]:
    """Select one exact, eligible review subject without a fallback scan.

    A non-candidate result is diagnostic only.  In particular, an explicit PR
    event which is not open, role-local, and main-based is never conflated with
    an eventless ``NOOP``. A native pull-request event must retain its literal
    head, while an issue comment is bound by its exact PR number. A workflow-run
    association must name this repository exactly, and a workflow head is never
    reverse-mapped by listing PRs.
    """
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise ReviewSnapshotError("selector repository is invalid")

    bound_head = expected_head.strip()
    if bound_head and _git_sha1(bound_head) is None:
        return _selection_result(
            "REOBSERVE_EXACT_EVENT_TARGET",
            "EXACT_EVENT_OR_DISPATCH",
            first_blocker="INVALID_EVENT_EXPECTED_HEAD",
            event_source="EVENT_HEAD",
            expected_head=bound_head,
            eligibility_reasons=["INVALID_EVENT_EXPECTED_HEAD"],
        )

    def exact_number(
        value: str,
        source: str,
        *,
        require_bound_head: bool,
        missing_head_blocker: str,
    ) -> dict[str, Any]:
        number = _positive_integer(value)
        if number is None:
            return _selection_result(
                "INELIGIBLE_EVENT_TARGET",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker="INVALID_EXACT_PULL_REQUEST_NUMBER",
                event_source=source,
                eligibility_reasons=["INVALID_EXACT_PULL_REQUEST_NUMBER"],
            )
        if require_bound_head and not bound_head:
            return _selection_result(
                "REOBSERVE_EXACT_EVENT_TARGET",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker=missing_head_blocker,
                pr_number=number,
                event_source=source,
                eligibility_reasons=[missing_head_blocker],
                subject_count=1,
            )
        try:
            observed = fetch_pull_request(number)
        except (OSError, ValueError, ReviewObservationError) as exc:
            return _selection_result(
                "REOBSERVE_EXACT_EVENT_TARGET",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker="PULL_REQUEST_OBSERVATION_UNAVAILABLE",
                pr_number=number,
                event_source=source,
                expected_head=bound_head or None,
                eligibility_reasons=["PULL_REQUEST_OBSERVATION_UNAVAILABLE"],
                subject_count=1,
                detail=str(exc)[:300],
            )
        if not isinstance(observed, Mapping):
            return _selection_result(
                "INELIGIBLE_EVENT_TARGET",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker="PULL_REQUEST_OBSERVATION_MALFORMED",
                pr_number=number,
                event_source=source,
                eligibility_reasons=["PULL_REQUEST_OBSERVATION_MALFORMED"],
            )
        subject, reasons = _eligible_review_subject(observed, repository, number)
        if reasons:
            return _selection_result(
                "INELIGIBLE_EVENT_TARGET",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker=reasons[0],
                pr_number=number,
                event_source=source,
                expected_head=bound_head or None,
                subject=subject,
                eligibility_reasons=reasons,
                subject_count=1,
            )
        if bound_head and subject["head_sha"] != bound_head:
            return _selection_result(
                "REOBSERVE_EXACT_EVENT_TARGET",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker="EVENT_TARGET_HEAD_DRIFT",
                pr_number=number,
                event_source=source,
                expected_head=bound_head,
                subject=subject,
                eligibility_reasons=["EVENT_TARGET_HEAD_DRIFT"],
                subject_count=1,
            )
        return _selection_result(
            "CANDIDATE",
            "EXACT_EVENT_OR_DISPATCH",
            pr_number=number,
            event_source=source,
            expected_head=bound_head or None,
            subject=subject,
            subject_count=1,
        )

    if requested_pr.strip() and event_pr.strip():
        requested_number = _positive_integer(requested_pr)
        event_number = _positive_integer(event_pr)
        if (
            requested_number is not None
            and event_number is not None
            and requested_number != event_number
        ):
            return _selection_result(
                "AMBIGUOUS_EVENT_SUBJECT",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker="CONFLICTING_EXACT_PULL_REQUEST_SUBJECTS",
                event_source="WORKFLOW_DISPATCH_AND_PULL_REQUEST_EVENT",
                subject_count=2,
            )

    if requested_pr.strip():
        return exact_number(
            requested_pr,
            "WORKFLOW_DISPATCH_PR",
            require_bound_head=True,
            missing_head_blocker="WORKFLOW_DISPATCH_HEAD_MISSING",
        )
    if event_pr.strip():
        if event_name in {"pull_request_target", "pull_request_review"}:
            return exact_number(
                event_pr,
                "PULL_REQUEST_EVENT",
                require_bound_head=True,
                missing_head_blocker="PULL_REQUEST_EVENT_HEAD_MISSING",
            )
        if event_name == "issue_comment":
            return exact_number(
                event_pr,
                "ISSUE_COMMENT_PULL_REQUEST_EVENT",
                require_bound_head=False,
                missing_head_blocker="ISSUE_COMMENT_HEAD_NOT_REQUIRED",
            )
        return _selection_result(
            "INELIGIBLE_EVENT_TARGET",
            "EXACT_EVENT_OR_DISPATCH",
            first_blocker="UNSUPPORTED_EXACT_EVENT_SOURCE",
            event_source=event_name or "UNKNOWN",
            eligibility_reasons=["UNSUPPORTED_EXACT_EVENT_SOURCE"],
        )

    if not workflow_event.strip():
        return _selection_result(
            "NO_EVENT_SUBJECT",
            "NO_EVENT_SUBJECT",
            first_blocker="NO_EXACT_EVENT_OR_DISPATCH_SUBJECT",
            event_source="NONE",
            expected_head=bound_head or None,
        )

    if workflow_event.strip():
        if workflow_event in {"schedule", "workflow_dispatch"}:
            return _selection_result(
                "INELIGIBLE_EVENT_TARGET",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker="SCHEDULED_OR_MANUAL_WORKFLOW_RUN_FORBIDDEN",
                event_source="WORKFLOW_RUN",
                expected_head=bound_head or None,
                eligibility_reasons=["SCHEDULED_OR_MANUAL_WORKFLOW_RUN_FORBIDDEN"],
            )
        if not workflow_prs:
            return _selection_result(
                "NO_EVENT_SUBJECT",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker="NO_EXACT_WORKFLOW_RUN_PULL_REQUEST",
                event_source="WORKFLOW_RUN",
                expected_head=bound_head or None,
            )
        if not isinstance(workflow_prs, Sequence) or isinstance(workflow_prs, (str, bytes)):
            return _selection_result(
                "INELIGIBLE_EVENT_TARGET",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker="MALFORMED_WORKFLOW_RUN_PULL_REQUESTS",
                event_source="WORKFLOW_RUN_PULL_REQUESTS",
                expected_head=bound_head or None,
                eligibility_reasons=["MALFORMED_WORKFLOW_RUN_PULL_REQUESTS"],
            )
        numbers: set[int] = set()
        for item in workflow_prs:
            if not isinstance(item, Mapping):
                return _selection_result(
                    "INELIGIBLE_EVENT_TARGET",
                    "EXACT_EVENT_OR_DISPATCH",
                    first_blocker="MALFORMED_WORKFLOW_RUN_PULL_REQUESTS",
                    event_source="WORKFLOW_RUN_PULL_REQUESTS",
                    expected_head=bound_head or None,
                    eligibility_reasons=["MALFORMED_WORKFLOW_RUN_PULL_REQUESTS"],
                )
            number, blocker = _workflow_run_pr_number(item, repository)
            if blocker is not None:
                return _selection_result(
                    "INELIGIBLE_EVENT_TARGET",
                    "EXACT_EVENT_OR_DISPATCH",
                    first_blocker=blocker,
                    event_source="WORKFLOW_RUN_PULL_REQUESTS",
                    expected_head=bound_head or None,
                    eligibility_reasons=[blocker],
                )
            assert number is not None
            numbers.add(number)
        if len(numbers) != 1:
            return _selection_result(
                "AMBIGUOUS_EVENT_SUBJECT",
                "EXACT_EVENT_OR_DISPATCH",
                first_blocker="WORKFLOW_RUN_MULTIPLE_PULL_REQUESTS",
                event_source="WORKFLOW_RUN_PULL_REQUESTS",
                expected_head=bound_head or None,
                subject_count=len(numbers),
            )
        return exact_number(
            str(next(iter(numbers))),
            "WORKFLOW_RUN_PULL_REQUESTS",
            require_bound_head=True,
            missing_head_blocker="WORKFLOW_RUN_HEAD_MISSING",
        )

    return _selection_result(
        "NO_EVENT_SUBJECT",
        "NO_EVENT_SUBJECT",
        first_blocker="NO_EXACT_EVENT_OR_DISPATCH_SUBJECT",
        event_source="NONE",
    )


def _gh_runs(path: str) -> list[Mapping[str, Any]]:
    pages = _run_json(("gh", "api", "--paginate", "--slurp", path))
    if not isinstance(pages, list):
        raise ReviewObservationError("workflow-run response is not a list")
    result: list[Mapping[str, Any]] = []
    for page in pages:
        if not isinstance(page, Mapping) or not isinstance(page.get("workflow_runs"), list):
            raise ReviewObservationError("workflow-run page is malformed")
        for item in page["workflow_runs"]:
            if not isinstance(item, Mapping):
                raise ReviewObservationError("workflow run is not an object")
            result.append(item)
    return result


def _gh_jobs(path: str) -> list[Mapping[str, Any]]:
    """Read and completeness-check every paginated job for one workflow run."""
    pages = _run_json(("gh", "api", "--paginate", "--slurp", path))
    if not isinstance(pages, list) or not pages:
        raise ReviewObservationError("workflow-job response is not a non-empty list")
    result: list[Mapping[str, Any]] = []
    declared_total: int | None = None
    for page in pages:
        if not isinstance(page, Mapping) or not isinstance(page.get("jobs"), list):
            raise ReviewObservationError("workflow-job page is malformed")
        total = page.get("total_count")
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise ReviewObservationError("workflow-job total_count is invalid")
        if declared_total is None:
            declared_total = total
        elif declared_total != total:
            raise ReviewObservationError("workflow-job total_count changed across pages")
        for item in page["jobs"]:
            if not isinstance(item, Mapping):
                raise ReviewObservationError("workflow job is not an object")
            result.append(item)
    if declared_total != len(result):
        raise ReviewObservationError(
            f"workflow-job projection is incomplete: {len(result)} != {declared_total}"
        )
    return result


def _git_text(arguments: Sequence[str]) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise ReviewObservationError(
            f"Git observation failed: {completed.stderr.strip().replace(chr(10), ' ')[:400]}"
        )
    return completed.stdout.strip()


def _git_bytes(arguments: Sequence[str], *, cwd: str | os.PathLike[str] | None = None) -> bytes:
    environment = os.environ.copy()
    environment.update({"LC_ALL": "C", "LANG": "C"})
    completed = subprocess.run(
        ["git", *arguments],
        capture_output=True,
        check=False,
        cwd=cwd,
        env=environment,
    )
    if completed.returncode:
        detail = completed.stderr.decode("utf-8", errors="replace").strip().replace("\n", " ")[:400]
        raise ReviewObservationError(f"Git observation failed: {detail}")
    return completed.stdout


def _canonical_git_diff(
    base: str,
    head: str,
    *,
    cwd: str | os.PathLike[str] | None = None,
) -> bytes:
    """Produce config-fenced exact diff bytes for one immutable commit pair."""
    return _git_bytes(
        (
            "-c", "color.ui=false",
            "-c", "diff.noprefix=false",
            "-c", "diff.mnemonicPrefix=false",
            "-c", "diff.algorithm=myers",
            "diff",
            "--no-color",
            "--src-prefix=a/",
            "--dst-prefix=b/",
            "--unified=3",
            "--inter-hunk-context=0",
            "--no-indent-heuristic",
            "--output-indicator-new=+",
            "--output-indicator-old=-",
            "--output-indicator-context= ",
            "-O/dev/null",
            "--submodule=short",
            "--binary",
            "--full-index",
            "--no-ext-diff", "--no-textconv", "--no-renames",
            base,
            head,
            "--",
        ),
        cwd=cwd,
    )


def _git_fetch(arguments: Sequence[str]) -> None:
    completed = subprocess.run(
        ["git", "fetch", *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise ReviewObservationError(
            f"Git fetch failed: {completed.stderr.strip().replace(chr(10), ' ')[:400]}"
        )


def _git_object_at(commit: str, path: str) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "--verify", f"{commit}:{path}"],
        text=True,
        capture_output=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def _git_scope(base: str, head: str) -> list[dict[str, Any]]:
    raw = _git_bytes(("diff", "--name-status", "-z", "--no-renames", base, head, "--"))
    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 2:
        raise ReviewObservationError("invalid NUL-delimited Git scope observation")
    status_names = {"A": "added", "D": "removed", "M": "modified", "T": "changed"}
    changed: list[dict[str, Any]] = []
    for offset in range(0, len(fields), 2):
        try:
            code = fields[offset].decode("ascii")
            path = fields[offset + 1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ReviewObservationError("Git scope contains a non-UTF-8 path") from exc
        status = status_names.get(code[:1])
        if status is None:
            raise ReviewObservationError(f"unsupported Git scope status: {code!r}")
        changed.append(
            {
                "path": path,
                "previous_path": None,
                "status": status,
                "base_blob_sha": None if status == "added" else _git_object_at(base, path),
                "head_blob_sha": None if status == "removed" else _git_object_at(head, path),
            }
        )
    return changed


def _thread_observation(repository: str, number: int) -> list[dict[str, Any]]:
    owner, name = repository.split("/", 1)
    query = """query($owner:String!,$name:String!,$number:Int!,$after:String){repository(owner:$owner,name:$name){pullRequest(number:$number){reviewThreads(first:100,after:$after){pageInfo{hasNextPage endCursor}nodes{id isResolved}}}}}"""
    after: str | None = None
    threads: list[dict[str, Any]] = []
    while True:
        command = [
            "gh", "api", "graphql", "-f", f"query={query}",
            "-F", f"owner={owner}", "-F", f"name={name}", "-F", f"number={number}",
        ]
        if after is not None:
            command.extend(("-F", f"after={after}"))
        graph = _run_json(command)
        try:
            connection = graph["data"]["repository"]["pullRequest"]["reviewThreads"]
            nodes = connection["nodes"]
            page_info = connection["pageInfo"]
        except (KeyError, TypeError) as exc:
            raise ReviewObservationError("review-thread response is malformed") from exc
        for node in nodes:
            threads.append(
                {
                    "id": str(node["id"]),
                    "is_resolved": bool(node["isResolved"]),
                    "body_sha256": None,
                }
            )
        if not page_info.get("hasNextPage"):
            break
        after = page_info.get("endCursor")
        if not isinstance(after, str) or not after:
            raise ReviewObservationError("review-thread pagination cursor is missing")
    return threads


def _discussion_observation(repository: str, number: int) -> list[dict[str, Any]]:
    endpoints = (
        ("ISSUE_COMMENT", f"repos/{repository}/issues/{number}/comments?per_page=100"),
        ("PULL_REQUEST_REVIEW", f"repos/{repository}/pulls/{number}/reviews?per_page=100"),
        ("REVIEW_COMMENT", f"repos/{repository}/pulls/{number}/comments?per_page=100"),
    )
    result: list[dict[str, Any]] = []
    for kind, endpoint in endpoints:
        for item in _gh_pages(endpoint):
            body = item.get("body") or ""
            author = (item.get("user") or {}).get("login")
            if (
                author == "github-actions[bot]"
                and any(
                    body.startswith(prefix)
                    for prefix in TRUSTED_AUTOMATION_DISCUSSION_PREFIXES
                )
            ):
                continue
            updated = (
                item.get("updated_at")
                or item.get("submitted_at")
                or item.get("created_at")
            )
            if not isinstance(updated, str) or not updated:
                raise ReviewObservationError(f"{kind} lacks an observation timestamp")
            result.append(
                {
                    "kind": kind,
                    "id": str(item.get("id")),
                    "author": author,
                    "author_association": item.get("author_association"),
                    "state": item.get("state"),
                    "commit_id": item.get("commit_id"),
                    "updated_at": updated,
                    "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                }
            )
    result.sort(key=lambda item: (item["kind"], item["id"]))
    return result


def _workflow_observation(
    repository: str,
    head: str,
) -> list[dict[str, Any]]:
    encoded_head = urllib.parse.quote(head, safe="")
    raw_runs = _gh_runs(
        f"repos/{repository}/actions/runs?head_sha={encoded_head}&event=pull_request&per_page=100"
    )
    runs: list[dict[str, Any]] = [
        {
            "id": item.get("id"),
            "workflow_id": item.get("workflow_id"),
            "name": item.get("name"),
            "path": item.get("path"),
            "event": item.get("event"),
            "status": item.get("status"),
            "conclusion": item.get("conclusion"),
            "run_number": item.get("run_number"),
            "run_attempt": item.get("run_attempt", 1),
            "head_sha": item.get("head_sha"),
            "jobs_total": None,
            "jobs": None,
        }
        for item in raw_runs
    ]
    latest = collapse_latest(runs)
    for run in latest.values():
        run_id = run.get("id")
        if isinstance(run_id, bool) or not isinstance(run_id, int) or run_id < 1:
            raise ReviewObservationError("workflow run lacks a positive id")
        raw_jobs = _gh_jobs(
            f"repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
        )
        run["jobs_total"] = len(raw_jobs)
        run["jobs"] = [
            {
                "id": job.get("id"),
                "status": job.get("status"),
                "conclusion": job.get("conclusion"),
            }
            for job in raw_jobs
        ]
        try:
            run["jobs"] = _canonical_jobs(run)
        except ReviewSnapshotError as exc:
            raise ReviewObservationError(
                f"workflow run {run_id} has invalid job evidence: {exc}"
            ) from exc
    return runs


def _active_writer_observation(
    repository: str,
    current_run_id: int,
    writer_names: set[str],
    relevant_heads: set[str],
) -> list[dict[str, Any]]:
    """Observe only writers that can still mutate this exact subject.

    Repository-wide Actions queries can retain queued admission ghosts
    on immutable predecessor heads. They are not leases on the current
    review. Main-driven writers remain relevant at the exact observed
    main head; candidate writers remain relevant at the exact PR head.
    Malformed relevant-head bindings fail closed.
    """
    if (
        not isinstance(relevant_heads, set)
        or not relevant_heads
        or any(_git_sha1(value) is None for value in relevant_heads)
    ):
        raise ReviewObservationError(
            "active writer relevant-head binding is invalid"
        )
    observed: dict[int, dict[str, Any]] = {}
    for status in ACTIVE_WRITER_STATES:
        for run in _gh_runs(
            f"repos/{repository}/actions/runs?status={status}&per_page=100"
        ):
            run_id = run.get("id")
            if (
                isinstance(run_id, int)
                and run_id != current_run_id
                and run.get("name") in writer_names
                and run.get("head_sha") in relevant_heads
            ):
                observed[run_id] = {
                    "id": run_id,
                    "name": run.get("name"),
                    "status": run.get("status"),
                    "head_sha": run.get("head_sha"),
                    "workflow_id": run.get("workflow_id"),
                    "path": run.get("path"),
                    "event": run.get("event"),
                    "run_number": run.get("run_number"),
                    "run_attempt": run.get("run_attempt", 1),
                }
    return sorted(observed.values(), key=lambda item: (str(item["name"]), item["id"]))


def observe_repository(
    repository: str,
    pr_number: int,
    current_run_id: int,
    required_gates: Sequence[str],
    required_gate_paths: Mapping[str, str],
    writer_workflows: Sequence[str],
    expected_head: str | None = None,
    event_context: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], bytes]:
    """Read one stable trusted-main repository observation without remote writes."""
    if expected_head is not None and _git_sha1(expected_head) is None:
        raise ReviewObservationError("exact selector head is not a Git SHA-1")
    pr = _gh_one(f"repos/{repository}/pulls/{pr_number}")
    if (
        expected_head is not None
        and pr.get("head", {}).get("sha") != expected_head
    ):
        raise ReviewObservationError("pull request head differs from exact selector event")
    main = _gh_one(f"repos/{repository}/commits/main")
    if not isinstance(pr, Mapping) or not isinstance(main, Mapping):
        raise ReviewObservationError("pull request or main observation is malformed")
    main_sha = str(main.get("sha"))
    if _git_text(("rev-parse", "HEAD")) != main_sha:
        raise ReviewObservationError("trusted-main checkout drifted from observed main")
    main_tree = _gh_one(f"repos/{repository}/git/commits/{main_sha}")["tree"]["sha"]
    if _git_text(("rev-parse", "HEAD^{tree}")) != main_tree:
        raise ReviewObservationError("trusted-main tree differs from observed main tree")

    base = pr["base"]["sha"]
    head = pr["head"]["sha"]
    title_sha256 = hashlib.sha256(str(pr.get("title") or "").encode("utf-8")).hexdigest()
    body_sha256 = hashlib.sha256(str(pr.get("body") or "").encode("utf-8")).hexdigest()
    _git_fetch(("--no-tags", "--depth=1", "origin", base))
    local_ref = f"refs/qikvrt/mesh-review-head-{pr_number}"
    _git_fetch(
        (
            "--no-tags",
            "--depth=1",
            "origin",
            f"+refs/pull/{pr_number}/head:{local_ref}",
        )
    )
    if _git_text(("rev-parse", "--verify", f"{local_ref}^{{commit}}")) != head:
        raise ReviewObservationError("pull-request ref drifted during fetch")

    base_tree = _gh_one(f"repos/{repository}/git/commits/{base}")["tree"]["sha"]
    head_tree = _gh_one(f"repos/{repository}/git/commits/{head}")["tree"]["sha"]
    if _git_text(("rev-parse", f"{head}^{{tree}}")) != head_tree:
        raise ReviewObservationError("local candidate tree differs from GitHub")
    scope = _git_scope(base, head)
    scope_envelope = {
        "changed_files": scope,
        "changed_paths": sorted(item["path"] for item in scope),
    }
    scope_digest = canonical_scope_digest(canonical_scope(scope_envelope))
    diff = _canonical_git_diff(base, head)

    gate_ids: dict[str, int] = {}
    gate_events = {name: "pull_request" for name in required_gates}
    for gate in required_gates:
        path = required_gate_paths[gate]
        workflow = _gh_one(
            f"repos/{repository}/actions/workflows/{urllib.parse.quote(pathlib.PurePosixPath(path).name, safe='')}"
        )
        if workflow.get("path") != path:
            raise ReviewObservationError(f"trusted workflow path mismatch: {gate}")
        gate_ids[gate] = int(workflow["id"])

    threads = _thread_observation(repository, pr_number)
    discussion = _discussion_observation(repository, pr_number)
    runs = _workflow_observation(repository, head)
    writers = _active_writer_observation(
        repository,
        current_run_id,
        set(writer_workflows),
        {main_sha, head},
    )
    final_main = _gh_one(f"repos/{repository}/commits/main")
    final_pr = _gh_one(f"repos/{repository}/pulls/{pr_number}")
    if final_main.get("sha") != main_sha:
        raise ReviewObservationError("main changed during repository observation")
    if (
        expected_head is not None
        and final_pr.get("head", {}).get("sha") != expected_head
    ):
        raise ReviewObservationError("pull request head drifted from exact selector event")
    if (
        final_pr.get("state") != pr.get("state")
        or final_pr.get("draft") != pr.get("draft")
        or final_pr.get("base", {}).get("sha") != base
        or final_pr.get("head", {}).get("sha") != head
        or hashlib.sha256(str(final_pr.get("title") or "").encode("utf-8")).hexdigest() != title_sha256
        or hashlib.sha256(str(final_pr.get("body") or "").encode("utf-8")).hexdigest() != body_sha256
    ):
        raise ReviewObservationError("pull request changed during repository observation")

    raw_labels = final_pr.get("labels", [])
    if not isinstance(raw_labels, list):
        raise ReviewObservationError("pull request labels are malformed")
    observed_labels: list[str] = []
    for item in raw_labels:
        if not isinstance(item, Mapping) or not isinstance(item.get("name"), str):
            raise ReviewObservationError("pull request label is malformed")
        observed_labels.append(item["name"])
    raw_reviewers = final_pr.get("requested_reviewers", [])
    raw_teams = final_pr.get("requested_teams", [])
    if not isinstance(raw_reviewers, list) or not isinstance(raw_teams, list):
        raise ReviewObservationError("pull request requested-reviewer projection is malformed")
    observed_reviewers: list[str] = []
    for item in raw_reviewers:
        if not isinstance(item, Mapping) or not isinstance(item.get("login"), str) or not item["login"]:
            raise ReviewObservationError("pull request requested reviewer is malformed")
        observed_reviewers.append(item["login"])
    observed_teams: list[str] = []
    for item in raw_teams:
        if not isinstance(item, Mapping) or not isinstance(item.get("slug"), str) or not item["slug"]:
            raise ReviewObservationError("pull request requested reviewer team is malformed")
        observed_teams.append(item["slug"])
    observed_reviewers.sort()
    observed_teams.sort()
    intake = _review_intake(
        event_context,
        observed_labels,
        observed_reviewers,
        observed_teams,
    )

    if repository == "Goldkelch/qik-vrt":
        role = "AUTHORITY"
    elif repository == "ingolf-lohmann/qik-vrt":
        role = "MIRROR"
    else:
        role = "MESH_NODE"
    snapshot = {
        "repository": repository,
        "repository_role": role,
        "pr_number": pr_number,
        "pr_state": final_pr.get("state"),
        "pr_title_sha256": title_sha256,
        "pr_body_sha256": body_sha256,
        "head_repository": final_pr.get("head", {}).get("repo", {}).get("full_name"),
        "base_ref": final_pr.get("base", {}).get("ref"),
        "draft": bool(final_pr.get("draft")),
        "trusted_evaluator_blob_sha": _git_text(("rev-parse", f"HEAD:{TRUSTED_EVALUATOR_PATH}")),
        "trusted_workflow_blob_sha": _git_text(("rev-parse", f"HEAD:{TRUSTED_WORKFLOW_PATH}")),
        "current_main_sha": main_sha,
        "current_main_tree_sha": main_tree,
        "base_sha": base,
        "base_tree_sha": base_tree,
        "head_sha": head,
        "observed_head_sha": final_pr.get("head", {}).get("sha"),
        "tree_sha": head_tree,
        "observed_tree_sha": head_tree,
        "requested_reviewers": observed_reviewers,
        "requested_team_reviewers": observed_teams,
        "review_intake": intake,
        **scope_envelope,
        "scope_sha256": scope_digest,
        "diff_sha256": hashlib.sha256(diff).hexdigest(),
        "diff_bytes": len(diff),
        # The observer has already materialized every diff byte.  The separate
        # The observer materializes every byte; receipt transport splits it
        # into independently bounded, content-addressed packets.
        "diff_complete": True,
        "review_threads": threads,
        "unresolved_review_threads": sum(1 for item in threads if not item["is_resolved"]),
        "discussion_items": discussion,
        "active_writers": writers,
        "required_gates": list(required_gates),
        "required_gate_paths": dict(required_gate_paths),
        "required_gate_workflow_ids": gate_ids,
        "required_gate_events": gate_events,
        "workflow_runs": runs,
    }
    return snapshot, diff


def verify_current_receipt(
    expected: Mapping[str, Any],
    expected_receipt_bytes: bytes,
    expected_diff: bytes,
    repository: str,
    pr_number: int,
    current_run_id: int,
    required_gates: Sequence[str],
    required_gate_paths: Mapping[str, str],
    writer_workflows: Sequence[str],
) -> tuple[dict[str, Any], dict[str, Any], bytes]:
    snapshot, diff = observe_repository(
        repository,
        pr_number,
        current_run_id,
        required_gates,
        required_gate_paths,
        writer_workflows,
        expected_head=_optional_text(expected.get("head_sha"), "receipt head_sha"),
        event_context=_event_context_from_review_intake(expected),
    )
    fresh = evaluate(snapshot, diff)
    try:
        stored_receipt = json.loads(expected_receipt_bytes)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        stored_receipt = None
    sealed_payload = dict(expected)
    claimed_payload_sha256 = sealed_payload.pop("receipt_payload_sha256", None)
    expected_binding = _historical_receipt_binding(expected)
    fresh_binding = _historical_receipt_binding(fresh)
    main_tip_binding = all(
        expected.get(field) == fresh.get(field)
        for field in REOBSERVATION_DECISION_INPUT_FIELDS
    )
    checks = {
        "expected_receipt_self_seal": claimed_payload_sha256 == _canonical_sha256(sealed_payload),
        "stored_receipt_parses_as_expected": stored_receipt == dict(expected),
        "stored_receipt_bytes": expected_receipt_bytes == _pretty_json_bytes(expected),
        "repository": expected.get("repository") == repository,
        "pr_number": expected.get("pr_number") == pr_number,
        "causal_binding": expected_binding == fresh_binding and main_tip_binding,
        "diff_sha256": expected.get("diff_sha256") == hashlib.sha256(diff).hexdigest(),
        "diff_bytes": expected.get("diff_bytes") == len(diff),
        "stored_diff_bytes": expected_diff == diff,
        "evidence_fingerprint": expected.get("evidence_fingerprint") == fresh.get("evidence_fingerprint"),
        "receipt_payload_sha256": expected.get("receipt_payload_sha256") == fresh.get("receipt_payload_sha256"),
    }
    ledger_checks = (
        "expected_receipt_self_seal",
        "stored_receipt_parses_as_expected",
        "stored_receipt_bytes",
        "repository",
        "pr_number",
        "causal_binding",
        "diff_sha256",
        "diff_bytes",
        "stored_diff_bytes",
    )
    ledger_safe = all(checks[name] for name in ledger_checks)
    exact = ledger_safe and checks["evidence_fingerprint"] and checks["receipt_payload_sha256"]
    progress_successor = ledger_safe and not exact
    report = {
        "schema": "qikvrt_mesh_review_reobservation_v1",
        "state": (
            "EXACT_CURRENT"
            if exact
            else "PROGRESS_SUCCESSOR_OBSERVED"
            if progress_successor
            else "HOLD_UNVERIFIED"
        ),
        "exact": exact,
        "ledger_safe": ledger_safe,
        "progress_successor": progress_successor,
        "checks": checks,
        "expected_fingerprint": expected.get("evidence_fingerprint"),
        "observed_fingerprint": fresh.get("evidence_fingerprint"),
        "first_blocker": (
            None
            if exact
            else "WORKFLOW_PROGRESS_SUCCESSOR_REQUIRED"
            if progress_successor
            else "CAUSAL_REVIEW_EVIDENCE_DRIFT"
        ),
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
        },
    }
    return report, fresh, diff


def _load(path: str) -> Mapping[str, Any]:
    value = json.load(sys.stdin) if path == "-" else json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise ReviewSnapshotError("snapshot JSON must be an object")
    return value


def _json_argument(value: str, label: str, expected: type) -> Any:
    parsed = json.loads(value)
    if not isinstance(parsed, expected):
        raise ReviewObservationError(f"{label} has the wrong JSON type")
    return parsed


def _write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_pretty_json_bytes(value))


def _add_observation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr-number", required=True, type=int)
    parser.add_argument("--current-run-id", required=True, type=int)
    parser.add_argument("--required-gates-json", required=True)
    parser.add_argument("--required-gate-paths-json", required=True)
    parser.add_argument("--writer-workflows-json", required=True)
    parser.add_argument("--expected-head", default="")
    parser.add_argument("--event-context-file")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    evaluate_parser = commands.add_parser("evaluate")
    evaluate_parser.add_argument("--input", default="-")
    evaluate_parser.add_argument("--diff-file")
    observe_parser = commands.add_parser("observe")
    _add_observation_arguments(observe_parser)
    observe_parser.add_argument("--snapshot-out", required=True)
    observe_parser.add_argument("--diff-out", required=True)
    observe_parser.add_argument("--receipt-out", required=True)
    verify_parser = commands.add_parser("verify")
    _add_observation_arguments(verify_parser)
    verify_parser.add_argument("--receipt", required=True)
    verify_parser.add_argument("--expected-diff", required=True)
    verify_parser.add_argument("--output-dir", required=True)
    verify_parser.add_argument(
        "--mode",
        choices=("strict", "ledger-history"),
        default="strict",
        help="strict projection check or history-safe workflow-progress admission",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "evaluate":
            diff = pathlib.Path(args.diff_file).read_bytes() if args.diff_file else None
            result = evaluate(_load(args.input), diff)
            print(json.dumps(result, sort_keys=True, indent=2))
            return 0 if result.get("state") in {"WAIT", "APPROVE"} else 2

        required_gates = _json_argument(
            args.required_gates_json,
            "required-gates-json",
            list,
        )
        required_gate_paths = _json_argument(
            args.required_gate_paths_json,
            "required-gate-paths-json",
            dict,
        )
        writer_workflows = _json_argument(
            args.writer_workflows_json,
            "writer-workflows-json",
            list,
        )
        if args.command == "observe":
            event_context = _load(args.event_context_file) if args.event_context_file else None
            snapshot, diff = observe_repository(
                args.repository,
                args.pr_number,
                args.current_run_id,
                required_gates,
                required_gate_paths,
                writer_workflows,
                args.expected_head or None,
                event_context,
            )
            result = evaluate(snapshot, diff)
            _write_json(pathlib.Path(args.snapshot_out), snapshot)
            diff_path = pathlib.Path(args.diff_out)
            diff_path.parent.mkdir(parents=True, exist_ok=True)
            diff_path.write_bytes(diff)
            _write_json(pathlib.Path(args.receipt_out), result)
            print(json.dumps(result, sort_keys=True, indent=2))
            return 0

        expected_receipt_bytes = pathlib.Path(args.receipt).read_bytes()
        expected_value = json.loads(expected_receipt_bytes)
        if not isinstance(expected_value, Mapping):
            raise ReviewSnapshotError("receipt JSON must be an object")
        expected = expected_value
        expected_diff = pathlib.Path(args.expected_diff).read_bytes()
        report, fresh, diff = verify_current_receipt(
            expected,
            expected_receipt_bytes,
            expected_diff,
            args.repository,
            args.pr_number,
            args.current_run_id,
            required_gates,
            required_gate_paths,
            writer_workflows,
        )
        output = pathlib.Path(args.output_dir)
        _write_json(output / "review.json", fresh)
        (output / "review.diff").write_bytes(diff)
        _write_json(output / "verification.json", report)
        print(json.dumps(report, sort_keys=True, indent=2))
        accepted = report["exact"] or (
            args.mode == "ledger-history" and report["ledger_safe"]
        )
        return 0 if accepted else 3
    except (
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        ReviewSnapshotError,
        ReviewObservationError,
        subprocess.SubprocessError,
    ) as exc:
        result = _result(
            {},
            "COMMENT_WITH_BLOCKER",
            "INVALID_REVIEW_SNAPSHOT",
            str(exc),
            findings=[_finding("INVALID_REVIEW_SNAPSHOT", "BLOCK", str(exc))],
        )
        if getattr(args, "command", None) == "observe" and getattr(args, "receipt_out", None):
            _write_json(pathlib.Path(args.receipt_out), result)
        if getattr(args, "command", None) == "verify" and getattr(args, "output_dir", None):
            output = pathlib.Path(args.output_dir)
            _write_json(output / "verification.json", result)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 3


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
