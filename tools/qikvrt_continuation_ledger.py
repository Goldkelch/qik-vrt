#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Pure, append-only continuation-ledger primitives.

A continuation is a durable *logical obligation*, rather than a process which
may be allowed to run forever.  Its liveness therefore remains
``INDEFINITE_UNTIL_EVIDENCED_OUTCOME`` while worker, queue, liveness and
observation leases remain the responsibility of their separate controllers.

This module deliberately has no GitHub, Git, clock, or write capability.  A
workflow may use its deterministic record and append plan as the input to a
separately authorized fast-forward/CAS ledger writer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


RECORD_SCHEMA = "qikvrt_continuation_ledger_record_v1"
APPEND_PLAN_SCHEMA = "qikvrt_continuation_ledger_append_plan_v1"
LIVENESS = "INDEFINITE_UNTIL_EVIDENCED_OUTCOME"
LEDGER_ROOT = "state/mesh/continuations"

LIVE_STATES = frozenset({"LIVE", "REOBSERVE_PENDING"})
OUTCOME_STATES = frozenset(
    {"POSTCONDITION_OBSERVED", "REBOUND", "EXTERNAL_HOLD"}
)
ALL_STATES = LIVE_STATES | OUTCOME_STATES

# These names are observation transport, not causal identity.  Producers are
# still expected to supply a deliberately scoped semantic input.  The
# projection below protects the common reflexive failure mode where a status
# refresh, a polling timestamp, or a self-generated status comment accidentally
# becomes a fresh unit of work.
VOLATILE_SEMANTIC_FIELDS = frozenset(
    {
        "updated_at",
        "observed_at",
        "last_observed_at",
        "generated_at",
        "refreshed_at",
        "polled_at",
        "created_at",
        "started_at",
        "completed_at",
        "run_started_at",
        "dispatched_at",
        "dispatch_id",
        "workflow_dispatch_id",
        "refresh_id",
        "poll_id",
        "self_generated_status",
        "self_generated_status_id",
        "self_generated_status_update",
        "self_generated_comment",
        "self_generated_comment_id",
        "self_generated_comment_update",
    }
)


class ContinuationLedgerError(ValueError):
    """The supplied continuation record cannot be used fail-closed."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize exactly one canonical JSON value."""
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContinuationLedgerError(f"{label} must be an object")
    return value


def _string(value: Any, label: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value:
        raise ContinuationLedgerError(f"{label} must be a non-empty string")
    return value


def _sha1(value: Any, label: str, *, nullable: bool = True) -> str | None:
    text = _string(value, label, nullable=nullable)
    if text is None:
        return None
    if len(text) != 40 or any(character not in "0123456789abcdef" for character in text):
        raise ContinuationLedgerError(f"{label} must be a lowercase forty-character Git SHA")
    return text


def _sha256(value: Any, label: str) -> str:
    text = _string(value, label)
    assert text is not None
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ContinuationLedgerError(f"{label} must be a lowercase SHA-256 digest")
    return text


def _positive_integer(value: Any, label: str, *, nullable: bool = True) -> int | None:
    if value is None and nullable:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ContinuationLedgerError(f"{label} must be a positive integer")
    return value


def _safe_segment(value: str) -> str:
    """Avoid placing an untrusted subject identifier directly in a ledger path."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def semantic_projection(value: Any) -> Any:
    """Strip recursively volatile transport fields from causal input.

    Human review/comment content must be represented by a stable content hash in
    the caller's semantic input.  This function intentionally does *not* erase
    generic ``review_id`` or content hashes: those can be exact causal bindings.
    """
    if isinstance(value, Mapping):
        projected: dict[str, Any] = {}
        for raw_key, child in value.items():
            if not isinstance(raw_key, str):
                raise ContinuationLedgerError("semantic input keys must be strings")
            lowered = raw_key.lower()
            if lowered in VOLATILE_SEMANTIC_FIELDS or lowered.startswith("self_generated_"):
                continue
            projected[raw_key] = semantic_projection(child)
        return projected
    if isinstance(value, list):
        return [semantic_projection(item) for item in value]
    if isinstance(value, tuple):
        return [semantic_projection(item) for item in value]
    return value


def normalize_subject(value: Mapping[str, Any]) -> dict[str, str]:
    """Validate the stable object whose continuation is being tracked."""
    subject = _mapping(value, "subject")
    repository = _string(subject.get("repository"), "subject.repository")
    kind = _string(subject.get("kind"), "subject.kind")
    identifier = _string(subject.get("identifier"), "subject.identifier")
    assert repository is not None and kind is not None and identifier is not None
    if any(character in kind for character in "/\\\x00\n\r"):
        raise ContinuationLedgerError("subject.kind contains an unsafe character")
    return {
        "repository": repository,
        "kind": kind,
        "identifier": identifier,
    }


def normalize_binding(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate common exact-binding fields while permitting future extensions.

    Head and tree form a pair.  A subject which has no Git ref (for example an
    issue-only external admission hold) records both as null instead of
    inventing an exact tree.
    """
    binding = dict(_mapping(value, "binding"))
    allowed = {
        "ref",
        "head_sha",
        "tree_sha",
        "base_sha",
        "workflow_path",
        "workflow_blob_sha",
        "workflow_run_id",
        "workflow_run_attempt",
        "job_id",
        "review_id",
        "receipt_sha256",
        "source_event",
    }
    unknown = sorted(set(binding) - allowed)
    if unknown:
        raise ContinuationLedgerError(
            "binding contains unsupported field(s): " + ", ".join(unknown)
        )
    head = _sha1(binding.get("head_sha"), "binding.head_sha")
    tree = _sha1(binding.get("tree_sha"), "binding.tree_sha")
    if (head is None) != (tree is None):
        raise ContinuationLedgerError("binding.head_sha and binding.tree_sha must be present together")
    normalized = {
        "ref": _string(binding.get("ref"), "binding.ref", nullable=True),
        "head_sha": head,
        "tree_sha": tree,
        "base_sha": _sha1(binding.get("base_sha"), "binding.base_sha"),
        "workflow_path": _string(
            binding.get("workflow_path"), "binding.workflow_path", nullable=True
        ),
        "workflow_blob_sha": _sha1(
            binding.get("workflow_blob_sha"), "binding.workflow_blob_sha"
        ),
        "workflow_run_id": _positive_integer(
            binding.get("workflow_run_id"), "binding.workflow_run_id"
        ),
        "workflow_run_attempt": _positive_integer(
            binding.get("workflow_run_attempt"), "binding.workflow_run_attempt"
        ),
        "job_id": _positive_integer(binding.get("job_id"), "binding.job_id"),
        "review_id": _positive_integer(binding.get("review_id"), "binding.review_id"),
        "receipt_sha256": (
            _sha256(binding["receipt_sha256"], "binding.receipt_sha256")
            if binding.get("receipt_sha256") is not None
            else None
        ),
        "source_event": _string(
            binding.get("source_event"), "binding.source_event", nullable=True
        ),
    }
    if normalized["workflow_run_attempt"] is not None and normalized["workflow_run_id"] is None:
        raise ContinuationLedgerError(
            "binding.workflow_run_attempt requires binding.workflow_run_id"
        )
    if normalized["workflow_blob_sha"] is not None and normalized["workflow_path"] is None:
        raise ContinuationLedgerError(
            "binding.workflow_blob_sha requires binding.workflow_path"
        )
    return normalized


def normalize_source(value: Mapping[str, Any]) -> dict[str, str]:
    """Validate a compact immutable source reference retained in the ledger."""
    source = _mapping(value, "immutable source")
    uri = _string(source.get("uri"), "immutable source.uri")
    digest = _sha256(source.get("sha256"), "immutable source.sha256")
    assert uri is not None
    if set(source) != {"uri", "sha256"}:
        raise ContinuationLedgerError("immutable source must contain only uri and sha256")
    return {"uri": uri, "sha256": digest}


def normalize_wake_predicates(value: Sequence[Any]) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ContinuationLedgerError("wake predicates must be a non-empty list")
    predicates = []
    for item in value:
        predicate = _string(item, "wake predicate")
        assert predicate is not None
        predicates.append(predicate)
    if len(predicates) != len(set(predicates)):
        raise ContinuationLedgerError("wake predicates must not contain duplicates")
    return sorted(predicates)


def _completion_claims() -> dict[str, bool]:
    return {
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
        "MERGE": False,
        "SYNCHRONIZATION": False,
    }


def _identity_payload(
    subject: Mapping[str, Any],
    binding: Mapping[str, Any],
    semantic_input: Mapping[str, Any],
    first_blocker: str | None,
    next_action: str,
    wake_predicates: Sequence[str],
) -> dict[str, Any]:
    return {
        "subject": dict(subject),
        "binding": dict(binding),
        "semantic_input": semantic_projection(semantic_input),
        "first_blocker": first_blocker,
        "next_action": next_action,
        "wake_predicates": list(wake_predicates),
    }


def continuation_key(
    *,
    subject: Mapping[str, Any],
    binding: Mapping[str, Any],
    semantic_input: Mapping[str, Any],
    first_blocker: str | None,
    next_action: str,
    wake_predicates: Sequence[Any],
) -> str:
    """Return the exact-binding key for one logical continuation."""
    normalized_subject = normalize_subject(subject)
    normalized_binding = normalize_binding(binding)
    _mapping(semantic_input, "semantic input")
    normalized_blocker = _string(first_blocker, "first blocker", nullable=True)
    normalized_action = _string(next_action, "next action")
    assert normalized_action is not None
    normalized_wakes = normalize_wake_predicates(wake_predicates)
    return sha256_json(
        _identity_payload(
            normalized_subject,
            normalized_binding,
            semantic_input,
            normalized_blocker,
            normalized_action,
            normalized_wakes,
        )
    )


def _record_id(continuation: str, state: str, outcome: Mapping[str, Any] | None) -> str:
    return sha256_json(
        {
            "continuation_key": continuation,
            "state": state,
            "outcome": dict(outcome) if outcome is not None else None,
        }
    )


def build_live_record(
    *,
    subject: Mapping[str, Any],
    binding: Mapping[str, Any],
    semantic_input: Mapping[str, Any],
    first_blocker: str | None,
    next_action: str,
    wake_predicates: Sequence[Any],
    immutable_source: Mapping[str, Any],
    state: str = "LIVE",
    predecessor_continuation_key: str | None = None,
    observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an indefinitely live continuation record without any clock input."""
    if state not in LIVE_STATES:
        raise ContinuationLedgerError("live continuation state is invalid")
    normalized_subject = normalize_subject(subject)
    normalized_binding = normalize_binding(binding)
    semantic = semantic_projection(_mapping(semantic_input, "semantic input"))
    normalized_blocker = _string(first_blocker, "first blocker", nullable=True)
    normalized_action = _string(next_action, "next action")
    assert normalized_action is not None
    normalized_wakes = normalize_wake_predicates(wake_predicates)
    source = normalize_source(immutable_source)
    if predecessor_continuation_key is not None:
        _sha256(predecessor_continuation_key, "predecessor continuation key")
    if observation is not None:
        _mapping(observation, "observation")

    key = continuation_key(
        subject=normalized_subject,
        binding=normalized_binding,
        semantic_input=semantic,
        first_blocker=normalized_blocker,
        next_action=normalized_action,
        wake_predicates=normalized_wakes,
    )
    record = {
        "schema": RECORD_SCHEMA,
        "record_id": _record_id(key, state, None),
        "continuation_key": key,
        "state": state,
        "liveness": LIVENESS,
        "subject": normalized_subject,
        "binding": normalized_binding,
        "semantic_input": semantic,
        "semantic_fingerprint": sha256_json(
            {
                "semantic_input": semantic,
                "first_blocker": normalized_blocker,
                "next_action": normalized_action,
                "wake_predicates": normalized_wakes,
            }
        ),
        "first_blocker": normalized_blocker,
        "next_action": normalized_action,
        "wake_predicates": normalized_wakes,
        "immutable_source": source,
        "predecessor_continuation_key": predecessor_continuation_key,
        "outcome": None,
        "observation": dict(observation) if observation is not None else {},
        "completion_claims": _completion_claims(),
    }
    validate_record(record)
    return record


def build_outcome_record(
    predecessor: Mapping[str, Any],
    *,
    state: str,
    immutable_source: Mapping[str, Any],
    postcondition: str | None = None,
    replacement_continuation_key: str | None = None,
    external_authority: str | None = None,
    external_reason: str | None = None,
    observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Append one directly evidenced outcome for an existing live record."""
    previous = dict(_mapping(predecessor, "predecessor record"))
    validate_record(previous)
    if previous["state"] not in LIVE_STATES:
        raise ContinuationLedgerError("only a live continuation may receive an outcome")
    if state not in OUTCOME_STATES:
        raise ContinuationLedgerError("continuation outcome state is invalid")
    source = normalize_source(immutable_source)
    if observation is not None:
        _mapping(observation, "observation")

    outcome: dict[str, Any]
    if state == "POSTCONDITION_OBSERVED":
        condition = _string(postcondition, "postcondition")
        assert condition is not None
        if any(value is not None for value in (replacement_continuation_key, external_authority, external_reason)):
            raise ContinuationLedgerError("postcondition outcome has incompatible fields")
        outcome = {"postcondition": condition}
    elif state == "REBOUND":
        replacement = _sha256(
            replacement_continuation_key, "replacement continuation key"
        )
        if any(value is not None for value in (postcondition, external_authority, external_reason)):
            raise ContinuationLedgerError("rebound outcome has incompatible fields")
        outcome = {"replacement_continuation_key": replacement}
    else:
        authority = _string(external_authority, "external hold authority")
        reason = _string(external_reason, "external hold reason")
        assert authority is not None and reason is not None
        if any(value is not None for value in (postcondition, replacement_continuation_key)):
            raise ContinuationLedgerError("external hold outcome has incompatible fields")
        outcome = {"authority": authority, "reason": reason}

    record = {
        **{
            key: value
            for key, value in previous.items()
            if key not in {"record_id", "state", "immutable_source", "outcome", "observation"}
        },
        "record_id": _record_id(previous["continuation_key"], state, outcome),
        "state": state,
        "immutable_source": source,
        "outcome": outcome,
        "observation": dict(observation) if observation is not None else {},
        "predecessor_record_id": previous["record_id"],
    }
    validate_record(record)
    return record


def rebind_record(
    predecessor: Mapping[str, Any],
    *,
    binding: Mapping[str, Any],
    semantic_input: Mapping[str, Any],
    first_blocker: str | None,
    next_action: str,
    wake_predicates: Sequence[Any],
    immutable_source: Mapping[str, Any],
    observation: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a stale predecessor outcome and its new exact-binding successor."""
    previous = dict(_mapping(predecessor, "predecessor record"))
    validate_record(previous)
    successor = build_live_record(
        subject=_mapping(previous["subject"], "predecessor subject"),
        binding=binding,
        semantic_input=semantic_input,
        first_blocker=first_blocker,
        next_action=next_action,
        wake_predicates=wake_predicates,
        immutable_source=immutable_source,
        predecessor_continuation_key=previous["continuation_key"],
        observation=observation,
    )
    if successor["continuation_key"] == previous["continuation_key"]:
        raise ContinuationLedgerError("rebound successor must have a changed exact semantic binding")
    stale = build_outcome_record(
        previous,
        state="REBOUND",
        immutable_source=immutable_source,
        replacement_continuation_key=successor["continuation_key"],
        observation=observation,
    )
    return stale, successor


def ledger_path(record: Mapping[str, Any]) -> str:
    """Return the deterministic, append-only path for an immutable record."""
    value = dict(_mapping(record, "record"))
    validate_record(value)
    subject = _mapping(value["subject"], "record subject")
    kind = _string(subject.get("kind"), "record subject.kind")
    identifier = _string(subject.get("identifier"), "record subject.identifier")
    assert kind is not None and identifier is not None
    return "/".join(
        (
            LEDGER_ROOT,
            kind.lower(),
            _safe_segment(identifier),
            value["continuation_key"],
            value["record_id"] + ".json",
        )
    )


def plan_append(
    *,
    ledger_head: str | None,
    path: str,
    existing_record_bytes: bytes | None,
    record_bytes: bytes,
) -> dict[str, Any]:
    """Plan one append-only CAS transition without executing it.

    A caller supplies bytes observed at the exact target path on ``ledger_head``.
    The plan never authorizes force or an overwrite of non-identical bytes.
    """
    if ledger_head is not None:
        _sha1(ledger_head, "ledger head", nullable=False)
    if not isinstance(path, str) or not path.startswith(LEDGER_ROOT + "/") or ".." in Path(path).parts:
        raise ContinuationLedgerError("ledger path is outside the continuation ledger root")
    if not isinstance(record_bytes, bytes) or not record_bytes:
        raise ContinuationLedgerError("record bytes are unavailable")
    if existing_record_bytes is not None and not isinstance(existing_record_bytes, bytes):
        raise ContinuationLedgerError("existing record bytes must be bytes or null")
    if ledger_head is None:
        if existing_record_bytes is not None:
            raise ContinuationLedgerError("orphan ledger root cannot have existing record bytes")
        action = "INITIALIZE_ORPHAN_ROOT"
        blocker = None
    elif existing_record_bytes is None:
        action = "APPEND_FAST_FORWARD"
        blocker = None
    elif existing_record_bytes == record_bytes:
        action = "NOOP_IDENTICAL_RECORD"
        blocker = None
    else:
        action = "HOLD"
        blocker = "APPEND_ONLY_LEDGER_PATH_COLLISION"
    return {
        "schema": APPEND_PLAN_SCHEMA,
        "path": path,
        "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "parent": ledger_head,
        "action": action,
        "force": False,
        "first_blocker": blocker,
        "completion_claims": _completion_claims(),
    }


def validate_record(value: Mapping[str, Any]) -> None:
    """Fail closed unless a record reproduces its canonical exact identity."""
    record = dict(_mapping(value, "record"))
    required = {
        "schema",
        "record_id",
        "continuation_key",
        "state",
        "liveness",
        "subject",
        "binding",
        "semantic_input",
        "semantic_fingerprint",
        "first_blocker",
        "next_action",
        "wake_predicates",
        "immutable_source",
        "predecessor_continuation_key",
        "outcome",
        "observation",
        "completion_claims",
    }
    optional = {"predecessor_record_id"}
    if set(record) - optional != required:
        raise ContinuationLedgerError("continuation record fields are invalid")
    if record.get("schema") != RECORD_SCHEMA:
        raise ContinuationLedgerError("continuation record schema is invalid")
    state = record.get("state")
    if state not in ALL_STATES:
        raise ContinuationLedgerError("continuation record state is invalid")
    if record.get("liveness") != LIVENESS:
        raise ContinuationLedgerError("continuation record liveness is invalid")
    subject = normalize_subject(_mapping(record.get("subject"), "record subject"))
    binding = normalize_binding(_mapping(record.get("binding"), "record binding"))
    semantic = semantic_projection(_mapping(record.get("semantic_input"), "record semantic input"))
    if semantic != record.get("semantic_input"):
        raise ContinuationLedgerError("continuation semantic input contains volatile metadata")
    blocker = _string(record.get("first_blocker"), "record first blocker", nullable=True)
    action = _string(record.get("next_action"), "record next action")
    assert action is not None
    wakes = normalize_wake_predicates(record.get("wake_predicates"))
    source = normalize_source(_mapping(record.get("immutable_source"), "record source"))
    key = continuation_key(
        subject=subject,
        binding=binding,
        semantic_input=semantic,
        first_blocker=blocker,
        next_action=action,
        wake_predicates=wakes,
    )
    if record.get("continuation_key") != key:
        raise ContinuationLedgerError("continuation key does not match exact binding")
    _sha256(record.get("record_id"), "record id")
    semantic_fingerprint = sha256_json(
        {
            "semantic_input": semantic,
            "first_blocker": blocker,
            "next_action": action,
            "wake_predicates": wakes,
        }
    )
    if record.get("semantic_fingerprint") != semantic_fingerprint:
        raise ContinuationLedgerError("semantic fingerprint does not match continuation input")
    predecessor_key = record.get("predecessor_continuation_key")
    if predecessor_key is not None:
        _sha256(predecessor_key, "predecessor continuation key")
    if not isinstance(record.get("observation"), Mapping):
        raise ContinuationLedgerError("record observation must be an object")
    if record.get("completion_claims") != _completion_claims():
        raise ContinuationLedgerError("continuation completion claims are invalid")

    outcome = record.get("outcome")
    if state in LIVE_STATES:
        if outcome is not None or "predecessor_record_id" in record:
            raise ContinuationLedgerError("live continuation cannot carry an outcome")
        expected_id = _record_id(key, state, None)
    else:
        if not isinstance(outcome, Mapping):
            raise ContinuationLedgerError("outcome continuation must carry an outcome object")
        predecessor_record_id = record.get("predecessor_record_id")
        _sha256(predecessor_record_id, "predecessor record id")
        if state == "POSTCONDITION_OBSERVED":
            if set(outcome) != {"postcondition"}:
                raise ContinuationLedgerError("postcondition outcome fields are invalid")
            _string(outcome.get("postcondition"), "postcondition")
        elif state == "REBOUND":
            if set(outcome) != {"replacement_continuation_key"}:
                raise ContinuationLedgerError("rebound outcome fields are invalid")
            _sha256(outcome.get("replacement_continuation_key"), "replacement continuation key")
        else:
            if set(outcome) != {"authority", "reason"}:
                raise ContinuationLedgerError("external hold outcome requires authority and reason")
            _string(outcome.get("authority"), "external hold authority")
            _string(outcome.get("reason"), "external hold reason")
        expected_id = _record_id(key, state, outcome)
    if record.get("record_id") != expected_id:
        raise ContinuationLedgerError("record id does not match immutable continuation event")
    # Avoid silently accepting a malformed source after only checking that it is
    # present; normalize_source's return value also verifies exact field shape.
    if source != record.get("immutable_source"):
        raise ContinuationLedgerError("immutable source is not canonical")


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(path.read_text(encoding="utf-8")), label)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContinuationLedgerError(f"cannot load {label}: {exc}") from exc


def _parse_json_argument(value: str, label: str) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(value), label)
    except json.JSONDecodeError as exc:
        raise ContinuationLedgerError(f"{label} is not JSON: {exc}") from exc


def _emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build-live")
    for argument in ("subject", "binding", "semantic-input", "source"):
        build.add_argument(f"--{argument}", required=True)
    build.add_argument("--first-blocker")
    build.add_argument("--next-action", required=True)
    build.add_argument("--wake-predicates", required=True)
    build.add_argument("--state", choices=sorted(LIVE_STATES), default="LIVE")
    build.add_argument("--predecessor-continuation-key")
    check = commands.add_parser("check")
    check.add_argument("--record", type=Path, required=True)
    path = commands.add_parser("path")
    path.add_argument("--record", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "build-live":
            predicates = json.loads(arguments.wake_predicates)
            value = build_live_record(
                subject=_parse_json_argument(arguments.subject, "subject"),
                binding=_parse_json_argument(arguments.binding, "binding"),
                semantic_input=_parse_json_argument(arguments.semantic_input, "semantic input"),
                first_blocker=arguments.first_blocker,
                next_action=arguments.next_action,
                wake_predicates=predicates,
                immutable_source=_parse_json_argument(arguments.source, "source"),
                state=arguments.state,
                predecessor_continuation_key=arguments.predecessor_continuation_key,
            )
            _emit(value)
        else:
            record = _load_json(arguments.record, "record")
            validate_record(record)
            if arguments.command == "path":
                print(ledger_path(record))
        return 0
    except (ContinuationLedgerError, TypeError, json.JSONDecodeError) as exc:
        print(f"BLOCK CONTINUATION_LEDGER {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
