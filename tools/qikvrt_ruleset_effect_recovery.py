#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Fail-closed classification for replaying an exact ruleset effect subject.

The bridge sees only Actions run metadata until a prior effect terminates.  A
terminal run is not automatically success or permission to repeat a
conditional ruleset update: its immutable artifact receipt determines whether
the bridge must stop, perform a GET-only recovery, or may start a fresh,
independently-proven conditional reconcile.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ACTIVE_STATUSES = frozenset({"requested", "pending", "queued", "in_progress", "waiting"})
TERMINAL_CONCLUSIONS = frozenset(
    {"success", "failure", "cancelled", "skipped", "timed_out", "action_required", "neutral", "stale", "startup_failure"}
)
RECOVERY_APPLY = "APPLY"
RECOVERY_REOBSERVE = "REOBSERVE_UNCONFIRMED"
VALID_RECOVERY_MODES = frozenset({RECOVERY_APPLY, RECOVERY_REOBSERVE})
SCHEMA = "qikvrt_ruleset_effect_recovery_v1"
CONTINUATION_RECEIPT_SCHEMA = "qikvrt_ruleset_effect_continuation_receipt_v1"
AUTHORITY_COMPLETION_SCHEMA = "qikvrt_ruleset_authority_continuation_readback_v1"


class EffectRecoveryError(ValueError):
    """The remote run or receipt cannot support a safe retry decision."""


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EffectRecoveryError(f"{label} must be a positive integer")
    return value


def _sha(value: str, label: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise EffectRecoveryError(f"{label} must be a lowercase 40-character SHA")
    return value


def _nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EffectRecoveryError(f"{label} must be a non-empty string")
    return value


def _bool(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise EffectRecoveryError(f"{label} must be a boolean")
    return value


def _hold_contract(value: Mapping[str, Any]) -> None:
    """Require the complete D0=2 contract before a carrier may recover it."""

    if value.get("verification_state") != "HOLD_UNVERIFIED":
        raise EffectRecoveryError("terminal HOLD receipt verification_state is invalid")
    if value.get("d0") != 2:
        raise EffectRecoveryError("terminal HOLD receipt top-level d0 must be 2")
    if value.get("continuation_required") is not True:
        raise EffectRecoveryError("terminal HOLD receipt must require continuation")
    _nonempty_text(value.get("first_blocker"), "terminal HOLD receipt.first_blocker")
    _nonempty_text(value.get("next_action"), "terminal HOLD receipt.next_action")
    hold_reason = value.get("hold_reason")
    if not isinstance(hold_reason, Mapping):
        raise EffectRecoveryError("terminal HOLD receipt.hold_reason must be an object")
    if hold_reason.get("d0") != 2:
        raise EffectRecoveryError("terminal HOLD receipt hold_reason.d0 must be 2")
    for field in ("reason_code", "reason", "next_action"):
        _nonempty_text(hold_reason.get(field), f"terminal HOLD receipt.hold_reason.{field}")
    for field in ("subject", "owner", "retry_condition"):
        if not isinstance(hold_reason.get(field), Mapping):
            raise EffectRecoveryError(f"terminal HOLD receipt.hold_reason.{field} must be an object")
    if not isinstance(hold_reason.get("evidence_refs"), list) or not hold_reason["evidence_refs"]:
        raise EffectRecoveryError("terminal HOLD receipt.hold_reason.evidence_refs must be non-empty")


def _authority_completion_contract(
    completion: Any,
    *,
    repository: str,
    pr_number: int,
    head_sha: str,
    main_sha: str,
    upstream_run_id: int,
    bridge_run_id: int | None,
    recovery_mode: str,
    recovery_of_effect_run_id: int | None,
) -> bool:
    if not isinstance(completion, Mapping):
        return False
    if (
        completion.get("schema") != AUTHORITY_COMPLETION_SCHEMA
        or completion.get("state") != "REQUEST_AUTHORITY"
        or completion.get("repository") != repository
        or completion.get("subject_mode") != "PR"
        or completion.get("pr_number") != pr_number
        or completion.get("head_sha") != head_sha
        or completion.get("trusted_main_sha") != main_sha
        or completion.get("upstream_run_id") != upstream_run_id
        or completion.get("bridge_run_id") != bridge_run_id
        or completion.get("recovery_mode") != recovery_mode
        or completion.get("recovery_of_effect_run_id") != recovery_of_effect_run_id
        or completion.get("hold_admissible") is not False
        or completion.get("issue_comment_readback") is not True
        or completion.get("exact_subject_readback") is not True
        or completion.get("full_exact_subject_verified") is not True
    ):
        return False
    return isinstance(completion.get("first_blocker"), str) and bool(completion["first_blocker"].strip())


def _pages(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        pages = [value]
        bounded_single_page = True
    elif isinstance(value, list):
        pages = value
        bounded_single_page = False
    else:
        raise EffectRecoveryError("effect runs must be a paginated array or bounded object page")
    items: list[Mapping[str, Any]] = []
    for page_index, page in enumerate(pages):
        if not isinstance(page, Mapping):
            raise EffectRecoveryError(f"effect runs page {page_index} must be an object")
        runs = page.get("workflow_runs")
        if not isinstance(runs, list):
            raise EffectRecoveryError(
                f"effect runs page {page_index}.workflow_runs must be an array"
            )
        if bounded_single_page:
            total_count = page.get("total_count")
            if (
                isinstance(total_count, bool)
                or not isinstance(total_count, int)
                or total_count < 0
                or total_count > 100
                or len(runs) != total_count
            ):
                raise EffectRecoveryError(
                    "bounded effect runs page must be complete and within 100 runs"
                )
        for run_index, run in enumerate(runs):
            if not isinstance(run, Mapping):
                raise EffectRecoveryError(
                    f"effect run {page_index}:{run_index} must be an object"
                )
            items.append(run)
    return items


def _effect_title_base(pr_number: int, head_sha: str, upstream_run_id: int) -> str:
    return (
        "QIKVRT ruleset effect mode=PR "
        f"pr={pr_number} head={head_sha} upstream={upstream_run_id}"
    )


def _title_mode(title: str, base: str) -> tuple[int | None, str, int | None] | None:
    """Return immutable bridge provenance for an exact title, if it matches."""

    if title == base:
        # Existing pre-provenance effect runs remain observable but never gain
        # a fabricated attempt id.  Their receipt is still classified before
        # any later carrier can act.
        return None, RECOVERY_APPLY, None
    if not title.startswith(base + " "):
        return None
    match = re.fullmatch(
        re.escape(base)
        + r" bridge=(?P<bridge>[1-9][0-9]*) carrier=(?:unbound|[1-9][0-9]*) recovery=(?P<recovery>APPLY|REOBSERVE_UNCONFIRMED) recovery_of=(?P<recovery_of>none|[1-9][0-9]*)(?: policy=none)?",
        title,
    )
    if match is None:
        raise EffectRecoveryError("exact effect title has malformed attempt provenance")
    recovery_of = match.group("recovery_of")
    if match.group("recovery") == RECOVERY_REOBSERVE and recovery_of == "none":
        raise EffectRecoveryError("GET-only recovery title omitted its original uncertain effect")
    return (
        int(match.group("bridge")),
        match.group("recovery"),
        None if recovery_of == "none" else int(recovery_of),
    )


def select_run(
    pages: Any,
    *,
    pr_number: int,
    head_sha: str,
    main_sha: str,
    upstream_run_id: int,
    expected_bridge_run_id: int | None = None,
    expected_recovery_mode: str | None = None,
) -> dict[str, Any]:
    """Choose the authoritative active or latest terminal exact effect run."""

    pr_number = _positive_int(pr_number, "pr_number")
    upstream_run_id = _positive_int(upstream_run_id, "upstream_run_id")
    if expected_bridge_run_id is not None:
        expected_bridge_run_id = _positive_int(expected_bridge_run_id, "bridge_run_id")
    if expected_recovery_mode is not None and expected_recovery_mode not in VALID_RECOVERY_MODES:
        raise EffectRecoveryError("expected recovery mode is invalid")
    _sha(head_sha, "head_sha")
    _sha(main_sha, "main_sha")
    base = _effect_title_base(pr_number, head_sha, upstream_run_id)
    matches: list[tuple[int, Mapping[str, Any], int | None, str, int | None]] = []
    for run in _pages(pages):
        title = run.get("display_title")
        if not isinstance(title, str):
            continue
        provenance = _title_mode(title, base)
        if provenance is None:
            continue
        if run.get("head_branch") != "main" or run.get("head_sha") != main_sha:
            raise EffectRecoveryError("exact effect title is not bound to trusted Main")
        run_id = _positive_int(run.get("id"), "effect run.id")
        status = run.get("status")
        if not isinstance(status, str):
            raise EffectRecoveryError("effect run.status must be a string")
        bridge_run_id, recovery_mode, recovery_of_effect_run_id = provenance
        if expected_bridge_run_id is not None and bridge_run_id != expected_bridge_run_id:
            continue
        if expected_recovery_mode is not None and recovery_mode != expected_recovery_mode:
            continue
        matches.append((run_id, run, bridge_run_id, recovery_mode, recovery_of_effect_run_id))

    active = [entry for entry in matches if entry[1].get("status") in ACTIVE_STATUSES]
    if active:
        run_id, run, bridge_run_id, recovery_mode, recovery_of_effect_run_id = max(
            active, key=lambda entry: entry[0]
        )
        return {
            "schema": SCHEMA,
            "state": "ACTIVE",
            "effect_run_id": run_id,
            "status": run["status"],
            "bridge_run_id": bridge_run_id,
            "recovery_mode": recovery_mode,
            "recovery_of_effect_run_id": recovery_of_effect_run_id,
        }

    terminal = []
    for entry in matches:
        status = entry[1].get("status")
        if status != "completed":
            raise EffectRecoveryError(f"exact effect run has unsupported terminal status {status!r}")
        conclusion = entry[1].get("conclusion")
        if conclusion not in TERMINAL_CONCLUSIONS:
            raise EffectRecoveryError("exact terminal effect run conclusion is invalid")
        terminal.append(entry)
    if not terminal:
        return {
            "schema": SCHEMA,
            "state": "NO_MATCH",
            "effect_run_id": None,
            "bridge_run_id": None,
            "recovery_mode": None,
        }
    run_id, run, bridge_run_id, recovery_mode, recovery_of_effect_run_id = max(
        terminal, key=lambda entry: entry[0]
    )
    return {
        "schema": SCHEMA,
        "state": "TERMINAL",
        "effect_run_id": run_id,
        "status": run["status"],
        "conclusion": run.get("conclusion"),
        "bridge_run_id": bridge_run_id,
        "recovery_mode": recovery_mode,
        "recovery_of_effect_run_id": recovery_of_effect_run_id,
    }


def classify_terminal_receipt(
    value: Any,
    *,
    recovery_mode: str,
    bridge_run_id: int | None,
    recovery_of_effect_run_id: int | None,
    conclusion: str | None,
    repository: str,
    pr_number: int,
    head_sha: str,
    main_sha: str,
    upstream_run_id: int,
    completion: Any | None = None,
) -> dict[str, Any]:
    """Map a terminal artifact receipt to a safe next carrier operation."""

    if recovery_mode not in VALID_RECOVERY_MODES:
        raise EffectRecoveryError("terminal recovery mode is invalid")
    if conclusion not in TERMINAL_CONCLUSIONS:
        raise EffectRecoveryError("terminal effect conclusion is invalid")
    pr_number = _positive_int(pr_number, "pr_number")
    upstream_run_id = _positive_int(upstream_run_id, "upstream_run_id")
    _sha(head_sha, "head_sha")
    _sha(main_sha, "main_sha")
    if not repository or "/" not in repository:
        raise EffectRecoveryError("repository is invalid")
    if not isinstance(value, Mapping):
        raise EffectRecoveryError("terminal effect receipt must be an object")
    if value.get("schema") != CONTINUATION_RECEIPT_SCHEMA:
        raise EffectRecoveryError("terminal effect receipt schema is invalid")
    if recovery_of_effect_run_id is not None:
        _positive_int(recovery_of_effect_run_id, "recovery_of_effect_run_id")
    if (
        value.get("repository") != repository
        or value.get("subject_mode") != "PR"
        or value.get("pr_number") != pr_number
        or value.get("head_sha") != head_sha
        or value.get("trusted_main_sha") != main_sha
        or value.get("upstream_run_id") != upstream_run_id
    ):
        raise EffectRecoveryError("terminal effect receipt exact subject provenance does not match")
    if bridge_run_id is not None:
        if _positive_int(bridge_run_id, "bridge_run_id") != bridge_run_id:
            raise EffectRecoveryError("bridge_run_id is invalid")
        if value.get("bridge_run_id") != bridge_run_id:
            raise EffectRecoveryError("terminal effect receipt bridge provenance does not match run title")
        if value.get("recovery_mode") != recovery_mode:
            raise EffectRecoveryError("terminal effect receipt recovery provenance does not match run title")
        if value.get("recovery_of_effect_run_id") != recovery_of_effect_run_id:
            raise EffectRecoveryError("terminal effect receipt recovery origin does not match run title")
    state = value.get("state")
    if not isinstance(state, str):
        raise EffectRecoveryError("terminal effect receipt.state must be a string")
    _bool(value.get("effect_transport_attempted"), "terminal effect receipt.effect_transport_attempted")
    _bool(value.get("effect_observed"), "terminal effect receipt.effect_observed")
    _nonempty_text(value.get("mutation"), "terminal effect receipt.mutation")
    exact_subject_verified = value.get("full_exact_subject_verified")
    if not isinstance(exact_subject_verified, bool):
        raise EffectRecoveryError("terminal effect receipt.full_exact_subject_verified must be a boolean")
    recovery_rebind_required = value.get("recovery_rebind_required", False)
    if not isinstance(recovery_rebind_required, bool):
        raise EffectRecoveryError("terminal effect receipt.recovery_rebind_required must be a boolean")
    if not exact_subject_verified and (
        state != "HOLD" or recovery_rebind_required is not True
    ):
        raise EffectRecoveryError(
            "terminal receipt without exact verification is not a safe terminal state"
        )
    if state in {"CURRENT", "APPLIED"} and conclusion == "success":
        return {
            "schema": SCHEMA,
            "state": "NOOP",
            "first_blocker": f"TERMINAL_EFFECT_RECEIPT_{state}",
            "next_recovery_mode": None,
        }
    if state in {"CURRENT", "APPLIED"}:
        # The reconciliation completed, but its later deduplicated receipt or
        # status publication did not.  A new normal carrier starts with an
        # idempotent GET and can repair that downstream effect.
        return {
            "schema": SCHEMA,
            "state": "RETRY",
            "first_blocker": "TERMINAL_EFFECT_COMPLETION_INCOMPLETE",
            "next_recovery_mode": RECOVERY_APPLY,
            "next_recovery_origin": "NONE",
        }
    if state == "REQUEST_AUTHORITY":
        if (
            value.get("verification_state") != "REQUEST_AUTHORITY_ACTIVE"
            or value.get("continuation_required") is not True
            or value.get("hold_admissible") is not False
            or not isinstance(value.get("first_blocker"), str)
            or not value["first_blocker"].strip()
            or not isinstance(value.get("next_action"), str)
            or not value["next_action"].strip()
            or not _authority_completion_contract(
                completion,
                repository=repository,
                pr_number=pr_number,
                head_sha=head_sha,
                main_sha=main_sha,
                upstream_run_id=upstream_run_id,
                bridge_run_id=bridge_run_id,
                recovery_mode=recovery_mode,
                recovery_of_effect_run_id=recovery_of_effect_run_id,
            )
        ):
            return {
                "schema": SCHEMA,
                "state": "RETRY",
                "first_blocker": "AUTHORITY_CONTINUATION_COMPLETION_UNPROVEN",
                "next_recovery_mode": RECOVERY_APPLY,
                "next_recovery_origin": "NONE",
            }
        return {
            "schema": SCHEMA,
            "state": "NOOP",
            "first_blocker": "TERMINAL_EFFECT_RECEIPT_REQUEST_AUTHORITY",
            "next_recovery_mode": None,
        }
    if state != "HOLD":
        raise EffectRecoveryError(f"terminal effect receipt.state {state!r} is unsupported")

    attempted = value.get("effect_transport_attempted")
    observed = value.get("effect_observed")
    if not isinstance(attempted, bool) or not isinstance(observed, bool):
        raise EffectRecoveryError(
            "terminal HOLD receipt must contain boolean transport and observation evidence"
        )
    _hold_contract(value)
    observed_state = value.get("observed_state")
    if observed_state is not None and not isinstance(observed_state, str):
        raise EffectRecoveryError("terminal HOLD receipt.observed_state must be a string or null")

    if recovery_mode == RECOVERY_REOBSERVE:
        if recovery_of_effect_run_id is None:
            raise EffectRecoveryError("terminal reobserve run omitted its original uncertain effect")
        if observed_state == "DRIFT" and not attempted:
            return {
                "schema": SCHEMA,
                "state": "RETRY",
                "first_blocker": "REOBSERVE_PROVED_RULESET_DRIFT",
                "next_recovery_mode": RECOVERY_APPLY,
                "next_recovery_origin": "TERMINAL_EFFECT",
            }
        return {
            "schema": SCHEMA,
            "state": "RETRY",
            "first_blocker": "REOBSERVE_TERMINAL_HOLD",
            "next_recovery_mode": RECOVERY_REOBSERVE,
            "next_recovery_origin": "TERMINAL_ORIGIN",
        }
    if attempted and not observed:
        return {
            "schema": SCHEMA,
            "state": "RETRY",
            "first_blocker": "PRIOR_RULESET_MUTATION_UNCONFIRMED",
            "next_recovery_mode": RECOVERY_REOBSERVE,
            "next_recovery_origin": "TERMINAL_EFFECT",
        }
    return {
        "schema": SCHEMA,
        "state": "RETRY",
        "first_blocker": "TERMINAL_EFFECT_HOLD_REOBSERVED",
        "next_recovery_mode": RECOVERY_APPLY,
        "next_recovery_origin": "NONE",
    }


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    select = commands.add_parser("select-run")
    select.add_argument("--runs", type=Path, required=True)
    select.add_argument("--pr", type=int, required=True)
    select.add_argument("--head", required=True)
    select.add_argument("--main", required=True)
    select.add_argument("--upstream", type=int, required=True)
    select.add_argument("--bridge-run-id", type=int)
    select.add_argument("--recovery-mode", choices=sorted(VALID_RECOVERY_MODES))
    select.add_argument("--output", type=Path, required=True)
    receipt = commands.add_parser("classify-receipt")
    receipt.add_argument("--receipt", type=Path, required=True)
    receipt.add_argument("--recovery-mode", choices=sorted(VALID_RECOVERY_MODES), required=True)
    receipt.add_argument("--bridge-run-id", type=int)
    receipt.add_argument("--recovery-of-effect-run-id", type=int)
    receipt.add_argument("--conclusion")
    receipt.add_argument("--completion", type=Path)
    receipt.add_argument("--repository", required=True)
    receipt.add_argument("--pr", type=int, required=True)
    receipt.add_argument("--head", required=True)
    receipt.add_argument("--main", required=True)
    receipt.add_argument("--upstream", type=int, required=True)
    receipt.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "select-run":
            result = select_run(
                _read(args.runs),
                pr_number=args.pr,
                head_sha=args.head,
                main_sha=args.main,
                upstream_run_id=args.upstream,
                expected_bridge_run_id=args.bridge_run_id,
                expected_recovery_mode=args.recovery_mode,
            )
        else:
            result = classify_terminal_receipt(
                _read(args.receipt),
                recovery_mode=args.recovery_mode,
                bridge_run_id=args.bridge_run_id,
                recovery_of_effect_run_id=args.recovery_of_effect_run_id,
                conclusion=args.conclusion,
                repository=args.repository,
                pr_number=args.pr,
                head_sha=args.head,
                main_sha=args.main,
                upstream_run_id=args.upstream,
                completion=_read(args.completion) if args.completion is not None else None,
            )
        _write(args.output, result)
    except (EffectRecoveryError, OSError, json.JSONDecodeError) as exc:
        print(f"qikvrt ruleset effect recovery error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
