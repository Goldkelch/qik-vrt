#!/usr/bin/env python3
"""Deterministic, resumable work-unit planner for repository-native issue processing.

The planner deliberately separates deterministic progress from semantic/model work.
It never upgrades a scientific claim and never emits DONE unless every mandatory unit
is complete. State is persisted as canonical JSON under evidence/issues/<n>/work-units.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "qikvrt_issue_work_units_v1"
STATUSES = {"PENDING", "READY", "RUNNING", "PARTIAL", "BLOCK", "DONE"}
UNITS = (
    ("ZENODO_RECORD_DISCOVERY", (), "deterministic"),
    ("ARTIFACT_FILE_INVENTORY", ("ZENODO_RECORD_DISCOVERY",), "deterministic"),
    ("SOURCE_HASH_BINDING", ("ARTIFACT_FILE_INVENTORY",), "deterministic"),
    ("CLAIM_EXTRACTION_QUEUE", ("SOURCE_HASH_BINDING",), "semantic"),
    ("CLAIM_CLASSIFICATION", ("CLAIM_EXTRACTION_QUEUE",), "semantic"),
    ("CLAIM_DEPENDENCY_GRAPH", ("CLAIM_CLASSIFICATION",), "semantic"),
    ("FORMALIZATION_CANDIDATE_QUEUE", ("CLAIM_DEPENDENCY_GRAPH",), "semantic"),
    ("LEAN_MODULE_GENERATION", ("FORMALIZATION_CANDIDATE_QUEUE",), "semantic"),
    ("LEAN_KERNEL_EXECUTION", ("LEAN_MODULE_GENERATION",), "deterministic"),
    ("NEGATIVE_TEST_EXECUTION", ("LEAN_KERNEL_EXECUTION",), "deterministic"),
    ("COVERAGE_AND_TRACEABILITY", ("NEGATIVE_TEST_EXECUTION",), "deterministic"),
    ("AUTHORITY_MIRROR_SYNC", ("COVERAGE_AND_TRACEABILITY",), "external"),
    ("ZENODO_PUBLICATION_ASSESSMENT", ("COVERAGE_AND_TRACEABILITY",), "deterministic"),
    ("FINAL_COMPLETION_GATE", ("AUTHORITY_MIRROR_SYNC", "ZENODO_PUBLICATION_ASSESSMENT"), "deterministic"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_head(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class PlannerConfig:
    root: Path
    issue: int
    model_available: bool
    execute: bool

    @property
    def evidence_dir(self) -> Path:
        return self.root / "evidence" / "issues" / str(self.issue)

    @property
    def work_dir(self) -> Path:
        return self.evidence_dir / "work-units"


def default_state(config: PlannerConfig) -> dict[str, Any]:
    head = git_head(config.root)
    units: list[dict[str, Any]] = []
    for index, (unit_id, prerequisites, kind) in enumerate(UNITS, start=1):
        units.append({
            "id": f"WU-{config.issue}-{index:02d}-{unit_id}",
            "name": unit_id,
            "kind": kind,
            "prerequisites": list(prerequisites),
            "status": "PENDING",
            "attempts": 0,
            "input_hashes": {},
            "repository_head": head,
            "last_progress_at": None,
            "next_cursor": None,
            "produced_files": [],
            "blocker": None,
            "next_action": "evaluate prerequisites",
        })
    return {
        "schema": SCHEMA,
        "issue": config.issue,
        "repository_head": head,
        "generated_at": utc_now(),
        "aggregate_status": "EFFECT_ACK_CONTINUE",
        "next_cursor": units[0]["name"],
        "units": units,
    }


def load_state(config: PlannerConfig) -> dict[str, Any]:
    path = config.work_dir / "STATE.json"
    if not path.exists():
        return default_state(config)
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != SCHEMA or state.get("issue") != config.issue:
        raise ValueError("incompatible work-unit state")
    return state


def unit_map(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {unit["name"]: unit for unit in state["units"]}


def prerequisites_done(unit: dict[str, Any], units: dict[str, dict[str, Any]]) -> bool:
    return all(units[name]["status"] == "DONE" for name in unit["prerequisites"])


def discover_zenodo_records(config: PlannerConfig) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(config.root.rglob("*")):
        if not path.is_file() or ".git" in path.parts:
            continue
        name = path.name.lower()
        if "zenodo" not in str(path).lower() and "doi" not in name:
            continue
        records.append({"path": path.relative_to(config.root).as_posix(), "sha256": hash_file(path), "bytes": path.stat().st_size})
    return records


def execute_deterministic(unit: dict[str, Any], config: PlannerConfig) -> tuple[str, list[dict[str, Any]], str | None, str]:
    produced: list[dict[str, Any]] = []
    blocker: str | None = None
    next_action = "advance to next unit"
    out = config.work_dir / "artifacts"
    out.mkdir(parents=True, exist_ok=True)

    if unit["name"] == "ZENODO_RECORD_DISCOVERY":
        payload = {"schema": "qikvrt_zenodo_record_inventory_v1", "issue": config.issue, "records": discover_zenodo_records(config)}
        target = out / "zenodo-records.json"
        target.write_bytes(canonical_bytes(payload))
    elif unit["name"] == "ARTIFACT_FILE_INVENTORY":
        files = []
        for path in sorted(config.root.rglob("*")):
            if path.is_file() and ".git" not in path.parts and config.work_dir not in path.parents:
                files.append({"path": path.relative_to(config.root).as_posix(), "bytes": path.stat().st_size})
        target = out / "artifact-files.json"
        target.write_bytes(canonical_bytes({"schema": "qikvrt_artifact_file_inventory_v1", "files": files}))
    elif unit["name"] == "SOURCE_HASH_BINDING":
        inventory = out / "artifact-files.json"
        data = json.loads(inventory.read_text(encoding="utf-8"))
        bindings = []
        for item in data["files"]:
            path = config.root / item["path"]
            if path.exists():
                bindings.append({**item, "sha256": hash_file(path)})
        target = out / "source-hash-bindings.json"
        target.write_bytes(canonical_bytes({"schema": "qikvrt_source_hash_bindings_v1", "bindings": bindings}))
    elif unit["name"] == "LEAN_KERNEL_EXECUTION":
        lean_files = sorted(config.root.rglob("*.lean"))
        target = out / "lean-kernel-receipt.json"
        if not lean_files:
            target.write_bytes(canonical_bytes({"schema": "qikvrt_lean_kernel_receipt_v1", "status": "BLOCK", "reason": "no Lean files discovered"}))
            blocker = "NO_LEAN_FILES_DISCOVERED"
            next_action = "generate Lean modules after semantic claim formalization"
            return "BLOCK", [], blocker, next_action
        lean = subprocess.run(["sh", "-c", "command -v lake || command -v lean"], cwd=config.root, capture_output=True, text=True)
        if lean.returncode != 0:
            target.write_bytes(canonical_bytes({"schema": "qikvrt_lean_kernel_receipt_v1", "status": "BLOCK", "reason": "Lean toolchain unavailable", "files": [p.relative_to(config.root).as_posix() for p in lean_files]}))
            blocker = "LEAN_TOOLCHAIN_UNAVAILABLE"
            next_action = "provision pinned Lean toolchain"
            return "BLOCK", [], blocker, next_action
        target.write_bytes(canonical_bytes({"schema": "qikvrt_lean_kernel_receipt_v1", "status": "PARTIAL", "tool": lean.stdout.strip(), "files": [p.relative_to(config.root).as_posix() for p in lean_files]}))
        return "PARTIAL", [{"path": target.relative_to(config.root).as_posix(), "sha256": hash_file(target)}], "LEAN_EXECUTION_ADAPTER_NOT_YET_BOUND", "bind repository Lean build command"
    elif unit["name"] in {"NEGATIVE_TEST_EXECUTION", "COVERAGE_AND_TRACEABILITY", "ZENODO_PUBLICATION_ASSESSMENT"}:
        target = out / f"{unit['name'].lower()}.json"
        target.write_bytes(canonical_bytes({"schema": f"qikvrt_{unit['name'].lower()}_v1", "status": "PARTIAL", "reason": "deterministic scaffold materialized; semantic inputs incomplete"}))
        return "PARTIAL", [{"path": target.relative_to(config.root).as_posix(), "sha256": hash_file(target)}], "SEMANTIC_INPUTS_INCOMPLETE", "resume after semantic units progress"
    elif unit["name"] == "FINAL_COMPLETION_GATE":
        return "BLOCK", [], "MANDATORY_UNITS_INCOMPLETE", "complete every mandatory work unit"
    else:
        return "BLOCK", [], f"NO_EXECUTOR_FOR_{unit['name']}", "implement deterministic executor"

    produced.append({"path": target.relative_to(config.root).as_posix(), "sha256": hash_file(target)})
    return "DONE", produced, blocker, next_action


def advance(state: dict[str, Any], config: PlannerConfig) -> bool:
    units = unit_map(state)
    progress = False
    for unit in state["units"]:
        if unit["status"] == "DONE":
            continue
        if not prerequisites_done(unit, units):
            unit["status"] = "PENDING"
            unit["next_action"] = "wait for prerequisites"
            continue
        unit["status"] = "READY"
        if not config.execute:
            state["next_cursor"] = unit["name"]
            break
        unit["status"] = "RUNNING"
        unit["attempts"] += 1
        unit["repository_head"] = git_head(config.root)
        if unit["kind"] == "semantic" and not config.model_available:
            unit["status"] = "BLOCK"
            unit["blocker"] = "MODEL_INFERENCE_UNAVAILABLE"
            unit["next_action"] = "provide semantic inference or manually curated claim data"
            state["next_cursor"] = unit["name"]
            break
        if unit["kind"] == "external":
            unit["status"] = "BLOCK"
            unit["blocker"] = "EXTERNAL_SYNC_NOT_EXECUTED"
            unit["next_action"] = "execute authenticated Authority/Mirror comparison and sync"
            state["next_cursor"] = unit["name"]
            break
        status, produced, blocker, next_action = execute_deterministic(unit, config)
        unit.update({"status": status, "produced_files": produced, "blocker": blocker, "next_action": next_action, "last_progress_at": utc_now() if produced else unit["last_progress_at"]})
        progress = progress or bool(produced) or status == "DONE"
        if status != "DONE":
            state["next_cursor"] = unit["name"]
            break
    mandatory_done = all(unit["status"] == "DONE" for unit in state["units"])
    state["aggregate_status"] = "DONE" if mandatory_done else "EFFECT_ACK_CONTINUE"
    if mandatory_done:
        state["next_cursor"] = None
    state["generated_at"] = utc_now()
    state["repository_head"] = git_head(config.root)
    return progress


def persist(state: dict[str, Any], config: PlannerConfig) -> None:
    config.work_dir.mkdir(parents=True, exist_ok=True)
    data = canonical_bytes(state)
    (config.work_dir / "STATE.json").write_bytes(data)
    (config.work_dir / "STATE.json.sha256").write_text(f"{sha256_bytes(data)}  STATE.json\n", encoding="utf-8")
    aggregate = {
        "automatic_merge": state["aggregate_status"] == "DONE",
        "generated_at": state["generated_at"],
        "issue_materialized": True,
        "model_inference_completed": all(u["status"] == "DONE" for u in state["units"] if u["kind"] == "semantic"),
        "no_false_pass": True,
        "status": state["aggregate_status"],
        "next_cursor": state["next_cursor"],
        "work_unit_state": "work-units/STATE.json",
    }
    (config.evidence_dir / "STATUS.work-units.json").write_bytes(canonical_bytes(aggregate))


def validate(state: dict[str, Any]) -> None:
    names = [u["name"] for u in state["units"]]
    if names != [u[0] for u in UNITS]:
        raise ValueError("work-unit order mismatch")
    for unit in state["units"]:
        if unit["status"] not in STATUSES:
            raise ValueError(f"invalid status: {unit['status']}")
        if any(p not in names for p in unit["prerequisites"]):
            raise ValueError(f"unknown prerequisite in {unit['name']}")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--model-available", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    config = PlannerConfig(args.root.resolve(), args.issue, args.model_available, not args.plan_only)
    state = load_state(config)
    validate(state)
    advance(state, config)
    validate(state)
    persist(state, config)
    print(json.dumps({"issue": config.issue, "status": state["aggregate_status"], "next_cursor": state["next_cursor"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
