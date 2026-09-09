#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Maintain an append-only exact-effect ledger for the ruleset control plane.

The ruleset workflow intentionally never retries a privileged PUT or POST.
That makes a later transport or observation failure meaningful: an observer
must retain the fact that the effect was attempted even when it cannot prove
the final server state.  This utility gives every workflow step one strict,
shared ledger format instead of letting later HOLD receipts replace that
history with a fresh ``mutation=NONE`` default.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile
from collections.abc import Mapping, Sequence
from typing import Any


SCHEMA = "qikvrt_effect_attempts_v1"
OUTCOMES = frozenset(
    {
        "ACKED",
        "ATTEMPTED_PENDING_READBACK",
        "OBSERVED_READBACK",
        "UNCONFIRMED_RATE_LIMIT",
        "UNCONFIRMED_TRANSPORT_FAILED",
        "UNCONFIRMED_READBACK_FAILED",
        "UNCONFIRMED_NOT_CURRENT",
        "UNCONFIRMED_RESPONSE_MALFORMED",
    }
)


class EffectAttemptError(ValueError):
    """The durable effect evidence was malformed or semantically impossible."""


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise EffectAttemptError(f"{label} must be an object")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise EffectAttemptError(f"{label} must be a boolean")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise EffectAttemptError(f"{label} must be a non-empty string")
    return value


def _attempt(value: Any) -> dict[str, Any]:
    raw = _mapping(value, "effect attempt")
    kind = _text(raw.get("kind"), "effect attempt kind")
    endpoint = _text(raw.get("endpoint_or_subject"), "effect attempt endpoint_or_subject")
    mutation = _text(raw.get("mutation"), "effect attempt mutation")
    attempted = _boolean(
        raw.get("effect_transport_attempted"), "effect attempt effect_transport_attempted"
    )
    outcome = _text(raw.get("transport_outcome"), "effect attempt transport_outcome")
    if outcome not in OUTCOMES:
        raise EffectAttemptError(f"effect attempt transport_outcome is not admitted: {outcome}")
    observed = _boolean(raw.get("effect_observed"), "effect attempt effect_observed")
    evidence_ref = _text(raw.get("evidence_ref"), "effect attempt evidence_ref")
    if not attempted:
        if outcome != "OBSERVED_READBACK" or not observed or mutation != "NONE":
            raise EffectAttemptError(
                "a non-transport effect entry must be an observed readback with mutation=NONE"
            )
    elif outcome == "OBSERVED_READBACK":
        raise EffectAttemptError("an effect transport attempt cannot use OBSERVED_READBACK")
    return {
        "kind": kind,
        "endpoint_or_subject": endpoint,
        "mutation": mutation,
        "effect_transport_attempted": attempted,
        "transport_outcome": outcome,
        "effect_observed": observed,
        "evidence_ref": evidence_ref,
    }


def read_attempts(path: pathlib.Path) -> list[dict[str, Any]]:
    """Read a complete validated ledger; a missing ledger means no effect yet."""

    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise EffectAttemptError("effect attempts ledger must be a JSON array")
    return [_attempt(item) for item in raw]


def write_attempts(path: pathlib.Path, attempts: Sequence[Mapping[str, Any]]) -> None:
    normalized = [_attempt(item) for item in attempts]
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=path.name + ".",
        suffix=".tmp",
    )
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(canonical_bytes(normalized))
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)


def create_empty_ledger(path: pathlib.Path) -> None:
    """Create the per-run ledger exactly once before any privileged effect."""

    if path.exists():
        raise EffectAttemptError("effect attempts ledger already exists; creation may not replace history")
    write_attempts(path, [])


def append_attempt(ledger_path: pathlib.Path, attempt: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Append exactly one validated observation without replacing prior effects."""

    attempts = read_attempts(ledger_path)
    attempts.append(_attempt(attempt))
    write_attempts(ledger_path, attempts)
    return attempts


def summary(attempts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    normalized = [_attempt(item) for item in attempts]
    transport_attempts = [item for item in normalized if item["effect_transport_attempted"]]
    latest = transport_attempts[-1] if transport_attempts else None
    return {
        "schema": SCHEMA,
        "effect_transport_attempted": bool(transport_attempts),
        "effect_observed": any(bool(item["effect_observed"]) for item in normalized),
        "mutation": latest["mutation"] if latest is not None else "NONE",
        "latest_transport_outcome": latest["transport_outcome"] if latest is not None else "NONE",
    }


def select_latest_status_id(
    snapshot: Any,
    *,
    sha: str,
    context: str,
    state: str,
) -> int | None:
    """Return a remotely observed status only when it is the latest context state.

    ``gh api --paginate --slurp`` produces an array of pages.  Selecting any
    historical matching state would be unsafe: a newer status with the same
    context may have superseded it.  The exact idempotence predicate is the
    newest entry for ``(sha, context)`` and its requested state.
    """

    if not isinstance(snapshot, list):
        raise EffectAttemptError("paginated status readback must be an array of pages")
    matching: list[Mapping[str, Any]] = []
    for page in snapshot:
        if not isinstance(page, list):
            raise EffectAttemptError("paginated status readback page must be an array")
        for item in page:
            raw = _mapping(item, "status readback entry")
            if raw.get("sha") != sha or raw.get("context") != context:
                continue
            status_id = raw.get("id")
            if isinstance(status_id, bool) or not isinstance(status_id, int) or status_id <= 0:
                raise EffectAttemptError("matching status readback id must be a positive integer")
            if not isinstance(raw.get("state"), str):
                raise EffectAttemptError("matching status readback state must be a string")
            matching.append(raw)
    if not matching:
        return None
    latest = max(matching, key=lambda item: int(item["id"]))
    return int(latest["id"]) if latest["state"] == state else None


def _bool_argument(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("must be exactly true or false")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create")
    create.add_argument("--ledger", required=True, type=pathlib.Path)

    show = commands.add_parser("show")
    show.add_argument("--ledger", required=True, type=pathlib.Path)

    summary_command = commands.add_parser("summary")
    summary_command.add_argument("--ledger", required=True, type=pathlib.Path)

    append = commands.add_parser("append")
    append.add_argument("--ledger", required=True, type=pathlib.Path)
    append.add_argument("--kind", required=True)
    append.add_argument("--endpoint-or-subject", required=True)
    append.add_argument("--mutation", required=True)
    append.add_argument("--effect-transport-attempted", required=True, type=_bool_argument)
    append.add_argument("--transport-outcome", required=True)
    append.add_argument("--effect-observed", required=True, type=_bool_argument)
    append.add_argument("--evidence-ref", required=True)

    status_id = commands.add_parser("status-id")
    status_id.add_argument("--sha", required=True)
    status_id.add_argument("--context", required=True)
    status_id.add_argument("--state", required=True)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "create":
            create_empty_ledger(args.ledger)
            value = read_attempts(args.ledger)
        elif args.command == "append":
            value = append_attempt(
                args.ledger,
                {
                    "kind": args.kind,
                    "endpoint_or_subject": args.endpoint_or_subject,
                    "mutation": args.mutation,
                    "effect_transport_attempted": args.effect_transport_attempted,
                    "transport_outcome": args.transport_outcome,
                    "effect_observed": args.effect_observed,
                    "evidence_ref": args.evidence_ref,
                },
            )
        elif args.command == "status-id":
            value = select_latest_status_id(
                json.load(sys.stdin),
                sha=args.sha,
                context=args.context,
                state=args.state,
            )
            sys.stdout.write("" if value is None else str(value) + "\n")
            return 0
        else:
            attempts = read_attempts(args.ledger)
            value = attempts if args.command == "show" else summary(attempts)
    except (EffectAttemptError, OSError, json.JSONDecodeError) as exc:
        print(f"qikvrt effect-attempt ledger error: {exc}", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(canonical_bytes(value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
