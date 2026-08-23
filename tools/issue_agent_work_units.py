#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Deterministic, resumable issue work units with scoped semantic holds.

A missing model blocks only the first semantic unit. Completed deterministic
units are content-addressed and never repeated. Platform publication is a
separate post-effect stage: a ready route is executed by the dedicated trusted
workflow, then public reobservation promotes the issue to DONE.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "qikvrt_issue_work_units_v2"
UNIT_STATUSES = {
    "PENDING",
    "READY",
    "RUNNING",
    "PARTIAL",
    "BLOCK",
    "WAITING_EFFECT",
    "DONE",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
DOI = re.compile(r"\b10\.5281/zenodo\.[1-9][0-9]*\b")
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
    (
        "ZENODO_PUBLICATION_ASSESSMENT",
        ("COVERAGE_AND_TRACEABILITY",),
        "deterministic",
    ),
    (
        "FINAL_COMPLETION_GATE",
        ("ZENODO_PUBLICATION_ASSESSMENT",),
        "deterministic",
    ),
    ("AUTHORITY_MIRROR_SYNC", ("FINAL_COMPLETION_GATE",), "post_effect"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(root: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--verify", "HEAD^{commit}"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def repository_head(config: "Config") -> str:
    """Bind work-unit inputs to Authority main, not to self-generated branch commits."""
    value = os.environ.get("QIKVRT_ISSUE_AUTHORITY_HEAD", "").strip()
    if re.fullmatch(r"[0-9a-f]{40}", value):
        return value
    return repository_head(config)


@dataclass(frozen=True)
class Config:
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

    @property
    def artifact_dir(self) -> Path:
        return self.work_dir / "artifacts"


def _unit_id(issue: int, ordinal: int, name: str) -> str:
    return f"WU-{issue}-{ordinal:02d}-{name}"


def default_state(config: Config) -> dict[str, Any]:
    head = repository_head(config)
    units = []
    for ordinal, (name, prerequisites, kind) in enumerate(UNITS, start=1):
        units.append(
            {
                "id": _unit_id(config.issue, ordinal, name),
                "name": name,
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
            }
        )
    return {
        "schema": SCHEMA,
        "issue": config.issue,
        "repository_head": head,
        "generated_at": utc_now(),
        "gate_status": "CONTINUE",
        "effect_ack_state": "EFFECT_ACK_CONTINUE",
        "pre_effect_ready": False,
        "publication_required": False,
        "publication_state": "NOT_REQUESTED",
        "next_cursor": units[0]["name"],
        "units": units,
    }


def load_state(config: Config) -> dict[str, Any]:
    path = config.work_dir / "STATE.json"
    if not path.is_file():
        return default_state(config)
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != SCHEMA or value.get("issue") != config.issue:
        raise ValueError("incompatible issue work-unit state")
    return value


def validate_state(state: Mapping[str, Any]) -> None:
    expected_names = [item[0] for item in UNITS]
    units = state.get("units")
    if not isinstance(units, list):
        raise ValueError("work-unit state units must be an array")
    names = [unit.get("name") for unit in units]
    if names != expected_names:
        raise ValueError("work-unit order mismatch")
    for unit in units:
        if unit.get("status") not in UNIT_STATUSES:
            raise ValueError(f"invalid work-unit status: {unit.get('status')}")
        if any(name not in expected_names for name in unit.get("prerequisites", [])):
            raise ValueError(f"unknown prerequisite in {unit.get('name')}")


def unit_map(state: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {unit["name"]: unit for unit in state["units"]}


def prerequisites_done(
    unit: Mapping[str, Any],
    units: Mapping[str, Mapping[str, Any]],
) -> bool:
    return all(units[name]["status"] == "DONE" for name in unit["prerequisites"])


def _relative(config: Config, path: Path) -> str:
    return path.resolve().relative_to(config.root.resolve()).as_posix()


def _artifact_record(config: Config, path: Path) -> dict[str, Any]:
    return {
        "path": _relative(config, path),
        "bytes": path.stat().st_size,
        "sha256": hash_file(path),
    }


def _write_artifact(
    config: Config,
    name: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    config.artifact_dir.mkdir(parents=True, exist_ok=True)
    target = config.artifact_dir / name
    target.write_bytes(canonical_bytes(payload))
    return _artifact_record(config, target)


def _bounded_repository_files(config: Config) -> list[Path]:
    files: list[Path] = []
    for path in sorted(config.root.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        if config.evidence_dir == path or config.evidence_dir in path.parents:
            continue
        files.append(path)
        if len(files) > 20000:
            raise RuntimeError("repository file inventory exceeded 20000 entries")
    return files


def _read_request_text(config: Config) -> str:
    request = config.evidence_dir / "REQUEST.json"
    if not request.is_file():
        return ""
    value = json.loads(request.read_text(encoding="utf-8"))
    body = value.get("body")
    return body if isinstance(body, str) else ""


def _discover_zenodo(config: Config) -> dict[str, Any]:
    records: dict[str, dict[str, Any]] = {}
    files = []
    for path in _bounded_repository_files(config):
        relative = _relative(config, path)
        lower = relative.casefold()
        if "zenodo" not in lower and "doi" not in path.name.casefold():
            continue
        item = _artifact_record(config, path)
        files.append(item)
        if path.stat().st_size > 4 * 1024 * 1024:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for doi in DOI.findall(text):
            records.setdefault(
                doi,
                {
                    "doi": doi,
                    "source_paths": [],
                },
            )["source_paths"].append(relative)
    for value in records.values():
        value["source_paths"] = sorted(set(value["source_paths"]))
    return {
        "schema": "qikvrt_zenodo_record_discovery_v2",
        "issue": config.issue,
        "repository_head": repository_head(config),
        "records": [records[key] for key in sorted(records)],
        "candidate_files": files,
        "network_inventory_performed": False,
    }


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _execute_semantic(
    unit: Mapping[str, Any],
    config: Config,
) -> tuple[str, list[dict[str, Any]], str | None, str]:
    if not config.model_available:
        return (
            "BLOCK",
            [],
            "MODEL_INFERENCE_UNAVAILABLE",
            "resume this exact cursor when trusted inference is available",
        )

    expected = {
        "CLAIM_EXTRACTION_QUEUE": (
            "CLAIMS.json",
            lambda value: isinstance(value.get("claims"), list),
            "MACHINE_READABLE_CLAIM_INVENTORY_MISSING",
        ),
        "CLAIM_CLASSIFICATION": (
            "CLAIMS.json",
            lambda value: bool(value.get("claims"))
            and all(
                isinstance(item, dict)
                and isinstance(item.get("status_class"), str)
                and item["status_class"]
                for item in value["claims"]
            ),
            "CLAIM_CLASSIFICATION_INCOMPLETE",
        ),
        "CLAIM_DEPENDENCY_GRAPH": (
            "CLAIM_GRAPH.json",
            lambda value: isinstance(value.get("nodes"), list)
            and isinstance(value.get("edges"), list),
            "CLAIM_DEPENDENCY_GRAPH_MISSING",
        ),
        "FORMALIZATION_CANDIDATE_QUEUE": (
            "FORMALIZATION_QUEUE.json",
            lambda value: isinstance(value.get("candidates"), list),
            "FORMALIZATION_QUEUE_MISSING",
        ),
        "LEAN_MODULE_GENERATION": (
            "LEAN_MODULES.json",
            lambda value: isinstance(value.get("modules"), list),
            "LEAN_MODULE_BINDING_MISSING",
        ),
    }
    filename, predicate, blocker = expected[unit["name"]]
    path = config.evidence_dir / filename
    if not path.is_file():
        return "BLOCK", [], blocker, f"materialize {filename} at the exact issue head"
    value = _load_json_object(path, filename)
    if not predicate(value):
        return "BLOCK", [], blocker, f"complete and validate {filename}"
    receipt = _write_artifact(
        config,
        unit["name"].casefold() + ".json",
        {
            "schema": "qikvrt_semantic_work_unit_receipt_v1",
            "issue": config.issue,
            "unit": unit["name"],
            "source": _artifact_record(config, path),
            "status": "DONE",
            "repository_head": repository_head(config),
        },
    )
    return "DONE", [receipt], None, "advance to next unit"


def _publication_assessment(
    config: Config,
) -> tuple[str, list[dict[str, Any]], str | None, str]:
    route_path = config.evidence_dir / "PUBLICATION_ROUTE.json"
    request_text = _read_request_text(config).casefold()
    requested_by_text = any(
        token in request_text
        for token in ("zenodo", "publication", "publikation", "doi")
    )
    if not route_path.is_file():
        payload = {
            "schema": "qikvrt_issue_publication_assessment_v1",
            "issue": config.issue,
            "required": requested_by_text,
            "state": "ROUTE_MISSING" if requested_by_text else "NOT_REQUESTED",
            "repository_head": repository_head(config),
        }
        receipt = _write_artifact(
            config,
            "zenodo_publication_assessment.json",
            payload,
        )
        if requested_by_text:
            return (
                "BLOCK",
                [receipt],
                "PUBLICATION_ROUTE_MISSING",
                "materialize one exact qikvrt_issue_publication_route_v1 route",
            )
        return "DONE", [receipt], None, "advance to final completion gate"

    route = _load_json_object(route_path, "PUBLICATION_ROUTE.json")
    required_keys = {
        "schema",
        "issue_number",
        "required",
        "platform",
        "state",
        "manifest_path",
        "manifest_sha256",
        "adapter",
        "receipt_path",
    }
    if set(route) != required_keys:
        return (
            "BLOCK",
            [],
            "PUBLICATION_ROUTE_INVALID",
            "regenerate the closed publication route contract",
        )
    if (
        route["schema"] != "qikvrt_issue_publication_route_v1"
        or route["issue_number"] != config.issue
        or route["required"] is not True
        or route["platform"] != "zenodo"
        or route["adapter"] != "tools/qikvrt_zenodo_publish.py"
        or route["state"] not in {"READY", "PUBLIC_VERIFIED"}
        or not isinstance(route["manifest_sha256"], str)
        or HEX64.fullmatch(route["manifest_sha256"]) is None
    ):
        return (
            "BLOCK",
            [],
            "PUBLICATION_ROUTE_INVALID",
            "regenerate the exact Zenodo publication route",
        )
    manifest = config.root / route["manifest_path"]
    if not manifest.is_file() or hash_file(manifest) != route["manifest_sha256"]:
        return (
            "BLOCK",
            [],
            "PUBLICATION_MANIFEST_MISSING_OR_DRIFTED",
            "restore the exact manifest bytes named by the route",
        )
    payload = {
        "schema": "qikvrt_issue_publication_assessment_v1",
        "issue": config.issue,
        "required": True,
        "state": route["state"],
        "route": _artifact_record(config, route_path),
        "manifest": _artifact_record(config, manifest),
        "repository_head": repository_head(config),
    }
    receipt = _write_artifact(
        config,
        "zenodo_publication_assessment.json",
        payload,
    )
    return "DONE", [receipt], None, "advance to final completion gate"


def _execute_deterministic(
    unit: Mapping[str, Any],
    config: Config,
    state: Mapping[str, Any],
) -> tuple[str, list[dict[str, Any]], str | None, str]:
    name = unit["name"]
    if name == "ZENODO_RECORD_DISCOVERY":
        receipt = _write_artifact(
            config,
            "zenodo-records.json",
            _discover_zenodo(config),
        )
        return "DONE", [receipt], None, "advance to artifact inventory"

    if name == "ARTIFACT_FILE_INVENTORY":
        files = [
            {
                "path": _relative(config, path),
                "bytes": path.stat().st_size,
            }
            for path in _bounded_repository_files(config)
        ]
        receipt = _write_artifact(
            config,
            "artifact-files.json",
            {
                "schema": "qikvrt_artifact_file_inventory_v2",
                "issue": config.issue,
                "repository_head": repository_head(config),
                "files": files,
            },
        )
        return "DONE", [receipt], None, "advance to source hash binding"

    if name == "SOURCE_HASH_BINDING":
        inventory_path = config.artifact_dir / "artifact-files.json"
        inventory = _load_json_object(inventory_path, "artifact-files.json")
        bindings = []
        for item in inventory.get("files", []):
            path = config.root / item["path"]
            if path.is_file():
                bindings.append(
                    {
                        "path": item["path"],
                        "bytes": path.stat().st_size,
                        "sha256": hash_file(path),
                    }
                )
        receipt = _write_artifact(
            config,
            "source-hash-bindings.json",
            {
                "schema": "qikvrt_source_hash_bindings_v2",
                "issue": config.issue,
                "repository_head": repository_head(config),
                "bindings": bindings,
            },
        )
        return "DONE", [receipt], None, "advance to semantic claim queue"

    if name == "LEAN_KERNEL_EXECUTION":
        path = config.evidence_dir / "LEAN_KERNEL_RECEIPT.json"
        if not path.is_file():
            return (
                "BLOCK",
                [],
                "EXACT_HEAD_LEAN_KERNEL_RECEIPT_MISSING",
                "execute the bound Lean/Lake target and persist LEAN_KERNEL_RECEIPT.json",
            )
        value = _load_json_object(path, "LEAN_KERNEL_RECEIPT.json")
        if (
            value.get("status") != "KERNEL_ACCEPTED"
            or value.get("repository_head") != repository_head(config)
        ):
            return (
                "BLOCK",
                [],
                "LEAN_KERNEL_RECEIPT_NOT_EXACT_HEAD_ACCEPTED",
                "rerun Lean/Lake on this exact head and replace the receipt",
            )
        return "DONE", [_artifact_record(config, path)], None, "advance to negative tests"

    if name == "NEGATIVE_TEST_EXECUTION":
        path = config.evidence_dir / "NEGATIVE_TEST_RECEIPT.json"
        if not path.is_file():
            return (
                "BLOCK",
                [],
                "EXACT_HEAD_NEGATIVE_TEST_RECEIPT_MISSING",
                "execute negative tests and persist NEGATIVE_TEST_RECEIPT.json",
            )
        value = _load_json_object(path, "NEGATIVE_TEST_RECEIPT.json")
        if (
            value.get("status") != "SUCCESS"
            or value.get("repository_head") != repository_head(config)
        ):
            return (
                "BLOCK",
                [],
                "NEGATIVE_TEST_RECEIPT_NOT_EXACT_HEAD_SUCCESS",
                "rerun negative tests on this exact head",
            )
        return "DONE", [_artifact_record(config, path)], None, "advance to traceability"

    if name == "COVERAGE_AND_TRACEABILITY":
        path = config.evidence_dir / "TRACEABILITY.json"
        if not path.is_file():
            return (
                "BLOCK",
                [],
                "COMPLETE_TRACEABILITY_RECEIPT_MISSING",
                "materialize exact claim/source/proof traceability",
            )
        value = _load_json_object(path, "TRACEABILITY.json")
        if (
            value.get("complete") is not True
            or value.get("repository_head") != repository_head(config)
        ):
            return (
                "BLOCK",
                [],
                "TRACEABILITY_INCOMPLETE_OR_STALE",
                "complete traceability and rebind it to this exact head",
            )
        return "DONE", [_artifact_record(config, path)], None, "assess publication route"

    if name == "ZENODO_PUBLICATION_ASSESSMENT":
        return _publication_assessment(config)

    if name == "FINAL_COMPLETION_GATE":
        route_path = config.evidence_dir / "PUBLICATION_ROUTE.json"
        if route_path.is_file():
            route = _load_json_object(route_path, "PUBLICATION_ROUTE.json")
            if route.get("required") is True and route.get("state") == "READY":
                return (
                    "WAITING_EFFECT",
                    [],
                    None,
                    "execute the exact authorized platform publication and reobserve it",
                )
            if route.get("required") is True and route.get("state") == "PUBLIC_VERIFIED":
                receipt = config.root / route["receipt_path"]
                if not receipt.is_file():
                    return (
                        "BLOCK",
                        [],
                        "PUBLICATION_EFFECT_RECEIPT_MISSING",
                        "restore the public-verification effect receipt",
                    )
                return "DONE", [_artifact_record(config, receipt)], None, "ready for auto-finish"
        return "DONE", [], None, "ready for auto-finish"

    raise ValueError(f"no deterministic executor for {name}")


def _update_aggregate(state: dict[str, Any], config: Config) -> None:
    units = unit_map(state)
    final = units["FINAL_COMPLETION_GATE"]
    route_path = config.evidence_dir / "PUBLICATION_ROUTE.json"
    publication_required = False
    publication_state = "NOT_REQUESTED"
    if route_path.is_file():
        try:
            route = _load_json_object(route_path, "PUBLICATION_ROUTE.json")
        except (OSError, ValueError, json.JSONDecodeError):
            publication_required = True
            publication_state = "INVALID"
        else:
            publication_required = route.get("required") is True
            publication_state = str(route.get("state", "INVALID"))

    blocking = next(
        (unit for unit in state["units"] if unit["status"] == "BLOCK"),
        None,
    )
    waiting = final["status"] == "WAITING_EFFECT"
    pre_effect_ready = waiting or final["status"] == "DONE"
    if blocking is not None:
        gate_status = "BLOCK"
        effect_ack_state = "EFFECT_ACK_CONTINUE"
        next_cursor = blocking["name"]
    elif waiting:
        gate_status = "CONTINUE"
        effect_ack_state = "EFFECT_ACK_CONTINUE"
        next_cursor = "PLATFORM_PUBLICATION_EFFECT"
    elif final["status"] == "DONE":
        gate_status = "DONE"
        effect_ack_state = (
            "EFFECT_ACK_DONE"
            if publication_required and publication_state == "PUBLIC_VERIFIED"
            else "REPOSITORY_DONE"
        )
        next_cursor = None
    else:
        gate_status = "CONTINUE"
        effect_ack_state = "EFFECT_ACK_CONTINUE"
        next_cursor = state.get("next_cursor")

    state.update(
        {
            "repository_head": repository_head(config),
            "gate_status": gate_status,
            "effect_ack_state": effect_ack_state,
            "pre_effect_ready": pre_effect_ready,
            "publication_required": publication_required,
            "publication_state": publication_state,
            "next_cursor": next_cursor,
            "first_blocker": blocking["blocker"] if blocking else None,
            "next_action": (
                blocking["next_action"]
                if blocking
                else final.get("next_action")
            ),
            "machine_owned_work_remaining": gate_status == "CONTINUE",
            "owner_decision_required": bool(
                blocking
                and blocking.get("blocker")
                in {
                    "OWNER_AUTHORIZATION_MISSING",
                    "RIGHTS_OR_LICENSE_DECISION_REQUIRED",
                }
            ),
        }
    )


def advance(state: dict[str, Any], config: Config) -> bool:
    units = unit_map(state)
    before = canonical_bytes(state)
    bound_head = repository_head(config)
    for unit in state["units"]:
        if unit["kind"] == "post_effect":
            if unit["status"] not in {"DONE", "WAITING_EFFECT"}:
                unit["status"] = "WAITING_EFFECT"
                unit["next_action"] = (
                    "owned by issue auto-finish after repository readiness"
                )
            continue
        if unit["status"] == "DONE":
            continue
        if not prerequisites_done(unit, units):
            unit["status"] = "PENDING"
            unit["next_action"] = "wait for prerequisites"
            continue

        # Do not create a new repository commit for the same unresolved
        # deterministic observation. A newly available model or a new Authority
        # head legitimately reopens the exact cursor.
        if (
            unit["status"] == "BLOCK"
            and unit.get("repository_head") == bound_head
            and not (
                unit.get("blocker") == "MODEL_INFERENCE_UNAVAILABLE"
                and config.model_available
            )
        ):
            state["next_cursor"] = unit["name"]
            break

        previous = {
            key: unit.get(key)
            for key in (
                "status",
                "attempts",
                "repository_head",
                "produced_files",
                "blocker",
                "next_action",
                "last_progress_at",
            )
        }
        unit["status"] = "READY"
        state["next_cursor"] = unit["name"]
        if not config.execute:
            break
        unit["status"] = "RUNNING"
        unit["attempts"] += 1
        unit["repository_head"] = bound_head
        if unit["kind"] == "semantic":
            status, produced, blocker, next_action = _execute_semantic(
                unit,
                config,
            )
        else:
            status, produced, blocker, next_action = _execute_deterministic(
                unit,
                config,
                state,
            )
        changed_unit = (
            status != previous["status"]
            or produced != previous["produced_files"]
            or blocker != previous["blocker"]
            or next_action != previous["next_action"]
            or bound_head != previous["repository_head"]
        )
        unit.update(
            {
                "status": status,
                "produced_files": produced,
                "blocker": blocker,
                "next_action": next_action,
                "last_progress_at": (
                    utc_now()
                    if changed_unit and (produced or status == "DONE")
                    else previous["last_progress_at"]
                ),
            }
        )
        if status != "DONE":
            state["next_cursor"] = unit["name"]
            break

    _update_aggregate(state, config)
    old_generated_at = state.get("generated_at")
    state_without_time = dict(state)
    state_without_time["generated_at"] = old_generated_at
    progress = canonical_bytes(state_without_time) != before
    if progress:
        state["generated_at"] = utc_now()
    return progress


def persist(state: dict[str, Any], config: Config) -> bool:
    config.work_dir.mkdir(parents=True, exist_ok=True)
    validate_state(state)
    raw = canonical_bytes(state)
    state_path = config.work_dir / "STATE.json"
    old = state_path.read_bytes() if state_path.is_file() else None
    changed = old != raw
    state_path.write_bytes(raw)
    (config.work_dir / "STATE.json.sha256").write_text(
        f"{sha256_bytes(raw)}  STATE.json\n",
        encoding="utf-8",
    )
    aggregate = {
        "schema": "qikvrt_issue_work_unit_aggregate_v2",
        "issue": config.issue,
        "status": state["gate_status"],
        "effect_ack_state": state["effect_ack_state"],
        "pre_effect_ready": state["pre_effect_ready"],
        "publication_required": state["publication_required"],
        "publication_state": state["publication_state"],
        "next_cursor": state["next_cursor"],
        "first_blocker": state["first_blocker"],
        "next_action": state["next_action"],
        "machine_owned_work_remaining": state["machine_owned_work_remaining"],
        "owner_decision_required": state["owner_decision_required"],
        "work_unit_state": "work-units/STATE.json",
        "repository_head": state["repository_head"],
        "no_false_pass": True,
    }
    (config.evidence_dir / "STATUS.work-units.json").write_bytes(
        canonical_bytes(aggregate)
    )
    return changed


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--issue", type=int, required=True)
    parser.add_argument("--model-available", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    config = Config(
        root=args.root.resolve(),
        issue=args.issue,
        model_available=args.model_available,
        execute=not args.plan_only,
    )
    state = load_state(config)
    validate_state(state)
    advance(state, config)
    changed = persist(state, config)
    print(
        json.dumps(
            {
                "issue": config.issue,
                "status": state["gate_status"],
                "next_cursor": state["next_cursor"],
                "changed": changed,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
