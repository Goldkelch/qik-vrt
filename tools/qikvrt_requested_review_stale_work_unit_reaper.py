# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed recovery for stale and orphaned requested-review work units.

The active-run classifier preserves the existing stale recursive transport
contract.  The durable-queue helpers additionally consume the append-only Mesh
review ledger from a local Git checkout, so queue recovery does not hydrate
every receipt and diff packet through the GitHub Installation API.

Only an exact live, unacknowledged queue intent can be dispatched.  Native
``pull_request_target`` observations remain outside the cancellation path.
"""
from __future__ import annotations

import json
import pathlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from tools.qikvrt_requested_review_executor import (
    REVIEW_QUEUE_ACK_ROOT,
    REVIEW_QUEUE_ROOT,
    ReviewSnapshotError,
    _canonical_sha256,
    _pretty_json_bytes,
    latest_status_matches_projection,
    reassemble_diff_transport,
    review_queue_intent,
)

_TITLE = re.compile(
    r"^QIKVRT requested review pr=(?P<pr>[1-9][0-9]*) "
    r"head=(?P<head>[0-9a-f]{40}) fp=(?P<fingerprint>[0-9a-f]{64})$"
)
_CANCELLABLE_ACTIVE = {"pending", "queued", "requested", "waiting"}
_WRITER_ACTIVE = _CANCELLABLE_ACTIVE | {"in_progress"}
_STATUS_CONTEXT = "QIKVRT requested review execution"


class RecursiveQueueEvidenceError(ValueError):
    """Durable recursive queue evidence is malformed or incomplete."""


def classify_run(run: dict[str, Any], pr: dict[str, Any], current_main_sha: str) -> dict[str, Any]:
    """Return a deterministic cancellation disposition for one queued child."""
    result: dict[str, Any] = {
        "state": "KEEP",
        "cancel": False,
        "first_blocker": None,
        "next_action": "NOOP",
    }
    if run.get("event") != "workflow_dispatch" or run.get("status") not in _CANCELLABLE_ACTIVE:
        return result

    match = _TITLE.fullmatch(str(run.get("display_title") or ""))
    if match is None:
        return {
            **result,
            "state": "HOLD_UNVERIFIED",
            "first_blocker": "RECURSIVE_WORK_UNIT_TITLE_UNBOUND",
            "next_action": "PRESERVE_FAIL_CLOSED_WITHOUT_CANCELLATION",
        }

    queued_pr = int(match.group("pr"))
    queued_head = match.group("head")
    live_number = pr.get("number")
    live_state = pr.get("state")
    live_head = (pr.get("head") or {}).get("sha")
    live_base = (pr.get("base") or {}).get("sha")

    if live_number != queued_pr:
        return {
            **result,
            "state": "HOLD_UNVERIFIED",
            "first_blocker": "RECURSIVE_WORK_UNIT_PR_IDENTITY_MISMATCH",
            "next_action": "PRESERVE_FAIL_CLOSED_WITHOUT_CANCELLATION",
        }
    if live_state != "open" or live_head != queued_head:
        return {
            **result,
            "state": "STALE_WORK_UNIT",
            "cancel": True,
            "first_blocker": "STALE_HEAD",
            "next_action": "CANCEL_STALE_RECURSIVE_TRANSPORT_ONLY",
        }
    if live_base != current_main_sha:
        return {
            **result,
            "state": "STALE_WORK_UNIT",
            "cancel": True,
            "first_blocker": "BASE_DRIFT",
            "next_action": "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN",
        }
    return result


def _ledger_file(ledger_root: pathlib.Path, relative_path: Any) -> pathlib.Path:
    if not isinstance(relative_path, str) or not relative_path:
        raise RecursiveQueueEvidenceError("ledger path is missing")
    pure = pathlib.PurePosixPath(relative_path)
    if pure.is_absolute() or ".." in pure.parts:
        raise RecursiveQueueEvidenceError(f"ledger path escapes root: {relative_path}")
    candidate = ledger_root.joinpath(*pure.parts)
    try:
        candidate.resolve().relative_to(ledger_root.resolve())
    except ValueError as error:
        raise RecursiveQueueEvidenceError(
            f"ledger path escapes root: {relative_path}"
        ) from error
    if not candidate.is_file():
        raise RecursiveQueueEvidenceError(f"ledger file is missing: {relative_path}")
    return candidate


def _json_object(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RecursiveQueueEvidenceError(f"invalid JSON evidence: {path}") from error
    if not isinstance(value, dict):
        raise RecursiveQueueEvidenceError(f"JSON evidence is not an object: {path}")
    return value


def _validate_intent_shape(intent: Mapping[str, Any], repository: str) -> None:
    required = {
        "schema",
        "work_unit_id",
        "repository",
        "pr_number",
        "head_sha",
        "tree_sha",
        "base_sha",
        "predecessor_fingerprint",
        "successor_fingerprint",
        "receipt_path",
        "diff_path",
        "state",
        "completion_claims",
    }
    if set(intent) != required:
        raise RecursiveQueueEvidenceError("recursive queue intent fields are invalid")
    number = intent.get("pr_number")
    head = intent.get("head_sha")
    tree = intent.get("tree_sha")
    base = intent.get("base_sha")
    predecessor = intent.get("predecessor_fingerprint")
    successor = intent.get("successor_fingerprint")
    if (
        intent.get("schema") != "qikvrt_mesh_review_queue_intent_v1"
        or intent.get("repository") != repository
        or isinstance(number, bool)
        or not isinstance(number, int)
        or number < 1
        or not isinstance(head, str)
        or len(head) != 40
        or not isinstance(tree, str)
        or len(tree) != 40
        or not isinstance(base, str)
        or len(base) != 40
        or not isinstance(predecessor, str)
        or len(predecessor) != 64
        or not isinstance(successor, str)
        or len(successor) != 64
        or any(
            ch not in "0123456789abcdef"
            for value in (head, tree, base, predecessor, successor)
            for ch in value
        )
    ):
        raise RecursiveQueueEvidenceError("recursive queue intent identity is invalid")
    if intent.get("work_unit_id") != f"pr-{number}/{head}/{successor}":
        raise RecursiveQueueEvidenceError("recursive queue work-unit identity is invalid")
    if intent.get("state") != "QUEUED_RECURSIVE_REOBSERVATION":
        raise RecursiveQueueEvidenceError("recursive queue state is invalid")
    if intent.get("completion_claims") != {
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
        "MERGE": False,
    }:
        raise RecursiveQueueEvidenceError("recursive queue claims are invalid")
    for field in ("receipt_path", "diff_path"):
        if not isinstance(intent.get(field), str) or not intent.get(field):
            raise RecursiveQueueEvidenceError(
                f"recursive queue {field} is invalid"
            )


def _validate_ack(intent: Mapping[str, Any], ack: Mapping[str, Any]) -> None:
    required = {
        "schema",
        "work_unit_id",
        "repository",
        "pr_number",
        "head_sha",
        "predecessor_fingerprint",
        "successor_fingerprint",
        "state",
        "completion_claims",
    }
    if set(ack) != required:
        raise RecursiveQueueEvidenceError("recursive queue acknowledgement fields are invalid")
    if (
        ack.get("schema") != "qikvrt_mesh_review_queue_ack_v1"
        or ack.get("repository") != intent.get("repository")
        or ack.get("pr_number") != intent.get("pr_number")
        or ack.get("head_sha") != intent.get("head_sha")
        or ack.get("predecessor_fingerprint") != intent.get("successor_fingerprint")
        or ack.get("work_unit_id")
        != f"pr-{intent.get('pr_number')}/{intent.get('head_sha')}/"
        f"{intent.get('successor_fingerprint')}"
        or ack.get("state") != "SUPERSEDED_BY_CAUSAL_REOBSERVATION"
    ):
        raise RecursiveQueueEvidenceError("recursive queue acknowledgement binding is invalid")
    successor = ack.get("successor_fingerprint")
    if (
        not isinstance(successor, str)
        or len(successor) != 64
        or any(ch not in "0123456789abcdef" for ch in successor)
    ):
        raise RecursiveQueueEvidenceError("recursive queue acknowledgement successor is invalid")
    claims = ack.get("completion_claims")
    if claims != {
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
        "MERGE": False,
    }:
        raise RecursiveQueueEvidenceError("recursive queue acknowledgement claims are invalid")


def _validate_queue_intent(
    ledger_root: pathlib.Path,
    queue_path: pathlib.Path,
    intent: Mapping[str, Any],
    repository: str,
) -> dict[str, Any]:
    receipt_path = intent.get("receipt_path")
    receipt_file = _ledger_file(ledger_root, receipt_path)
    receipt_bytes = receipt_file.read_bytes()
    receipt = _json_object(receipt_file)
    if receipt_bytes != _pretty_json_bytes(receipt):
        raise RecursiveQueueEvidenceError("recursive queue receipt bytes are non-canonical")

    payload = dict(receipt)
    claimed_payload = payload.pop("receipt_payload_sha256", None)
    if claimed_payload != _canonical_sha256(payload):
        raise RecursiveQueueEvidenceError("recursive queue receipt payload digest mismatch")

    expected_path, expected_intent = review_queue_intent(
        receipt,
        str(intent.get("predecessor_fingerprint") or ""),
    )
    relative_queue_path = queue_path.relative_to(ledger_root).as_posix()
    if relative_queue_path != expected_path or dict(intent) != expected_intent:
        raise RecursiveQueueEvidenceError("recursive queue intent binding mismatch")
    if intent.get("repository") != repository:
        raise RecursiveQueueEvidenceError("recursive queue repository mismatch")

    manifest_path = intent.get("diff_path")
    manifest_file = _ledger_file(ledger_root, manifest_path)
    manifest_bytes = manifest_file.read_bytes()
    manifest = _json_object(manifest_file)
    if manifest_bytes != _pretty_json_bytes(manifest):
        raise RecursiveQueueEvidenceError("recursive queue diff manifest is non-canonical")
    if manifest != receipt.get("diff_transport"):
        raise RecursiveQueueEvidenceError("recursive queue diff manifest binding mismatch")

    declared_packets = manifest.get("packets")
    if not isinstance(declared_packets, list):
        raise RecursiveQueueEvidenceError("recursive queue diff packets are unavailable")
    packets: list[bytes] = []
    for packet in declared_packets:
        if not isinstance(packet, Mapping):
            raise RecursiveQueueEvidenceError("recursive queue diff packet declaration is invalid")
        packets.append(_ledger_file(ledger_root, packet.get("path")).read_bytes())
    diff = reassemble_diff_transport(manifest, packets)
    if receipt.get("diff_sha256") != manifest.get("sha256"):
        raise RecursiveQueueEvidenceError("recursive queue diff digest binding mismatch")
    if receipt.get("diff_bytes") != len(diff):
        raise RecursiveQueueEvidenceError("recursive queue diff byte-count binding mismatch")
    return receipt


def load_unacknowledged_queue(
    ledger_root: pathlib.Path | str,
    repository: str,
    *,
    limit: int = 16,
) -> list[dict[str, Any]]:
    """Return a bounded, validated list of unacknowledged durable work units."""
    root = pathlib.Path(ledger_root)
    if not isinstance(repository, str) or repository.count("/") != 1:
        raise RecursiveQueueEvidenceError("repository identity is invalid")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise RecursiveQueueEvidenceError("queue scan limit is invalid")

    queue_root = root / REVIEW_QUEUE_ROOT
    if not queue_root.is_dir():
        return []

    result: list[dict[str, Any]] = []
    for queue_path in sorted(queue_root.rglob("*.json")):
        intent = _json_object(queue_path)
        _validate_intent_shape(intent, repository)
        ack_relative = (
            f"{REVIEW_QUEUE_ACK_ROOT}/pr-{intent['pr_number']}/"
            f"{intent['head_sha']}/{intent['successor_fingerprint']}.json"
        )
        ack_path = root.joinpath(*pathlib.PurePosixPath(ack_relative).parts)
        if ack_path.exists():
            ack_bytes = ack_path.read_bytes()
            ack = _json_object(ack_path)
            if ack_bytes != _pretty_json_bytes(ack):
                raise RecursiveQueueEvidenceError(
                    "recursive queue acknowledgement bytes are non-canonical"
                )
            _validate_ack(intent, ack)
            continue

        receipt = _validate_queue_intent(root, queue_path, intent, repository)
        expected_state = (
            "success"
            if receipt.get("state") == "APPROVE"
            else "pending"
            if receipt.get("state") == "WAIT"
            else "failure"
        )
        result.append(
            {
                "queue_path": queue_path.relative_to(root).as_posix(),
                "ack_path": ack_relative,
                "intent": dict(intent),
                "expected_status_state": expected_state,
            }
        )
        if len(result) >= limit:
            break
    return result


def classify_queue_work_unit(
    work_unit: Mapping[str, Any],
    pr: Mapping[str, Any],
    current_main_sha: str,
    statuses: Sequence[Mapping[str, Any]],
    active_runs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify one locally validated queue intent for one exact dispatch."""
    intent = work_unit.get("intent")
    if not isinstance(intent, Mapping):
        raise RecursiveQueueEvidenceError("queue work unit intent is missing")
    expected_state = work_unit.get("expected_status_state")
    if expected_state not in {"success", "pending", "failure"}:
        raise RecursiveQueueEvidenceError("queue work unit status projection is invalid")

    result: dict[str, Any] = {
        "state": "KEEP",
        "d0": 0,
        "dispatch": False,
        "first_blocker": None,
        "next_action": "NOOP",
        "pr_number": intent.get("pr_number"),
        "head_sha": intent.get("head_sha"),
        "fingerprint": intent.get("successor_fingerprint"),
    }
    if pr.get("number") != intent.get("pr_number"):
        return {
            **result,
            "state": "HOLD_UNVERIFIED",
            "d0": 1,
            "first_blocker": "RECURSIVE_QUEUE_PR_IDENTITY_MISMATCH",
            "next_action": "PRESERVE_FAIL_CLOSED_WITHOUT_DISPATCH",
        }

    live_head = (pr.get("head") or {}).get("sha")
    live_base = (pr.get("base") or {}).get("sha")
    if pr.get("state") != "open" or live_head != intent.get("head_sha"):
        return {
            **result,
            "state": "STALE_QUEUE_WORK_UNIT",
            "first_blocker": "STALE_HEAD",
            "next_action": "AWAIT_CAUSAL_QUEUE_SUPERSESSION",
        }
    if live_base != current_main_sha or live_base != intent.get("base_sha"):
        return {
            **result,
            "state": "STALE_QUEUE_WORK_UNIT",
            "first_blocker": "BASE_DRIFT",
            "next_action": "HISTORY_PRESERVING_REBIND_TO_CURRENT_MAIN",
        }

    if latest_status_matches_projection(
        statuses,
        _STATUS_CONTEXT,
        expected_state,
        str(intent.get("successor_fingerprint") or ""),
    ):
        return {
            **result,
            "state": "ALREADY_PROJECTED",
            "next_action": "AWAIT_DURABLE_QUEUE_ACK",
        }

    active = [
        int(run["id"])
        for run in active_runs
        if run.get("status") in _WRITER_ACTIVE and isinstance(run.get("id"), int)
    ]
    if active:
        return {
            **result,
            "state": "HOLD",
            "d0": 1,
            "first_blocker": "REQUESTED_REVIEW_WRITER_ACTIVE",
            "next_action": "REOBSERVE_ON_EXECUTOR_COMPLETION_INTERRUPT",
            "active_run_ids": active,
        }

    return {
        **result,
        "state": "REOBSERVE",
        "d0": 2,
        "dispatch": True,
        "next_action": "DISPATCH_ONE_EXACT_DURABLE_REVIEW_WORK_UNIT",
    }
