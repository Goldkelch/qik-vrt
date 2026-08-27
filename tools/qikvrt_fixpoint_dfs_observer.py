# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Head/tree-bound positional DFS observer for QIK-VRT fixpoints."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "state/fixpoints/QIKVRT_HARDWARE_MACHINE_LANGUAGE_FIXPOINT_V1.json"
SHA = re.compile(r"^[0-9a-f]{40}$")
ADVERSE = {"action_required", "cancelled", "failure", "startup_failure", "stale", "timed_out"}
ACTIVE = {"queued", "in_progress", "waiting", "requested", "pending"}


class ContractError(ValueError):
    pass


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def require_sha(name: str, value: Any) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ContractError(f"{name} must be a full lowercase SHA")
    return value


def load_contract(path: pathlib.Path = CONTRACT) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_contract(value: dict[str, Any]) -> list[str]:
    expected = {
        "schema": "qikvrt.hardware-machine-language-fixpoint.v1",
        "scope_literal": "./Goldkelch/qik-vrt/*",
        "operator_literal": "*=<>.",
        "proof_terminator_literal": "q.e.d.",
        "signatory_literal": "Ingolf Lohmann",
    }
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise ContractError(f"{key} drift")
    positions = value.get("positions")
    if not isinstance(positions, list) or len(positions) != 2:
        raise ContractError("exactly two positions required")
    hardware, machine = positions
    if hardware.get("index") != 0 or hardware.get("id") != "hardware":
        raise ContractError("hardware position drift")
    if hardware.get("parent") is not None or hardware.get("children") != ["machine_language"]:
        raise ContractError("hardware tree drift")
    if hardware.get("completion_criterion_literal") != "DoD":
        raise ContractError("hardware DoD drift")
    if hardware.get("opening_operator_literal") != "*=<>." or hardware.get("closing_operator_literal") != "*=<>.":
        raise ContractError("hardware operator drift")
    if machine.get("index") != 1 or machine.get("id") != "machine_language":
        raise ContractError("machine-language position drift")
    if machine.get("parent") != "hardware" or machine.get("children") != []:
        raise ContractError("machine-language tree drift")
    if machine.get("runs_on_position") != "hardware":
        raise ContractError("machine-language carrier drift")
    for position in positions:
        text = position.get("exact_text_lf")
        if not isinstance(text, str) or not text.endswith("\n") or "\r" in text:
            raise ContractError("position bytes must be LF-terminated UTF-8 text")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != position.get("sha256"):
            raise ContractError(f"position digest drift: {position.get('id')}")
    observation = value.get("observation") or {}
    required_observation = {
        "traversal": "DEPTH_FIRST_PREORDER",
        "event_delivery": "PRIMARY",
        "blind_retry": False,
        "polling_loop": False,
        "silent_truncation": False,
        "exact_head_required": True,
        "exact_tree_required": True,
    }
    for key, wanted in required_observation.items():
        if observation.get(key) != wanted:
            raise ContractError(f"observation drift: {key}")
    boundaries = value.get("claim_boundaries") or {}
    if not boundaries or any(item is not False for item in boundaries.values()):
        raise ContractError("broadened claim boundary enabled")
    return ["hardware", "machine_language"]


def normalize_snapshot(snapshot: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    limits = contract["observation"]
    runs = snapshot.get("workflow_runs")
    if not isinstance(runs, list) or len(runs) > limits["maximum_workflow_runs"]:
        raise ContractError("workflow inventory invalid")
    normalized_runs = []
    for run in runs:
        jobs = run.get("jobs") or []
        if len(jobs) > limits["maximum_jobs_per_run"]:
            raise ContractError("job inventory exceeds bound")
        normalized_jobs = []
        for job in jobs:
            steps = job.get("steps") or []
            if len(steps) > limits["maximum_steps_per_job"]:
                raise ContractError("step inventory exceeds bound")
            normalized_jobs.append({
                "id": int(job["id"]),
                "name": str(job.get("name") or ""),
                "status": str(job.get("status") or ""),
                "conclusion": job.get("conclusion"),
                "steps": sorted([
                    {
                        "number": int(step.get("number") or 0),
                        "name": str(step.get("name") or ""),
                        "status": str(step.get("status") or ""),
                        "conclusion": step.get("conclusion"),
                    }
                    for step in steps
                ], key=lambda item: (item["number"], item["name"])),
            })
        reported = int(run.get("jobs_total_reported", len(normalized_jobs)))
        if reported != len(normalized_jobs):
            raise ContractError(f"incomplete job inventory for run {run.get('id')}")
        normalized_runs.append({
            "id": int(run["id"]),
            "name": str(run.get("name") or ""),
            "event": str(run.get("event") or ""),
            "status": str(run.get("status") or ""),
            "conclusion": run.get("conclusion"),
            "created_at": str(run.get("created_at") or ""),
            "jobs": sorted(normalized_jobs, key=lambda item: (item["id"], item["name"])),
        })
    repo = str(snapshot.get("repository") or "")
    pr = snapshot.get("pull_request")
    if "/" not in repo or not isinstance(pr, int) or isinstance(pr, bool) or pr <= 0:
        raise ContractError("invalid exact subject")
    return {
        "repository": repo,
        "pull_request": pr,
        "head_ref": str(snapshot.get("head_ref") or ""),
        "base_sha": require_sha("base_sha", snapshot.get("base_sha")),
        "head_sha_before": require_sha("head_sha_before", snapshot.get("head_sha_before")),
        "tree_sha_before": require_sha("tree_sha_before", snapshot.get("tree_sha_before")),
        "head_sha_after": require_sha("head_sha_after", snapshot.get("head_sha_after")),
        "tree_sha_after": require_sha("tree_sha_after", snapshot.get("tree_sha_after")),
        "captured_at": str(snapshot.get("captured_at") or ""),
        "workflow_runs": sorted(normalized_runs, key=lambda item: (item["created_at"], item["id"], item["name"])),
    }


def nodes(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for run in snapshot["workflow_runs"]:
        result.append({key: run[key] for key in ("id", "name", "event", "status", "conclusion", "created_at")} | {"kind": "workflow"})
        for job in run["jobs"]:
            result.append({
                "kind": "job", "id": job["id"], "parent_run": run["id"],
                "name": job["name"], "status": job["status"], "conclusion": job["conclusion"],
            })
            for step in job["steps"]:
                result.append({
                    "kind": "step", "number": step["number"], "parent_job": job["id"],
                    "parent_run": run["id"], "name": step["name"],
                    "status": step["status"], "conclusion": step["conclusion"],
                })
    return result


def first_adverse(snapshot: dict[str, Any]) -> dict[str, Any] | None:
    for run in snapshot["workflow_runs"]:
        for job in run["jobs"]:
            for step in job["steps"]:
                if step.get("conclusion") in ADVERSE:
                    return {
                        "kind": "step", "number": step["number"], "parent_job": job["id"],
                        "parent_run": run["id"], "name": step["name"],
                        "status": step["status"], "conclusion": step["conclusion"],
                    }
            if job.get("conclusion") in ADVERSE:
                return {
                    "kind": "job", "id": job["id"], "parent_run": run["id"],
                    "name": job["name"], "status": job["status"], "conclusion": job["conclusion"],
                }
        if run.get("conclusion") in ADVERSE:
            return {
                "kind": "workflow", "id": run["id"], "name": run["name"],
                "status": run["status"], "conclusion": run["conclusion"],
            }
    return None


def build_receipt(snapshot: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    order = validate_contract(contract)
    value = normalize_snapshot(snapshot, contract)
    drift = value["head_sha_before"] != value["head_sha_after"] or value["tree_sha_before"] != value["tree_sha_after"]
    adverse = first_adverse(value)
    flat = nodes(value)
    active = any(node.get("status") in ACTIVE for node in flat)
    if drift:
        state, reason = "REOBSERVE", "EXACT_BINDING_DRIFT_DURING_DEPTH_FIRST_OBSERVATION"
    elif adverse:
        state, reason = "HOLD", "FIRST_CAUSAL_ADVERSE_EXECUTION_NODE"
    elif active:
        state, reason = "CONTINUE", "ACTIVE_EXECUTION_REMAINS"
    else:
        state, reason = "OBSERVE", "LOCAL_EXACT_HEAD_EXECUTION_FIXPOINT_REACHED"
    receipt = {
        "schema": "qikvrt.fixpoint-positional-dfs-receipt.v1",
        "state": state,
        "reason": reason,
        "binding": {key: value[key] for key in (
            "repository", "pull_request", "head_ref", "base_sha",
            "head_sha_before", "tree_sha_before", "head_sha_after", "tree_sha_after"
        )} | {"binding_drift": drift},
        "positions": {
            "traversal": "DEPTH_FIRST_PREORDER",
            "order": order,
            "hardware_sha256": contract["positions"][0]["sha256"],
            "machine_language_sha256": contract["positions"][1]["sha256"],
        },
        "execution": {
            "workflow_run_count": len(value["workflow_runs"]),
            "node_count": len(flat),
            "depth_first_nodes": [
                {"ordinal": index, "binding_sha256": digest(node), **node}
                for index, node in enumerate(flat)
            ],
            "active": active,
            "first_adverse": adverse,
            "captured_at": value["captured_at"],
        },
        "claims": dict(contract["claim_boundaries"]),
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def render_markdown(receipt: dict[str, Any]) -> str:
    binding, execution = receipt["binding"], receipt["execution"]
    lines = [
        "<!-- qikvrt-fixpoint-positional-dfs-observation -->",
        "## Positional fixpoint depth-first observation", "",
        f"- state: `{receipt['state']}`",
        f"- reason: `{receipt['reason']}`",
        f"- exact head before: `{binding['head_sha_before']}`",
        f"- exact tree before: `{binding['tree_sha_before']}`",
        f"- exact head after: `{binding['head_sha_after']}`",
        f"- exact tree after: `{binding['tree_sha_after']}`",
        f"- binding drift: `{'true' if binding['binding_drift'] else 'false'}`",
        "- position order: `hardware → machine_language`",
        f"- workflow runs observed: `{execution['workflow_run_count']}`",
        f"- execution nodes observed depth-first: `{execution['node_count']}`",
        f"- receipt SHA-256: `{receipt['receipt_sha256']}`",
    ]
    if execution["first_adverse"]:
        adverse = execution["first_adverse"]
        lines += ["", "### First causal adverse node", "",
                  f"- kind: `{adverse['kind']}`", f"- name: `{adverse['name']}`",
                  f"- status: `{adverse['status']}`", f"- conclusion: `{adverse['conclusion']}`"]
    lines += ["", "`PASS=false` · `FINAL_PASS=false` · `EFFECT_ACK_DONE=false` · `AUTHORITY_MAIN_EFFECT=false`", "",
              "Exact-head repository observation only; no merge, publication, deployment, physical hardware execution, astrophysical simulation, or quantum-state simulation is asserted."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=pathlib.Path, default=CONTRACT)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    observe = sub.add_parser("observe")
    observe.add_argument("--input", type=pathlib.Path, required=True)
    observe.add_argument("--output", type=pathlib.Path, required=True)
    observe.add_argument("--markdown-output", type=pathlib.Path)
    args = parser.parse_args(argv)
    contract = load_contract(args.contract)
    if args.command == "validate":
        print(json.dumps({"position_order": validate_contract(contract)}, sort_keys=True))
        return 0
    receipt = build_receipt(json.loads(args.input.read_text(encoding="utf-8")), contract)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.markdown_output:
        args.markdown_output.write_text(render_markdown(receipt), encoding="utf-8")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
