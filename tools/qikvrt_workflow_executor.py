#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Exact-head workflow-executor planning and mesh-node continuity checks.

The controller is deliberately repository-local.  It observes Git state and
workflow metadata supplied by the caller, creates a deterministic dispatch
plan, and validates a node-split continuity receipt.  It never calls GitHub,
dispatches a workflow, writes a repository file, or treats a terminal watcher
as a successful gate.  The narrowly authorised Action wrapper performs the
single REST dispatch only after this controller has produced a candidate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.parse
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_RELATIVE_PATH = "state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json"
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
ACTIVE_RUN_STATUSES = frozenset({"queued", "in_progress", "waiting", "requested", "pending"})
WORK_STATES = frozenset({"READY", "RUNNING", "WAITING", "BLOCKED", "COMPLETED"})
WORKFLOW_SUFFIXES = (".yml", ".yaml")


class ExecutorBlock(RuntimeError):
    """A fail-closed executor or continuity validation error."""


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ExecutorBlock(f"{label} must be an object")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExecutorBlock(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ExecutorBlock(f"{label} must be a list of non-empty strings")
    return list(value)


def _sha(value: Any, label: str) -> str:
    value = _string(value, label)
    if not SHA_RE.fullmatch(value):
        raise ExecutorBlock(f"{label} must be a lower-case 40-character Git SHA")
    return value


def _sha256(value: Any, label: str) -> str:
    value = _string(value, label)
    if not SHA256_RE.fullmatch(value):
        raise ExecutorBlock(f"{label} must be a lower-case 64-character SHA-256")
    return value


def _integer(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ExecutorBlock(f"{label} must be an integer greater than or equal to {minimum}")
    return value


def _repository_path(value: Any, label: str) -> str:
    value = _string(value, label)
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts or value.startswith("./"):
        raise ExecutorBlock(f"{label} must be a normalized repository-relative path")
    return candidate.as_posix()


def _cycle_nodes(graph: Mapping[str, Sequence[str]]) -> list[str]:
    """Return every node participating in a directed cycle."""

    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    result: set[str] = set()

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for dependency in graph.get(node, ()):
            if dependency not in graph:
                continue
            if dependency not in indices:
                visit(dependency)
                lowlinks[node] = min(lowlinks[node], lowlinks[dependency])
            elif dependency in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[dependency])
        if lowlinks[node] != indices[node]:
            return
        component: list[str] = []
        while stack:
            member = stack.pop()
            on_stack.remove(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1 or node in graph.get(node, ()):
            result.update(component)

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return sorted(result)


def _git(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise ExecutorBlock(f"git {' '.join(arguments)} failed: {detail}")
    return completed.stdout.strip()


def load_contract(root: Path = ROOT) -> dict[str, Any]:
    path = root / CONTRACT_RELATIVE_PATH
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutorBlock(f"cannot load workflow executor contract: {exc}") from exc
    result = dict(_mapping(value, "workflow executor contract"))
    if result.get("schema") != "qikvrt_workflow_executor_mesh_contract_v1":
        raise ExecutorBlock("workflow executor contract schema is not v1")
    if result.get("contract_id") != "qikvrt-workflow-executor-mesh-v1":
        raise ExecutorBlock("workflow executor contract id is not recognized")
    return result


def _contract_sha256(root: Path) -> str:
    try:
        return sha256_bytes((root / CONTRACT_RELATIVE_PATH).read_bytes())
    except OSError as exc:
        raise ExecutorBlock(f"cannot hash workflow executor contract: {exc}") from exc


def _workflow_inventory(root: Path, revision: str) -> list[dict[str, str]]:
    completed = subprocess.run(
        ["git", "-C", str(root), "ls-tree", "-r", "-z", revision, "--", ".github/workflows"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ExecutorBlock(f"cannot enumerate workflow tree: {detail}")
    inventory: list[dict[str, str]] = []
    for entry in completed.stdout.split(b"\0"):
        if not entry:
            continue
        try:
            metadata, encoded_path = entry.split(b"\t", 1)
            _mode, object_type, blob_sha = metadata.decode("ascii").split(" ", 2)
            path = encoded_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise ExecutorBlock("workflow inventory contains a malformed Git tree entry") from exc
        if object_type != "blob" or not path.endswith(WORKFLOW_SUFFIXES):
            continue
        inventory.append({"path": path, "blob_sha": _sha(blob_sha, f"workflow blob for {path}")})
    return sorted(inventory, key=lambda item: item["path"])


def _workflow_bytes(root: Path, revision: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), "show", f"{revision}:{path}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ExecutorBlock(f"cannot read exact workflow blob {path}: {detail}")
    return completed.stdout


def _strip_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _inline_yaml_list(value: str, label: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        body = value[1:-1].strip()
        if not body:
            return []
        return [_strip_yaml_scalar(item) for item in body.split(",")]
    if value.startswith("[") or value.endswith("]"):
        raise ExecutorBlock(f"{label} has malformed inline list syntax")
    return [_strip_yaml_scalar(value)]


def _top_level_section(lines: Sequence[str], key: str) -> tuple[int, int] | None:
    marker = f"{key}:"
    for index, line in enumerate(lines):
        if line == marker:
            end = index + 1
            while end < len(lines):
                candidate = lines[end]
                if candidate and not candidate.startswith((" ", "#")):
                    break
                end += 1
            return index, end
    return None


def _parse_needs(job_lines: Sequence[str], path: str, job: str) -> list[str]:
    needs: list[str] = []
    for index, line in enumerate(job_lines):
        match = re.fullmatch(r"    needs:\s*(.*)", line)
        if not match:
            continue
        inline = match.group(1).strip()
        if inline:
            needs.extend(_inline_yaml_list(inline, f"{path}:{job} needs"))
            continue
        cursor = index + 1
        while cursor < len(job_lines):
            nested = job_lines[cursor]
            item = re.fullmatch(r"      -\s*(.+)", nested)
            if item:
                needs.append(_strip_yaml_scalar(item.group(1)))
                cursor += 1
                continue
            if nested.startswith("      ") or not nested.strip():
                cursor += 1
                continue
            break
    if len(needs) != len(set(needs)):
        raise ExecutorBlock(f"workflow {path} job {job} repeats a needs dependency")
    return needs


def _parse_workflow(path: str, payload: bytes) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExecutorBlock(f"workflow {path} is not UTF-8") from exc
    lines = text.splitlines()
    if any(re.match(r"^[ ]*\t", line) for line in lines):
        raise ExecutorBlock(f"workflow {path} uses a tab for YAML indentation")
    name: str | None = None
    for line in lines:
        match = re.fullmatch(r"name:\s*(.+)", line)
        if match:
            name = _strip_yaml_scalar(match.group(1))
            break
    if not name:
        raise ExecutorBlock(f"workflow {path} has no top-level name")

    concurrency_section = _top_level_section(lines, "concurrency")
    group: str | None = None
    cancel: bool | None = None
    if concurrency_section is not None:
        start, end = concurrency_section
        for line in lines[start + 1 : end]:
            group_match = re.fullmatch(r"  group:\s*(.+)", line)
            cancel_match = re.fullmatch(r"  cancel-in-progress:\s*(true|false)", line)
            if group_match:
                group = _strip_yaml_scalar(group_match.group(1))
            if cancel_match:
                cancel = cancel_match.group(1) == "true"

    jobs_section = _top_level_section(lines, "jobs")
    if jobs_section is None:
        raise ExecutorBlock(f"workflow {path} has no jobs section")
    jobs_start, jobs_end = jobs_section
    headers: list[tuple[str, int]] = []
    for index in range(jobs_start + 1, jobs_end):
        match = re.fullmatch(r"  ([A-Za-z0-9_-]+):\s*", lines[index])
        if match:
            headers.append((match.group(1), index))
    if not headers:
        raise ExecutorBlock(f"workflow {path} declares no jobs")
    jobs: dict[str, dict[str, Any]] = {}
    for position, (job, start) in enumerate(headers):
        end = headers[position + 1][1] if position + 1 < len(headers) else jobs_end
        block = lines[start + 1 : end]
        timeout_values = [
            match.group(1)
            for line in block
            if (match := re.fullmatch(r"    timeout-minutes:\s*(.+)", line))
        ]
        timeout: int | None = None
        if len(timeout_values) > 1:
            raise ExecutorBlock(f"workflow {path} job {job} repeats timeout-minutes")
        if timeout_values:
            raw_timeout = _strip_yaml_scalar(timeout_values[0])
            if not raw_timeout.isdigit():
                raise ExecutorBlock(f"workflow {path} job {job} timeout-minutes is not an integer")
            timeout = int(raw_timeout)
        jobs[job] = {"timeout_minutes": timeout, "needs": _parse_needs(block, path, job)}

    on_section = _top_level_section(lines, "on")
    workflow_run_upstreams: list[str] = []
    if on_section is not None:
        on_start, on_end = on_section
        workflow_run_start: int | None = None
        for index in range(on_start + 1, on_end):
            if re.fullmatch(r"  workflow_run:\s*", lines[index]):
                workflow_run_start = index
                break
        if workflow_run_start is not None:
            cursor = workflow_run_start + 1
            while cursor < on_end and (not lines[cursor] or lines[cursor].startswith("    ")):
                match = re.fullmatch(r"    workflows:\s*(.*)", lines[cursor])
                if not match:
                    cursor += 1
                    continue
                inline = match.group(1).strip()
                if inline:
                    workflow_run_upstreams.extend(
                        _inline_yaml_list(inline, f"{path} workflow_run.workflows")
                    )
                else:
                    cursor += 1
                    while cursor < on_end:
                        item = re.fullmatch(r"      -\s*(.+)", lines[cursor])
                        if item:
                            workflow_run_upstreams.append(_strip_yaml_scalar(item.group(1)))
                            cursor += 1
                            continue
                        if not lines[cursor].strip():
                            cursor += 1
                            continue
                        break
                break
    return {
        "path": path,
        "name": name,
        "concurrency_group": group,
        "cancel_in_progress": cancel,
        "jobs": jobs,
        "workflow_run_upstreams": workflow_run_upstreams,
    }


def _shared_serial_lanes(contract: Mapping[str, Any]) -> dict[str, set[str]]:
    orchestration = _mapping(contract.get("orchestration"), "orchestration contract")
    topology = _mapping(orchestration.get("topology"), "orchestration topology")
    lanes = topology.get("shared_serial_lanes")
    if not isinstance(lanes, list):
        raise ExecutorBlock("shared serial lanes must be a list")
    result: dict[str, set[str]] = {}
    all_paths: set[str] = set()
    for raw in lanes:
        lane = _mapping(raw, "shared serial lane")
        group = _string(lane.get("group"), "shared serial lane group")
        paths = set(_string_list(lane.get("workflow_paths"), "shared serial lane workflow paths"))
        group_key = group.casefold()
        if len(paths) < 2 or group_key in result:
            raise ExecutorBlock("shared serial lane must bind one unique group to at least two workflows")
        if paths & all_paths:
            raise ExecutorBlock("a workflow may belong to only one shared serial lane")
        if lane.get("order") != "RESERVE_THEN_FINALIZE":
            raise ExecutorBlock("shared serial lane order must be reserve then finalize")
        if lane.get("wait_while_holding_lane") is not False:
            raise ExecutorBlock("shared serial lane may not wait while holding its lane")
        result[group_key] = paths
        all_paths.update(paths)
    return result


def _workflow_topology_from_records(
    workflows: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    orchestration = _mapping(contract.get("orchestration"), "orchestration contract")
    topology_contract = _mapping(orchestration.get("topology"), "orchestration topology")
    maximum_timeout = _integer(
        topology_contract.get("maximum_job_timeout_minutes"),
        "maximum job timeout minutes",
        minimum=1,
    )
    names: dict[str, str] = {}
    groups: dict[str, set[str]] = defaultdict(set)
    workflow_run_graph: dict[str, list[str]] = {}
    for workflow in workflows:
        path = workflow["path"]
        name = workflow["name"]
        if name in names:
            raise ExecutorBlock(f"duplicate workflow name {name!r}: {names[name]} and {path}")
        names[name] = path
        group = workflow["concurrency_group"]
        if topology_contract.get("every_workflow_requires_concurrency") is True and not group:
            raise ExecutorBlock(f"workflow topology violation: {path} has no concurrency group")
        if (
            topology_contract.get("every_concurrency_group_requires_cancel_policy") is True
            and workflow["cancel_in_progress"] is None
        ):
            raise ExecutorBlock(f"workflow topology violation: {path} has no cancel-in-progress policy")
        if group:
            # GitHub concurrency group names are case-insensitive.
            groups[group.casefold()].add(path)
        job_graph = {job: value["needs"] for job, value in workflow["jobs"].items()}
        for job, value in workflow["jobs"].items():
            timeout = value["timeout_minutes"]
            if topology_contract.get("every_job_requires_timeout_minutes") is True and timeout is None:
                raise ExecutorBlock(f"workflow topology violation: {path} job {job} has no timeout-minutes")
            if timeout is not None and (timeout < 1 or timeout > maximum_timeout):
                raise ExecutorBlock(
                    f"workflow topology violation: {path} job {job} timeout {timeout} is outside 1..{maximum_timeout}"
                )
            unknown = sorted(set(value["needs"]) - set(workflow["jobs"]))
            if unknown:
                raise ExecutorBlock(f"workflow topology violation: {path} job {job} has unknown needs {unknown}")
        cycles = _cycle_nodes(job_graph)
        if topology_contract.get("job_needs_graph_must_be_acyclic") is True and cycles:
            raise ExecutorBlock(f"workflow topology violation: {path} job dependency cycle {cycles}")
        workflow_run_graph[name] = list(workflow["workflow_run_upstreams"])

    shared = _shared_serial_lanes(contract)
    for group, paths in sorted(groups.items()):
        if len(paths) > 1 and paths != shared.get(group):
            raise ExecutorBlock(
                f"workflow topology violation: undeclared shared concurrency group {group!r} for {sorted(paths)}"
            )
    for group, expected_paths in sorted(shared.items()):
        if groups.get(group, set()) != expected_paths:
            raise ExecutorBlock(
                f"workflow topology violation: shared lane {group!r} differs: "
                f"expected={sorted(expected_paths)} actual={sorted(groups.get(group, set()))}"
            )
    for name, upstreams in workflow_run_graph.items():
        missing = sorted(set(upstreams) - set(names))
        if missing:
            raise ExecutorBlock(f"workflow topology violation: {name!r} observes unknown workflows {missing}")
    workflow_cycles = _cycle_nodes(workflow_run_graph)
    if topology_contract.get("workflow_run_graph_must_be_acyclic") is True and workflow_cycles:
        raise ExecutorBlock(f"workflow topology violation: workflow_run cycle {workflow_cycles}")

    compact_workflows = []
    for workflow in workflows:
        compact_workflows.append(
            {
                "path": workflow["path"],
                "name": workflow["name"],
                "concurrency_group": workflow["concurrency_group"],
                "cancel_in_progress": workflow["cancel_in_progress"],
                "jobs": [
                    {
                        "id": job,
                        "timeout_minutes": value["timeout_minutes"],
                        "needs": value["needs"],
                    }
                    for job, value in sorted(workflow["jobs"].items())
                ],
                "workflow_run_upstreams": workflow["workflow_run_upstreams"],
            }
        )
    return {
        "state": "ACYCLIC_BOUNDED",
        "workflow_count": len(compact_workflows),
        "job_count": sum(len(workflow["jobs"]) for workflow in compact_workflows),
        "shared_serial_lane_count": len(shared),
        "workflow_run_edge_count": sum(len(value) for value in workflow_run_graph.values()),
        "workflows": compact_workflows,
    }


def workflow_topology(
    root: Path,
    revision: str,
    inventory: Sequence[Mapping[str, str]],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    workflows = [
        _parse_workflow(item["path"], _workflow_bytes(root, revision, item["path"]))
        for item in inventory
    ]
    return _workflow_topology_from_records(workflows, contract)


def _validate_contract_shape(contract: Mapping[str, Any], root: Path) -> None:
    authority = _mapping(contract.get("authority"), "contract authority")
    if authority.get("repository") != "Goldkelch/qik-vrt" or authority.get("entrypoint") != "AI":
        raise ExecutorBlock("contract authority binding is not canonical")
    executor = _mapping(contract.get("executor"), "contract executor")
    for key in ("controller_path", "workflow_path", "watchdog_workflow_path", "monitor_workflow_path"):
        relative_path = _string(executor.get(key), f"contract executor.{key}")
        if not (root / relative_path).is_file():
            raise ExecutorBlock(f"contract-required file is absent: {relative_path}")
    if executor.get("observation_mode") != "REPOSITORY_NATIVE_EXACT_HEAD_BOUND":
        raise ExecutorBlock("executor observation mode is not exact-head bound")
    if executor.get("stateful_writes") != "ACTION_ARTIFACTS_ONLY":
        raise ExecutorBlock("executor stateful write boundary is not artifact-only")
    if _string_list(executor.get("single_writer_order"), "executor single writer order") != [
        "AUTHORITY",
        "MIRROR",
        "MESH_NODE",
    ]:
        raise ExecutorBlock("executor single writer order is not authority-first")
    if executor.get("orchestration_mode") != "ACYCLIC_LEASED_CONFLICT_COMPONENTS":
        raise ExecutorBlock("executor orchestration mode is not deadlock-preventive")

    orchestration = _mapping(contract.get("orchestration"), "orchestration contract")
    if orchestration.get("scope") != "EVERY_WORKFLOW_IN_EXACT_TREE":
        raise ExecutorBlock("orchestration does not cover every exact-tree workflow")
    topology = _mapping(orchestration.get("topology"), "orchestration topology")
    for key in (
        "every_workflow_requires_concurrency",
        "every_concurrency_group_requires_cancel_policy",
        "every_job_requires_timeout_minutes",
        "job_needs_graph_must_be_acyclic",
        "workflow_run_graph_must_be_acyclic",
    ):
        if topology.get(key) is not True:
            raise ExecutorBlock(f"orchestration topology invariant is disabled: {key}")
    if _integer(
        topology.get("maximum_job_timeout_minutes"),
        "maximum job timeout minutes",
        minimum=1,
    ) != 360:
        raise ExecutorBlock("maximum job timeout must remain 360 minutes")
    if topology.get("undeclared_shared_concurrency_group") != "BLOCK":
        raise ExecutorBlock("undeclared shared concurrency groups must block")
    _shared_serial_lanes(contract)

    work_queue = _mapping(orchestration.get("work_queue"), "orchestration work queue")
    lanes = _string_list(work_queue.get("lanes"), "work queue lanes")
    expected_lanes = [
        "AUTHORITY_CANDIDATE",
        "AUTHORITY_PROMOTION",
        "MIRROR_PORT",
        "MIRROR_PROMOTION",
        "MESH_NODE",
        "EXTERNAL_EFFECT",
    ]
    if lanes != expected_lanes:
        raise ExecutorBlock("work queue lanes are not the canonical authority-first order")
    if _string_list(work_queue.get("lane_order"), "work queue lane order") != lanes:
        raise ExecutorBlock("work queue lanes must have one total acquisition order")
    parallel_lanes = set(_string_list(work_queue.get("parallel_lanes"), "parallel lanes"))
    serialized_lanes = set(_string_list(work_queue.get("serialized_lanes"), "serialized lanes"))
    if parallel_lanes & serialized_lanes or parallel_lanes | serialized_lanes != set(lanes):
        raise ExecutorBlock("work queue lanes must be partitioned into parallel and serialized lanes")
    if parallel_lanes != {"AUTHORITY_CANDIDATE"} or serialized_lanes != set(lanes[1:]):
        raise ExecutorBlock("only Authority candidates may use the parallel lane")
    maximum_parallel = _integer(
        work_queue.get("maximum_parallel_candidates"),
        "maximum parallel candidates",
        minimum=1,
    )
    if maximum_parallel != executor.get("maximum_parallel_independent_candidates"):
        raise ExecutorBlock("executor and work queue parallel limits differ")
    if work_queue.get("blocked_candidate_stalls_independent_component") is not False:
        raise ExecutorBlock("a blocked candidate may not stall an independent component")
    if work_queue.get("dependency_cycle_policy") != "REJECT_CYCLE_AND_CONTINUE_INDEPENDENT_COMPONENTS":
        raise ExecutorBlock("dependency cycles must be rejected without stalling independent work")
    if work_queue.get("hold_lease_while_waiting") is not False:
        raise ExecutorBlock("hold-and-wait is forbidden")
    if work_queue.get("mirror_requires_completed_authority_dependency") is not True:
        raise ExecutorBlock("Mirror work must remain Authority-successor-bound")
    if work_queue.get("planner_command") != (
        "python3 -B tools/qikvrt_workflow_executor.py plan-work"
    ):
        raise ExecutorBlock("work queue planner command is not canonical")
    if _string_list(
        work_queue.get("work_item_required_fields"),
        "work item required fields",
    ) != [
        "id",
        "lane",
        "state",
        "changed_paths",
        "dependencies",
        "last_progress_epoch",
        "state_signature",
    ]:
        raise ExecutorBlock("work item schema differs")
    if _string_list(
        work_queue.get("lease_required_fields"),
        "lease required fields",
    ) != [
        "id",
        "owner_id",
        "conflict_paths",
        "acquired_epoch",
        "expires_epoch",
        "generation",
        "state_signature",
    ]:
        raise ExecutorBlock("lease schema differs")
    if _string_list(work_queue.get("fairness_order"), "work queue fairness order") != [
        "LAST_PROGRESS_EPOCH_ASC",
        "WORK_ID_ASC",
    ]:
        raise ExecutorBlock("work queue fairness order is not stable")
    if _string_list(
        work_queue.get("generated_projection_paths"),
        "generated projection paths",
    ) != [
        "REPOSITORY_FILE_MANIFEST.json",
        "REPOSITORY_FILE_MANIFEST.json.sha256",
        "SHA256SUMS.txt",
    ]:
        raise ExecutorBlock("generated projection path classification differs")
    if work_queue.get("semantic_path_overlap_defines_conflict") is not True:
        raise ExecutorBlock("semantic path overlap must define a conflict")
    if work_queue.get("generated_projection_overlap_alone_defines_conflict") is not False:
        raise ExecutorBlock("generated projection overlap alone must not define a conflict")
    lease = _mapping(work_queue.get("lease"), "work queue lease")
    if _integer(lease.get("duration_seconds"), "lease duration seconds", minimum=1) != 900:
        raise ExecutorBlock("lease duration must remain bounded to 900 seconds")
    for key in (
        "caller_supplies_observation_epoch",
        "renewal_requires_state_signature_change",
        "owner_and_conflict_scope_binding_required",
    ):
        if lease.get(key) is not True:
            raise ExecutorBlock(f"lease invariant is disabled: {key}")
    if lease.get("expired_lease_blocks_work") is not False:
        raise ExecutorBlock("expired leases must not block work")

    policy = _mapping(contract.get("dispatch_policy"), "dispatch policy")
    if policy.get("enabled") is not True or policy.get("dispatch_ref") != "main":
        raise ExecutorBlock("dispatch policy is not enabled for main")
    if policy.get("terminal_or_active_exact_run_suppresses_duplicate_dispatch") is not True:
        raise ExecutorBlock("dispatch policy does not suppress duplicate exact-head runs")
    if policy.get("rerun") != "ONLY_REPOSITORY_DECLARED_TRANSIENT_FAILURE":
        raise ExecutorBlock("dispatch policy allows an unbounded rerun")
    required_conditions = set(_string_list(policy.get("required_conditions"), "dispatch conditions"))
    for condition in (
        "CURRENT_MAIN_HEAD_REOBSERVED",
        "CURRENT_MAIN_TREE_REOBSERVED",
        "WORKFLOW_IS_EXACT_TREE_MEMBER",
        "NO_COMPETING_WRITER",
        "NO_EQUIVALENT_EXACT_HEAD_RUN",
        "NO_EXTERNAL_OR_IRREVERSIBLE_EFFECT",
    ):
        if condition not in required_conditions:
            raise ExecutorBlock(f"dispatch condition missing: {condition}")
    _string_list(policy.get("writer_workflow_names"), "writer workflow names")
    allowed = policy.get("authorized_workflows")
    if not isinstance(allowed, list) or not allowed:
        raise ExecutorBlock("dispatch policy has no authorized workflow")
    for entry in allowed:
        item = _mapping(entry, "authorized workflow")
        workflow_id = _string(item.get("workflow_id"), "authorized workflow id")
        workflow_path = _string(item.get("workflow_path"), "authorized workflow path")
        if Path(workflow_path).name != workflow_id or not workflow_path.startswith(".github/workflows/"):
            raise ExecutorBlock("authorized workflow id/path binding is invalid")
        _string(item.get("workflow_name"), "authorized workflow name")
        if _string_list(item.get("allowed_events"), "authorized workflow events") != ["workflow_dispatch"]:
            raise ExecutorBlock("authorized workflow has an unbounded event set")
        if item.get("external_effect") != "NONE" or item.get("is_writer") is not False:
            raise ExecutorBlock("authorized workflow exceeds the no-effect observer boundary")

    boundaries = _mapping(contract.get("boundaries"), "executor boundaries")
    if boundaries.get("direct_repository_mutation") != "FORBIDDEN":
        raise ExecutorBlock("executor permits direct repository mutation")
    for key in (
        "watchdog_terminality_is_gate_success",
        "action_required_is_trusted_execution",
        "zero_job_is_trusted_execution",
    ):
        if boundaries.get(key) is not False:
            raise ExecutorBlock(f"executor boundary {key} must be false")

    continuity = _mapping(contract.get("mesh_node_split_acceptance"), "mesh node split acceptance")
    if continuity.get("applies_to") != "EVERY_FUTURE_NODE_ADDED_BY_QUEUE_ROW":
        raise ExecutorBlock("mesh node acceptance does not bind every future queue node")
    for key in ("receipt_path", "receipt_schema", "continuity_declaration_schema"):
        _string(continuity.get(key), f"mesh node split acceptance.{key}")
    _string_list(continuity.get("required_acceptance_tests"), "mesh node acceptance tests")
    _string_list(continuity.get("connection_order"), "mesh node connection order")


def workflow_delta(
    current_inventory: Sequence[Mapping[str, str]], baseline: Mapping[str, Any] | None
) -> dict[str, Any]:
    if baseline is None:
        return {"state": "BASELINE_UNAVAILABLE", "added": [], "removed": [], "changed": []}
    previous_raw = baseline.get("workflow_inventory")
    if not isinstance(previous_raw, list):
        raise ExecutorBlock("baseline does not contain a workflow inventory")
    previous: dict[str, str] = {}
    for entry in previous_raw:
        item = _mapping(entry, "baseline workflow inventory entry")
        path = _string(item.get("path"), "baseline workflow path")
        previous[path] = _sha(item.get("blob_sha"), f"baseline workflow blob for {path}")
    current = {item["path"]: item["blob_sha"] for item in current_inventory}
    return {
        "state": "COMPARED",
        "added": sorted(set(current) - set(previous)),
        "removed": sorted(set(previous) - set(current)),
        "changed": sorted(path for path in set(current) & set(previous) if current[path] != previous[path]),
    }


def _work_item(raw: Any, lanes: set[str], index: int) -> dict[str, Any]:
    item = _mapping(raw, f"work item {index}")
    work_id = _string(item.get("id"), f"work item {index} id")
    lane = _string(item.get("lane"), f"work item {work_id} lane")
    if lane not in lanes:
        raise ExecutorBlock(f"work item {work_id} uses unknown lane {lane}")
    state = _string(item.get("state"), f"work item {work_id} state")
    if state not in WORK_STATES:
        raise ExecutorBlock(f"work item {work_id} uses unknown state {state}")
    changed_paths = [
        _repository_path(path, f"work item {work_id} changed path")
        for path in _string_list(item.get("changed_paths"), f"work item {work_id} changed paths")
    ]
    dependencies = _string_list(item.get("dependencies"), f"work item {work_id} dependencies")
    if len(changed_paths) != len(set(changed_paths)):
        raise ExecutorBlock(f"work item {work_id} repeats a changed path")
    if len(dependencies) != len(set(dependencies)) or work_id in dependencies:
        raise ExecutorBlock(f"work item {work_id} has invalid dependencies")
    return {
        "id": work_id,
        "lane": lane,
        "state": state,
        "changed_paths": sorted(changed_paths),
        "dependencies": sorted(dependencies),
        "last_progress_epoch": _integer(
            item.get("last_progress_epoch"),
            f"work item {work_id} last progress epoch",
        ),
        "state_signature": _sha256(
            item.get("state_signature"),
            f"work item {work_id} state signature",
        ),
    }


def work_queue_plan(
    document: Mapping[str, Any],
    now_epoch: int,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Select independent work without hold-and-wait or head-of-line blocking.

    The caller owns observation.  This pure planner validates caller-supplied
    work and finite leases, rejects cyclic components, and continues selecting
    unrelated components deterministically.
    """

    now_epoch = _integer(now_epoch, "observation epoch")
    contract = load_contract(root)
    _validate_contract_shape(contract, root)
    queue = _mapping(
        _mapping(contract["orchestration"], "orchestration contract")["work_queue"],
        "orchestration work queue",
    )
    lanes = _string_list(queue["lanes"], "work queue lanes")
    lane_positions = {lane: index for index, lane in enumerate(lanes)}
    parallel_lanes = set(_string_list(queue["parallel_lanes"], "parallel lanes"))
    serialized_lanes = set(_string_list(queue["serialized_lanes"], "serialized lanes"))
    generated_paths = set(
        _string_list(queue["generated_projection_paths"], "generated projection paths")
    )
    maximum_parallel = _integer(
        queue["maximum_parallel_candidates"],
        "maximum parallel candidates",
        minimum=1,
    )
    lease_contract = _mapping(queue["lease"], "work queue lease")
    lease_duration = _integer(
        lease_contract["duration_seconds"],
        "lease duration seconds",
        minimum=1,
    )

    raw_items = document.get("work_items")
    raw_leases = document.get("leases")
    if not isinstance(raw_items, list) or not isinstance(raw_leases, list):
        raise ExecutorBlock("work plan input must contain work_items and leases lists")
    items = [_work_item(raw, set(lanes), index) for index, raw in enumerate(raw_items)]
    item_by_id = {item["id"]: item for item in items}
    if len(item_by_id) != len(items):
        raise ExecutorBlock("work item ids must be unique")
    for item in items:
        unknown = sorted(set(item["dependencies"]) - set(item_by_id))
        if unknown:
            raise ExecutorBlock(f"work item {item['id']} has unknown dependencies {unknown}")

    dependency_graph = {item["id"]: item["dependencies"] for item in items}
    cycle_nodes = set(_cycle_nodes(dependency_graph))
    semantic_paths = {
        item["id"]: set(item["changed_paths"]) - generated_paths for item in items
    }

    active_leases: list[dict[str, Any]] = []
    expired_lease_ids: list[str] = []
    lease_owner_blockers: dict[str, str] = {}
    seen_lease_ids: set[str] = set()
    for index, raw in enumerate(raw_leases):
        lease = _mapping(raw, f"lease {index}")
        lease_id = _string(lease.get("id"), f"lease {index} id")
        if lease_id in seen_lease_ids:
            raise ExecutorBlock(f"lease id is repeated: {lease_id}")
        seen_lease_ids.add(lease_id)
        owner_id = _string(lease.get("owner_id"), f"lease {lease_id} owner id")
        if owner_id not in item_by_id:
            raise ExecutorBlock(f"lease {lease_id} has unknown owner {owner_id}")
        conflict_paths = [
            _repository_path(path, f"lease {lease_id} conflict path")
            for path in _string_list(lease.get("conflict_paths"), f"lease {lease_id} conflict paths")
        ]
        if len(conflict_paths) != len(set(conflict_paths)):
            raise ExecutorBlock(f"lease {lease_id} repeats a conflict path")
        if set(conflict_paths) != set(item_by_id[owner_id]["changed_paths"]):
            raise ExecutorBlock(f"lease {lease_id} conflict scope is not bound to owner {owner_id}")
        acquired_epoch = _integer(lease.get("acquired_epoch"), f"lease {lease_id} acquired epoch")
        expires_epoch = _integer(lease.get("expires_epoch"), f"lease {lease_id} expires epoch")
        if acquired_epoch > now_epoch or expires_epoch <= acquired_epoch:
            raise ExecutorBlock(f"lease {lease_id} has an invalid time interval")
        if expires_epoch - acquired_epoch > lease_duration:
            raise ExecutorBlock(f"lease {lease_id} exceeds the bounded lease duration")
        state_signature = _sha256(
            lease.get("state_signature"),
            f"lease {lease_id} state signature",
        )
        if state_signature != item_by_id[owner_id]["state_signature"]:
            raise ExecutorBlock(f"lease {lease_id} state signature is not bound to owner {owner_id}")
        generation = _integer(lease.get("generation"), f"lease {lease_id} generation", minimum=1)
        renewed_from = lease.get("renewed_from_state_signature")
        unchanged_renewal = False
        if generation == 1 and renewed_from is not None:
            raise ExecutorBlock(f"initial lease {lease_id} may not declare a renewal signature")
        if generation > 1 and renewed_from is None:
            raise ExecutorBlock(f"renewed lease {lease_id} must bind its prior state signature")
        if renewed_from is not None:
            unchanged_renewal = (
                _sha256(renewed_from, f"lease {lease_id} prior state signature")
                == state_signature
            )
        if expires_epoch <= now_epoch:
            expired_lease_ids.append(lease_id)
            continue
        owner_state = item_by_id[owner_id]["state"]
        if owner_state != "RUNNING":
            lease_owner_blockers[owner_id] = "ACTIVE_LEASE_WITHOUT_RUNNING_OWNER"
        elif unchanged_renewal:
            lease_owner_blockers[owner_id] = "LEASE_RENEWAL_WITHOUT_PROGRESS"
        active_leases.append(
            {
                "id": lease_id,
                "owner_id": owner_id,
                "lane": item_by_id[owner_id]["lane"],
                "semantic_paths": sorted(set(conflict_paths) - generated_paths),
                "expires_epoch": expires_epoch,
            }
        )

    def conflicts(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        if left["lane"] in serialized_lanes and right["lane"] in serialized_lanes:
            return True
        return bool(set(left["semantic_paths"]) & set(right["semantic_paths"]))

    dispositions: dict[str, dict[str, Any]] = {}
    eligible: list[dict[str, Any]] = []
    for item in items:
        work_id = item["id"]
        blocker: str | None = None
        if work_id in cycle_nodes:
            blocker = "DEPENDENCY_CYCLE"
        elif work_id in lease_owner_blockers:
            blocker = lease_owner_blockers[work_id]
        elif item["state"] != "READY":
            blocker = {
                "RUNNING": "ALREADY_RUNNING",
                "WAITING": "CALLER_WAITING",
                "BLOCKED": "CALLER_BLOCKED",
                "COMPLETED": "ALREADY_COMPLETED",
            }[item["state"]]
        else:
            incomplete = [
                dependency
                for dependency in item["dependencies"]
                if item_by_id[dependency]["state"] != "COMPLETED"
            ]
            if incomplete:
                blocker = "DEPENDENCY_INCOMPLETE"
            elif item["lane"] in {"MIRROR_PORT", "MIRROR_PROMOTION"}:
                authority_dependencies = [
                    dependency
                    for dependency in item["dependencies"]
                    if item_by_id[dependency]["lane"].startswith("AUTHORITY_")
                    and item_by_id[dependency]["state"] == "COMPLETED"
                ]
                if not authority_dependencies:
                    blocker = "COMPLETED_AUTHORITY_DEPENDENCY_REQUIRED"
        if blocker is None:
            candidate = dict(item)
            candidate["semantic_paths"] = sorted(semantic_paths[work_id])
            conflicting_leases = [
                lease["id"]
                for lease in active_leases
                if lease["owner_id"] != work_id and conflicts(candidate, lease)
            ]
            if conflicting_leases:
                dispositions[work_id] = {
                    "id": work_id,
                    "disposition": "HOLD",
                    "first_blocker": "ACTIVE_CONFLICT_LEASE",
                    "blocking_leases": sorted(conflicting_leases),
                }
            else:
                eligible.append(candidate)
            continue
        dispositions[work_id] = {
            "id": work_id,
            "disposition": "SKIP" if blocker == "ALREADY_COMPLETED" else "HOLD",
            "first_blocker": blocker,
        }

    eligible.sort(
        key=lambda item: (
            item["last_progress_epoch"],
            item["id"],
            lane_positions[item["lane"]],
        )
    )
    selected: list[dict[str, Any]] = []
    for candidate in eligible:
        if len(selected) >= maximum_parallel:
            blocker = "PARALLEL_LIMIT_REACHED"
        elif any(conflicts(candidate, incumbent) for incumbent in selected):
            blocker = "SELECTED_CONFLICT_COMPONENT"
        elif candidate["lane"] not in parallel_lanes and any(
            incumbent["lane"] not in parallel_lanes for incumbent in selected
        ):
            blocker = "SERIALIZED_LANE_SELECTED"
        else:
            blocker = None
        if blocker is not None:
            dispositions[candidate["id"]] = {
                "id": candidate["id"],
                "disposition": "HOLD",
                "first_blocker": blocker,
            }
            continue
        selected.append(candidate)
        dispositions[candidate["id"]] = {
            "id": candidate["id"],
            "disposition": "RUN",
            "first_blocker": None,
        }

    recommended_leases = [
        {
            "id": f"lease:{item['id']}:{now_epoch}",
            "owner_id": item["id"],
            "conflict_paths": item["changed_paths"],
            "acquired_epoch": now_epoch,
            "expires_epoch": now_epoch + lease_duration,
            "generation": 1,
            "state_signature": item["state_signature"],
        }
        for item in selected
    ]
    ordered_dispositions = [dispositions[item["id"]] for item in items]
    return {
        "schema": "qikvrt_work_queue_plan_v1",
        "contract_id": contract["contract_id"],
        "state": "RUNNABLE_COMPONENTS_READY" if selected else "HOLD",
        "observed_epoch": now_epoch,
        "selected_ids": [item["id"] for item in selected],
        "cycle_nodes": sorted(cycle_nodes),
        "active_lease_ids": sorted(lease["id"] for lease in active_leases),
        "expired_lease_ids": sorted(expired_lease_ids),
        "recommended_leases": recommended_leases,
        "dispositions": ordered_dispositions,
    }


def snapshot(
    root: Path = ROOT,
    *,
    revision: str = "HEAD",
    baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    contract = load_contract(root)
    _validate_contract_shape(contract, root)
    head = _sha(_git(root, "rev-parse", "--verify", f"{revision}^{{commit}}"), "exact head")
    tree = _sha(_git(root, "rev-parse", "--verify", f"{revision}^{{tree}}"), "exact tree")
    inventory = _workflow_inventory(root, revision)
    topology = workflow_topology(root, revision, inventory, contract)
    inventory_by_path = {item["path"]: item["blob_sha"] for item in inventory}
    for authorized in _mapping(contract["dispatch_policy"], "dispatch policy")["authorized_workflows"]:
        path = _mapping(authorized, "authorized workflow")["workflow_path"]
        if path not in inventory_by_path:
            raise ExecutorBlock(f"authorized workflow is absent from exact tree: {path}")
    return {
        "schema": "qikvrt_workflow_executor_snapshot_v1",
        "contract_id": contract["contract_id"],
        "contract_path": CONTRACT_RELATIVE_PATH,
        "contract_sha256": _contract_sha256(root),
        "head_sha": head,
        "tree_sha": tree,
        "workflow_inventory": inventory,
        "workflow_inventory_sha256": sha256_bytes(canonical_json_bytes(inventory)),
        "workflow_topology": topology,
        "workflow_topology_sha256": sha256_bytes(canonical_json_bytes(topology)),
        "workflow_delta": workflow_delta(inventory, baseline),
    }


def _runs(value: Mapping[str, Any] | Sequence[Any]) -> list[Mapping[str, Any]]:
    raw: Any = value.get("workflow_runs") if isinstance(value, Mapping) else value
    if not isinstance(raw, list):
        raise ExecutorBlock("workflow run observation must contain workflow_runs")
    return [item for item in raw if isinstance(item, Mapping)]


def dispatch_plan(snapshot_value: Mapping[str, Any], runs_value: Mapping[str, Any] | Sequence[Any], ref: str) -> dict[str, Any]:
    contract = load_contract()
    policy = _mapping(contract["dispatch_policy"], "dispatch policy")
    if ref != policy["dispatch_ref"]:
        raise ExecutorBlock(f"dispatch ref {ref!r} is not the authorised ref {policy['dispatch_ref']!r}")
    head = _sha(snapshot_value.get("head_sha"), "snapshot head")
    tree = _sha(snapshot_value.get("tree_sha"), "snapshot tree")
    inventory = snapshot_value.get("workflow_inventory")
    if not isinstance(inventory, list):
        raise ExecutorBlock("snapshot workflow inventory is missing")
    workflow_blobs = {
        _string(_mapping(item, "snapshot workflow").get("path"), "snapshot workflow path"):
        _sha(_mapping(item, "snapshot workflow").get("blob_sha"), "snapshot workflow blob")
        for item in inventory
    }
    runs = _runs(runs_value)
    writer_names = set(_string_list(policy["writer_workflow_names"], "writer workflow names"))
    active_writers = [
        {
            "id": run.get("id"),
            "name": run.get("name"),
            "status": run.get("status"),
            "head_sha": run.get("head_sha"),
        }
        for run in runs
        if run.get("name") in writer_names and run.get("status") in ACTIVE_RUN_STATUSES
    ]
    candidates: list[dict[str, Any]] = []
    for raw_authorized in policy["authorized_workflows"]:
        authorized = _mapping(raw_authorized, "authorized workflow")
        path = _string(authorized["workflow_path"], "authorized workflow path")
        workflow_name = _string(authorized["workflow_name"], "authorized workflow name")
        candidate = {
            "workflow_id": _string(authorized["workflow_id"], "authorized workflow id"),
            "workflow_path": path,
            "workflow_name": workflow_name,
            "ref": ref,
            "head_sha": head,
            "tree_sha": tree,
            "workflow_blob_sha": workflow_blobs.get(path),
            "external_effect": authorized["external_effect"],
            "required_artifact_prefix": authorized["required_artifact_prefix"],
        }
        if candidate["workflow_blob_sha"] is None:
            candidate.update({"disposition": "HOLD", "first_blocker": "WORKFLOW_ABSENT_FROM_EXACT_TREE"})
        elif active_writers:
            candidate.update({"disposition": "HOLD", "first_blocker": "COMPETING_WRITER_ACTIVE"})
        else:
            equivalent = [
                run
                for run in runs
                if run.get("name") == workflow_name and run.get("head_sha") == head
            ]
            active = [run for run in equivalent if run.get("status") in ACTIVE_RUN_STATUSES]
            if active:
                candidate.update({"disposition": "HOLD", "first_blocker": "EQUIVALENT_EXACT_HEAD_RUN_ACTIVE"})
            elif equivalent:
                trusted = all(
                    run.get("conclusion") not in {"action_required", None} for run in equivalent
                )
                candidate.update(
                    {
                        "disposition": "HOLD",
                        "first_blocker": (
                            "EQUIVALENT_EXACT_HEAD_RUN_REQUIRES_JOB_EVIDENCE"
                            if not trusted
                            else "EQUIVALENT_EXACT_HEAD_RUN_TERMINAL"
                        ),
                    }
                )
            else:
                candidate.update({"disposition": "DISPATCH", "first_blocker": None})
        candidates.append(candidate)
    return {
        "schema": "qikvrt_workflow_executor_plan_v1",
        "contract_id": contract["contract_id"],
        "observed": dict(snapshot_value),
        "active_writers": active_writers,
        "candidates": candidates,
        "state": "DISPATCH_CANDIDATE_READY" if any(item["disposition"] == "DISPATCH" for item in candidates) else "HOLD",
    }


def expected_node_receipt_url(node_repository: str, node_branch: str) -> str:
    _string(node_repository, "node repository")
    _string(node_branch, "node branch")
    contract = load_contract()
    receipt_path = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")["receipt_path"]
    return (
        f"https://raw.githubusercontent.com/{node_repository}/"
        f"{urllib.parse.quote(node_branch, safe='/-._~')}/{receipt_path}"
    )


def validate_node_continuity_declaration(
    document: Mapping[str, Any], node_repository: str, node_branch: str
) -> str:
    contract = load_contract()
    continuity = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")
    value = _mapping(document.get(continuity["registration_request_field"]), "workflow executor continuity declaration")
    if value.get("schema") != continuity["continuity_declaration_schema"]:
        raise ExecutorBlock("workflow executor continuity declaration schema is invalid")
    if value.get("receipt_path") != continuity["receipt_path"]:
        raise ExecutorBlock("workflow executor continuity declaration receipt path is invalid")
    receipt_url = _string(value.get("receipt_url"), "workflow executor continuity receipt url")
    if receipt_url != expected_node_receipt_url(node_repository, node_branch):
        raise ExecutorBlock("workflow executor continuity receipt URL is not bound to the node repository and branch")
    if value.get("acceptance_required") is not True:
        raise ExecutorBlock("workflow executor continuity declaration does not require acceptance")
    return receipt_url


def build_node_receipt(node_repository: str, node_branch: str, root: Path = ROOT) -> dict[str, Any]:
    contract = load_contract(root)
    value = snapshot(root)
    executor = _mapping(contract["executor"], "contract executor")
    continuity = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")
    return {
        "schema": continuity["receipt_schema"],
        "qikvrt_event": "QIKVRT_WORKFLOW_EXECUTOR_MESH_NODE_CONTINUITY",
        "node_repository": node_repository,
        "node_branch": node_branch,
        "authority": {
            "repository": _mapping(contract["authority"], "contract authority")["repository"],
            "entrypoint": "AI",
            "contract_id": contract["contract_id"],
            "contract_sha256": value["contract_sha256"],
            "head_sha": value["head_sha"],
            "tree_sha": value["tree_sha"],
        },
        "executor": {
            "controller_path": executor["controller_path"],
            "workflow_path": executor["workflow_path"],
            "watchdog_workflow_path": executor["watchdog_workflow_path"],
            "monitor_workflow_path": executor["monitor_workflow_path"],
        },
        "acceptance": {
            "required_tests": continuity["required_acceptance_tests"],
            "connection_order": continuity["connection_order"],
            "status": "DECLARED_NOT_EXECUTION_EVIDENCE",
        },
        "external_effect": "NONE",
        "completion_claims": contract["completion_claims"],
    }


def validate_node_receipt(
    receipt: Mapping[str, Any], node_repository: str, node_branch: str, root: Path = ROOT
) -> dict[str, Any]:
    contract = load_contract(root)
    continuity = _mapping(contract["mesh_node_split_acceptance"], "mesh node split acceptance")
    receipt = _mapping(receipt, "node continuity receipt")
    if receipt.get("schema") != continuity["receipt_schema"]:
        raise ExecutorBlock("node continuity receipt schema is invalid")
    if receipt.get("qikvrt_event") != "QIKVRT_WORKFLOW_EXECUTOR_MESH_NODE_CONTINUITY":
        raise ExecutorBlock("node continuity receipt event is invalid")
    if receipt.get("node_repository") != node_repository or receipt.get("node_branch") != node_branch:
        raise ExecutorBlock("node continuity receipt is not bound to the declared node")
    authority = _mapping(receipt.get("authority"), "node receipt authority")
    contract_authority = _mapping(contract["authority"], "contract authority")
    if authority.get("repository") != contract_authority["repository"] or authority.get("entrypoint") != "AI":
        raise ExecutorBlock("node continuity receipt authority binding is invalid")
    if authority.get("contract_id") != contract["contract_id"]:
        raise ExecutorBlock("node continuity receipt contract id is invalid")
    if authority.get("contract_sha256") != _contract_sha256(root):
        raise ExecutorBlock("node continuity receipt does not bind the current authority contract")
    _sha(authority.get("head_sha"), "node receipt authority head")
    _sha(authority.get("tree_sha"), "node receipt authority tree")

    expected_executor = _mapping(contract["executor"], "contract executor")
    executor = _mapping(receipt.get("executor"), "node receipt executor")
    for key in ("controller_path", "workflow_path", "watchdog_workflow_path", "monitor_workflow_path"):
        if executor.get(key) != expected_executor[key]:
            raise ExecutorBlock(f"node continuity receipt executor binding is invalid: {key}")
    acceptance = _mapping(receipt.get("acceptance"), "node receipt acceptance")
    if _string_list(acceptance.get("required_tests"), "node receipt required tests") != continuity["required_acceptance_tests"]:
        raise ExecutorBlock("node continuity receipt acceptance tests are incomplete")
    if _string_list(acceptance.get("connection_order"), "node receipt connection order") != continuity["connection_order"]:
        raise ExecutorBlock("node continuity receipt connection order is incomplete")
    if acceptance.get("status") != "DECLARED_NOT_EXECUTION_EVIDENCE":
        raise ExecutorBlock("node continuity receipt overstates execution evidence")
    if receipt.get("external_effect") != "NONE":
        raise ExecutorBlock("node continuity receipt exceeds the no-effect boundary")
    claims = _mapping(receipt.get("completion_claims"), "node receipt completion claims")
    for key, expected in _mapping(contract["completion_claims"], "contract completion claims").items():
        if claims.get(key) is not expected:
            raise ExecutorBlock(f"node continuity receipt completion claim is invalid: {key}")
    return {
        "schema": "qikvrt_workflow_executor_node_receipt_validation_v1",
        "state": "NODE_SPLIT_CONTINUITY_ACCEPTANCE_READY",
        "node_repository": node_repository,
        "node_branch": node_branch,
        "contract_sha256": _contract_sha256(root),
        "first_blocker": None,
    }


def _read_json_file(path: Path, label: str) -> Mapping[str, Any] | Sequence[Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutorBlock(f"cannot load {label}: {exc}") from exc
    if not isinstance(value, (Mapping, list)):
        raise ExecutorBlock(f"{label} must be an object or a list")
    return value


def _emit(value: Mapping[str, Any], as_json: bool) -> None:
    if as_json:
        print(canonical_json_bytes(value).decode("utf-8"), end="")
        return
    print(
        f"{value.get('state', 'OBSERVATION_READY')} "
        f"head={value.get('head_sha', value.get('node_repository', '-'))} "
        f"tree={value.get('tree_sha', '-')}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("snapshot", "check"):
        command = subcommands.add_parser(name)
        command.add_argument("--baseline", type=Path)
        command.add_argument("--expect-head")
        command.add_argument("--json", action="store_true")
    plan = subcommands.add_parser("plan")
    plan.add_argument("--runs-file", type=Path, required=True)
    plan.add_argument("--baseline", type=Path)
    plan.add_argument("--expect-head", required=True)
    plan.add_argument("--ref", required=True)
    plan.add_argument("--json", action="store_true")
    work = subcommands.add_parser("plan-work")
    work.add_argument("--input", type=Path, required=True)
    work.add_argument("--now-epoch", type=int, required=True)
    work.add_argument("--json", action="store_true")
    template = subcommands.add_parser("node-receipt-template")
    template.add_argument("--node-repository", required=True)
    template.add_argument("--node-branch", required=True)
    template.add_argument("--json", action="store_true")
    receipt = subcommands.add_parser("validate-node-receipt")
    receipt.add_argument("--receipt", type=Path, required=True)
    receipt.add_argument("--node-repository", required=True)
    receipt.add_argument("--node-branch", required=True)
    receipt.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.command in {"snapshot", "check", "plan"}:
            baseline = _read_json_file(arguments.baseline, "baseline") if arguments.baseline else None
            value = snapshot(baseline=baseline if isinstance(baseline, Mapping) else None)
            if arguments.expect_head is not None and value["head_sha"] != arguments.expect_head:
                raise ExecutorBlock("EXACT_HEAD_DRIFT")
            if arguments.command == "plan":
                runs = _read_json_file(arguments.runs_file, "workflow runs")
                value = dispatch_plan(value, runs, arguments.ref)
        elif arguments.command == "plan-work":
            work_input = _read_json_file(arguments.input, "work plan input")
            if not isinstance(work_input, Mapping):
                raise ExecutorBlock("work plan input must be an object")
            value = work_queue_plan(work_input, arguments.now_epoch)
        elif arguments.command == "node-receipt-template":
            value = build_node_receipt(arguments.node_repository, arguments.node_branch)
        else:
            receipt = _read_json_file(arguments.receipt, "node continuity receipt")
            if not isinstance(receipt, Mapping):
                raise ExecutorBlock("node continuity receipt must be an object")
            value = validate_node_receipt(receipt, arguments.node_repository, arguments.node_branch)
        _emit(value, arguments.json)
        return 0
    except ExecutorBlock as exc:
        print(f"BLOCK WORKFLOW_EXECUTOR {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
