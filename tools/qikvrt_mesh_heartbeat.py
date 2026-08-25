#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Event-driven QIK-VRT Mesh heartbeat and bounded audit system test.

One pulse per second proves liveness and lease freshness only. Heartbeats never
select work, trigger semantic work, poll domain state or blind-retry failures.
Semantic work begins only from one locally constructed content-bound event and
follows the exact local lifecycle:

0 -> 1 -> ARBEIT -> ERGEBNIS -> REOBSERVATION -> AUTHORITY_EFFEKT -> 0

The bounded system test uses four independent emitter processes and real
loopback TCP. Its authority effect is local-test-ledger-only; repository
Authority effects remain the responsibility of the separate trusted writer.
"""
from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import json
import os
import pathlib
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from tools.qikvrt_subprocess import run_bounded

HEARTBEAT_SCHEMA = "qikvrt_mesh_heartbeat_v1"
AUDIT_SCHEMA = "qikvrt_mesh_heartbeat_execution_receipt_v1"
WORK_EVENT_SCHEMA = "qikvrt_mesh_work_event_v1"
WORK_RECEIPT_SCHEMA = "qikvrt_mesh_work_receipt_v1"
AUTHORITY_LEDGER_SCHEMA = "qikvrt_mesh_local_authority_ledger_v1"
LEDGER_REF_CONTROL_SCHEMA = "qikvrt_mesh_heartbeat_ledger_ref_control_v1"
NETWORK_SCOPE = "LOOPBACK_TCP_ONLY"
HEARTBEAT_ROLE = "LIVENESS_AND_LEASE_FRESHNESS_ONLY"
AUTHORITY_EFFECT_SCOPE = "LOCAL_TEST_LEDGER_ONLY"
EXTERNAL_EFFECT = "NONE"
HEARTBEAT_HZ = 1
HEARTBEAT_INTERVAL_NS = 1_000_000_000
MAX_SEND_LATENESS_NS = 750_000_000
SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
LIFECYCLE = ["0", "1", "ARBEIT", "ERGEBNIS", "REOBSERVATION", "AUTHORITY_EFFEKT", "0"]
NODE_SPECS = (
    ("authority-a", "pair-a", "AUTHORITY"),
    ("mirror-a", "pair-a", "MIRROR"),
    ("authority-b", "pair-b", "AUTHORITY"),
    ("mirror-b", "pair-b", "MIRROR"),
)
LEDGER_REF = "refs/heads/qikvrt/mesh-heartbeat-ledger-v1"
LEDGER_REQUIRED_RULE_TYPES = frozenset({"deletion", "non_fast_forward"})
LEDGER_OBSERVATION_PHASES = frozenset({
    "INITIAL", "PRE_PUSH", "POST_READBACK",
})
LEDGER_RULESET_SOURCE_TYPES = frozenset({"Repository", "Organization"})
REPOSITORY_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
REPOSITORY_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


class HeartbeatContractError(ValueError):
    """Fail-closed contract violation."""


class HeartbeatTransportError(RuntimeError):
    """Bounded loopback transport failure."""


def canonical_json_bytes(value: Any) -> bytes:
    def normalize(item: Any) -> Any:
        if item is None or isinstance(item, (bool, int, str)):
            return item
        if isinstance(item, float):
            raise HeartbeatContractError("floating-point values are not canonical")
        if isinstance(item, Mapping):
            result: dict[str, Any] = {}
            for key, child in item.items():
                if not isinstance(key, str) or key in result:
                    raise HeartbeatContractError("invalid canonical object key")
                result[key] = normalize(child)
            return result
        if isinstance(item, (list, tuple)):
            return [normalize(child) for child in item]
        raise HeartbeatContractError("unsupported canonical value")

    return json.dumps(
        normalize(value), ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def sha256_ref(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any) -> str:
    return sha256_ref(canonical_json_bytes(value))


def _strict_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _strict_json_loads(text: str, blocker: str) -> Any:
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_json_object,
            parse_constant=_reject_json_constant,
        )
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise HeartbeatContractError(blocker) from exc


def _ledger_control_common(
    *, repository: str, source_head: str, source_run_id: int,
    observer_run_id: int, observer_run_attempt: int, observation_phase: str,
    ledger_ref: str, ledger_transition: str,
) -> dict[str, Any]:
    if not isinstance(repository, str) or not REPOSITORY_RE.fullmatch(repository):
        raise HeartbeatContractError("repository must be owner/name")
    _sha1(source_head, "source_head")
    _integer(source_run_id, "source_run_id")
    _integer(observer_run_id, "observer_run_id")
    _integer(observer_run_attempt, "observer_run_attempt")
    if source_run_id <= 0:
        raise HeartbeatContractError("source run binding must be positive")
    if observer_run_id <= 0 or observer_run_attempt <= 0:
        raise HeartbeatContractError("observer run binding must be positive")
    if observation_phase not in LEDGER_OBSERVATION_PHASES:
        raise HeartbeatContractError("ledger observation phase is invalid")
    if ledger_ref != LEDGER_REF:
        raise HeartbeatContractError("ledger_ref is not the exact governed ref")
    if ledger_transition not in {
        "NONE", "NOOP_ALREADY_CURRENT", "FAST_FORWARD_PUSHED",
    }:
        raise HeartbeatContractError("ledger transition is invalid")
    if (
        observation_phase in {"INITIAL", "PRE_PUSH"}
        and ledger_transition != "NONE"
    ) or (
        observation_phase == "POST_READBACK"
        and ledger_transition not in {
            "NOOP_ALREADY_CURRENT", "FAST_FORWARD_PUSHED",
        }
    ):
        raise HeartbeatContractError("ledger phase/transition binding is invalid")
    return {
        "schema": LEDGER_REF_CONTROL_SCHEMA,
        "repository": repository,
        "source_head": source_head,
        "source_run_id": source_run_id,
        "observer_run_id": observer_run_id,
        "observer_run_attempt": observer_run_attempt,
        "observation_phase": observation_phase,
        "ledger_ref": ledger_ref,
        "ledger_branch": ledger_ref.removeprefix("refs/heads/"),
        "observation_endpoint": "GET_REPOSITORY_RULES_FOR_BRANCH_AND_RULESET_DETAIL",
        "api_version": "2022-11-28",
        "required_rule_types_on_one_ruleset": sorted(LEDGER_REQUIRED_RULE_TYPES),
        "ledger_transition_before_observation": ledger_transition,
        "repository_ruleset_mutation_performed": False,
        "ruleset_push_atomicity_observed": False,
        "post_readback_control_is_detection_not_prevention": True,
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "MERGE": False,
            "DEPLOYMENT": False,
        },
    }


def _seal_ledger_control(receipt: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(receipt)
    result["receipt_sha256"] = canonical_sha256(result)
    return result


def ledger_ref_control_reobserve(
    *, repository: str, source_head: str, source_run_id: int,
    observer_run_id: int = 1, observer_run_attempt: int = 1,
    observation_phase: str = "INITIAL",
    ledger_ref: str = LEDGER_REF, blocker: str,
    ledger_transition: str = "NONE",
    expected_snapshot_sha256: str | None = None,
    observed_snapshot_sha256: str | None = None,
) -> dict[str, Any]:
    if not isinstance(blocker, str) or not re.fullmatch(r"[A-Z0-9_]{1,128}", blocker):
        raise HeartbeatContractError("ledger control blocker is invalid")
    if (expected_snapshot_sha256 is None) != (observed_snapshot_sha256 is None):
        raise HeartbeatContractError("ledger control comparison binding is incomplete")
    if expected_snapshot_sha256 is not None:
        _sha256(expected_snapshot_sha256, "expected_snapshot_sha256")
        _sha256(observed_snapshot_sha256, "observed_snapshot_sha256")
        if (
            blocker != "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT"
            or expected_snapshot_sha256 == observed_snapshot_sha256
            or observation_phase == "INITIAL"
        ):
            raise HeartbeatContractError(
                "ledger control comparison semantics are invalid"
            )
    elif blocker == "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT":
        raise HeartbeatContractError(
            "ledger control drift blocker requires comparison evidence"
        )
    return _seal_ledger_control({
        **_ledger_control_common(
            repository=repository,
            source_head=source_head,
            source_run_id=source_run_id,
            observer_run_id=observer_run_id,
            observer_run_attempt=observer_run_attempt,
            observation_phase=observation_phase,
            ledger_ref=ledger_ref,
            ledger_transition=ledger_transition,
        ),
        "observation_complete": False,
        "state": "REOBSERVE",
        "d0": 2,
        "first_blocker": blocker,
        "ledger_write_guard_satisfied": False,
        "protection_snapshot": None,
        "protection_snapshot_sha256": None,
        "qualifying_ruleset_ids": [],
        "selected_ruleset_id": None,
        "comparison_performed": expected_snapshot_sha256 is not None,
        "expected_protection_snapshot_sha256": expected_snapshot_sha256,
        "observed_protection_snapshot_sha256": observed_snapshot_sha256,
        "productive_effect_released_by_observation": False,
    })


def flatten_ledger_rule_pages(value: Any) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or not value or len(value) > 100:
        raise HeartbeatContractError("LEDGER_RULE_PAGINATION_INVALID")
    result: list[Mapping[str, Any]] = []
    for page in value:
        if not isinstance(page, list) or len(page) > 100:
            raise HeartbeatContractError("LEDGER_RULE_PAGE_INVALID")
        for item in page:
            if not isinstance(item, Mapping):
                raise HeartbeatContractError("LEDGER_RULE_ITEM_INVALID")
            result.append(item)
    return result


def _effective_ledger_rule_projection(
    rules: Sequence[Mapping[str, Any]],
    *,
    repository: str,
) -> tuple[list[dict[str, Any]], dict[int, set[str]]]:
    if isinstance(rules, (str, bytes)) or not isinstance(rules, Sequence):
        raise HeartbeatContractError("LEDGER_RULE_OBSERVATION_INVALID")
    projection: list[dict[str, Any]] = []
    grouped: dict[int, set[str]] = {}
    sources_by_ruleset: dict[int, tuple[str, str]] = {}
    seen: set[tuple[int, str, str, str]] = set()
    for rule in rules:
        if not isinstance(rule, Mapping):
            raise HeartbeatContractError("LEDGER_RULE_ITEM_INVALID")
        ruleset_id = rule.get("ruleset_id")
        rule_type = rule.get("type")
        source_type = rule.get("ruleset_source_type")
        source = rule.get("ruleset_source")
        if (
            isinstance(ruleset_id, bool)
            or not isinstance(ruleset_id, int)
            or ruleset_id <= 0
            or not isinstance(rule_type, str)
            or not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", rule_type)
        ):
            raise HeartbeatContractError("LEDGER_RULE_BINDING_INVALID")
        source_type, source = _validate_ruleset_source(
            repository,
            source_type,
            source,
        )
        canonical_source = (source_type, source)
        previous_source = sources_by_ruleset.setdefault(
            ruleset_id,
            canonical_source,
        )
        if previous_source != canonical_source:
            raise HeartbeatContractError(
                "LEDGER_RULESET_EFFECTIVE_SOURCE_CONTRADICTION"
            )
        key = (ruleset_id, rule_type, source_type, source)
        if key in seen:
            raise HeartbeatContractError("LEDGER_RULE_DUPLICATE")
        seen.add(key)
        grouped.setdefault(ruleset_id, set()).add(rule_type)
        projection.append({
            "ruleset_id": ruleset_id,
            "type": rule_type,
            "ruleset_source_type": source_type,
            "ruleset_source": source,
        })
    projection.sort(key=lambda item: (
        item["ruleset_id"], item["type"],
        item["ruleset_source_type"], item["ruleset_source"],
    ))
    return projection, grouped


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and bool(item) for item in value
    ):
        raise HeartbeatContractError(f"{label} must be a string list")
    if len(set(value)) != len(value):
        raise HeartbeatContractError(f"{label} contains duplicates")
    return sorted(value)


def _rule_type_list(value: Any, label: str) -> list[str]:
    result = _string_list(value, label)
    if any(not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", item) for item in result):
        raise HeartbeatContractError(f"{label} contains an invalid rule type")
    return result


def _validate_ruleset_source(
    repository: str,
    source_type: Any,
    source: Any,
) -> tuple[str, str]:
    if not isinstance(source_type, str) or source_type not in (
        LEDGER_RULESET_SOURCE_TYPES
    ) or not isinstance(source, str):
        raise HeartbeatContractError("LEDGER_RULESET_SOURCE_DOMAIN_INVALID")
    owner = repository.split("/", 1)[0]
    expected_source = repository if source_type == "Repository" else owner
    source_shape_valid = (
        REPOSITORY_RE.fullmatch(source)
        if source_type == "Repository"
        else REPOSITORY_COMPONENT_RE.fullmatch(source)
    )
    if source_shape_valid is None:
        raise HeartbeatContractError("LEDGER_RULESET_SOURCE_DOMAIN_INVALID")
    if source.lower() != expected_source.lower():
        raise HeartbeatContractError("LEDGER_RULESET_SOURCE_REPOSITORY_MISMATCH")
    return source_type, expected_source


def evaluate_ledger_ref_control(
    effective_rules: Sequence[Mapping[str, Any]],
    ruleset_details: Mapping[int, Mapping[str, Any]],
    *, repository: str, source_head: str, source_run_id: int,
    observer_run_id: int = 1, observer_run_attempt: int = 1,
    observation_phase: str = "INITIAL",
    ledger_ref: str = LEDGER_REF, ledger_transition: str = "NONE",
) -> dict[str, Any]:
    common = _ledger_control_common(
        repository=repository,
        source_head=source_head,
        source_run_id=source_run_id,
        observer_run_id=observer_run_id,
        observer_run_attempt=observer_run_attempt,
        observation_phase=observation_phase,
        ledger_ref=ledger_ref,
        ledger_transition=ledger_transition,
    )
    effective_projection, grouped = _effective_ledger_rule_projection(
        effective_rules,
        repository=repository,
    )
    if not isinstance(ruleset_details, Mapping):
        raise HeartbeatContractError("LEDGER_RULESET_DETAILS_INVALID")
    for key, detail in ruleset_details.items():
        if isinstance(key, bool) or not isinstance(key, int) or key <= 0:
            raise HeartbeatContractError("LEDGER_RULESET_DETAIL_KEY_INVALID")
        if not isinstance(detail, Mapping):
            raise HeartbeatContractError("LEDGER_RULESET_DETAIL_INVALID")

    candidate_ids = sorted(
        ruleset_id for ruleset_id, types in grouped.items()
        if LEDGER_REQUIRED_RULE_TYPES.issubset(types)
    )
    detail_projection: list[dict[str, Any]] = []
    qualifying: list[int] = []
    blockers: list[str] = []
    for ruleset_id in candidate_ids:
        if ruleset_id not in ruleset_details:
            raise HeartbeatContractError("LEDGER_RULESET_DETAIL_MISSING")
        detail = ruleset_details[ruleset_id]
        effective_sources = {
            (item["ruleset_source_type"], item["ruleset_source"])
            for item in effective_projection
            if item["ruleset_id"] == ruleset_id
        }
        if (
            len(effective_sources) != 1
            or any(
                not isinstance(value, str) or not value
                for value in next(iter(effective_sources))
            )
        ):
            raise HeartbeatContractError("LEDGER_RULESET_EFFECTIVE_SOURCE_INVALID")
        effective_source_type, effective_source = next(iter(effective_sources))
        _validate_ruleset_source(
            repository,
            effective_source_type,
            effective_source,
        )
        detail_id = detail.get("id")
        if (
            isinstance(detail_id, bool)
            or not isinstance(detail_id, int)
            or detail_id <= 0
            or detail_id != ruleset_id
        ):
            raise HeartbeatContractError("LEDGER_RULESET_DETAIL_ID_MISMATCH")
        rules = detail.get("rules")
        if not isinstance(rules, list) or not all(isinstance(rule, Mapping) for rule in rules):
            raise HeartbeatContractError("LEDGER_RULESET_DETAIL_RULES_INVALID")
        detail_rule_types = _rule_type_list(
            [rule.get("type") for rule in rules],
            "ruleset detail rule types",
        )
        conditions = detail.get("conditions")
        if not isinstance(conditions, Mapping) or not isinstance(conditions.get("ref_name"), Mapping):
            raise HeartbeatContractError("LEDGER_RULESET_DETAIL_CONDITIONS_INVALID")
        ref_name = conditions["ref_name"]
        includes = _string_list(ref_name.get("include"), "ruleset include")
        excludes = _string_list(ref_name.get("exclude"), "ruleset exclude")
        target = detail.get("target")
        enforcement = detail.get("enforcement")
        if (
            not isinstance(target, str)
            or not target
            or not isinstance(enforcement, str)
            or not enforcement
        ):
            raise HeartbeatContractError("LEDGER_RULESET_DETAIL_STATE_INVALID")
        detail_source_type, detail_source = _validate_ruleset_source(
            repository,
            detail.get("source_type"),
            detail.get("source"),
        )
        bypass_visible = "bypass_actors" in detail
        bypass = detail.get("bypass_actors")
        if bypass_visible and (
            not isinstance(bypass, list)
            or not all(isinstance(actor, Mapping) for actor in bypass)
        ):
            raise HeartbeatContractError("LEDGER_RULESET_BYPASS_INVALID")
        bypass_projection = (
            sorted(
                (dict(actor) for actor in bypass),
                key=lambda actor: canonical_json_bytes(actor),
            )
            if bypass_visible
            else None
        )
        if (
            detail_source_type != effective_source_type
            or detail_source != effective_source
        ):
            raise HeartbeatContractError(
                "LEDGER_RULESET_SOURCE_BINDING_MISMATCH"
            )
        if (
            target != "branch"
            or enforcement != "active"
            or not LEDGER_REQUIRED_RULE_TYPES.issubset(detail_rule_types)
        ):
            raise HeartbeatContractError(
                "LEDGER_RULESET_EFFECTIVE_DETAIL_CONTRADICTION"
            )
        literal_include = ledger_ref in includes
        excludes_empty = excludes == []
        bypass_empty = bypass_visible and bypass_projection == []
        detail_projection.append({
            "ruleset_id": ruleset_id,
            "source_type": detail_source_type,
            "source": detail_source,
            "target": target,
            "enforcement": enforcement,
            "include": includes,
            "exclude": excludes,
            "rule_types": detail_rule_types,
            "bypass_actors_visible": bypass_visible,
            "bypass_actors": bypass_projection,
            "effective_source_type": effective_source_type,
            "effective_source": effective_source,
        })
        if (
            literal_include
            and excludes_empty
            and bypass_empty
        ):
            qualifying.append(ruleset_id)
            continue
        if not bypass_visible:
            blockers.append("LEDGER_RULESET_BYPASS_VISIBILITY_REQUIRED")
        elif not bypass_empty:
            blockers.append("LEDGER_RULESET_BYPASS_PRESENT")
        elif not literal_include:
            blockers.append("LEDGER_RULESET_LITERAL_INCLUDE_MISSING")
        elif not excludes_empty:
            blockers.append("LEDGER_RULESET_EXCLUDE_PRESENT")
        else:
            blockers.append("LEDGER_IMMUTABILITY_RULESET_NOT_ACTIVE")

    snapshot = {
        "ledger_ref": ledger_ref,
        "effective_rules": effective_projection,
        "candidate_rulesets": sorted(detail_projection, key=lambda item: item["ruleset_id"]),
        "required_rule_types_on_one_ruleset": sorted(LEDGER_REQUIRED_RULE_TYPES),
    }
    snapshot_sha256 = canonical_sha256(snapshot)
    selected = min(qualifying) if qualifying else None
    if selected is not None:
        state = "CONTROL_OBSERVED"
        d0 = None
        blocker = None
        guard = True
    else:
        state = "REQUEST_AUTHORITY"
        d0 = 3
        blocker = blockers[0] if blockers else "LEDGER_IMMUTABILITY_RULESET_NOT_ACTIVE"
        guard = False
    return _seal_ledger_control({
        **common,
        "observation_complete": True,
        "state": state,
        "d0": d0,
        "first_blocker": blocker,
        "ledger_write_guard_satisfied": guard,
        "protection_snapshot": snapshot,
        "protection_snapshot_sha256": snapshot_sha256,
        "qualifying_ruleset_ids": sorted(qualifying),
        "selected_ruleset_id": selected,
        "productive_effect_released_by_observation": False,
    })


def _gh_json(command: Sequence[str]) -> Any:
    result = run_bounded(command, timeout=60, max_output_bytes=4 * 1024 * 1024)
    if result.timed_out:
        raise HeartbeatContractError("LEDGER_RULESET_API_TIMEOUT")
    if result.output_limit_exceeded:
        raise HeartbeatContractError("LEDGER_RULESET_API_OUTPUT_LIMIT")
    if result.returncode:
        raise HeartbeatContractError("LEDGER_RULESET_API_FAILED")
    return _strict_json_loads(
        result.stdout,
        "LEDGER_RULESET_API_INVALID_JSON",
    )


def observe_ledger_ref_control(
    *, repository: str, source_head: str, source_run_id: int,
    observer_run_id: int = 1, observer_run_attempt: int = 1,
    observation_phase: str = "INITIAL",
    ledger_ref: str = LEDGER_REF, ledger_transition: str = "NONE",
) -> dict[str, Any]:
    try:
        common = _ledger_control_common(
            repository=repository,
            source_head=source_head,
            source_run_id=source_run_id,
            observer_run_id=observer_run_id,
            observer_run_attempt=observer_run_attempt,
            observation_phase=observation_phase,
            ledger_ref=ledger_ref,
            ledger_transition=ledger_transition,
        )
        branch = common["ledger_branch"]
        headers = [
            "-H", "Accept: application/vnd.github+json",
            "-H", "X-GitHub-Api-Version: 2022-11-28",
        ]
        endpoint = (
            f"repos/{repository}/rules/branches/{quote(branch, safe='')}?per_page=100"
        )
        pages = _gh_json(["gh", "api", "--paginate", "--slurp", *headers, endpoint])
        effective_rules = flatten_ledger_rule_pages(pages)
        _, grouped = _effective_ledger_rule_projection(
            effective_rules,
            repository=repository,
        )
        candidate_ids = sorted(
            ruleset_id for ruleset_id, types in grouped.items()
            if LEDGER_REQUIRED_RULE_TYPES.issubset(types)
        )
        details: dict[int, Mapping[str, Any]] = {}
        for ruleset_id in candidate_ids:
            detail = _gh_json([
                "gh", "api", *headers,
                f"repos/{repository}/rulesets/{ruleset_id}?includes_parents=true",
            ])
            if not isinstance(detail, Mapping):
                raise HeartbeatContractError("LEDGER_RULESET_DETAIL_INVALID")
            details[ruleset_id] = detail
        return evaluate_ledger_ref_control(
            effective_rules,
            details,
            repository=repository,
            source_head=source_head,
            source_run_id=source_run_id,
            observer_run_id=observer_run_id,
            observer_run_attempt=observer_run_attempt,
            observation_phase=observation_phase,
            ledger_ref=ledger_ref,
            ledger_transition=ledger_transition,
        )
    except HeartbeatContractError as exc:
        blocker = str(exc)
        if not re.fullmatch(r"[A-Z0-9_]{1,128}", blocker):
            blocker = "LEDGER_RULESET_OBSERVATION_INVALID"
        return ledger_ref_control_reobserve(
            repository=repository,
            source_head=source_head,
            source_run_id=source_run_id,
            observer_run_id=observer_run_id,
            observer_run_attempt=observer_run_attempt,
            observation_phase=observation_phase,
            ledger_ref=ledger_ref,
            blocker=blocker,
            ledger_transition=ledger_transition,
        )
    except Exception:
        return ledger_ref_control_reobserve(
            repository=repository,
            source_head=source_head,
            source_run_id=source_run_id,
            observer_run_id=observer_run_id,
            observer_run_attempt=observer_run_attempt,
            observation_phase=observation_phase,
            ledger_ref=ledger_ref,
            blocker="LEDGER_RULESET_OBSERVATION_UNEXPECTED",
            ledger_transition=ledger_transition,
        )


def _verify_ledger_protection_snapshot(
    value: Any,
    ledger_ref: str,
    repository: str,
) -> tuple[list[int], str]:
    if not isinstance(value, Mapping) or set(value) != {
        "ledger_ref", "effective_rules", "candidate_rulesets",
        "required_rule_types_on_one_ruleset",
    }:
        raise HeartbeatContractError("ledger control snapshot fields are not exact")
    if value["ledger_ref"] != ledger_ref:
        raise HeartbeatContractError("ledger control snapshot ref mismatch")
    if value["required_rule_types_on_one_ruleset"] != sorted(
        LEDGER_REQUIRED_RULE_TYPES
    ):
        raise HeartbeatContractError("ledger control snapshot rules mismatch")
    effective_rules = value["effective_rules"]
    projection, grouped = _effective_ledger_rule_projection(
        effective_rules,
        repository=repository,
    )
    if projection != effective_rules:
        raise HeartbeatContractError("ledger control effective rules are not canonical")
    candidates = value["candidate_rulesets"]
    if not isinstance(candidates, list) or not all(
        isinstance(candidate, Mapping) for candidate in candidates
    ):
        raise HeartbeatContractError("ledger control candidates are invalid")
    expected_ids = sorted(
        ruleset_id for ruleset_id, types in grouped.items()
        if LEDGER_REQUIRED_RULE_TYPES.issubset(types)
    )
    observed_ids: list[int] = []
    qualifying: list[int] = []
    blockers: list[str] = []
    expected_fields = {
        "ruleset_id", "source_type", "source", "target", "enforcement",
        "include", "exclude", "rule_types", "bypass_actors_visible",
        "bypass_actors", "effective_source_type", "effective_source",
    }
    for candidate in candidates:
        if set(candidate) != expected_fields:
            raise HeartbeatContractError("ledger control candidate fields are not exact")
        ruleset_id = candidate["ruleset_id"]
        if (
            isinstance(ruleset_id, bool)
            or not isinstance(ruleset_id, int)
            or ruleset_id <= 0
        ):
            raise HeartbeatContractError("ledger control candidate ID is invalid")
        observed_ids.append(ruleset_id)
        includes = _string_list(candidate["include"], "snapshot include")
        excludes = _string_list(candidate["exclude"], "snapshot exclude")
        rule_types = _rule_type_list(
            candidate["rule_types"],
            "snapshot rule types",
        )
        if (
            includes != candidate["include"]
            or excludes != candidate["exclude"]
            or rule_types != candidate["rule_types"]
        ):
            raise HeartbeatContractError("ledger control candidate is not canonical")
        bypass_visible = candidate["bypass_actors_visible"]
        bypass = candidate["bypass_actors"]
        if not isinstance(bypass_visible, bool):
            raise HeartbeatContractError("ledger control bypass visibility is invalid")
        if bypass_visible:
            if not isinstance(bypass, list) or not all(
                isinstance(actor, Mapping) for actor in bypass
            ):
                raise HeartbeatContractError("ledger control bypass list is invalid")
            try:
                canonical_bypass = sorted(
                    (dict(actor) for actor in bypass),
                    key=canonical_json_bytes,
                )
            except (HeartbeatContractError, TypeError, ValueError) as exc:
                raise HeartbeatContractError(
                    "ledger control bypass list is not canonical"
                ) from exc
            if bypass != canonical_bypass:
                raise HeartbeatContractError(
                    "ledger control bypass list is not canonical"
                )
        elif bypass is not None:
            raise HeartbeatContractError("hidden bypass data must be null")
        effective_sources = {
            (item["ruleset_source_type"], item["ruleset_source"])
            for item in projection
            if item["ruleset_id"] == ruleset_id
        }
        if (
            len(effective_sources) != 1
            or any(
                not isinstance(source_value, str) or not source_value
                for source_value in next(iter(effective_sources))
            )
        ):
            raise HeartbeatContractError(
                "ledger control effective source binding is invalid"
            )
        derived_source_type, derived_source = next(iter(effective_sources))
        if (
            candidate["effective_source_type"] != derived_source_type
            or candidate["effective_source"] != derived_source
        ):
            raise HeartbeatContractError(
                "ledger control effective source binding mismatch"
            )
        candidate_source_type, candidate_source = _validate_ruleset_source(
            repository,
            candidate["source_type"],
            candidate["source"],
        )
        if (
            candidate_source_type != derived_source_type
            or candidate_source != derived_source
        ):
            raise HeartbeatContractError(
                "LEDGER_RULESET_SOURCE_BINDING_MISMATCH"
            )
        target = candidate["target"]
        enforcement = candidate["enforcement"]
        if (
            not isinstance(target, str)
            or not target
            or not isinstance(enforcement, str)
            or not enforcement
        ):
            raise HeartbeatContractError(
                "ledger control candidate state is invalid"
            )
        if (
            target != "branch"
            or enforcement != "active"
            or not LEDGER_REQUIRED_RULE_TYPES.issubset(rule_types)
        ):
            raise HeartbeatContractError(
                "LEDGER_RULESET_EFFECTIVE_DETAIL_CONTRADICTION"
            )
        qualifies = (
            ledger_ref in includes
            and excludes == []
            and bypass_visible is True
            and bypass == []
        )
        if qualifies:
            qualifying.append(ruleset_id)
        elif not bypass_visible:
            blockers.append("LEDGER_RULESET_BYPASS_VISIBILITY_REQUIRED")
        elif bypass != []:
            blockers.append("LEDGER_RULESET_BYPASS_PRESENT")
        elif ledger_ref not in includes:
            blockers.append("LEDGER_RULESET_LITERAL_INCLUDE_MISSING")
        elif excludes != []:
            blockers.append("LEDGER_RULESET_EXCLUDE_PRESENT")
        else:
            blockers.append("LEDGER_IMMUTABILITY_RULESET_NOT_ACTIVE")
    if observed_ids != expected_ids or observed_ids != sorted(set(observed_ids)):
        raise HeartbeatContractError("ledger control candidate IDs mismatch")
    return (
        sorted(qualifying),
        blockers[0] if blockers else "LEDGER_IMMUTABILITY_RULESET_NOT_ACTIVE",
    )


def verify_ledger_ref_control_receipt(
    value: Any,
    *,
    expected_snapshot_sha256: str | None = None,
    allow_noncontrol_state: bool = False,
) -> dict[str, Any]:
    if type(allow_noncontrol_state) is not bool:
        raise HeartbeatContractError(
            "allow_noncontrol_state must be an exact Boolean"
        )
    if not isinstance(value, Mapping) or value.get("schema") != LEDGER_REF_CONTROL_SCHEMA:
        raise HeartbeatContractError("ledger control receipt schema mismatch")
    observation_complete = value.get("observation_complete")
    common_fields = {
        "schema", "repository", "source_head", "source_run_id",
        "observer_run_id", "observer_run_attempt", "observation_phase",
        "ledger_ref",
        "ledger_branch", "observation_endpoint", "api_version",
        "required_rule_types_on_one_ruleset", "ledger_transition_before_observation",
        "repository_ruleset_mutation_performed", "ruleset_push_atomicity_observed",
        "post_readback_control_is_detection_not_prevention", "completion_claims",
        "observation_complete", "state", "d0", "first_blocker",
        "ledger_write_guard_satisfied", "protection_snapshot",
        "protection_snapshot_sha256", "qualifying_ruleset_ids",
        "selected_ruleset_id", "productive_effect_released_by_observation",
        "receipt_sha256",
    }
    reobserve_fields = {
        "comparison_performed", "expected_protection_snapshot_sha256",
        "observed_protection_snapshot_sha256",
    }
    expected_fields = (
        common_fields if observation_complete is True
        else common_fields | reobserve_fields if observation_complete is False
        else set()
    )
    if set(value) != expected_fields:
        raise HeartbeatContractError("ledger control receipt fields are not exact")
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256")
    if seal != canonical_sha256(unsigned):
        raise HeartbeatContractError("ledger control receipt seal mismatch")
    expected_common = _ledger_control_common(
        repository=value["repository"],
        source_head=value["source_head"],
        source_run_id=value["source_run_id"],
        observer_run_id=value["observer_run_id"],
        observer_run_attempt=value["observer_run_attempt"],
        observation_phase=value["observation_phase"],
        ledger_ref=value["ledger_ref"],
        ledger_transition=value["ledger_transition_before_observation"],
    )
    for key, expected in expected_common.items():
        if value.get(key) != expected:
            raise HeartbeatContractError("ledger control common binding mismatch")
    if value.get("repository_ruleset_mutation_performed") is not False:
        raise HeartbeatContractError("ledger control manufactured ruleset mutation")
    if value.get("ruleset_push_atomicity_observed") is not False:
        raise HeartbeatContractError("ledger control manufactured atomicity")
    if value.get("post_readback_control_is_detection_not_prevention") is not True:
        raise HeartbeatContractError("ledger control detection boundary mismatch")
    if value.get("productive_effect_released_by_observation") is not False:
        raise HeartbeatContractError("ledger control manufactured productive effect")
    completion_claims = value.get("completion_claims")
    if (
        not isinstance(completion_claims, Mapping)
        or set(completion_claims) != {
            "PASS", "FINAL_PASS", "EFFECT_ACK_DONE", "MERGE", "DEPLOYMENT",
        }
        or any(claim is not False for claim in completion_claims.values())
    ):
        raise HeartbeatContractError("ledger control completion claims are invalid")

    if observation_complete is False:
        if (
            value.get("state") != "REOBSERVE"
            or isinstance(value.get("d0"), bool)
            or not isinstance(value.get("d0"), int)
            or value.get("d0") != 2
            or value.get("ledger_write_guard_satisfied") is not False
            or value.get("protection_snapshot") is not None
            or value.get("protection_snapshot_sha256") is not None
            or value.get("qualifying_ruleset_ids") != []
            or value.get("selected_ruleset_id") is not None
            or not isinstance(value.get("first_blocker"), str)
            or not re.fullmatch(r"[A-Z0-9_]{1,128}", value["first_blocker"])
        ):
            raise HeartbeatContractError("ledger control reobserve state mismatch")
        compared = value.get("comparison_performed")
        expected = value.get("expected_protection_snapshot_sha256")
        observed = value.get("observed_protection_snapshot_sha256")
        if compared is True:
            _sha256(expected, "expected_protection_snapshot_sha256")
            _sha256(observed, "observed_protection_snapshot_sha256")
            if (
                value.get("first_blocker")
                != "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT"
                or expected == observed
                or value.get("observation_phase") == "INITIAL"
            ):
                raise HeartbeatContractError(
                    "ledger control comparison semantics are invalid"
                )
        elif (
            compared is not False
            or expected is not None
            or observed is not None
            or value.get("first_blocker")
            == "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT"
        ):
            raise HeartbeatContractError("ledger control comparison mismatch")
        if allow_noncontrol_state:
            return dict(value)
        raise HeartbeatContractError("LEDGER_REF_CONTROL_REOBSERVE")

    snapshot_sha256 = value.get("protection_snapshot_sha256")
    _sha256(snapshot_sha256, "protection_snapshot_sha256")
    protection_snapshot = value.get("protection_snapshot")
    if canonical_sha256(protection_snapshot) != snapshot_sha256:
        raise HeartbeatContractError("ledger control snapshot digest mismatch")
    qualifying, recomputed_blocker = _verify_ledger_protection_snapshot(
        protection_snapshot,
        value["ledger_ref"],
        value["repository"],
    )
    observed_qualifying = value.get("qualifying_ruleset_ids")
    if (
        not isinstance(observed_qualifying, list)
        or any(
            isinstance(ruleset_id, bool)
            or not isinstance(ruleset_id, int)
            or ruleset_id <= 0
            for ruleset_id in observed_qualifying
        )
        or observed_qualifying != sorted(set(observed_qualifying))
        or observed_qualifying != qualifying
    ):
        raise HeartbeatContractError("ledger control qualifying IDs mismatch")
    selected_ruleset_id = value.get("selected_ruleset_id")
    if selected_ruleset_id is not None and (
        isinstance(selected_ruleset_id, bool)
        or not isinstance(selected_ruleset_id, int)
        or selected_ruleset_id <= 0
    ):
        raise HeartbeatContractError("ledger control selected ID is invalid")
    if qualifying:
        if (
            value.get("state") != "CONTROL_OBSERVED"
            or value.get("d0") is not None
            or value.get("first_blocker") is not None
            or value.get("ledger_write_guard_satisfied") is not True
            or value.get("selected_ruleset_id") != min(qualifying)
        ):
            raise HeartbeatContractError("ledger control success state mismatch")
    else:
        if (
            value.get("state") != "REQUEST_AUTHORITY"
            or isinstance(value.get("d0"), bool)
            or not isinstance(value.get("d0"), int)
            or value.get("d0") != 3
            or value.get("ledger_write_guard_satisfied") is not False
            or value.get("selected_ruleset_id") is not None
            or value.get("first_blocker") != recomputed_blocker
            or not isinstance(value.get("first_blocker"), str)
            or not re.fullmatch(r"[A-Z0-9_]{1,128}", value["first_blocker"])
        ):
            raise HeartbeatContractError("ledger control authority state mismatch")
        if allow_noncontrol_state:
            return dict(value)
        raise HeartbeatContractError("LEDGER_REF_CONTROL_REQUEST_AUTHORITY")
    if expected_snapshot_sha256 is not None and snapshot_sha256 != expected_snapshot_sha256:
        raise HeartbeatContractError("LEDGER_REF_CONTROL_SNAPSHOT_DRIFT")
    return dict(value)


def _sha1(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA1_RE.fullmatch(value):
        raise HeartbeatContractError(f"{label} must be a lowercase Git SHA-1")
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise HeartbeatContractError(f"{label} must be a canonical sha256 reference")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise HeartbeatContractError(f"{label} must be a bounded identifier")
    return value


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise HeartbeatContractError(f"{label} must be a non-negative integer")
    return value


def heartbeat_digest(value: Mapping[str, Any]) -> str:
    return canonical_sha256(dict(value))


def build_heartbeat(
    *, node_id: str, pair_id: str, role: str, sequence: int,
    scheduled_monotonic_ns: int, sent_monotonic_ns: int,
    previous_heartbeat_sha256: str, source_head: str, source_tree: str,
) -> dict[str, Any]:
    value = {
        "schema": HEARTBEAT_SCHEMA,
        "node_id": node_id,
        "pair_id": pair_id,
        "role": role,
        "sequence": sequence,
        "scheduled_monotonic_ns": scheduled_monotonic_ns,
        "sent_monotonic_ns": sent_monotonic_ns,
        "lease_expires_monotonic_ns": scheduled_monotonic_ns + 2 * HEARTBEAT_INTERVAL_NS,
        "previous_heartbeat_sha256": previous_heartbeat_sha256,
        "source_head": source_head,
        "source_tree": source_tree,
        "heartbeat_hz": HEARTBEAT_HZ,
        "heartbeat_role": HEARTBEAT_ROLE,
        "semantic_work_triggered": False,
        "polling": False,
        "blind_retry": False,
        "external_effect": EXTERNAL_EFFECT,
    }
    return normalize_heartbeat(value)


def normalize_heartbeat(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HeartbeatContractError("heartbeat must be an object")
    required = {
        "schema", "node_id", "pair_id", "role", "sequence",
        "scheduled_monotonic_ns", "sent_monotonic_ns",
        "lease_expires_monotonic_ns", "previous_heartbeat_sha256",
        "source_head", "source_tree", "heartbeat_hz", "heartbeat_role",
        "semantic_work_triggered", "polling", "blind_retry", "external_effect",
    }
    if set(value) != required:
        raise HeartbeatContractError("heartbeat fields are not exact")
    sequence = _integer(value["sequence"], "sequence")
    scheduled = _integer(value["scheduled_monotonic_ns"], "scheduled_monotonic_ns")
    sent = _integer(value["sent_monotonic_ns"], "sent_monotonic_ns")
    lease = _integer(value["lease_expires_monotonic_ns"], "lease_expires_monotonic_ns")
    if value["schema"] != HEARTBEAT_SCHEMA or value["heartbeat_hz"] != 1:
        raise HeartbeatContractError("heartbeat schema or rate mismatch")
    if value["role"] not in {"AUTHORITY", "MIRROR"}:
        raise HeartbeatContractError("heartbeat role mismatch")
    if lease != scheduled + 2 * HEARTBEAT_INTERVAL_NS:
        raise HeartbeatContractError("heartbeat lease interval is not exact")
    if value["heartbeat_role"] != HEARTBEAT_ROLE:
        raise HeartbeatContractError("heartbeat role is not liveness-only")
    if value["semantic_work_triggered"] is not False:
        raise HeartbeatContractError("heartbeat may not trigger semantic work")
    if value["polling"] is not False:
        raise HeartbeatContractError("heartbeat may not poll")
    if value["blind_retry"] is not False:
        raise HeartbeatContractError("heartbeat may not blind-retry")
    if value["external_effect"] != EXTERNAL_EFFECT:
        raise HeartbeatContractError("heartbeat external effect must remain NONE")
    previous = value["previous_heartbeat_sha256"]
    if sequence == 0:
        if previous != "GENESIS":
            raise HeartbeatContractError("first heartbeat must bind GENESIS")
    else:
        _sha256(previous, "previous heartbeat")
    return {
        **dict(value),
        "node_id": _identifier(value["node_id"], "node_id"),
        "pair_id": _identifier(value["pair_id"], "pair_id"),
        "source_head": _sha1(value["source_head"], "source_head"),
        "source_tree": _sha1(value["source_tree"], "source_tree"),
        "sequence": sequence,
        "scheduled_monotonic_ns": scheduled,
        "sent_monotonic_ns": sent,
        "lease_expires_monotonic_ns": lease,
    }


def build_work_event(*, source_head: str, source_tree: str) -> dict[str, Any]:
    payload = {
        "operation": "HASH_BOUND_MESH_AUDIT",
        "nonce": "heartbeat-work-0001",
        "external_effect": EXTERNAL_EFFECT,
    }
    return {
        "schema": WORK_EVENT_SCHEMA,
        "event_id": "mesh-work-0001",
        "payload": payload,
        "payload_sha256": canonical_sha256(payload),
        "source_head": _sha1(source_head, "source_head"),
        "source_tree": _sha1(source_tree, "source_tree"),
        "authority_scope": AUTHORITY_EFFECT_SCOPE,
        "construction_scope": "LOCAL_SYSTEM_TEST",
        "external_ingress_authentication_observed": False,
    }


def normalize_work_event(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise HeartbeatContractError("work event must be an object")
    required = {
        "schema", "event_id", "payload", "payload_sha256",
        "source_head", "source_tree", "authority_scope",
        "construction_scope", "external_ingress_authentication_observed",
    }
    if set(value) != required or value["schema"] != WORK_EVENT_SCHEMA:
        raise HeartbeatContractError("work event fields are not exact")
    if value["payload_sha256"] != canonical_sha256(value["payload"]):
        raise HeartbeatContractError("work event payload digest mismatch")
    if value["authority_scope"] != AUTHORITY_EFFECT_SCOPE:
        raise HeartbeatContractError("work event authority scope mismatch")
    if value["construction_scope"] != "LOCAL_SYSTEM_TEST":
        raise HeartbeatContractError("work event construction scope mismatch")
    if value["external_ingress_authentication_observed"] is not False:
        raise HeartbeatContractError(
            "work event may not manufacture external ingress authentication"
        )
    return {
        **copy.deepcopy(dict(value)),
        "event_id": _identifier(value["event_id"], "event_id"),
        "payload_sha256": _sha256(value["payload_sha256"], "payload_sha256"),
        "source_head": _sha1(value["source_head"], "source_head"),
        "source_tree": _sha1(value["source_tree"], "source_tree"),
    }


@dataclass
class WorkRing:
    state: str = "0"
    latest_lease_by_node: dict[str, int] = field(default_factory=dict)
    receipts: dict[str, dict[str, Any]] = field(default_factory=dict)
    payloads: dict[str, str] = field(default_factory=dict)
    authority_ledger: list[dict[str, Any]] = field(default_factory=list)
    heartbeat_semantic_work_count: int = 0
    polling_count: int = 0
    blind_retry_count: int = 0

    def observe_heartbeat(self, value: Any) -> None:
        heartbeat = normalize_heartbeat(value)
        before = self.state
        self.latest_lease_by_node[heartbeat["node_id"]] = heartbeat["lease_expires_monotonic_ns"]
        if self.state != before or self.state != "0":
            self.heartbeat_semantic_work_count += 1
            raise HeartbeatContractError("heartbeat changed semantic work state")

    def execute(self, value: Any) -> dict[str, Any]:
        event = normalize_work_event(value)
        event_id = event["event_id"]
        digest = event["payload_sha256"]
        if event_id in self.payloads:
            if self.payloads[event_id] != digest:
                raise HeartbeatContractError("event_id reuse with different payload is forbidden")
            return copy.deepcopy(self.receipts[event_id])
        if self.state != "0":
            raise HeartbeatContractError("work ring is not quiescent")
        transitions = ["0"]
        self.state = "1"; transitions.append(self.state)
        self.state = "ARBEIT"; transitions.append(self.state)
        result_sha = canonical_sha256({
            "event_id": event_id, "payload_sha256": digest,
            "source_head": event["source_head"], "source_tree": event["source_tree"],
        })
        self.state = "ERGEBNIS"; transitions.append(self.state)
        if result_sha != canonical_sha256({
            "event_id": event_id, "payload_sha256": digest,
            "source_head": event["source_head"], "source_tree": event["source_tree"],
        }):
            raise HeartbeatContractError("result reobservation mismatch")
        self.state = "REOBSERVATION"; transitions.append(self.state)
        previous = self.authority_ledger[-1]["record_sha256"] if self.authority_ledger else "GENESIS"
        record = {
            "schema": AUTHORITY_LEDGER_SCHEMA,
            "index": len(self.authority_ledger),
            "event_id": event_id,
            "result_sha256": result_sha,
            "previous_record_sha256": previous,
            "authority_scope": AUTHORITY_EFFECT_SCOPE,
            "external_effect": EXTERNAL_EFFECT,
        }
        record["record_sha256"] = canonical_sha256(record)
        self.authority_ledger.append(record)
        self.state = "AUTHORITY_EFFEKT"; transitions.append(self.state)
        self.state = "0"; transitions.append(self.state)
        if transitions != LIFECYCLE:
            raise HeartbeatContractError("work lifecycle mismatch")
        receipt = {
            "schema": WORK_RECEIPT_SCHEMA,
            "event_id": event_id,
            "payload_sha256": digest,
            "result_sha256": result_sha,
            "lifecycle": transitions,
            "local_authority_effect_reobserved": True,
            "repository_authority_effect_observed": False,
            "authority_effect_scope": AUTHORITY_EFFECT_SCOPE,
            "external_effect": EXTERNAL_EFFECT,
            "general_effect_ack_done": False,
        }
        receipt["receipt_sha256"] = canonical_sha256(receipt)
        self.payloads[event_id] = digest
        self.receipts[event_id] = copy.deepcopy(receipt)
        return receipt


@dataclass
class Collector:
    expected_total: int
    source_head: str
    source_tree: str
    events: list[dict[str, Any]] = field(default_factory=list)
    done: asyncio.Event = field(default_factory=asyncio.Event)
    failure: BaseException | None = None

    async def handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while len(self.events) < self.expected_total:
                line = await asyncio.wait_for(reader.readline(), timeout=5.0)
                if not line:
                    break
                heartbeat = normalize_heartbeat(json.loads(line.decode("utf-8")))
                if heartbeat["source_head"] != self.source_head or heartbeat["source_tree"] != self.source_tree:
                    raise HeartbeatContractError("collector source binding mismatch")
                digest = heartbeat_digest(heartbeat)
                self.events.append({
                    "heartbeat": heartbeat,
                    "heartbeat_sha256": digest,
                    "arrival_monotonic_ns": time.monotonic_ns(),
                })
                ack = {
                    "node_id": heartbeat["node_id"],
                    "sequence": heartbeat["sequence"],
                    "heartbeat_sha256": digest,
                    "semantic_work_triggered": False,
                    "external_effect": EXTERNAL_EFFECT,
                }
                writer.write(canonical_json_bytes(ack) + b"\n")
                await writer.drain()
                if len(self.events) == self.expected_total:
                    self.done.set()
        except BaseException as exc:
            self.failure = self.failure or exc
            self.done.set()
        finally:
            writer.close()
            await writer.wait_closed()


async def emit_heartbeats(
    *, host: str, port: int, node_id: str, pair_id: str, role: str,
    source_head: str, source_tree: str, start_monotonic_ns: int, count: int,
) -> None:
    reader, writer = await asyncio.open_connection(host, port)
    previous = "GENESIS"
    try:
        for sequence in range(count):
            scheduled = start_monotonic_ns + sequence * HEARTBEAT_INTERVAL_NS
            await asyncio.sleep(max(0.0, (scheduled - time.monotonic_ns()) / 1_000_000_000))
            heartbeat = build_heartbeat(
                node_id=node_id, pair_id=pair_id, role=role, sequence=sequence,
                scheduled_monotonic_ns=scheduled, sent_monotonic_ns=time.monotonic_ns(),
                previous_heartbeat_sha256=previous,
                source_head=source_head, source_tree=source_tree,
            )
            digest = heartbeat_digest(heartbeat)
            writer.write(canonical_json_bytes(heartbeat) + b"\n")
            await writer.drain()
            ack = json.loads((await asyncio.wait_for(reader.readline(), timeout=3.0)).decode("utf-8"))
            if ack != {
                "node_id": node_id,
                "sequence": sequence,
                "heartbeat_sha256": digest,
                "semantic_work_triggered": False,
                "external_effect": EXTERNAL_EFFECT,
            }:
                raise HeartbeatContractError("heartbeat acknowledgement mismatch")
            previous = digest
    finally:
        writer.close()
        await writer.wait_closed()


def verify_history(events: Sequence[Mapping[str, Any]], count_per_node: int) -> dict[str, int | bool]:
    by_node = {node_id: [] for node_id, _, _ in NODE_SPECS}
    for record in events:
        heartbeat = normalize_heartbeat(record["heartbeat"])
        if heartbeat["node_id"] not in by_node or record["heartbeat_sha256"] != heartbeat_digest(heartbeat):
            raise HeartbeatContractError("unexpected heartbeat history")
        by_node[heartbeat["node_id"]].append(record)
    max_lateness = 0
    max_gap = 0
    for node_id, records in by_node.items():
        records.sort(key=lambda item: item["heartbeat"]["sequence"])
        if len(records) != count_per_node:
            raise HeartbeatContractError(f"heartbeat count mismatch for {node_id}")
        previous = "GENESIS"
        scheduled: int | None = None
        arrival: int | None = None
        for sequence, record in enumerate(records):
            heartbeat = record["heartbeat"]
            if heartbeat["sequence"] != sequence or heartbeat["previous_heartbeat_sha256"] != previous:
                raise HeartbeatContractError("heartbeat chain is not contiguous")
            if scheduled is not None and heartbeat["scheduled_monotonic_ns"] - scheduled != HEARTBEAT_INTERVAL_NS:
                raise HeartbeatContractError("heartbeat schedule is not exactly 1/s")
            lateness = max(0, heartbeat["sent_monotonic_ns"] - heartbeat["scheduled_monotonic_ns"])
            if lateness > MAX_SEND_LATENESS_NS:
                raise HeartbeatContractError("heartbeat lateness exceeds bound")
            max_lateness = max(max_lateness, lateness)
            if arrival is not None:
                max_gap = max(max_gap, record["arrival_monotonic_ns"] - arrival)
            previous = record["heartbeat_sha256"]
            scheduled = heartbeat["scheduled_monotonic_ns"]
            arrival = record["arrival_monotonic_ns"]
    return {
        "node_count": len(NODE_SPECS),
        "pair_count": 2,
        "total_heartbeats": len(events),
        "max_send_lateness_ns": max_lateness,
        "max_arrival_gap_ns": max_gap,
        "heartbeat_chain_verified": True,
        "scheduled_one_hertz_verified": True,
    }


async def run_demo(
    *, source_head: str, source_tree: str, output_dir: pathlib.Path,
    heartbeat_count: int, event_name: str, run_id: int,
) -> dict[str, Any]:
    _sha1(source_head, "source_head"); _sha1(source_tree, "source_tree")
    if heartbeat_count not in range(2, 11):
        raise HeartbeatContractError("heartbeat_count must be in 2..10")
    if event_name not in {"pull_request", "push", "workflow_dispatch", "local"}:
        raise HeartbeatContractError("unexpected event name")
    collector = Collector(len(NODE_SPECS) * heartbeat_count, source_head, source_tree)
    server = await asyncio.start_server(collector.handle, "127.0.0.1", 0)
    host, port = server.sockets[0].getsockname()[:2]
    start_ns = time.monotonic_ns() + 250_000_000
    processes: list[asyncio.subprocess.Process] = []
    try:
        for node_id, pair_id, role in NODE_SPECS:
            processes.append(await asyncio.create_subprocess_exec(
                sys.executable, "-B", str(pathlib.Path(__file__).resolve()), "emit",
                "--host", host, "--port", str(port), "--node-id", node_id,
                "--pair-id", pair_id, "--role", role, "--source-head", source_head,
                "--source-tree", source_tree, "--start-monotonic-ns", str(start_ns),
                "--count", str(heartbeat_count),
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            ))
        await asyncio.wait_for(collector.done.wait(), timeout=heartbeat_count + 6.0)
        if collector.failure:
            raise collector.failure
        for process in processes:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=3.0)
            if process.returncode:
                raise HeartbeatTransportError((stderr + stdout).decode("utf-8", errors="replace"))
    finally:
        server.close(); await server.wait_closed()
        for process in processes:
            if process.returncode is None:
                process.terminate(); await process.wait()

    metrics = verify_history(collector.events, heartbeat_count)
    ring = WorkRing()
    for record in collector.events:
        ring.observe_heartbeat(record["heartbeat"])
    event = build_work_event(source_head=source_head, source_tree=source_tree)
    work_receipt = ring.execute(event)
    replay_identical = canonical_json_bytes(ring.execute(event)) == canonical_json_bytes(work_receipt)
    tampered = copy.deepcopy(event)
    tampered["payload"]["nonce"] = "heartbeat-work-tampered"
    tampered["payload_sha256"] = canonical_sha256(tampered["payload"])
    tamper_blocked = False
    try:
        ring.execute(tampered)
    except HeartbeatContractError:
        tamper_blocked = True
    if not replay_identical or not tamper_blocked or len(ring.authority_ledger) != 1:
        raise HeartbeatContractError("work-ring replay or tamper contract failed")

    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "heartbeats": output_dir / "heartbeats.jsonl",
        "work": output_dir / "work-receipt.json",
        "ledger": output_dir / "authority-ledger.json",
    }
    files["heartbeats"].write_bytes(b"".join(canonical_json_bytes(x) + b"\n" for x in collector.events))
    files["work"].write_bytes(canonical_json_bytes(work_receipt) + b"\n")
    files["ledger"].write_bytes(canonical_json_bytes(ring.authority_ledger) + b"\n")
    audit = {
        "schema": AUDIT_SCHEMA,
        "repository": os.environ.get("GITHUB_REPOSITORY", "Goldkelch/qik-vrt"),
        "event": event_name,
        "run_id": run_id,
        "source_head": source_head,
        "source_tree": source_tree,
        "network_scope": NETWORK_SCOPE,
        "heartbeat_hz": HEARTBEAT_HZ,
        "heartbeat_role": HEARTBEAT_ROLE,
        "node_process_count": metrics["node_count"],
        "pair_count": metrics["pair_count"],
        "heartbeats_per_node": heartbeat_count,
        "total_heartbeats": metrics["total_heartbeats"],
        "heartbeat_chain_verified": True,
        "scheduled_one_hertz_verified": True,
        "scheduled_interval_ns": HEARTBEAT_INTERVAL_NS,
        "max_send_lateness_ns": metrics["max_send_lateness_ns"],
        "max_arrival_gap_ns": metrics["max_arrival_gap_ns"],
        "heartbeat_semantic_work_count": ring.heartbeat_semantic_work_count,
        "polling_count": ring.polling_count,
        "blind_retry_count": ring.blind_retry_count,
        "locally_constructed_content_bound_work_event_count": 1,
        "external_ingress_authentication_observed": False,
        "work_lifecycle": work_receipt["lifecycle"],
        "duplicate_event_replay_byte_identical": replay_identical,
        "event_id_payload_rebinding_blocked": tamper_blocked,
        "local_authority_effect_reobserved": True,
        "repository_authority_effect_observed": False,
        "authority_effect_scope": AUTHORITY_EFFECT_SCOPE,
        "external_effect": EXTERNAL_EFFECT,
        "general_effect_ack_done": False,
        "physical_hardware_execution_observed": False,
        "publication_observed": False,
        "deployment_observed": False,
        "pass": False,
        "final_pass": False,
        "heartbeats_sha256": sha256_ref(files["heartbeats"].read_bytes()),
        "work_receipt_sha256": sha256_ref(files["work"].read_bytes()),
        "authority_ledger_sha256": sha256_ref(files["ledger"].read_bytes()),
    }
    verify_audit(audit, source_head=source_head, source_tree=source_tree)
    (output_dir / "execution-receipt.json").write_bytes(canonical_json_bytes(audit) + b"\n")
    return audit


def verify_audit(value: Any, *, source_head: str, source_tree: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or value.get("schema") != AUDIT_SCHEMA:
        raise HeartbeatContractError("unexpected audit schema")
    if value.get("source_head") != _sha1(source_head, "source_head") or value.get("source_tree") != _sha1(source_tree, "source_tree"):
        raise HeartbeatContractError("audit source binding mismatch")
    if value.get("network_scope") != NETWORK_SCOPE or value.get("heartbeat_hz") != 1 or value.get("heartbeat_role") != HEARTBEAT_ROLE:
        raise HeartbeatContractError("audit heartbeat contract mismatch")
    if value.get("node_process_count") != 4 or value.get("pair_count") != 2:
        raise HeartbeatContractError("audit topology mismatch")
    if value.get("total_heartbeats") != 4 * value.get("heartbeats_per_node", -1):
        raise HeartbeatContractError("audit heartbeat total mismatch")
    for key in (
        "heartbeat_chain_verified", "scheduled_one_hertz_verified",
        "duplicate_event_replay_byte_identical", "event_id_payload_rebinding_blocked",
        "local_authority_effect_reobserved",
    ):
        if value.get(key) is not True:
            raise HeartbeatContractError(f"audit {key} must be true")
    if value.get("scheduled_interval_ns") != HEARTBEAT_INTERVAL_NS or value.get("work_lifecycle") != LIFECYCLE:
        raise HeartbeatContractError("audit schedule or lifecycle mismatch")
    if value.get("locally_constructed_content_bound_work_event_count") != 1:
        raise HeartbeatContractError("audit must execute exactly one work event")
    for key in ("heartbeat_semantic_work_count", "polling_count", "blind_retry_count"):
        if value.get(key) != 0:
            raise HeartbeatContractError(f"audit {key} must be zero")
    if value.get("repository_authority_effect_observed") is not False:
        raise HeartbeatContractError("audit may not manufacture repository authority effect")
    if value.get("external_ingress_authentication_observed") is not False:
        raise HeartbeatContractError(
            "audit may not manufacture external ingress authentication"
        )
    if value.get("authority_effect_scope") != AUTHORITY_EFFECT_SCOPE or value.get("external_effect") != EXTERNAL_EFFECT:
        raise HeartbeatContractError("audit authority or external effect mismatch")
    for key in (
        "general_effect_ack_done", "physical_hardware_execution_observed",
        "publication_observed", "deployment_observed", "pass", "final_pass",
    ):
        if value.get(key) is not False:
            raise HeartbeatContractError(f"audit {key} must remain false")
    for key in ("heartbeats_sha256", "work_receipt_sha256", "authority_ledger_sha256"):
        _sha256(value.get(key), key)
    return dict(value)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("demo")
    demo.add_argument("--source-head", required=True); demo.add_argument("--source-tree", required=True)
    demo.add_argument("--output-dir", type=pathlib.Path, required=True)
    demo.add_argument("--heartbeat-count", type=int, default=4)
    demo.add_argument("--event", default=os.environ.get("GITHUB_EVENT_NAME", "local"))
    demo.add_argument("--run-id", type=int, default=int(os.environ.get("GITHUB_RUN_ID", "0")))
    emit = sub.add_parser("emit", help=argparse.SUPPRESS)
    for name in ("host", "node-id", "pair-id", "role", "source-head", "source-tree"):
        emit.add_argument("--" + name, required=True)
    emit.add_argument("--port", type=int, required=True)
    emit.add_argument("--start-monotonic-ns", type=int, required=True)
    emit.add_argument("--count", type=int, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--receipt", type=pathlib.Path, required=True)
    verify.add_argument("--source-head", required=True); verify.add_argument("--source-tree", required=True)
    ledger_control = sub.add_parser("ledger-ref-control")
    ledger_control.add_argument(
        "--repository", default=os.environ.get("GITHUB_REPOSITORY", "")
    )
    ledger_control.add_argument("--source-head", required=True)
    ledger_control.add_argument("--source-run-id", type=int, required=True)
    ledger_control.add_argument("--observer-run-id", type=int, required=True)
    ledger_control.add_argument("--observer-run-attempt", type=int, required=True)
    ledger_control.add_argument(
        "--observation-phase",
        choices=tuple(sorted(LEDGER_OBSERVATION_PHASES)),
        required=True,
    )
    ledger_control.add_argument("--ledger-ref", default=LEDGER_REF)
    ledger_control.add_argument(
        "--ledger-transition",
        choices=("NONE", "NOOP_ALREADY_CURRENT", "FAST_FORWARD_PUSHED"),
        default="NONE",
    )
    ledger_control.add_argument("--output", type=pathlib.Path, required=True)
    enforce_control = sub.add_parser("enforce-ledger-ref-control")
    enforce_control.add_argument("--receipt", type=pathlib.Path, required=True)
    enforce_control.add_argument(
        "--expected-snapshot-receipt", type=pathlib.Path
    )
    enforce_control.add_argument("--comparison-output", type=pathlib.Path)
    enforce_control.add_argument(
        "--repository", default=os.environ.get("GITHUB_REPOSITORY", "")
    )
    enforce_control.add_argument("--source-head", required=True)
    enforce_control.add_argument("--source-run-id", type=int, required=True)
    enforce_control.add_argument("--observer-run-id", type=int, required=True)
    enforce_control.add_argument(
        "--observer-run-attempt", type=int, required=True
    )
    enforce_control.add_argument(
        "--observation-phase",
        choices=tuple(sorted(LEDGER_OBSERVATION_PHASES)),
        required=True,
    )
    enforce_control.add_argument("--ledger-ref", default=LEDGER_REF)
    enforce_control.add_argument(
        "--ledger-transition",
        choices=("NONE", "NOOP_ALREADY_CURRENT", "FAST_FORWARD_PUSHED"),
        default="NONE",
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "emit":
        asyncio.run(emit_heartbeats(
            host=args.host, port=args.port, node_id=args.node_id, pair_id=args.pair_id,
            role=args.role, source_head=args.source_head, source_tree=args.source_tree,
            start_monotonic_ns=args.start_monotonic_ns, count=args.count,
        ))
        return 0
    if args.command == "ledger-ref-control":
        value = observe_ledger_ref_control(
            repository=args.repository,
            source_head=args.source_head,
            source_run_id=args.source_run_id,
            observer_run_id=args.observer_run_id,
            observer_run_attempt=args.observer_run_attempt,
            observation_phase=args.observation_phase,
            ledger_ref=args.ledger_ref,
            ledger_transition=args.ledger_transition,
        )
        args.output.write_bytes(canonical_json_bytes(value) + b"\n")
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    if args.command == "enforce-ledger-ref-control":
        value: Any = None
        baseline: Any = None
        try:
            value = _strict_json_loads(
                args.receipt.read_text(encoding="utf-8"),
                "LEDGER_REF_CONTROL_EVIDENCE_INVALID_JSON",
            )
            expected = None
            if args.expected_snapshot_receipt is not None:
                baseline = _strict_json_loads(
                    args.expected_snapshot_receipt.read_text(encoding="utf-8"),
                    "LEDGER_REF_CONTROL_EVIDENCE_INVALID_JSON",
                )
                verify_ledger_ref_control_receipt(baseline)
                expected = baseline["protection_snapshot_sha256"]
            verified = verify_ledger_ref_control_receipt(
                value,
                allow_noncontrol_state=True,
            )
            context_required = (
                args.expected_snapshot_receipt is not None
                or args.source_head is not None
                or args.source_run_id is not None
            )
            if context_required:
                if (
                    not args.repository
                    or args.source_head is None
                    or args.source_run_id is None
                    or args.observer_run_id is None
                    or args.observer_run_attempt is None
                ):
                    raise HeartbeatContractError(
                        "LEDGER_REF_CONTROL_CONTEXT_INCOMPLETE"
                    )
                expected_context = {
                    "repository": args.repository,
                    "source_head": args.source_head,
                    "source_run_id": args.source_run_id,
                    "observer_run_id": args.observer_run_id,
                    "observer_run_attempt": args.observer_run_attempt,
                    "ledger_ref": args.ledger_ref,
                }
                if (
                    any(
                        verified.get(key) != expected_value
                        for key, expected_value in expected_context.items()
                    )
                    or verified.get("observation_phase")
                    != args.observation_phase
                    or verified.get("ledger_transition_before_observation")
                    != args.ledger_transition
                ):
                    raise HeartbeatContractError(
                        "LEDGER_REF_CONTROL_CONTEXT_MISMATCH"
                    )
                if args.expected_snapshot_receipt is not None:
                    if (
                        args.observation_phase == "INITIAL"
                        or any(
                            baseline.get(key) != expected_value
                            for key, expected_value in expected_context.items()
                        )
                        or baseline.get("observation_phase") != "INITIAL"
                        or baseline.get("ledger_transition_before_observation")
                        != "NONE"
                    ):
                        raise HeartbeatContractError(
                            "LEDGER_REF_CONTROL_CONTEXT_MISMATCH"
                        )
                    if verified["state"] == "CONTROL_OBSERVED" and (
                        verified["protection_snapshot_sha256"] != expected
                    ):
                        raise HeartbeatContractError(
                            "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT"
                        )
                elif args.observation_phase != "INITIAL":
                    raise HeartbeatContractError(
                        "LEDGER_REF_CONTROL_BASELINE_REQUIRED"
                    )
        except Exception as exc:
            code = str(exc)
            print(code, file=sys.stderr)
            if args.comparison_output is not None:
                if (
                    not args.repository
                    or args.source_head is None
                    or args.source_run_id is None
                ):
                    print(
                        "ledger control comparison context is incomplete",
                        file=sys.stderr,
                    )
                    return 2
                blocker = (
                    "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT"
                    if code == "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT"
                    else "LEDGER_REF_CONTROL_EVIDENCE_INVALID"
                )
                expected_snapshot = None
                observed_snapshot = None
                if blocker == "LEDGER_REF_CONTROL_SNAPSHOT_DRIFT":
                    try:
                        expected_snapshot = baseline[
                            "protection_snapshot_sha256"
                        ]
                        observed_snapshot = value[
                            "protection_snapshot_sha256"
                        ]
                        _sha256(expected_snapshot, "expected_snapshot_sha256")
                        _sha256(observed_snapshot, "observed_snapshot_sha256")
                    except Exception:
                        blocker = "LEDGER_REF_CONTROL_EVIDENCE_INVALID"
                        expected_snapshot = None
                        observed_snapshot = None
                comparison = ledger_ref_control_reobserve(
                    repository=args.repository,
                    source_head=args.source_head,
                    source_run_id=args.source_run_id,
                    observer_run_id=args.observer_run_id,
                    observer_run_attempt=args.observer_run_attempt,
                    observation_phase=args.observation_phase,
                    ledger_ref=args.ledger_ref,
                    blocker=blocker,
                    ledger_transition=args.ledger_transition,
                    expected_snapshot_sha256=expected_snapshot,
                    observed_snapshot_sha256=observed_snapshot,
                )
                args.comparison_output.write_bytes(
                    canonical_json_bytes(comparison) + b"\n"
                )
            return 2
        if verified["state"] == "REQUEST_AUTHORITY":
            print("LEDGER_REF_CONTROL_REQUEST_AUTHORITY", file=sys.stderr)
            return 3
        if verified["state"] == "REOBSERVE":
            print("LEDGER_REF_CONTROL_REOBSERVE", file=sys.stderr)
            return 2
        print(
            "LEDGER_REF_CONTROL=OBSERVED "
            + str(verified["protection_snapshot_sha256"])
        )
        return 0
    if args.command == "demo":
        value = asyncio.run(run_demo(
            source_head=args.source_head, source_tree=args.source_tree,
            output_dir=args.output_dir, heartbeat_count=args.heartbeat_count,
            event_name=args.event, run_id=args.run_id,
        ))
    else:
        value = verify_audit(
            json.loads(args.receipt.read_text(encoding="utf-8")),
            source_head=args.source_head, source_tree=args.source_tree,
        )
    print(json.dumps(value, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
