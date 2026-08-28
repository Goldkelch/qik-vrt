#!/usr/bin/env python3
"""Canonical handler descriptors for the issue-agent control plane."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any


MODEL_HANDLER_ID = "OPTIONAL-GITHUB-MODELS-INFERENCE-V1"
UNAVAILABLE_HANDLER_ID = "OPTIONAL-MODEL-UNAVAILABLE-V1"
EXTERNAL_FAILURE_HANDLER_ID = "EXTERNAL-AGENT-ADMISSION-FAILURE-V1"
UNTRUSTED_MARKER_HANDLER_ID = "UNTRUSTED-OWNER-MARKER-V1"
AMBIGUOUS_MARKER_HANDLER_ID = "UNKNOWN-OR-AMBIGUOUS-OWNER-MARKER-V1"
UNTRUSTED_UNTYPED_HANDLER_ID = "UNTRUSTED-UNTYPED-ISSUE-V1"
OWNER_CONTRACT_SCHEMA = "qikvrt_owner_observed_repository_work_cycle_v1"
ALLOWED_DISPOSITIONS = {
    "EXECUTE_NOW",
    "CLARIFICATION_REQUIRED",
    "BLOCKED_WITH_NEXT_ACTION",
    "CLOSE_COMPLETED",
    "CLOSE_NOT_PLANNED",
    "CLOSE_INVALID_OR_UNSUPPORTED",
}


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def descriptor_sha256(descriptor: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(descriptor)).hexdigest()


def validate_policy(policy: dict[str, Any]) -> None:
    if policy.get("schema") != "qikvrt_issue_agent_deterministic_intake_v1":
        raise ValueError("deterministic intake policy schema is invalid")
    prefix = policy.get("owner_marker_prefix")
    if not isinstance(prefix, str) or not prefix:
        raise ValueError("owner marker prefix is invalid")
    trusted = policy.get("trusted_owner_logins")
    if not isinstance(trusted, list) or not trusted or len(trusted) != len(set(trusted)):
        raise ValueError("trusted owner login set is invalid")
    actions = policy.get("accepted_event_actions")
    if not isinstance(actions, dict) or not actions:
        raise ValueError("accepted event actions are invalid")
    for name, values in actions.items():
        if not isinstance(name, str) or not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise ValueError("accepted event action set is invalid")
    handlers = policy.get("handlers")
    if not isinstance(handlers, list) or not handlers:
        raise ValueError("registered handler set is invalid")
    markers: set[str] = set()
    handler_ids: set[str] = set()
    for handler in handlers:
        if not isinstance(handler, dict):
            raise ValueError("registered handler is invalid")
        marker = handler.get("marker")
        handler_id = handler.get("handler_id")
        if (
            not isinstance(marker, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]{1,199}", marker)
            or marker in markers
        ):
            raise ValueError("registered handler marker is invalid or duplicated")
        if not isinstance(handler_id, str) or not handler_id or handler_id in handler_ids:
            raise ValueError("registered handler id is invalid or duplicated")
        if handler.get("disposition") not in ALLOWED_DISPOSITIONS:
            raise ValueError("registered handler disposition is invalid")
        for key in ("work_class", "executor_contract", "materialization_scope", "required_next_action"):
            if not isinstance(handler.get(key), str) or not handler[key].strip():
                raise ValueError(f"registered handler {key} is invalid")
        markers.add(marker)
        handler_ids.add(handler_id)
    signatures = policy.get("external_agent_failure_signatures")
    if not isinstance(signatures, list) or len(signatures) != len(set(signatures)):
        raise ValueError("external failure signatures are invalid")


def model_descriptor(model: str, system_prompt_sha256: str) -> dict[str, Any]:
    return {
        "handler_id": MODEL_HANDLER_ID,
        "model": model,
        "system_prompt_sha256": system_prompt_sha256,
    }


def unavailable_descriptor() -> dict[str, Any]:
    return {"handler_id": UNAVAILABLE_HANDLER_ID}


def external_failure_descriptor(signatures: list[str]) -> dict[str, Any]:
    return {
        "handler_id": EXTERNAL_FAILURE_HANDLER_ID,
        "signatures": signatures,
    }


def reject_descriptor(handler_id: str, markers: list[str]) -> dict[str, Any]:
    if handler_id not in {
        UNTRUSTED_MARKER_HANDLER_ID,
        AMBIGUOUS_MARKER_HANDLER_ID,
        UNTRUSTED_UNTYPED_HANDLER_ID,
    }:
        raise ValueError("unknown deterministic rejection handler")
    return {"handler_id": handler_id, "markers": markers}


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate owner-contract JSON key")
        value[key] = item
    return value


def _reject_constant(token: str) -> None:
    raise ValueError(f"non-finite owner-contract JSON number: {token}")


def extract_owner_contract(body: str, handler: dict[str, Any]) -> dict[str, Any] | None:
    contract = handler.get("payload_contract")
    if contract is None:
        return {}
    if contract != OWNER_CONTRACT_SCHEMA:
        return None
    matches: list[dict[str, Any]] = []
    for raw in re.findall(r"(?ms)^```json\s*$\n(.*?)^```\s*$", body):
        try:
            value = json.loads(
                raw,
                object_pairs_hook=_strict_object,
                parse_constant=_reject_constant,
            )
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(value, dict) and value.get("schema") == contract:
            matches.append(value)
    if len(matches) != 1:
        return None
    value = matches[0]
    hex40 = re.compile(r"^[0-9a-f]{40}$")
    if value.get("repository") != handler.get("repository"):
        return None
    if type(value.get("carrier_pr")) is not int or value["carrier_pr"] < 1:
        return None
    if not hex40.fullmatch(str(value.get("observed_head") or "")):
        return None
    if not hex40.fullmatch(str(value.get("observed_tree") or "")):
        return None
    if not hex40.fullmatch(str(value.get("authority_main") or "")):
        return None
    if value.get("cycle") != handler.get("required_cycle"):
        return None
    reaction = value.get("observed_repository_reaction")
    if not isinstance(reaction, dict):
        return None
    if type(reaction.get("d0")) is not int or reaction["d0"] not in {0, 1, 2, 3}:
        return None
    if reaction.get("state") not in {"NOOP", "HOLD", "REOBSERVE", "REQUEST_AUTHORITY"}:
        return None
    if not isinstance(value.get("finding"), str) or not value["finding"].strip():
        return None
    behavior = value.get("required_future_behavior")
    if not isinstance(behavior, list) or not behavior or not all(
        isinstance(item, str) and item.strip() for item in behavior
    ):
        return None
    non_claims = value.get("non_claims")
    required_false = handler.get("required_false_non_claims")
    if not isinstance(non_claims, dict) or not isinstance(required_false, list):
        return None
    if any(non_claims.get(key) is not False for key in required_false):
        return None
    return value


def marker_state(request_value: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    trigger = request_value.get("trigger") or {}
    selected_body = trigger.get("selected_body")
    if not isinstance(selected_body, str):
        raise ValueError("selected body is invalid")
    prefix = policy.get("owner_marker_prefix")
    if not isinstance(prefix, str) or not prefix:
        raise ValueError("owner marker prefix is invalid")
    by_marker = {
        value.get("marker"): value
        for value in policy.get("handlers") or []
        if isinstance(value, dict) and isinstance(value.get("marker"), str)
    }
    extracted = re.findall(r"<!--\s*([a-z0-9][a-z0-9_.:-]{1,199})\s*-->", selected_body)
    markers = sorted({marker for marker in extracted if marker.startswith(prefix) or marker in by_marker})
    trusted = set(policy.get("trusted_owner_logins") or [])
    recognized = [
        by_marker[marker]
        for marker in markers
        if marker in by_marker and extract_owner_contract(selected_body, by_marker[marker]) is not None
    ]
    return {
        "markers": markers,
        "recognized": recognized,
        "actor_trusted": trigger.get("actor_login") in trusted,
        "selected_author_trusted": trigger.get("selected_author_login") in trusted,
    }


def external_failure_state(request_value: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    validate_policy(policy)
    trigger = request_value.get("trigger") or {}
    selected_body = trigger.get("selected_body")
    if not isinstance(selected_body, str):
        raise ValueError("selected body is invalid")
    combined = "\n".join(
        (
            str(request_value.get("title") or ""),
            str(request_value.get("body") or ""),
            selected_body,
        )
    )
    signatures = policy.get("external_agent_failure_signatures") or []
    matched = [value for value in signatures if isinstance(value, str) and value in combined]
    provenance = policy.get("external_agent_failure_provenance") or {}
    structured = (
        trigger.get("selected_source") == provenance.get("selected_source")
        and request_value.get("author_type") == provenance.get("issue_author_type")
        and trigger.get("actor_login") == request_value.get("author")
    )
    return {"matched_signatures": matched, "structured": structured}
