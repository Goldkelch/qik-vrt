#!/usr/bin/env python3
"""Validate and print the repository's machine-readable AI handoff context.

Standard-library only. Read-only: this script does not modify repository or Git
state and performs no network access.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, NoReturn

ROOT = Path(__file__).resolve().parents[1]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from tools.qikvrt_integrity import (
    PORTABLE_GIT_SOURCE_VERIFICATION_MODE,
    cross_check_portable_git_source_capsule,
    load_portable_git_source_capsule,
    portable_git_source_evidence,
)

CONTEXT_PATH = ROOT / "AI_CONTEXT.json"
SUPPORTED_CONTEXT_SCHEMAS = frozenset(
    {
        "qikvrt-ai-context/1.0",
        "qikvrt-ai-context/1.2",
        "qikvrt-ai-context/1.3",
        "qikvrt-ai-context/1.4",
    }
)


def fail(message: str) -> NoReturn:
    print(f"AI_HANDOFF_BLOCK: {message}", file=sys.stderr)
    raise SystemExit(2)


def load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        fail(f"cannot read {path}: {exc}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"top-level value in {path} must be an object")
    return value


def require(obj: dict[str, Any], key: str, expected: type) -> Any:
    value = obj.get(key)
    if not isinstance(value, expected):
        fail(f"field {key!r} must be {expected.__name__}")
    return value


def git_value(*args: str) -> str:
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return proc.stdout.strip() or "unavailable"

def validate_bound_file(
    receipt: dict[str, Any],
    path_key: str,
    sha_key: str,
    scope_id: str,
) -> None:
    path_value = receipt.get(path_key)
    sha_value = receipt.get(sha_key)
    if (
        not isinstance(path_value, str)
        or Path(path_value).is_absolute()
        or ".." in Path(path_value).parts
        or not isinstance(sha_value, str)
        or not re.fullmatch(r"[0-9a-f]{64}", sha_value)
    ):
        fail(f"AI progress DONE scope file binding is invalid: {scope_id}:{path_key}")
    try:
        actual = hashlib.sha256((ROOT / path_value).read_bytes()).hexdigest()
    except OSError as exc:
        fail(f"AI progress DONE scope bound file is unavailable: {scope_id}:{path_value}: {exc}")
    if actual != sha_value:
        fail(f"AI progress DONE scope bound file digest drift: {scope_id}:{path_value}")

def validate_progress(context: dict[str, Any]) -> str:
    protocol = require(context, "progress_protocol", dict)
    schema_path = ROOT / require(protocol, "machine_schema", str)
    progress_path = ROOT / require(protocol, "machine_state", str)
    schema = load_json(schema_path)
    progress = load_json(progress_path)
    durable = schema.get("$defs", {}).get("durableSnapshotV3")
    if not isinstance(durable, dict):
        fail("human-machine progress schema lacks durableSnapshotV3")
    required_fields = durable.get("required")
    if not isinstance(required_fields, list) or any(
        not isinstance(key, str) for key in required_fields
    ):
        fail("durable progress schema required-field contract is malformed")
    missing = [key for key in required_fields if key not in progress]
    if missing:
        fail("AI progress missing durable fields: " + ", ".join(sorted(missing)))
    if progress.get("schema") != "qikvrt-ai-progress/3.1":
        fail("AI progress must use qikvrt-ai-progress/3.1")
    source_sha = progress.get("source_sha")
    if not isinstance(source_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", source_sha):
        fail("AI progress source_sha is invalid")
    try:
        dt.datetime.fromisoformat(
            require(progress, "updated_at", str).replace("Z", "+00:00")
        )
    except ValueError as exc:
        fail(f"AI progress updated_at is invalid: {exc}")
    evidence = require(progress, "source_evidence", dict)
    if evidence.get("ref_name") != progress.get("ref_name"):
        fail("AI progress source evidence ref drift")
    if evidence.get("commit") != source_sha:
        fail("AI progress source evidence commit drift")
    blobs = require(evidence, "blobs", dict)
    if not blobs:
        fail("AI progress source evidence must bind at least one blob")
    for path, expected in blobs.items():
        if (
            not isinstance(path, str)
            or not path
            or Path(path).is_absolute()
            or ".." in Path(path).parts
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{40}", expected)
        ):
            fail(f"AI progress source blob binding is invalid: {path!r}")
    if evidence.get("verification_mode") != PORTABLE_GIT_SOURCE_VERIFICATION_MODE:
        fail("AI progress source evidence verification mode drift")
    capsule_binding = require(evidence, "capsule", dict)
    capsule_path = capsule_binding.get("path")
    if not isinstance(capsule_path, str):
        fail("AI progress source capsule path is invalid")
    try:
        capsule = load_portable_git_source_capsule(
            ROOT,
            capsule_path,
            expected_binding=capsule_binding,
        )
        cross_check_portable_git_source_capsule(ROOT, capsule)
    except (OSError, RuntimeError, UnicodeError, ValueError) as exc:
        fail(f"AI progress portable source capsule is invalid: {exc}")
    if evidence != portable_git_source_evidence(capsule):
        fail("AI progress source evidence does not match its portable Git closure")
    canonical_repositories = (
        context.get("project", {})
        .get("canonicality", {})
        .get("repositories", [])
    )
    if (
        not canonical_repositories
        or evidence.get("source_repository") != canonical_repositories[0]
    ):
        fail("AI progress portable source repository is not the Authority")
    scopes = require(progress, "scopes", dict)
    if not scopes:
        fail("AI progress must contain at least one bounded scope")
    incomplete = 0
    for scope_id, scope in scopes.items():
        if not isinstance(scope_id, str) or not isinstance(scope, dict):
            fail("AI progress scope contract is malformed")
        claims = require(scope, "claims", dict)
        release = tuple(claims.get(key) for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE"))
        effect_state = scope.get("effect_state")
        if effect_state == "EFFECT_ACK_DONE":
            if scope.get("state") != "FINAL_PASS" or release != (True, True, True):
                fail(f"AI progress DONE scope is not FINAL_PASS: {scope_id}")
            pass_evidence = require(scope, "pass_evidence", dict)
            repositories = pass_evidence.get("repository")
            if not isinstance(repositories, list) or not repositories:
                fail(f"AI progress DONE scope lacks repository evidence: {scope_id}")
            for repository in repositories:
                if (
                    not isinstance(repository, dict)
                    or not isinstance(repository.get("repository"), str)
                    or not isinstance(repository.get("ref_name"), str)
                    or not re.fullmatch(
                        r"[0-9a-f]{40}", str(repository.get("source_sha", ""))
                    )
                ):
                    fail(f"AI progress DONE scope repository/ref/SHA evidence is invalid: {scope_id}")
            checks = pass_evidence.get("checks")
            if not isinstance(checks, dict) or not checks:
                fail(f"AI progress DONE scope lacks check evidence: {scope_id}")
            receipt = require(pass_evidence, "evidence", dict)
            validate_bound_file(receipt, "path", "sha256", scope_id)
            for path_key, sha_key in (
                ("finalization_input_path", "finalization_input_sha256"),
                ("exact_head_run_evidence_path", "exact_head_run_evidence_sha256"),
            ):
                if path_key in receipt or sha_key in receipt:
                    validate_bound_file(receipt, path_key, sha_key, scope_id)
            if scope_id == "qikvrt-global-claim-scope-v1":
                gate_matrix = checks.get("receipt_gate_matrix")
                exact_runs = checks.get("exact_head_runs")
                required_gates = {
                    "global_completion",
                    "manuscript_proof",
                    "mandatory_repository_gates",
                }
                if (
                    not isinstance(gate_matrix, dict)
                    or set(gate_matrix) != {"authority", "mirror"}
                    or any(
                        not isinstance(gate_matrix.get(side), dict)
                        or set(gate_matrix[side]) != required_gates
                        or any(
                            value != "success"
                            for value in gate_matrix[side].values()
                        )
                        for side in ("authority", "mirror")
                    )
                    or not isinstance(exact_runs, dict)
                    or set(exact_runs) != {"authority", "mirror"}
                ):
                    fail("AI progress global DONE gate matrix is invalid")
                run_ids: dict[str, int] = {}
                for side in ("authority", "mirror"):
                    run = exact_runs[side]
                    if (
                        not isinstance(run, dict)
                        or isinstance(run.get("run_id"), bool)
                        or not isinstance(run.get("run_id"), int)
                        or run["run_id"] <= 0
                        or isinstance(run.get("job_id"), bool)
                        or not isinstance(run.get("job_id"), int)
                        or run["job_id"] <= 0
                        or not isinstance(run.get("gate_steps"), dict)
                        or set(run["gate_steps"]) != required_gates
                        or any(
                            not isinstance(step, dict)
                            or step.get("conclusion") != "success"
                            for step in run["gate_steps"].values()
                        )
                    ):
                        fail(f"AI progress global DONE exact-head run is invalid: {side}")
                    run_ids[side] = run["run_id"]
                repository_by_name = {
                    item["repository"]: item
                    for item in repositories
                    if isinstance(item, dict)
                    and isinstance(item.get("repository"), str)
                }
                for side, name in (
                    ("authority", "Goldkelch/qik-vrt"),
                    ("mirror", "ingolf-lohmann/qik-vrt"),
                ):
                    item = repository_by_name.get(name)
                    if (
                        not isinstance(item, dict)
                        or item.get("ref_name")
                        != f"actions/runs/{run_ids[side]}"
                    ):
                        fail(
                            "AI progress global DONE run/ref binding is invalid: "
                            + side
                        )
        elif effect_state in {"EFFECT_ACK_CONTINUE", "EFFECT_ACK_BLOCK"}:
            incomplete += 1
            if release != (False, False, False):
                fail(f"AI progress incomplete scope inflates release: {scope_id}")
        else:
            fail(f"AI progress scope effect state is invalid: {scope_id}")
    if progress.get("incomplete_scope_count") != incomplete:
        fail("AI progress incomplete_scope_count is invalid")
    top_claims = require(progress, "claims", dict)
    if incomplete:
        if progress.get("effect_state") != "EFFECT_ACK_CONTINUE":
            fail("AI progress incomplete scopes require top-level CONTINUE")
        if tuple(top_claims.get(key) for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE")) != (False, False, False):
            fail("AI progress top-level release claims are inflated")
    elif (
        progress.get("state") != "PASS"
        or progress.get("effect_state") != "EFFECT_ACK_DONE"
        or tuple(
            top_claims.get(key)
            for key in ("PASS", "FINAL_PASS", "EFFECT_ACK_DONE")
        )
        != (True, True, True)
    ):
        fail("AI progress complete scopes require top-level PASS/DONE")
    effects = require(progress, "repository_effects", dict)
    if any(
        value != "NOT_EVALUATED"
        for key, value in effects.items()
        if key != "scope"
    ):
        fail("AI progress transient repository effects must remain unevaluated")
    owner = require(progress, "projection_owner", dict)
    owner_tool = owner.get("tool")
    owner_check = owner.get("check_command")
    if (
        not isinstance(owner_tool, str)
        or not owner_tool.startswith("tools/")
        or Path(owner_tool).is_absolute()
        or ".." in Path(owner_tool).parts
        or not (ROOT / owner_tool).is_file()
        or not isinstance(owner_check, str)
    ):
        fail("AI progress projection owner is invalid")
    try:
        command = shlex.split(owner_check)
    except ValueError as exc:
        fail(f"AI progress projection check is invalid: {exc}")
    if (
        len(command) != 4
        or command[0] != "python3"
        or command[1] != "-B"
        or command[2] != owner_tool
        or not command[3].startswith("--check")
    ):
        fail("AI progress projection check is outside the fail-closed command contract")
    try:
        checked = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        fail(f"AI progress projection check failed to execute: {exc}")
    if checked.returncode != 0:
        detail = checked.stderr.strip() or checked.stdout.strip() or "no diagnostic"
        fail(f"AI progress projection is stale: {detail}")
    return owner_check


def validate_adapters(context: dict[str, Any]) -> tuple[str, int]:
    registry_name = require(context, "adapter_registry", str)
    registry = load_json(ROOT / registry_name)
    if require(registry, "schema", str) != "qikvrt-ai-adapters/1.0":
        fail("unsupported AI adapter registry schema")
    if require(registry, "canonical_entrypoint", str) != "AI":
        fail("AI adapter registry must bind canonical entrypoint AI")
    adapters = require(registry, "adapters", list)
    if not adapters:
        fail("AI adapter registry must contain at least one adapter")
    missing: list[str] = []
    for adapter in adapters:
        if not isinstance(adapter, dict):
            fail("every AI adapter entry must be an object")
        path = require(adapter, "path", str)
        if not (ROOT / path).is_file():
            missing.append(path)
    if missing:
        fail("missing AI adapter files: " + ", ".join(sorted(missing)))
    return registry_name, len(adapters)


def main() -> int:
    context = load_json(CONTEXT_PATH)
    schema = require(context, "schema", str)
    if schema not in SUPPORTED_CONTEXT_SCHEMAS:
        fail(f"unsupported schema {schema!r}")

    project = require(context, "project", dict)
    name = require(project, "name", str)
    canonicality = require(project, "canonicality", dict)
    repositories = require(canonicality, "repositories", list)
    if not repositories or not all(isinstance(x, str) and x for x in repositories):
        fail("canonical repositories must be a non-empty string list")

    read_order = require(context, "required_read_order", list)
    if not read_order or not all(isinstance(x, str) and x for x in read_order):
        fail("required_read_order must be a non-empty string list")

    missing = [path for path in read_order if not (ROOT / path).is_file()]
    if missing:
        fail("missing required files: " + ", ".join(missing))

    registry_name, adapter_count = validate_adapters(context)
    projection_check = validate_progress(context)

    licensing = require(context, "licensing_policy", dict)
    architecture = require(licensing, "architecture", dict)
    implementation = require(licensing, "implementation", dict)

    print("AI_HANDOFF_STATUS=VALID")
    print(f"PROJECT={name}")
    print(f"CONTEXT_ID={context.get('context_id', 'unknown')}")
    print(f"GIT_REF={git_value('rev-parse', '--abbrev-ref', 'HEAD')}")
    print(f"GIT_COMMIT={git_value('rev-parse', 'HEAD')}")
    print("CANONICAL_MODE=" + str(canonicality.get("mode", "unknown")))
    print("CANONICAL_REPOSITORIES=" + ",".join(repositories))
    print("READ_ORDER=" + " -> ".join(read_order))
    print(f"AI_ADAPTER_REGISTRY={registry_name}")
    print(f"AI_ADAPTER_COUNT={adapter_count}")
    print(f"AI_PROGRESS_CHECK={projection_check}")
    print("ARCHITECTURE_POLICY=" + str(architecture.get("intent", "unknown")))
    print("IMPLEMENTATION_POLICY=" + str(implementation.get("intent", "unknown")))
    print("NEXT_ACTION=Read required files, inspect task-relevant verified state, then continue without relying on chat memory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
