#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Evaluate one read-only, exact-head publication-candidate snapshot.

This module deliberately has no network client and no mutation code.  It only
turns a complete observation captured by the companion GitHub Actions workflow
into an artifact receipt.  A receipt is advisory: it cannot ready a pull
request, merge, dispatch, publish, release, deploy, submit, or acknowledge an
external effect.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections.abc import Mapping, Sequence
from typing import Any


SNAPSHOT_SCHEMA = "qikvrt_publication_candidate_readiness_snapshot_v1"
RECEIPT_SCHEMA = "qikvrt_publication_candidate_readiness_receipt_v1"
CONTRACT_SCHEMA = "qikvrt_publication_candidate_readiness_observer_contract_v1"
ACTIVE = frozenset({"queued", "in_progress", "pending", "requested", "waiting"})
ADVERSE = frozenset({"failure", "timed_out", "cancelled", "action_required", "startup_failure"})


class ReadinessBlock(ValueError):
    """A missing or contradictory observation that must fail closed."""


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ReadinessBlock(f"{label} must be an object")
    return value


def _array(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReadinessBlock(f"{label} must be a list")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ReadinessBlock(f"{label} must be a non-empty string")
    return value


def _sha(value: Any, label: str) -> str:
    text = _text(value, label)
    if len(text) != 40 or any(character not in "0123456789abcdef" for character in text):
        raise ReadinessBlock(f"{label} must be a lowercase forty-character Git SHA")
    return text


def _number(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ReadinessBlock(f"{label} must be a positive integer")
    return value


def _strings(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    values = _array(value, label)
    if not allow_empty and not values:
        raise ReadinessBlock(f"{label} must not be empty")
    if any(not isinstance(item, str) or not item for item in values):
        raise ReadinessBlock(f"{label} must contain non-empty strings")
    if len(values) != len(set(values)):
        raise ReadinessBlock(f"{label} must not contain duplicates")
    return list(values)


def _root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def load_contract(path: pathlib.Path | None = None) -> Mapping[str, Any]:
    source = path or _root() / "state/autonomy/PUBLICATION_CANDIDATE_READINESS_OBSERVER_CONTRACT_V1.json"
    contract = _object(json.loads(source.read_text(encoding="utf-8")), "contract")
    if contract.get("schema") != CONTRACT_SCHEMA:
        raise ReadinessBlock("contract schema is not publication-candidate readiness observer v1")
    return contract


def _files(candidate: Mapping[str, Any]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    paths: set[str] = set()
    for index, value in enumerate(_array(candidate.get("changed_files"), "candidate.changed_files")):
        item = _object(value, f"candidate.changed_files[{index}]")
        path = _text(item.get("path"), f"candidate.changed_files[{index}].path")
        if path in paths:
            raise ReadinessBlock("candidate.changed_files paths must be unique")
        paths.add(path)
        entry = {"path": path}
        if item.get("sha") is not None:
            entry["sha"] = _sha(item.get("sha"), f"candidate.changed_files[{index}].sha")
        entries.append(entry)
    if candidate.get("changed_file_count") != len(entries):
        raise ReadinessBlock("candidate.changed_file_count does not match changed_files")
    return sorted(entries, key=lambda item: item["path"])


def _inventory(value: Any, label: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for path, blob in _object(value, label).items():
        result[_text(path, f"{label} path")] = _sha(blob, f"{label}[{path}]")
    return dict(sorted(result.items()))


def _workflow_config(contract: Mapping[str, Any]) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    gates = _object(contract.get("workflow_gates"), "contract.workflow_gates")
    required: dict[str, Mapping[str, Any]] = {}
    conditional: dict[str, Mapping[str, Any]] = {}
    for kind, destination in (("required", required), ("conditionally_not_applicable", conditional)):
        for index, raw in enumerate(_array(gates.get(kind), f"contract.workflow_gates.{kind}")):
            entry = _object(raw, f"contract.workflow_gates.{kind}[{index}]")
            name = _text(entry.get("name"), f"contract.workflow_gates.{kind}[{index}].name")
            _text(entry.get("path"), f"contract.workflow_gates.{kind}[{index}].path")
            if name in required or name in conditional:
                raise ReadinessBlock("workflow gate names must be unique")
            if kind == "conditionally_not_applicable":
                _strings(entry.get("applicable_head_refs"), f"conditional gate {name}.applicable_head_refs", allow_empty=False)
            destination[name] = entry
    return required, conditional


def _job_state(raw: Any) -> tuple[str, str, str]:
    job = _object(raw, "workflow job")
    return _text(job.get("name"), "workflow job name"), _text(job.get("status"), "workflow job status"), _text(job.get("conclusion"), "workflow job conclusion")


def _permitted_skip(job_name: str, prefixes: Sequence[str]) -> bool:
    return any(job_name == prefix or job_name.startswith(prefix + " ") or job_name.startswith(prefix + " (") for prefix in prefixes)


def _success_run(run: Mapping[str, Any], entry: Mapping[str, Any]) -> tuple[str, str, dict[str, int]]:
    jobs = _array(run.get("jobs"), "workflow run jobs")
    summary = {"total": len(jobs), "success": 0, "skipped": 0, "active": 0, "adverse": 0, "untrusted": 0}
    prefixes = _strings(entry.get("permitted_skipped_job_prefixes", []), "permitted skipped job prefixes")
    if run.get("status") in ACTIVE:
        return "ACTIVE", "RUN_NOT_TERMINAL", summary
    if run.get("status") != "completed":
        return "UNTRUSTED", "UNRECOGNIZED_RUN_STATUS", summary
    if run.get("conclusion") in ADVERSE:
        return "FAILED", "ADVERSE_TERMINAL_CONCLUSION", summary
    if run.get("conclusion") != "success":
        return "UNTRUSTED", "TERMINAL_CONCLUSION_NOT_SUCCESS", summary
    if not jobs:
        return "UNTRUSTED", "ZERO_JOB_TERMINAL_RUN", summary
    for raw in jobs:
        name, status, conclusion = _job_state(raw)
        if status in ACTIVE:
            summary["active"] += 1
        elif status != "completed":
            summary["untrusted"] += 1
        elif conclusion == "success":
            summary["success"] += 1
        elif conclusion == "skipped":
            summary["skipped"] += 1
            if not _permitted_skip(name, prefixes):
                summary["untrusted"] += 1
        elif conclusion in ADVERSE:
            summary["adverse"] += 1
        else:
            summary["untrusted"] += 1
    if summary["adverse"]:
        return "FAILED", "ADVERSE_JOB_CONCLUSION", summary
    if summary["active"]:
        return "ACTIVE", "JOB_NOT_TERMINAL", summary
    if summary["untrusted"]:
        return "UNTRUSTED", "UNDECLARED_OR_UNTRUSTED_JOB_STATE", summary
    if not summary["success"]:
        return "UNTRUSTED", "NO_EXECUTED_SUCCESS_JOB", summary
    return "SUCCESS", "TERMINAL_SUCCESS_WITH_EXECUTED_JOB_EVIDENCE", summary


def _skipped_run(run: Mapping[str, Any], applicable: bool) -> tuple[str, str, dict[str, int]]:
    jobs = _array(run.get("jobs"), "workflow run jobs")
    summary = {"total": len(jobs), "success": 0, "skipped": 0, "active": 0, "adverse": 0, "untrusted": 0}
    for raw in jobs:
        _, status, conclusion = _job_state(raw)
        if status in ACTIVE:
            summary["active"] += 1
        elif status != "completed":
            summary["untrusted"] += 1
        elif conclusion == "skipped":
            summary["skipped"] += 1
        elif conclusion in ADVERSE:
            summary["adverse"] += 1
        else:
            summary["untrusted"] += 1
    if applicable:
        return "UNTRUSTED", "SKIPPED_WHILE_APPLICABLE", summary
    if not jobs or summary["skipped"] != len(jobs):
        return "UNTRUSTED", "SKIPPED_RUN_LACKS_ALL_SKIPPED_JOB_EVIDENCE", summary
    return "NOT_APPLICABLE", "DECLARED_HEAD_REF_GATE", summary


def _latest_runs(raw_runs: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    selected: dict[str, Mapping[str, Any]] = {}
    for run in raw_runs:
        name = _text(run.get("name"), "workflow run name")
        number = run.get("run_number")
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            raise ReadinessBlock(f"workflow run {name} lacks a valid run_number")
        run_id = run.get("id")
        if not isinstance(run_id, (int, str)) or isinstance(run_id, bool) or not str(run_id):
            raise ReadinessBlock(f"workflow run {name} lacks an id")
        old = selected.get(name)
        if old is None or (number, str(run_id)) > (old["run_number"], str(old["id"])):
            selected[name] = run
    return selected


def _workflow_observation(snapshot: Mapping[str, Any], candidate: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    required, conditional = _workflow_config(contract)
    declared = {**required, **conditional}
    head = _sha(candidate.get("head_sha"), "candidate.head_sha")
    head_ref = _text(candidate.get("head_ref"), "candidate.head_ref")
    observer_name = "QIKVRT publication candidate readiness observer"
    raw_runs = [_object(value, "workflow run") for value in _array(snapshot.get("workflow_runs"), "workflow_runs")]
    stale = [run for run in raw_runs if run.get("head_sha") != head]
    exact = [run for run in raw_runs if run.get("head_sha") == head and run.get("name") != observer_name]
    selected = _latest_runs(exact)
    gates: list[dict[str, Any]] = []
    blockers: list[str] = []
    for name, run in sorted(selected.items()):
        if run.get("event") != "pull_request" or run.get("head_branch") != head_ref:
            gates.append({"name": name, "run_id": run.get("id"), "state": "UNTRUSTED", "reason": "EXACT_HEAD_EVENT_OR_BRANCH_MISMATCH"})
            blockers.append("EXACT_HEAD_WORKFLOW_UNTRUSTED")
            continue
        entry = declared.get(name)
        if entry is None:
            gates.append({"name": name, "run_id": run.get("id"), "state": "UNTRUSTED", "reason": "UNDECLARED_EXACT_HEAD_WORKFLOW"})
            blockers.append("UNDECLARED_EXACT_HEAD_WORKFLOW")
            continue
        if name in conditional and run.get("conclusion") == "skipped":
            state, reason, jobs = _skipped_run(run, head_ref in entry["applicable_head_refs"])
        else:
            state, reason, jobs = _success_run(run, entry)
            if name in conditional and head_ref not in entry["applicable_head_refs"]:
                state, reason = "UNTRUSTED", "EXECUTED_OUTSIDE_DECLARED_HEAD_REF_SCOPE"
        gates.append({"name": name, "run_id": run.get("id"), "run_number": run.get("run_number"), "state": state, "reason": reason, "jobs": jobs})
    present = {gate["name"] for gate in gates}
    for name in sorted(required):
        gate = next((item for item in gates if item["name"] == name), None)
        if gate is None:
            gates.append({"name": name, "state": "MISSING", "reason": "REQUIRED_EXACT_HEAD_WORKFLOW_MISSING"})
            blockers.append("REQUIRED_EXACT_HEAD_GATE_MISSING")
        elif gate["state"] != "SUCCESS":
            blockers.append("REQUIRED_EXACT_HEAD_GATE_NOT_TRUSTED")
    for name, entry in sorted(conditional.items()):
        if name not in present:
            if head_ref in entry["applicable_head_refs"]:
                gates.append({"name": name, "state": "MISSING", "reason": "CONDITIONAL_WORKFLOW_MISSING_WHILE_APPLICABLE"})
                blockers.append("CONDITIONAL_EXACT_HEAD_GATE_MISSING")
            else:
                gates.append({"name": name, "state": "NOT_APPLICABLE", "reason": "DECLARED_HEAD_REF_GATE_NO_RUN"})
    for gate in gates:
        if gate["state"] == "FAILED":
            blockers.append("APPLICABLE_EXACT_HEAD_EXECUTED_FAILURE")
        elif gate["state"] in {"ACTIVE", "UNTRUSTED"}:
            blockers.append("EXACT_HEAD_WORKFLOW_UNTRUSTED")
    return {
        "gates": sorted(gates, key=lambda item: item["name"]),
        "stale_runs_discarded": len(stale),
        "exact_head_run_count": len(exact),
    }, blockers


def _workflow_blobs(snapshot: Mapping[str, Any], contract: Mapping[str, Any]) -> tuple[dict[str, Any], str | None]:
    inventories = _object(snapshot.get("workflow_inventories"), "workflow_inventories")
    base = _inventory(inventories.get("base"), "workflow_inventories.base")
    head = _inventory(inventories.get("head"), "workflow_inventories.head")
    required, conditional = _workflow_config(contract)
    relevant = sorted({entry["path"] for entry in {**required, **conditional}.values()})
    missing = [path for path in relevant if path not in base or path not in head]
    changed = [path for path in relevant if path in base and path in head and base[path] != head[path]]
    return {
        "base_workflow_inventory_sha256": digest(base),
        "head_workflow_inventory_sha256": digest(head),
        "relevant_paths": relevant,
        "missing_paths": missing,
        "changed_paths": changed,
    }, "WORKFLOW_BLOB_DRIFT" if missing or changed else None


def _supersession(files: Sequence[Mapping[str, str]], value: Any) -> tuple[dict[str, Any], str | None]:
    if value is None:
        return {"state": "NOT_DECLARED"}, None
    predecessor = _object(value, "declared_predecessor")
    number = _number(predecessor.get("number"), "declared_predecessor.number")
    declared = _sha(predecessor.get("declared_head_sha"), "declared_predecessor.declared_head_sha")
    observed = _sha(predecessor.get("observed_head_sha"), "declared_predecessor.observed_head_sha")
    if declared != observed:
        return {"state": "PREDECESSOR_HEAD_DRIFT", "number": number, "declared_head_sha": declared, "observed_head_sha": observed}, "PREDECESSOR_HEAD_DRIFT"
    paths = _strings(predecessor.get("changed_paths"), "declared_predecessor.changed_paths")
    candidate_paths = {item["path"] for item in files}
    missing = sorted(set(paths) - candidate_paths)
    if missing:
        return {"state": "PREDECESSOR_SCOPE_GAP", "number": number, "missing_paths": missing}, "PREDECESSOR_SCOPE_NOT_COVERED"
    state = _text(predecessor.get("state"), "declared_predecessor.state")
    if state not in {"open", "closed"}:
        raise ReadinessBlock("declared_predecessor.state must be open or closed")
    return {
        "state": "CURRENT_MAIN_SUCCESSOR_SCOPE_COVERED",
        "number": number,
        "predecessor_state": state,
        "covered_path_count": len(paths),
        "lifecycle_followup": "PREDECESSOR_STILL_OPEN" if state == "open" else "NONE",
    }, None


def _external(snapshot: Mapping[str, Any], contract: Mapping[str, Any]) -> dict[str, Any]:
    inputs = _object(snapshot.get("external_inputs", {}), "external_inputs")
    result: dict[str, Any] = {}
    for raw in _array(contract.get("external_boundaries"), "contract.external_boundaries"):
        boundary = _object(raw, "external boundary")
        target = _text(boundary.get("target"), "external boundary target")
        source_path = _text(boundary.get("source_path"), "external boundary source path")
        input_value = inputs.get(target)
        if input_value is None:
            result[target] = {"state": "NOT_OBSERVED", "source_path": source_path, "effect_evidence": "NOT_OBSERVED_BY_READ_ONLY_OBSERVER"}
            continue
        observed = _object(input_value, f"external_inputs.{target}")
        if observed.get("present") is not True:
            result[target] = {"state": "NOT_OBSERVED", "source_path": source_path, "effect_evidence": "NOT_OBSERVED_BY_READ_ONLY_OBSERVER"}
            continue
        result[target] = {
            "state": boundary.get("default_state", "NOT_AUTHORIZED"),
            "source_path": source_path,
            "source_blob_sha": _sha(observed.get("blob_sha"), f"external_inputs.{target}.blob_sha"),
            "source_sha256": _text(observed.get("sha256"), f"external_inputs.{target}.sha256"),
            "effect_evidence": "NOT_OBSERVED_BY_READ_ONLY_OBSERVER",
        }
    return result


def _reviews(snapshot: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    reviews = [_object(item, "review") for item in _array(snapshot.get("reviews"), "reviews")]
    states = [item.get("state") for item in reviews if isinstance(item.get("state"), str)]
    return {
        "draft": candidate.get("draft"),
        "submitted_review_count": len(reviews),
        "approved_count": sum(state == "APPROVED" for state in states),
        "changes_requested_count": sum(state == "CHANGES_REQUESTED" for state in states),
        "review_comment_count": snapshot.get("review_comment_count", 0),
    }


def _next_action(blocker: str | None) -> str:
    actions = {
        "BASE_DRIFT": "REOBSERVE_CURRENT_MAIN_AND_REBIND_THE_CANDIDATE",
        "HEAD_DRIFT": "DISCARD_STALE_GATE_EVIDENCE_AND_REOBSERVE_THE_NEW_HEAD",
        "TREE_DRIFT": "DISCARD_STALE_GATE_EVIDENCE_AND_REOBSERVE_THE_NEW_TREE",
        "SCOPE_DRIFT": "REOBSERVE_CHANGED_PATHS_AND_RECOMPUTE_THE_SCOPE_DIGEST",
        "WORKFLOW_BLOB_DRIFT": "REOBSERVE_THE_DECLARED_WORKFLOW_BLOBS_ON_THE_EXACT_HEAD",
        "CONTRACT_BLOB_DRIFT": "REOBSERVE_THE_READINESS_CONTRACT_ON_THE_EXACT_HEAD",
        "NOT_MERGEABLE": "RESOLVE_THE_CANDIDATE_MERGEABILITY_BEFORE_REOBSERVATION",
        "COMPETING_WRITER_OVERLAP": "SERIALIZE_OR_REBASE_ONE_CURRENT_BASE_WRITER_BEFORE_PROMOTION",
        "DRAFT_REVIEW_PENDING": "KEEP_DRAFT_AND_COMPLETE_REVIEW_REOBSERVATION_BEFORE_ANY_PROMOTION_DECISION",
        "PREDECESSOR_HEAD_DRIFT": "REOBSERVE_THE_DECLARED_PREDECESSOR_AND_RECONSTRUCT_SCOPE_COVERAGE",
        "PREDECESSOR_SCOPE_NOT_COVERED": "CREATE_OR_REPAIR_A_SINGLE_CURRENT_MAIN_SUCCESSOR_SCOPE",
    }
    return actions.get(blocker, "REOBSERVE_AND_RESOLVE_THE_FIRST_DETERMINISTIC_BLOCKER") if blocker else "REOBSERVE_BASE_HEAD_TREE_SCOPE_WORKFLOWS_AND_WRITERS_IMMEDIATELY_BEFORE_ANY_SEPARATELY_AUTHORIZED_PROMOTION"


def evaluate(snapshot: Mapping[str, Any], contract: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        raise ReadinessBlock("snapshot schema is not publication-candidate readiness v1")
    contract = contract or load_contract()
    candidate = _object(snapshot.get("candidate"), "candidate")
    authority = _object(snapshot.get("authority"), "authority")
    reobserved = _object(snapshot.get("reobservation"), "reobservation")
    if candidate.get("state") != "open" or candidate.get("base_ref") != "main":
        raise ReadinessBlock("candidate must be an open pull request against main")
    if not isinstance(candidate.get("draft"), bool) or not isinstance(candidate.get("mergeable"), bool):
        raise ReadinessBlock("candidate.draft and candidate.mergeable must be booleans")
    files = _files(candidate)
    scope = {"changed_file_count": len(files), "scope_sha256": digest(files), "paths": [item["path"] for item in files]}
    workflow_blobs, workflow_blob_blocker = _workflow_blobs(snapshot, contract)
    workflows, workflow_blockers = _workflow_observation(snapshot, candidate, contract)
    supersession, supersession_blocker = _supersession(files, snapshot.get("declared_predecessor"))
    overlaps: list[dict[str, Any]] = []
    for raw in _array(snapshot.get("competing_writers", []), "competing_writers"):
        writer = _object(raw, "competing writer")
        paths = sorted(_strings(writer.get("overlap_paths"), "competing writer overlap_paths", allow_empty=False))
        overlaps.append({"number": _number(writer.get("number"), "competing writer number"), "overlap_paths": paths})
    overlaps.sort(key=lambda item: item["number"])
    binding = {
        "authority_main_head_sha": _sha(authority.get("main_head_sha"), "authority.main_head_sha"),
        "authority_main_tree_sha": _sha(authority.get("main_tree_sha"), "authority.main_tree_sha"),
        "candidate_base_sha": _sha(candidate.get("base_sha"), "candidate.base_sha"),
        "candidate_head_sha": _sha(candidate.get("head_sha"), "candidate.head_sha"),
        "candidate_head_tree_sha": _sha(candidate.get("head_tree_sha"), "candidate.head_tree_sha"),
        "scope_sha256": scope["scope_sha256"],
        "workflow_blob_inventory_sha256": workflow_blobs["head_workflow_inventory_sha256"],
        "contract_blob_sha": _sha(snapshot.get("contract_blob_sha"), "contract_blob_sha"),
        "reobserved_main_head_sha": _sha(reobserved.get("main_head_sha"), "reobservation.main_head_sha"),
        "reobserved_candidate_base_sha": _sha(reobserved.get("base_sha"), "reobservation.base_sha"),
        "reobserved_candidate_head_sha": _sha(reobserved.get("head_sha"), "reobservation.head_sha"),
        "reobserved_candidate_head_tree_sha": _sha(reobserved.get("head_tree_sha"), "reobservation.head_tree_sha"),
        "reobserved_scope_sha256": _text(reobserved.get("scope_sha256"), "reobservation.scope_sha256"),
        "reobserved_workflow_blob_inventory_sha256": _text(reobserved.get("workflow_blob_inventory_sha256"), "reobservation.workflow_blob_inventory_sha256"),
        "reobserved_contract_blob_sha": _sha(reobserved.get("contract_blob_sha"), "reobservation.contract_blob_sha"),
    }
    blocker: str | None = None
    if binding["authority_main_head_sha"] != binding["candidate_base_sha"] or binding["reobserved_main_head_sha"] != binding["authority_main_head_sha"] or binding["reobserved_candidate_base_sha"] != binding["candidate_base_sha"]:
        blocker = "BASE_DRIFT"
    elif binding["reobserved_candidate_head_sha"] != binding["candidate_head_sha"]:
        blocker = "HEAD_DRIFT"
    elif binding["reobserved_candidate_head_tree_sha"] != binding["candidate_head_tree_sha"]:
        blocker = "TREE_DRIFT"
    elif binding["reobserved_scope_sha256"] != binding["scope_sha256"]:
        blocker = "SCOPE_DRIFT"
    elif binding["reobserved_workflow_blob_inventory_sha256"] != binding["workflow_blob_inventory_sha256"] or workflow_blob_blocker:
        blocker = "WORKFLOW_BLOB_DRIFT"
    elif binding["reobserved_contract_blob_sha"] != binding["contract_blob_sha"]:
        blocker = "CONTRACT_BLOB_DRIFT"
    elif candidate.get("mergeable") is not True:
        blocker = "NOT_MERGEABLE"
    elif overlaps:
        blocker = "COMPETING_WRITER_OVERLAP"
    elif supersession_blocker:
        blocker = supersession_blocker
    elif workflow_blockers:
        blocker = workflow_blockers[0]
    elif candidate.get("draft"):
        blocker = "DRAFT_REVIEW_PENDING"
    state = "HOLD" if blocker else "PROMOTE_REPOSITORY_CANDIDATE"
    return {
        "schema": RECEIPT_SCHEMA,
        "repository": _text(snapshot.get("repository"), "repository"),
        "pr_number": _number(candidate.get("number"), "candidate.number"),
        "state": state,
        "first_blocker": blocker,
        "smallest_safe_next_action": _next_action(blocker),
        "binding": binding,
        "scope": scope,
        "workflow_blobs": workflow_blobs,
        "workflows": workflows,
        "review": _reviews(snapshot, candidate),
        "competing_writers": overlaps,
        "supersession": supersession,
        "repository_readiness": state,
        "external_boundaries": _external(snapshot, contract),
        "completion_claims": {
            "PASS": False,
            "FINAL_PASS": False,
            "EFFECT_ACK_DONE": False,
            "EXTERNAL_EFFECT": False,
            "ZENODO_EFFECT": False,
            "ARXIV_EFFECT": False,
            "IETF_EFFECT": False,
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("evaluate",))
    parser.add_argument("--input", default="-", help="snapshot JSON file, or - for stdin")
    parser.add_argument("--contract", type=pathlib.Path, help="explicit observer contract")
    args = parser.parse_args(argv)
    try:
        raw = json.load(sys.stdin) if args.input == "-" else json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
        result = evaluate(_object(raw, "snapshot"), load_contract(args.contract))
    except (OSError, UnicodeError, json.JSONDecodeError, ReadinessBlock) as exc:
        result = {
            "schema": RECEIPT_SCHEMA,
            "state": "HOLD",
            "first_blocker": "INVALID_PUBLICATION_CANDIDATE_READINESS_SNAPSHOT",
            "smallest_safe_next_action": "RECONSTRUCT_A_COMPLETE_EXACT_HEAD_READ_ONLY_SNAPSHOT",
            "detail": str(exc),
            "completion_claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False, "EXTERNAL_EFFECT": False},
        }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
