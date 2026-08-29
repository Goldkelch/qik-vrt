#!/usr/bin/env python3
"""Route one exact issue admission to one registered deterministic executor.

The controller runs trusted current-main code only.  It may materialize a
bounded execution receipt in a detached current-main worktree; Git transport,
draft-PR creation, and every Authority lifecycle effect remain workflow
adapter boundaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.issue_agent.binding import canonical_bytes, json_loads_strict
from scripts.issue_agent.validate import REQUIRED as CANDIDATE_REQUIRED_FILES
from scripts.issue_agent.validate import validate as validate_candidate_bundle


CONTRACT_PATH = "state/autonomy/ISSUE_AGENT_TYPED_EXECUTOR_CONTRACT_V1.json"
POLICY_PATH = "policy/ISSUE_AGENT_DETERMINISTIC_INTAKE_V1.json"
INTEGRITY_PATHS = (
    "REPOSITORY_FILE_MANIFEST.json",
    "REPOSITORY_FILE_MANIFEST.json.sha256",
    "SHA256SUMS.txt",
)
EXECUTION_FILES = ("EXECUTION_RECEIPT.json", "EXECUTION_RECEIPT.sha256")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FALSE_CLAIMS = {
    "PASS": False,
    "FINAL_PASS": False,
    "EFFECT_ACK_DONE": False,
    "MERGE": False,
    "ISSUE_CLOSE": False,
    "MIRROR_SYNC": False,
    "TAG": False,
    "PUBLICATION": False,
    "DEPLOYMENT": False,
}
ADMISSION_RECEIPT_KEYS = {
    "schema", "repository", "pull_request", "head", "tree", "current_main",
    "request_fingerprint", "candidate_class", "issue_disposition", "handler_id",
    "handler_sha256", "work_order_payload_sha256", "declared_executor_contract",
    "executor_registry_sha256", "executor_entry_sha256", "executor_controller_path",
    "executor_controller_blob_sha1", "executor_workflow_path",
    "executor_workflow_blob_sha1", "registered_executor_id",
    "executor_registration_state", "verifier_workflow_run_id",
    "verifier_workflow_run_attempt", "verifier_workflow_name", "verifier_workflow_ref",
    "verifier_workflow_sha", "verifier_workflow_blob_sha1", "verifier_authority_tree",
    "review_required", "review_gate", "pr_snapshot_sha256", "reviews_sha256",
    "threads_sha256", "ci_run_id", "ci_jobs_sha256", "issue_agent_run_id",
    "issue_agent_jobs_sha256", "issue_reduction_artifact_id", "state",
    "repository_content_effect", "authority_lifecycle_effect",
    "platform_transport_effects_declared", "claims",
}


class ExecutorBlock(RuntimeError):
    """The trusted executor contract or exact admission is malformed."""


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json_loads_strict(path.read_bytes())
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ExecutorBlock(f"{label} cannot be loaded: {exc}") from exc
    if not isinstance(value, dict):
        raise ExecutorBlock(f"{label} must be a JSON object")
    return value


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExecutorBlock(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExecutorBlock(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or any(not isinstance(item, str) or not item for item in value)
        or value != sorted(set(value))
    ):
        raise ExecutorBlock(f"{label} must be a canonical string list")
    return list(value)


def _safe_relative(value: str, label: str) -> str:
    path = PurePosixPath(_string(value, label))
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ExecutorBlock(f"{label} is not a safe repository-relative path")
    return path.as_posix()


def _git(root: Path, *arguments: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=not binary,
    )
    if completed.returncode:
        stderr = completed.stderr
        detail = (
            stderr.decode("utf-8", errors="replace") if isinstance(stderr, bytes) else stderr
        ).strip()
        raise ExecutorBlock(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout


def _ls_tree(root: Path, commit: str, pathspec: str) -> dict[str, tuple[str, str, str]]:
    raw = _git(root, "ls-tree", "-r", "-z", commit, "--", pathspec, binary=True)
    assert isinstance(raw, bytes)
    result: dict[str, tuple[str, str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
            path = raw_path.decode("utf-8", errors="strict")
        except (ValueError, UnicodeError) as exc:
            raise ExecutorBlock("Git tree contains a malformed entry") from exc
        if path in result:
            raise ExecutorBlock(f"Git tree contains a duplicate path: {path}")
        result[path] = (mode, object_type, object_id)
    return result


def _regular_blob_entries(
    entries: Mapping[str, tuple[str, str, str]], expected: set[str], label: str
) -> None:
    if set(entries) != expected:
        missing = sorted(expected - set(entries))
        surplus = sorted(set(entries) - expected)
        raise ExecutorBlock(f"{label} path set differs: missing={missing} surplus={surplus}")
    unsafe = sorted(
        path for path, (mode, object_type, _) in entries.items()
        if mode != "100644" or object_type != "blob"
    )
    if unsafe:
        raise ExecutorBlock(f"{label} contains a non-100644 regular blob: {unsafe}")


def _verify_sidecar(path: Path) -> str:
    sidecar = path.with_suffix(".sha256")
    if not path.is_file() or path.is_symlink() or not sidecar.is_file() or sidecar.is_symlink():
        raise ExecutorBlock(f"{path.name} or its sidecar is absent or unsafe")
    digest = sha256_bytes(path.read_bytes())
    fields = sidecar.read_text(encoding="utf-8").strip().split()
    if fields != [digest, path.name]:
        raise ExecutorBlock(f"{path.name} sidecar differs from exact bytes")
    return digest


def load_contract(root: Path = ROOT) -> tuple[dict[str, Any], str]:
    path = root / CONTRACT_PATH
    contract = _load_json(path, "typed executor contract")
    if contract.get("schema") != "qikvrt_issue_agent_typed_executor_contract_v1":
        raise ExecutorBlock("typed executor contract schema is not v1")
    if contract.get("contract_id") != "QIKVRT-TYPED-WORK-ORDER-HANDOFF-V1":
        raise ExecutorBlock("typed executor contract id is not canonical")
    if contract.get("status") != "ACTIVE":
        raise ExecutorBlock("typed executor contract is not active")

    authority = _mapping(contract.get("authority"), "executor authority")
    if authority != {
        "repository": "Goldkelch/qik-vrt",
        "default_branch": "main",
        "intake_policy_path": POLICY_PATH,
    }:
        raise ExecutorBlock("typed executor Authority binding differs")
    controller = _mapping(contract.get("controller"), "executor controller")
    if controller.get("path") != "scripts/issue_agent/executor.py":
        raise ExecutorBlock("typed executor controller path differs")
    if controller.get("workflow_path") != ".github/workflows/issue-agent-executor.yml":
        raise ExecutorBlock("typed executor workflow path differs")
    if controller.get("trusted_code_ref") != "CURRENT_AUTHORITY_MAIN_ONLY":
        raise ExecutorBlock("typed executor does not require trusted current-main code")
    if controller.get("candidate_code_execution") is not False:
        raise ExecutorBlock("typed executor permits candidate-code execution")
    if controller.get("unmapped_handler") != "HOLD" or controller.get("drift") != "HOLD":
        raise ExecutorBlock("typed executor is not fail-closed")

    candidate = _mapping(contract.get("candidate"), "executor candidate")
    if candidate.get("branch_template") != "issue-executor/<issue>/<full-64-hex-execution-id>":
        raise ExecutorBlock("executor candidate branch template differs")
    if candidate.get("ref_write") != "EMPTY_EXPECTED_REMOTE_LEASE_CREATE_ONLY":
        raise ExecutorBlock("executor candidate ref is not create-only")
    if candidate.get("pull_request_mode") != "DRAFT":
        raise ExecutorBlock("executor candidate pull request is not draft-only")
    if candidate.get("parent_count") != 1 or candidate.get("base") != (
        "EXACT_REOBSERVED_AUTHORITY_MAIN"
    ):
        raise ExecutorBlock("executor candidate history binding differs")
    for key in ("history_rewrite", "automatic_ready", "automatic_merge"):
        if candidate.get(key) is not False:
            raise ExecutorBlock(f"executor candidate boundary {key} must be false")

    output = _mapping(contract.get("output"), "executor output")
    if output.get("root_template") != (
        "evidence/issues/<issue>/executions/<request-fingerprint>/<execution-id>"
    ):
        raise ExecutorBlock("executor output root template differs")
    if _string_list(output.get("executor_files"), "executor output files") != sorted(
        EXECUTION_FILES
    ):
        raise ExecutorBlock("executor file allowlist differs")
    if _string_list(
        output.get("workflow_owned_additional_paths"),
        "executor workflow-owned paths",
    ) != sorted(INTEGRITY_PATHS):
        raise ExecutorBlock("executor workflow-owned path allowlist differs")
    if output.get("any_other_path") != "HOLD":
        raise ExecutorBlock("executor output does not HOLD on surplus paths")

    handlers = contract.get("handlers")
    if not isinstance(handlers, list) or not handlers:
        raise ExecutorBlock("typed executor registry is empty")
    handler_ids: set[str] = set()
    executor_ids: set[str] = set()
    policy_for_registry = _load_json(root / POLICY_PATH, "registry-bound intake policy")
    policy_handlers = policy_for_registry.get("handlers")
    if not isinstance(policy_handlers, list):
        raise ExecutorBlock("registry-bound intake policy handlers are malformed")
    for raw in handlers:
        handler = _mapping(raw, "registered executor")
        handler_id = _string(handler.get("handler_id"), "registered handler id")
        handler_sha256 = _string(
            handler.get("handler_sha256"), "registered handler descriptor digest"
        )
        if not HEX64.fullmatch(handler_sha256):
            raise ExecutorBlock(f"registered handler digest is invalid for {handler_id}")
        policy_matches = [
            value for value in policy_handlers
            if isinstance(value, Mapping) and value.get("handler_id") == handler_id
        ]
        if len(policy_matches) != 1 or sha256_bytes(
            canonical_bytes(dict(policy_matches[0]))
        ) != handler_sha256:
            raise ExecutorBlock(f"registered handler descriptor differs for {handler_id}")
        executor_id = _string(handler.get("executor_id"), "registered executor id")
        if handler_id in handler_ids or executor_id in executor_ids:
            raise ExecutorBlock("typed executor registry contains a duplicate identity")
        handler_ids.add(handler_id)
        executor_ids.add(executor_id)
        if handler.get("implementation") not in {"ROOT_CONTROL_PLANE_ATTESTATION_V1"}:
            raise ExecutorBlock(f"unsupported executor implementation for {handler_id}")
        if handler.get("input_contract") != "FIXED_REGISTERED_HANDLER_DESCRIPTOR":
            raise ExecutorBlock(f"{handler_id} input contract is not fixed")
        if handler.get("selected_body_controls_operations") is not False:
            raise ExecutorBlock(f"{handler_id} permits selected-body-driven operations")
        if handler.get("work_product") != (
            "EXACT_MAIN_BOUNDED_ROOT_CONTROL_PLANE_ATTESTATION_NOT_REPAIR_COMPLETION"
        ):
            raise ExecutorBlock(f"{handler_id} work-product boundary differs")
        required = _string_list(handler.get("required_files"), f"{handler_id} required files")
        absent = _string_list(
            handler.get("required_absent_files"),
            f"{handler_id} required absent files",
            allow_empty=True,
        )
        for path_value in [*required, *absent]:
            _safe_relative(path_value, f"{handler_id} path")
        if handler.get("allowed_repository_effects") != [
            "MATERIALIZE_BOUND_EXECUTION_RECEIPT_ON_IMMUTABLE_DRAFT_CANDIDATE"
        ]:
            raise ExecutorBlock(f"{handler_id} repository effect allowlist differs")

    boundaries = _mapping(contract.get("boundaries"), "executor boundaries")
    for key in (
        "authority_main_effect",
        "issue_lifecycle_effect",
        "candidate_code_execution",
        "free_form_command_execution",
        "unregistered_handler_execution",
        "foreign_repository_write",
        "force_push",
        "merge",
        "release",
        "publication",
        "deployment",
    ):
        if boundaries.get(key) != "FORBIDDEN":
            raise ExecutorBlock(f"executor boundary {key} is not forbidden")
    if contract.get("completion_claims") != FALSE_CLAIMS:
        raise ExecutorBlock("typed executor contract contains a completion claim")
    required_receipt_fields = contract.get("required_admission_receipt_fields")
    if not isinstance(required_receipt_fields, list) or set(required_receipt_fields) != {
        "repository", "pull_request", "head", "tree", "current_main",
        "request_fingerprint", "candidate_class", "issue_disposition", "handler_id",
        "handler_sha256", "work_order_payload_sha256", "declared_executor_contract",
        "executor_registry_sha256", "executor_entry_sha256", "executor_controller_path",
        "executor_controller_blob_sha1", "executor_workflow_path",
        "executor_workflow_blob_sha1", "registered_executor_id",
        "executor_registration_state", "verifier_workflow_run_id",
        "verifier_workflow_run_attempt", "verifier_workflow_name", "verifier_workflow_ref",
        "verifier_workflow_sha", "verifier_workflow_blob_sha1", "verifier_authority_tree",
        "state",
    }:
        raise ExecutorBlock("typed executor required admission field set differs")
    return contract, sha256_bytes(path.read_bytes())


def _load_policy(root: Path) -> dict[str, Any]:
    policy = _load_json(root / POLICY_PATH, "deterministic intake policy")
    if policy.get("schema") != "qikvrt_issue_agent_deterministic_intake_v1":
        raise ExecutorBlock("deterministic intake policy schema differs")
    return policy


def _policy_handler(policy: Mapping[str, Any], handler_id: str) -> Mapping[str, Any] | None:
    matches = [
        value
        for value in policy.get("handlers", [])
        if isinstance(value, Mapping) and value.get("handler_id") == handler_id
    ]
    if len(matches) > 1:
        raise ExecutorBlock("intake policy contains a duplicate handler")
    return matches[0] if matches else None


def _registry_handler(contract: Mapping[str, Any], handler_id: str) -> Mapping[str, Any] | None:
    matches = [
        value
        for value in contract.get("handlers", [])
        if isinstance(value, Mapping) and value.get("handler_id") == handler_id
    ]
    if len(matches) > 1:
        raise ExecutorBlock("executor registry contains a duplicate handler")
    return matches[0] if matches else None


def _root_control_plane_attestation(
    root: Path,
    registered: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    required = _string_list(registered.get("required_files"), "root executor required files")
    absent = _string_list(
        registered.get("required_absent_files"),
        "root executor required absent files",
        allow_empty=True,
    )
    missing = [path for path in required if not (root / path).is_file()]
    unexpectedly_present = [path for path in absent if (root / path).exists()]
    if missing or unexpectedly_present:
        raise ExecutorBlock(
            f"root control-plane file boundary differs: missing={missing}, "
            f"unexpected={unexpectedly_present}"
        )

    forbidden = set(policy.get("forbidden") or [])
    if not {"schedule", "cron", "blind_retry"}.issubset(forbidden):
        raise ExecutorBlock("intake policy does not forbid polling or blind retry")
    execution = _mapping(policy.get("execution_boundary"), "intake execution boundary")
    if execution.get("EXECUTE_NOW") != "WORK_UNIT_ADMISSION_NOT_SUBSTANTIVE_HANDLER_COMPLETION":
        raise ExecutorBlock("intake policy conflates admission with execution")
    if execution.get("silent_drop_allowed") is not False:
        raise ExecutorBlock("intake policy permits silent work loss")
    if execution.get("required_for_substantive_completion") != (
        "SEPARATELY_REGISTERED_EXECUTOR_AND_BOUND_WORK_PRODUCT_DIGESTS"
    ):
        raise ExecutorBlock("intake policy lacks the substantive executor boundary")
    terminal = _mapping(policy.get("terminal_boundary"), "intake terminal boundary")
    if terminal.get("work_admission_state") != "REGISTRATION_DEPENDENT":
        raise ExecutorBlock("intake work-admission state is not registration-dependent")
    if terminal.get("registered_work_admission_state") != (
        "READY_FOR_EXACT_HEAD_EXECUTOR_DISPATCH"
    ):
        raise ExecutorBlock("registered intake handoff state differs")
    if terminal.get("unregistered_work_admission_state") != "HOLD_EXECUTOR_NOT_REGISTERED":
        raise ExecutorBlock("unregistered intake handoff state differs")
    registry_binding = _mapping(policy.get("executor_registry"), "intake executor registry")
    if registry_binding != {
        "path": CONTRACT_PATH,
        "schema": "qikvrt_issue_agent_typed_executor_contract_v1",
        "contract_id": "QIKVRT-TYPED-WORK-ORDER-HANDOFF-V1",
    }:
        raise ExecutorBlock("intake policy executor registry binding differs")

    processing = (root / ".github/workflows/issue-autonomous-processing.yml").read_text(
        encoding="utf-8"
    )
    verifier = (root / ".github/workflows/issue-agent-autofinish.yml").read_text(
        encoding="utf-8"
    )
    executor = (root / ".github/workflows/issue-agent-executor.yml").read_text(
        encoding="utf-8"
    )
    if "schedule:" in processing or "schedule:" in verifier or "schedule:" in executor:
        raise ExecutorBlock("issue control plane contains a polling schedule")
    for token in ("issue_comment:", "strategy:", "matrix:", "--force-with-lease=\"refs/heads/$branch:\""):
        if token not in processing:
            raise ExecutorBlock(f"deterministic intake workflow is missing {token}")
    for token in (
        "Issue agent exact candidate verifier",
        "executor_registry_sha256",
        "registered_executor_id",
        "REGISTERED_EXACT_HEAD",
    ):
        if token not in verifier:
            raise ExecutorBlock(f"candidate verifier is missing {token}")
    for token in (
        "Issue agent registered executor",
        "issue-executor/$ISSUE_NUMBER/$EXECUTION_ID",
        "--force-with-lease=\"refs/heads/$branch:\"",
        "--draft",
    ):
        if token not in executor:
            raise ExecutorBlock(f"typed executor workflow is missing {token}")
    if "gh pr merge" in executor or "gh release" in executor:
        raise ExecutorBlock("typed executor workflow contains a forbidden effect")

    bindings = [
        {
            "path": path,
            "sha256": sha256_bytes((root / path).read_bytes()),
        }
        for path in required
    ]
    return {
        "schema": "qikvrt_root_control_plane_attestation_v1",
        "required_files": bindings,
        "required_absent_files": absent,
        "event_driven_lexical_invariants_observed": True,
        "quadratic_epoch_bound": policy.get("quadratic_epoch", {}).get("lane_count") == "N*N",
        "registered_executor_present": True,
        "candidate_code_execution": False,
        "repository_content_effect": "NOT_YET_APPLIED",
        "authority_main_effect": "NONE",
    }


def _hold(
    *,
    reason: str,
    request: Mapping[str, Any],
    receipt: Mapping[str, Any],
    registry_sha256: str,
) -> dict[str, Any]:
    return {
        "schema": "qikvrt_issue_agent_executor_plan_v1",
        "state": "HOLD",
        "failure_class": reason,
        "repository": request.get("repository"),
        "issue_number": request.get("issue_number"),
        "request_fingerprint": request.get("request_fingerprint"),
        "handler_id": receipt.get("handler_id"),
        "executor_registry_sha256": registry_sha256,
        "changed_paths": [],
        "repository_content_effect": "NONE",
        "authority_main_effect": "NONE",
        "claims": FALSE_CLAIMS,
    }


def _validate_admission(
    root: Path,
    bundle: Path,
    verification_receipt: Path,
    *,
    verify_authority: bool,
    verify_candidate_git: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    try:
        validate_candidate_bundle(bundle, verify_authority=verify_authority)
    except SystemExit as exc:
        raise ExecutorBlock(f"candidate bundle validation failed: {exc}") from exc
    request = _load_json(bundle / "REQUEST.json", "candidate request")
    status = _load_json(bundle / "STATUS.json", "candidate status")
    receipt_digest = _verify_sidecar(verification_receipt)
    receipt = _load_json(verification_receipt, "candidate verification receipt")
    contract, registry_sha256 = load_contract(root)
    policy = _load_policy(root)

    if set(receipt) != ADMISSION_RECEIPT_KEYS:
        missing = sorted(ADMISSION_RECEIPT_KEYS - set(receipt))
        surplus = sorted(set(receipt) - ADMISSION_RECEIPT_KEYS)
        raise ExecutorBlock(
            f"candidate verifier receipt field set differs: missing={missing} surplus={surplus}"
        )

    executor_registry = _mapping(policy.get("executor_registry"), "policy executor registry")
    if executor_registry.get("path") != CONTRACT_PATH:
        raise ExecutorBlock("policy points to a different executor registry")
    if executor_registry.get("contract_id") != contract["contract_id"]:
        raise ExecutorBlock("policy and executor contract ids differ")
    if receipt.get("schema") != "qikvrt_issue_agent_work_admission_receipt_v2":
        raise ExecutorBlock("candidate verifier receipt is not a work admission")
    if receipt.get("candidate_class") != "WORK_ADMISSION":
        raise ExecutorBlock("candidate verifier receipt class is not work admission")
    if receipt.get("issue_disposition") != "EXECUTE_NOW":
        raise ExecutorBlock("candidate verifier receipt disposition is not executable")
    if receipt.get("state") not in {
        "READY_FOR_EXACT_HEAD_EXECUTOR_DISPATCH",
        "HOLD_EXECUTOR_NOT_REGISTERED",
    }:
        raise ExecutorBlock("candidate verifier receipt handoff state differs")
    if receipt.get("claims") != FALSE_CLAIMS:
        raise ExecutorBlock("candidate verifier receipt contains a completion claim")
    if receipt.get("repository_content_effect") != "NONE":
        raise ExecutorBlock("candidate verifier receipt contains a repository effect")
    if receipt.get("authority_lifecycle_effect") != "NONE":
        raise ExecutorBlock("candidate verifier receipt contains an Authority lifecycle effect")

    binding = _mapping(request.get("binding"), "request binding")
    expected = {
        "repository": request.get("repository"),
        "request_fingerprint": request.get("request_fingerprint"),
        "current_main": binding.get("authority_head"),
        "handler_id": status.get("handler_id"),
        "handler_sha256": status.get("handler_sha256"),
        "work_order_payload_sha256": binding.get("selected_body_sha256"),
        "candidate_class": "WORK_ADMISSION",
        "issue_disposition": "EXECUTE_NOW",
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ExecutorBlock(f"candidate verifier receipt {key} differs from exact bundle")
    if status.get("status") != "CONTINUE" or status.get("evaluation_completed") is not True:
        raise ExecutorBlock("candidate status is not a completed admitted evaluation")
    if receipt.get("executor_registry_sha256") != registry_sha256:
        raise ExecutorBlock("candidate receipt executor registry digest differs")

    verifier_run_id = receipt.get("verifier_workflow_run_id")
    verifier_attempt = receipt.get("verifier_workflow_run_attempt")
    if type(verifier_run_id) is not int or verifier_run_id < 1:
        raise ExecutorBlock("candidate receipt verifier run id is invalid")
    if type(verifier_attempt) is not int or verifier_attempt < 1:
        raise ExecutorBlock("candidate receipt verifier run attempt is invalid")
    if receipt.get("verifier_workflow_name") != "Issue agent exact candidate verifier":
        raise ExecutorBlock("candidate receipt verifier workflow name differs")
    expected_workflow_ref = (
        f"{request['repository']}/.github/workflows/issue-agent-autofinish.yml@refs/heads/main"
    )
    if receipt.get("verifier_workflow_ref") != expected_workflow_ref:
        raise ExecutorBlock("candidate receipt verifier workflow ref differs")
    if receipt.get("verifier_workflow_sha") != binding.get("authority_head"):
        raise ExecutorBlock("candidate receipt verifier workflow SHA differs")
    if receipt.get("verifier_authority_tree") != binding.get("authority_tree"):
        raise ExecutorBlock("candidate receipt verifier Authority tree differs")

    policy_handler = _policy_handler(policy, str(status.get("handler_id")))
    if policy_handler is None:
        if receipt.get("declared_executor_contract") != "UNREGISTERED":
            raise ExecutorBlock("untyped intake handler declares an executor contract")
    elif (
        policy_handler.get("executor_contract") != contract["contract_id"]
        or receipt.get("declared_executor_contract") != contract["contract_id"]
    ):
        raise ExecutorBlock("intake handler declares a different executor contract")

    registered = _registry_handler(contract, str(status.get("handler_id")))
    if registered is not None:
        if registered.get("handler_sha256") != status.get("handler_sha256"):
            raise ExecutorBlock("registered handler id/digest pair differs from candidate")
        expected_entry_sha256 = sha256_bytes(canonical_bytes(dict(registered)))
        if receipt.get("executor_entry_sha256") != expected_entry_sha256:
            raise ExecutorBlock("candidate receipt executor entry digest differs")
        if receipt.get("registered_executor_id") != registered.get("executor_id"):
            raise ExecutorBlock("candidate receipt registered executor id differs")
        if receipt.get("executor_registration_state") != "REGISTERED_EXACT_HEAD":
            raise ExecutorBlock("candidate receipt did not observe exact registered executor")
        if receipt.get("state") != "READY_FOR_EXACT_HEAD_EXECUTOR_DISPATCH":
            raise ExecutorBlock("registered candidate receipt is not dispatch-ready")
    else:
        if (
            receipt.get("executor_entry_sha256") != "UNMAPPED"
            or receipt.get("registered_executor_id") != "UNMAPPED"
            or receipt.get("executor_registration_state") != "NOT_REGISTERED_EXACT_HEAD"
            or receipt.get("state") != "HOLD_EXECUTOR_NOT_REGISTERED"
        ):
            raise ExecutorBlock("unmapped candidate receipt does not hold fail-closed")
    if receipt.get("executor_controller_path") != "scripts/issue_agent/executor.py":
        raise ExecutorBlock("candidate receipt executor controller path differs")
    if receipt.get("executor_workflow_path") != ".github/workflows/issue-agent-executor.yml":
        raise ExecutorBlock("candidate receipt executor workflow path differs")

    if verify_authority:
        controller_blob = str(
            _git(root, "rev-parse", f"{binding['authority_head']}:scripts/issue_agent/executor.py")
        ).strip()
        executor_workflow_blob = str(
            _git(
                root,
                "rev-parse",
                f"{binding['authority_head']}:.github/workflows/issue-agent-executor.yml",
            )
        ).strip()
        verifier_workflow_blob = str(
            _git(
                root,
                "rev-parse",
                f"{binding['authority_head']}:.github/workflows/issue-agent-autofinish.yml",
            )
        ).strip()
        if receipt.get("executor_controller_blob_sha1") != controller_blob:
            raise ExecutorBlock("candidate receipt executor controller blob differs")
        if receipt.get("executor_workflow_blob_sha1") != executor_workflow_blob:
            raise ExecutorBlock("candidate receipt executor workflow blob differs")
        if receipt.get("verifier_workflow_blob_sha1") != verifier_workflow_blob:
            raise ExecutorBlock("candidate receipt verifier workflow blob differs")

    if verify_authority:
        head = str(_git(root, "rev-parse", "--verify", "HEAD^{commit}")).strip()
        tree = str(_git(root, "rev-parse", "--verify", "HEAD^{tree}")).strip()
        if head != binding.get("authority_head") or tree != binding.get("authority_tree"):
            raise ExecutorBlock("trusted executor checkout differs from admission Authority")
    if verify_candidate_git:
        candidate_head = _string(receipt.get("head"), "admission candidate head")
        candidate_tree = _string(receipt.get("tree"), "admission candidate tree")
        if not HEX40.fullmatch(candidate_head) or not HEX40.fullmatch(candidate_tree):
            raise ExecutorBlock("admission candidate Git identity is invalid")
        actual_tree = str(_git(root, "rev-parse", f"{candidate_head}^{{tree}}")).strip()
        parent_line = str(_git(root, "rev-list", "--parents", "-n", "1", candidate_head)).split()
        if actual_tree != candidate_tree or parent_line != [candidate_head, str(binding["authority_head"])]:
            raise ExecutorBlock("admission candidate does not have the exact bound parent and tree")
        evidence_root = (
            f"evidence/issues/{request['issue_number']}/epochs/{request['request_fingerprint']}"
        )
        expected_evidence_paths = {
            f"{evidence_root}/{name}" for name in CANDIDATE_REQUIRED_FILES
        }
        evidence_entries = _ls_tree(root, candidate_head, evidence_root)
        _regular_blob_entries(
            evidence_entries, expected_evidence_paths, "admission candidate evidence"
        )
        for repository_path in sorted(expected_evidence_paths):
            name = repository_path.removeprefix(f"{evidence_root}/")
            committed = _git(root, "show", f"{candidate_head}:{repository_path}", binary=True)
            assert isinstance(committed, bytes)
            local = bundle / name
            if not local.is_file() or local.is_symlink() or local.read_bytes() != committed:
                raise ExecutorBlock(
                    f"supplied bundle differs from candidate blob: {repository_path}"
                )
        integrity_entries: dict[str, tuple[str, str, str]] = {}
        for path in INTEGRITY_PATHS:
            integrity_entries.update(_ls_tree(root, candidate_head, f":(top){path}"))
        _regular_blob_entries(integrity_entries, set(INTEGRITY_PATHS), "candidate integrity trio")
        changed_raw = _git(
            root, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z",
            candidate_head, binary=True,
        )
        assert isinstance(changed_raw, bytes)
        try:
            changed = {
                path.decode("utf-8", errors="strict")
                for path in changed_raw.split(b"\0") if path
            }
        except UnicodeError as exc:
            raise ExecutorBlock("admission candidate changed path is not UTF-8") from exc
        expected_changed = expected_evidence_paths | set(INTEGRITY_PATHS)
        if changed != expected_changed:
            raise ExecutorBlock(
                "admission candidate changed path set differs: "
                f"missing={sorted(expected_changed - changed)} "
                f"surplus={sorted(changed - expected_changed)}"
            )
    return request, status, receipt, receipt_digest, registry_sha256


def build_plan(
    bundle: Path,
    verification_receipt: Path,
    *,
    root: Path = ROOT,
    verify_authority: bool = True,
    verify_candidate_git: bool = True,
) -> dict[str, Any]:
    request, status, receipt, receipt_digest, registry_sha256 = _validate_admission(
        root,
        bundle,
        verification_receipt,
        verify_authority=verify_authority,
        verify_candidate_git=verify_candidate_git,
    )
    contract, _ = load_contract(root)
    policy = _load_policy(root)
    registered = _registry_handler(contract, str(status["handler_id"]))
    if registered is None:
        return _hold(
            reason="UNMAPPED_HANDLER",
            request=request,
            receipt=receipt,
            registry_sha256=registry_sha256,
        )
    if receipt.get("executor_registration_state") != "REGISTERED_EXACT_HEAD":
        return _hold(
            reason="VERIFIER_DID_NOT_OBSERVE_REGISTERED_EXECUTOR",
            request=request,
            receipt=receipt,
            registry_sha256=registry_sha256,
        )
    if receipt.get("registered_executor_id") != registered.get("executor_id"):
        return _hold(
            reason="REGISTERED_EXECUTOR_ID_DRIFT",
            request=request,
            receipt=receipt,
            registry_sha256=registry_sha256,
        )

    implementation = registered.get("implementation")
    if implementation == "ROOT_CONTROL_PLANE_ATTESTATION_V1":
        work_product = _root_control_plane_attestation(root, registered, policy)
    else:  # load_contract already rejects this, retained as a fail-closed fence.
        return _hold(
            reason="UNSUPPORTED_EXECUTOR_IMPLEMENTATION",
            request=request,
            receipt=receipt,
            registry_sha256=registry_sha256,
        )
    # Runtime delivery and verification-run identities are provenance, not
    # semantics.  The execution id therefore excludes the verifier receipt
    # digest and all Actions run ids so redelivery is durably idempotent.
    work_product_sha256 = sha256_bytes(canonical_bytes(work_product))
    identity = {
        "schema": "qikvrt_issue_agent_execution_identity_v1",
        "repository": request["repository"],
        "issue_number": request["issue_number"],
        "request_fingerprint": request["request_fingerprint"],
        "authority_main": receipt["current_main"],
        "admission_candidate_head": receipt["head"],
        "admission_candidate_tree": receipt["tree"],
        "handler_id": status["handler_id"],
        "handler_sha256": status["handler_sha256"],
        "work_order_payload_sha256": receipt["work_order_payload_sha256"],
        "executor_contract": contract["contract_id"],
        "executor_registry_sha256": registry_sha256,
        "executor_entry_sha256": receipt["executor_entry_sha256"],
        "executor_id": registered["executor_id"],
        "executor_controller_blob_sha1": receipt["executor_controller_blob_sha1"],
        "executor_workflow_blob_sha1": receipt["executor_workflow_blob_sha1"],
        "work_product_sha256": work_product_sha256,
    }
    execution_id = sha256_bytes(canonical_bytes(identity))
    admission_provenance = {
        "candidate_verification_receipt_sha256": receipt_digest,
        "verifier_workflow_run_id": receipt.get("verifier_workflow_run_id"),
        "verifier_workflow_run_attempt": receipt.get("verifier_workflow_run_attempt"),
        "verifier_workflow_name": receipt.get("verifier_workflow_name"),
        "verifier_workflow_ref": receipt.get("verifier_workflow_ref"),
        "verifier_workflow_sha": receipt.get("verifier_workflow_sha"),
        "verifier_workflow_blob_sha1": receipt.get("verifier_workflow_blob_sha1"),
        "verifier_authority_tree": receipt.get("verifier_authority_tree"),
    }
    relative_root = (
        f"evidence/issues/{request['issue_number']}/executions/"
        f"{request['request_fingerprint']}/{execution_id}"
    )
    changed_paths = sorted(
        [f"{relative_root}/{name}" for name in EXECUTION_FILES]
    )
    return {
        "schema": "qikvrt_issue_agent_executor_plan_v1",
        "state": "READY_TO_MATERIALIZE",
        "repository": request["repository"],
        "issue_number": request["issue_number"],
        "request_fingerprint": request["request_fingerprint"],
        "authority_main": receipt["current_main"],
        "handler_id": status["handler_id"],
        "handler_sha256": status["handler_sha256"],
        "executor_contract": contract["contract_id"],
        "executor_registry_sha256": registry_sha256,
        "executor_id": registered["executor_id"],
        "implementation": implementation,
        "execution_identity": identity,
        "admission_provenance": admission_provenance,
        "execution_id": execution_id,
        "output_root": relative_root,
        "changed_paths": changed_paths,
        "allowed_candidate_paths": sorted([*changed_paths, *INTEGRITY_PATHS]),
        "work_product": work_product,
        "work_product_sha256": work_product_sha256,
        "repository_content_effect": "NOT_YET_APPLIED",
        "authority_main_effect": "NONE",
        "claims": FALSE_CLAIMS,
    }


def build_execution_receipt(plan: Mapping[str, Any]) -> dict[str, Any]:
    if plan.get("state") != "READY_TO_MATERIALIZE":
        raise ExecutorBlock("only a ready plan can materialize an execution receipt")
    identity = _mapping(plan.get("execution_identity"), "execution identity")
    return {
        "schema": "qikvrt_issue_agent_execution_receipt_v1",
        "state": "BOUNDED_WORK_PRODUCT_MATERIALIZED_ON_DRAFT_CANDIDATE",
        **identity,
        "admission_provenance": plan["admission_provenance"],
        "execution_id": plan["execution_id"],
        "implementation": plan["implementation"],
        "output_root": plan["output_root"],
        "work_product": plan["work_product"],
        "repository_content_effect": "DRAFT_CANDIDATE_WORKTREE_ONLY",
        "authority_main_effect": "NONE",
        "issue_lifecycle_effect": "NONE",
        "candidate_code_executed": False,
        "claims": FALSE_CLAIMS,
    }


def _worktree_head_and_clean(worktree: Path, expected_head: str) -> None:
    actual = str(_git(worktree, "rev-parse", "--verify", "HEAD^{commit}")).strip()
    if actual != expected_head:
        raise ExecutorBlock("output worktree is not the exact planned Authority main")
    status = str(_git(worktree, "status", "--porcelain=v1", "--untracked-files=all")).strip()
    if status:
        raise ExecutorBlock("output worktree must be clean before materialization")


def materialize(
    bundle: Path,
    verification_receipt: Path,
    output_worktree: Path,
    *,
    root: Path = ROOT,
    verify_authority: bool = True,
    verify_candidate_git: bool = True,
) -> dict[str, Any]:
    plan = build_plan(
        bundle,
        verification_receipt,
        root=root,
        verify_authority=verify_authority,
        verify_candidate_git=verify_candidate_git,
    )
    if plan["state"] != "READY_TO_MATERIALIZE":
        return plan
    _worktree_head_and_clean(output_worktree, str(plan["authority_main"]))
    output = output_worktree / str(plan["output_root"])
    cursor = output_worktree
    for part in PurePosixPath(str(plan["output_root"])).parts[:-1]:
        cursor = cursor / part
        if cursor.exists() and (cursor.is_symlink() or not cursor.is_dir()):
            raise ExecutorBlock(f"unsafe output ancestor: {cursor}")
    if output.exists():
        raise ExecutorBlock("execution output root already exists")
    output.mkdir(parents=True, exist_ok=False)
    receipt_path = output / "EXECUTION_RECEIPT.json"
    receipt_path.write_bytes(canonical_bytes(build_execution_receipt(plan)))
    (output / "EXECUTION_RECEIPT.sha256").write_text(
        f"{sha256_bytes(receipt_path.read_bytes())}  EXECUTION_RECEIPT.json\n",
        encoding="utf-8",
    )
    changed = sorted(
        line
        for line in str(
            _git(output_worktree, "status", "--porcelain=v1", "--untracked-files=all")
        ).splitlines()
        if line
    )
    changed_paths = sorted(line[3:] for line in changed)
    if changed_paths != plan["changed_paths"]:
        raise ExecutorBlock(
            f"materialized path set differs: expected={plan['changed_paths']} actual={changed_paths}"
        )
    return {
        **plan,
        "state": "MATERIALIZED",
        "repository_content_effect": "DRAFT_CANDIDATE_WORKTREE_ONLY",
    }


def verify_materialized(
    bundle: Path,
    verification_receipt: Path,
    output_worktree: Path,
    *,
    root: Path = ROOT,
    verify_authority: bool = True,
    verify_candidate_git: bool = True,
) -> dict[str, Any]:
    plan = build_plan(
        bundle,
        verification_receipt,
        root=root,
        verify_authority=verify_authority,
        verify_candidate_git=verify_candidate_git,
    )
    if plan["state"] != "READY_TO_MATERIALIZE":
        return plan
    output = output_worktree / str(plan["output_root"])
    receipt_path = output / "EXECUTION_RECEIPT.json"
    _verify_sidecar(receipt_path)
    actual = _load_json(receipt_path, "materialized execution receipt")
    expected = build_execution_receipt(plan)
    if actual != expected:
        raise ExecutorBlock("materialized execution receipt differs from exact plan")
    changed = sorted(
        line[3:]
        for line in str(
            _git(output_worktree, "status", "--porcelain=v1", "--untracked-files=all")
        ).splitlines()
        if line
    )
    surplus = sorted(set(changed) - set(plan["allowed_candidate_paths"]))
    missing = sorted(set(plan["changed_paths"]) - set(changed))
    if surplus or missing:
        raise ExecutorBlock(
            f"candidate path allowlist differs: missing={missing} surplus={surplus}"
        )
    return {
        **plan,
        "state": "VERIFIED_MATERIALIZATION",
        "repository_content_effect": "DRAFT_CANDIDATE_WORKTREE_ONLY",
    }


def verify_existing_result(
    bundle: Path,
    verification_receipt: Path,
    result_worktree: Path,
    *,
    root: Path = ROOT,
    verify_authority: bool = True,
    verify_candidate_git: bool = True,
) -> dict[str, Any]:
    """Verify an immutable prior result for the same semantic execution id.

    Delivery run/attempt and receipt-transport digest are provenance, so a
    sequential redelivery may legitimately differ there.  Every semantic
    field, stable verifier binding, path, mode, parent, and work-product byte
    remains exact.
    """
    plan = build_plan(
        bundle,
        verification_receipt,
        root=root,
        verify_authority=verify_authority,
        verify_candidate_git=verify_candidate_git,
    )
    if plan["state"] != "READY_TO_MATERIALIZE":
        return plan
    head = str(_git(result_worktree, "rev-parse", "--verify", "HEAD^{commit}")).strip()
    parents = str(_git(result_worktree, "rev-list", "--parents", "-n", "1", head)).split()
    if parents != [head, str(plan["authority_main"])]:
        raise ExecutorBlock("existing result is not a one-parent exact-main successor")
    status = str(
        _git(result_worktree, "status", "--porcelain=v1", "--untracked-files=all")
    ).strip()
    if status:
        raise ExecutorBlock("existing result worktree is not clean")

    changed_raw = _git(
        result_worktree, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z",
        head, binary=True,
    )
    assert isinstance(changed_raw, bytes)
    try:
        changed = {
            value.decode("utf-8", errors="strict")
            for value in changed_raw.split(b"\0") if value
        }
    except UnicodeError as exc:
        raise ExecutorBlock("existing result changed path is not UTF-8") from exc
    expected_paths = set(plan["allowed_candidate_paths"])
    if changed != expected_paths:
        raise ExecutorBlock(
            "existing result path set differs: "
            f"missing={sorted(expected_paths - changed)} surplus={sorted(changed - expected_paths)}"
        )
    entries: dict[str, tuple[str, str, str]] = {}
    for path in sorted(expected_paths):
        entries.update(_ls_tree(result_worktree, head, f":(top){path}"))
    _regular_blob_entries(entries, expected_paths, "existing result")

    receipt_path = result_worktree / str(plan["output_root"]) / "EXECUTION_RECEIPT.json"
    _verify_sidecar(receipt_path)
    actual = _load_json(receipt_path, "existing execution receipt")
    expected = build_execution_receipt(plan)
    actual_without_provenance = dict(actual)
    expected_without_provenance = dict(expected)
    actual_provenance = _mapping(
        actual_without_provenance.pop("admission_provenance", None),
        "existing admission provenance",
    )
    expected_provenance = _mapping(
        expected_without_provenance.pop("admission_provenance", None),
        "expected admission provenance",
    )
    if actual_without_provenance != expected_without_provenance:
        raise ExecutorBlock("existing execution receipt semantic fields differ")
    if set(actual_provenance) != set(expected_provenance):
        raise ExecutorBlock("existing execution provenance field set differs")
    for key in (
        "verifier_workflow_name", "verifier_workflow_ref", "verifier_workflow_sha",
        "verifier_workflow_blob_sha1", "verifier_authority_tree",
    ):
        if actual_provenance.get(key) != expected_provenance.get(key):
            raise ExecutorBlock(f"existing stable verifier provenance differs: {key}")
    if not HEX64.fullmatch(str(actual_provenance.get("candidate_verification_receipt_sha256"))):
        raise ExecutorBlock("existing verifier receipt provenance digest is invalid")
    for key in ("verifier_workflow_run_id", "verifier_workflow_run_attempt"):
        value = actual_provenance.get(key)
        if type(value) is not int or value < 1:
            raise ExecutorBlock(f"existing verifier provenance is invalid: {key}")
    return {
        **plan,
        "state": "VERIFIED_EXISTING_RESULT",
        "existing_result_head": head,
        "repository_content_effect": "EXISTING_IMMUTABLE_DRAFT_CANDIDATE_REOBSERVED",
    }


def _emit(value: Mapping[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "materialize", "verify", "verify-existing"):
        command = sub.add_parser(name)
        command.add_argument("--bundle", type=Path, required=True)
        command.add_argument("--verification-receipt", type=Path, required=True)
        if name != "plan":
            command.add_argument("--output-worktree", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "plan":
            result = build_plan(args.bundle, args.verification_receipt)
        elif args.command == "materialize":
            result = materialize(
                args.bundle,
                args.verification_receipt,
                args.output_worktree,
            )
        elif args.command == "verify":
            result = verify_materialized(
                args.bundle,
                args.verification_receipt,
                args.output_worktree,
            )
        else:
            result = verify_existing_result(
                args.bundle,
                args.verification_receipt,
                args.output_worktree,
            )
    except (ExecutorBlock, OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        _emit(
            {
                "schema": "qikvrt_issue_agent_executor_plan_v1",
                "state": "HOLD",
                "failure_class": "EXECUTOR_VALIDATION_BLOCKED",
                "detail": str(exc),
                "changed_paths": [],
                "repository_content_effect": "NONE",
                "authority_main_effect": "NONE",
                "claims": FALSE_CLAIMS,
            }
        )
        return 2
    _emit(result)
    return 0 if result.get("state") != "HOLD" else 2


if __name__ == "__main__":
    raise SystemExit(main())
