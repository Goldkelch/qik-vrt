#!/usr/bin/env python3
"""Validate and normalize explicit QIK-VRT HOLD contracts.

A HOLD is a typed transition, not an unclassified waiting state.  Every new
HOLD/HOLD_UNVERIFIED must name the exact reason, subject, evidence, owner,
retry condition and one next action.  Historical receipts remain immutable;
this module validates new emissions or explicit lifecycle projections.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

HOLD_TOKENS = {"HOLD", "HOLD_UNVERIFIED"}
FORBIDDEN_REASON_CODES = {
    "", "NONE", "NULL", "UNKNOWN", "UNSPECIFIED", "GENERIC_HOLD", "WAIT", "RETRY"
}
FORBIDDEN_NEXT_ACTIONS = {"", "WAIT", "RETRY", "TRY_AGAIN", "HOLD"}
REOBSERVE_REASONS = {
    "ZERO_EXECUTED_JOB_GATE",
    "CAUSAL_REVIEW_EVIDENCE_DRIFT",
    "EXACT_SUBJECT_DRIFT",
    "MISSING_EXACT_SUBJECT_EVIDENCE",
    "GITHUB_INSTALLATION_RATE_LIMIT_EXHAUSTED",
}
AUTHORITY_REASONS = {
    "INDEPENDENT_CODE_OWNER_AUTHORITY_NOT_OBSERVED",
    "EXACT_SCOPE_AUTHORITY_NOT_OBSERVED",
}
HOLD_STATE_KEYS = {"state", "verification_state", "effect_ack", "disposition"}


class HoldContractError(ValueError):
    """Raised when a HOLD lacks a complete deterministic continuation."""


def _nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HoldContractError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise HoldContractError(f"{field} must be a non-empty list")
    result = []
    for index, item in enumerate(value):
        result.append(_nonempty_string(item, f"{field}[{index}]"))
    return result


def validate_hold_reason(reason: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(reason, Mapping):
        raise HoldContractError("hold_reason must be an object")

    reason_code = _nonempty_string(reason.get("reason_code"), "reason_code").upper()
    if reason_code in FORBIDDEN_REASON_CODES:
        raise HoldContractError(f"reason_code {reason_code!r} is not explicit")

    explanation = _nonempty_string(reason.get("reason"), "reason")
    subject = reason.get("subject")
    if not isinstance(subject, Mapping):
        raise HoldContractError("subject must be an object")
    repository = _nonempty_string(subject.get("repository"), "subject.repository")
    kind = _nonempty_string(subject.get("kind"), "subject.kind")
    identifier = subject.get("number", subject.get("identifier"))
    if identifier is None or (isinstance(identifier, str) and not identifier.strip()):
        raise HoldContractError("subject.number or subject.identifier is required")
    head_sha = subject.get("head_sha")
    if kind in {"pull_request", "commit", "workflow_run"}:
        _nonempty_string(head_sha, "subject.head_sha")

    evidence_refs = _string_list(reason.get("evidence_refs"), "evidence_refs")

    owner = reason.get("owner")
    if not isinstance(owner, Mapping):
        raise HoldContractError("owner must be an object")
    owner_role = _nonempty_string(owner.get("role"), "owner.role")
    owner_actor = _nonempty_string(owner.get("actor"), "owner.actor")

    retry = reason.get("retry_condition")
    if not isinstance(retry, Mapping):
        raise HoldContractError("retry_condition must be an object")
    retry_event = _nonempty_string(retry.get("event"), "retry_condition.event")
    retry_predicate = _nonempty_string(retry.get("predicate"), "retry_condition.predicate")

    next_action = _nonempty_string(reason.get("next_action"), "next_action").upper()
    if next_action in FORBIDDEN_NEXT_ACTIONS:
        raise HoldContractError(f"next_action {next_action!r} is not deterministic")

    d0 = reason.get("d0")
    if not isinstance(d0, int) or d0 not in {1, 2, 3}:
        raise HoldContractError("d0 must be one of 1, 2, or 3 for a HOLD")
    if reason_code in REOBSERVE_REASONS and d0 != 2:
        raise HoldContractError(f"{reason_code} must be D0=2 REOBSERVE")
    if reason_code in AUTHORITY_REASONS and d0 != 3:
        raise HoldContractError(f"{reason_code} must be D0=3 REQUEST_AUTHORITY")

    return {
        "reason_code": reason_code,
        "reason": explanation,
        "subject": {
            "repository": repository,
            "kind": kind,
            "identifier": identifier,
            "head_sha": head_sha,
        },
        "evidence_refs": evidence_refs,
        "owner": {"role": owner_role, "actor": owner_actor},
        "retry_condition": {"event": retry_event, "predicate": retry_predicate},
        "next_action": next_action,
        "d0": d0,
    }


def is_hold_object(value: Mapping[str, Any]) -> bool:
    return any(value.get(key) in HOLD_TOKENS for key in HOLD_STATE_KEYS)


def _legacy_hold_reason(value: Mapping[str, Any]) -> dict[str, Any] | None:
    """Accept a complete legacy receipt only when the reason is actually explicit.

    Legacy receipts remain immutable.  This adapter is intentionally narrow:
    a bare HOLD, a null blocker, or a generic WAIT is rejected.
    """
    blocker = value.get("first_blocker")
    detail = value.get("detail")
    action = value.get("derived_action")
    if not isinstance(blocker, str) or not blocker.strip():
        return None
    if not isinstance(detail, str) or not detail.strip():
        return None
    if not isinstance(action, Mapping):
        return None
    next_action = action.get("next_action")
    d0 = action.get("d0")
    subject_number = value.get("pr_number", value.get("run_id", value.get("subject_id")))
    repository = value.get("repository")
    head_sha = value.get("head_sha")
    if not isinstance(repository, str) or not repository:
        return None
    if subject_number is None or not isinstance(head_sha, str) or not head_sha:
        return None
    return {
        "reason_code": blocker,
        "reason": detail,
        "subject": {
            "repository": repository,
            "kind": "pull_request" if value.get("pr_number") is not None else "workflow_run",
            "number": subject_number,
            "head_sha": head_sha,
        },
        "evidence_refs": [
            ref for ref in (
                value.get("ledger_path"),
                value.get("ledger_diff_path"),
                f"evidence_fingerprint:{value.get('evidence_fingerprint')}"
                if value.get("evidence_fingerprint") else None,
            ) if isinstance(ref, str) and ref
        ] or ["legacy-receipt:inline"],
        "owner": {
            "role": "REQUIRED_AUTHORITY" if d0 == 3 else "EXACT_SUBJECT_OBSERVER",
            "actor": "repository-native-controller",
        },
        "retry_condition": {
            "event": str(next_action),
            "predicate": f"first_blocker {blocker} no longer applies to the same exact subject",
        },
        "next_action": next_action,
        "d0": d0,
    }


def validate_hold_object(value: Mapping[str, Any]) -> dict[str, Any] | None:
    if not is_hold_object(value):
        return None
    explicit = value.get("hold_reason")
    if explicit is not None:
        return validate_hold_reason(explicit)
    legacy = _legacy_hold_reason(value)
    if legacy is None:
        raise HoldContractError("HOLD has no explicit hold_reason and no complete legacy blocker contract")
    return validate_hold_reason(legacy)


def iter_hold_objects(value: Any, path: str = "$") -> Iterable[tuple[str, Mapping[str, Any]]]:
    if isinstance(value, Mapping):
        if is_hold_object(value):
            yield path, value
        for key, child in value.items():
            yield from iter_hold_objects(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_hold_objects(child, f"{path}[{index}]")


def validate_document(value: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path, hold in iter_hold_objects(value):
        try:
            normalized = validate_hold_object(hold)
        except HoldContractError as exc:
            raise HoldContractError(f"{path}: {exc}") from exc
        if normalized is not None:
            results.append({"path": path, "hold_reason": normalized})
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    report = []
    for path in args.paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        report.append({"path": str(path), "holds": validate_document(value)})
    print(json.dumps({
        "schema": "qikvrt_explicit_hold_validation_v1",
        "documents": report,
        "completion_claims": {
            "MERGE": False,
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
        },
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
