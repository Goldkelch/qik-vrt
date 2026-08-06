#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Durable fail-closed work-queue orchestrator for bounded QIK-VRT work.

The controller performs only repository-internal, reversible work units that are
explicitly declared in ``state/autonomy/WORK_QUEUE_V2.json``.  Human judgment,
empirical work, cross-repository writes without configuration, and irreversible
external effects are represented as terminal waiting states and are never
silently converted into success.
"""
from __future__ import annotations

import argparse
import base64
import copy
import fnmatch
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

ROOT = pathlib.Path(os.environ.get("QIKVRT_ROOT", pathlib.Path(__file__).resolve().parents[1]))
CONTRACT_PATH = ROOT / "state/autonomy/AUTONOMOUS_ORCHESTRATOR_V2.json"
QUEUE_PATH = ROOT / "state/autonomy/WORK_QUEUE_V2.json"
DELEGATION_PATH = ROOT / "state/authorization/delegations/OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json"
WORK_UNIT_PROMOTION_PATH = ROOT / "state/authorization/promotions/AUTONOMOUS_WORK_UNIT_PROMOTION_V2.json"
RECEIPT_ROOT = ROOT / "receipts/autonomy"
STATUS_CONTEXT = "QIKVRT Autonomous Orchestrator Exact Head"
TERMINAL_DEPENDENCY_STATES = frozenset({"DONE", "SUPERSEDED"})
WAITING_STATES = frozenset(
    {
        "WAITING_HUMAN",
        "WAITING_EXTERNAL_AUTH",
        "WAITING_EMPIRICAL",
        "WAITING_CONFIGURATION",
    }
)
PROMOTION_CONDITIONS = (
    "CURRENT_BASE_REOBSERVED",
    "HEAD_UNCHANGED",
    "DIFF_ALLOWLISTED",
    "NO_EXTERNAL_EFFECT",
    "ALL_APPLICABLE_GATES_TERMINAL_GREEN",
    "NO_COMPETING_WRITER",
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
WORK_UNIT_ID = re.compile(r"^AUT-[A-Z0-9-]+$")


class OrchestratorBlock(RuntimeError):
    """Fail-closed orchestration error."""


@dataclass(frozen=True)
class CommandResult:
    command: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class Candidate:
    pr_number: int
    head_branch: str
    head_sha: str
    base_sha: str
    work_unit_id: str


def run(
    command: Sequence[str],
    *,
    cwd: pathlib.Path | None = None,
    timeout: int = 900,
    check: bool = False,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    completed = subprocess.run(
        list(command),
        cwd=str(cwd or ROOT),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=dict(os.environ if env is None else env),
    )
    result = CommandResult(
        tuple(command),
        completed.returncode,
        completed.stdout,
        completed.stderr,
    )
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise OrchestratorBlock(
            f"command failed ({result.returncode}): {' '.join(command)}: {detail}"
        )
    return result


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OrchestratorBlock(f"{label} cannot be loaded: {exc}") from exc
    if not isinstance(value, dict):
        raise OrchestratorBlock(f"{label} must be a JSON object")
    return value


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value), encoding="utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    return sha256_bytes(path.read_bytes())


def require_sha(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise OrchestratorBlock(f"{label} is not a valid digest")
    return value


def require_false_claims(value: Any, label: str) -> None:
    if not isinstance(value, Mapping):
        raise OrchestratorBlock(f"{label} completion claims are absent")
    for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"):
        if value.get(key) is not False:
            raise OrchestratorBlock(f"{label} falsely claims {key}")
    for key, item in value.items():
        if isinstance(item, bool) and item:
            raise OrchestratorBlock(f"{label} completion claim {key} must remain false")


def validate_delegation(value: Mapping[str, Any]) -> None:
    if value.get("schema") != "qikvrt_owner_autonomous_repository_continuation_v2":
        raise OrchestratorBlock("owner delegation schema mismatch")
    scope = value.get("authorization_scope", {})
    if not isinstance(scope, Mapping) or scope.get("state") != "ACTIVE":
        raise OrchestratorBlock("owner autonomous delegation is not ACTIVE")
    allowed = set(value.get("allowed_without_reinteraction", []))
    required = {
        "read_only_repository_and_public_evidence_observation",
        "semantic_fingerprint_bound_branch_creation",
        "draft_pull_request_creation_for_allowlisted_repository_internal_repairs",
        "expected_head_bound_promotion_when_all_declared_conditions_hold",
        "append_only_receipt_status_and_work_unit_projection_creation",
    }
    if not required.issubset(allowed):
        raise OrchestratorBlock("owner delegation lacks required repository-internal capabilities")
    if (
        scope.get("reviewable_successor_creation") is not True
        and "reviewable_successor_creation" not in allowed
    ):
        raise OrchestratorBlock("owner delegation lacks reviewable successor creation")
    forbidden = set(value.get("not_authorized", []))
    required_forbidden = {
        "zenodo_create_upload_metadata_mutation_or_publication",
        "ietf_datatracker_submission_resubmission_or_metadata_mutation",
        "github_release_or_tag_creation",
        "force_push_or_history_rewrite",
        "unconditional_automatic_merge_or_unbound_promotion",
    }
    if not required_forbidden.issubset(forbidden):
        raise OrchestratorBlock("owner delegation external-effect boundary differs")
    policy = value.get("promotion_policy", {})
    if policy.get("unconditional_automatic_merge") != "FORBIDDEN":
        raise OrchestratorBlock("delegation permits unconditional automatic merge")
    if policy.get("expected_head_bound_promotion") != "ALLOWED_ONLY_IF":
        raise OrchestratorBlock("delegation expected-head policy differs")
    if policy.get("conditions") != list(PROMOTION_CONDITIONS):
        raise OrchestratorBlock("delegation promotion conditions differ")
    if policy.get("requires_existing_repository_bound_promotion_contract") is not True:
        raise OrchestratorBlock("delegation requires no promotion contract")
    require_false_claims(value.get("completion_claims"), "owner delegation")


def validate_contract(value: Mapping[str, Any], delegation: Mapping[str, Any]) -> None:
    if value.get("schema") != "qikvrt_autonomous_orchestrator_contract_v2":
        raise OrchestratorBlock("orchestrator contract schema mismatch")
    if value.get("authority_repository") != "Goldkelch/qik-vrt":
        raise OrchestratorBlock("authority repository mismatch")
    if value.get("delegation_path") != str(DELEGATION_PATH.relative_to(ROOT)):
        raise OrchestratorBlock("orchestrator delegation path mismatch")
    if value.get("queue_path") != str(QUEUE_PATH.relative_to(ROOT)):
        raise OrchestratorBlock("orchestrator queue path mismatch")
    if value.get("work_unit_promotion_contract_path") != str(
        WORK_UNIT_PROMOTION_PATH.relative_to(ROOT)
    ):
        raise OrchestratorBlock("work-unit promotion contract path mismatch")
    expected_parts = [
        f"tools/qikvrt_autonomous_orchestrator_part{index:02d}.inc"
        for index in range(1, 12)
    ]
    if value.get("controller_parts") != expected_parts:
        raise OrchestratorBlock("orchestrator controller-part binding differs")
    for relative in expected_parts:
        if not (ROOT / relative).is_file():
            raise OrchestratorBlock(f"orchestrator controller part is absent: {relative}")
    model = value.get("execution_model", {})
    if model.get("selection") != "one_highest_priority_eligible_work_unit_per_run":
        raise OrchestratorBlock("orchestrator must serialize work-unit selection")
    if model.get("mutation") != "deterministic_review_branch_only":
        raise OrchestratorBlock("orchestrator mutation boundary differs")
    if model.get("promotion") != "expected_head_bound_only":
