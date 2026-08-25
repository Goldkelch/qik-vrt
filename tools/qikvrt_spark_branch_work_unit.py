#!/usr/bin/env python3
"""Select and execute one complete virtual Spark branch-work-unit ring.

The Motorola 68000 kernel performs exactly one planning pass. It returns a
complete bounded plan, not a single activity. A host adapter may then execute
those steps serially with exact-head compare-and-swap and reobservation after
every effect. This module provides the deterministic pure reference adapter;
repository writes remain a separately authorized adapter boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
COMPILER_PATH = ROOT / "tools/qikvrt_spark_branch_m68000_compiler.py"
CATALOG_PATH = ROOT / "runtime/m68000/QIKVRT_SPARK_BRANCH_PLANS_V1.json"
HEX_PATH = ROOT / "runtime/m68000/qikvrt_spark_branch_plan_v1.hex"
OBSERVATION_KEYS = (
    "malformed_or_scope_invalid",
    "main_effect_observed",
    "base_current",
    "integrity_current",
    "gates_terminal",
    "gates_non_adverse",
    "mergeable",
    "authority_available",
)


def _load_compiler():
    spec = importlib.util.spec_from_file_location("qikvrt_spark_branch_compiler", COMPILER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Spark compiler cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def normalize_observation(value: dict[str, Any]) -> dict[str, bool]:
    if set(value) != set(OBSERVATION_KEYS):
        missing = sorted(set(OBSERVATION_KEYS) - set(value))
        extra = sorted(set(value) - set(OBSERVATION_KEYS))
        raise ValueError(f"observation key mismatch: missing={missing}, extra={extra}")
    result: dict[str, bool] = {}
    for key in OBSERVATION_KEYS:
        item = value[key]
        if type(item) is not bool:
            raise ValueError(f"observation field must be boolean: {key}")
        result[key] = item
    return result


def encode_observation(observation: dict[str, bool]) -> int:
    normalized = normalize_observation(observation)
    flags = 0
    for bit, key in enumerate(OBSERVATION_KEYS):
        if normalized[key]:
            flags |= 1 << bit
    return flags


def load_catalog() -> tuple[dict[str, Any], dict[int, dict[str, Any]]]:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if catalog.get("schema") != "QIKVRT_SPARK_BRANCH_PLANS_V1":
        raise ValueError("unexpected Spark plan catalog schema")
    entries = catalog.get("plans")
    if not isinstance(entries, list):
        raise ValueError("Spark plans must be a list")
    by_code = {entry["code"]: entry for entry in entries}
    if sorted(by_code) != list(range(12)) or len(entries) != 12:
        raise ValueError("Spark plan inventory must be exact 0..11")
    return catalog, by_code


def select_complete_plan(observation: dict[str, Any]) -> dict[str, Any]:
    compiler = _load_compiler()
    normalized = normalize_observation(observation)
    flags = encode_observation(normalized)
    machine = bytes.fromhex("".join(HEX_PATH.read_text(encoding="ascii").split()))
    if machine != compiler.MACHINE:
        raise ValueError("registered Spark bytes differ from deterministic compiler")
    plan_code, dynamic_instructions = compiler.execute_kernel(machine, flags)
    expected = compiler.reference_plan(flags)
    if plan_code != expected:
        raise AssertionError((flags, expected, plan_code))
    catalog, by_code = load_catalog()
    plan = by_code[plan_code]
    observation_bytes = _canonical_json(normalized)
    return {
        "schema": "QIKVRT_SPARK_BRANCH_WORK_UNIT_PLAN_V1",
        "observation": normalized,
        "observation_flags": flags,
        "observation_sha256": hashlib.sha256(observation_bytes).hexdigest(),
        "kernel_id": catalog["kernel_id"],
        "kernel_sha256": hashlib.sha256(machine).hexdigest(),
        "spark_core_passes": 1,
        "dynamic_m68000_instructions": dynamic_instructions,
        "complete_branch_plan_selected": True,
        "plan": plan,
        "host_effects_executed": False,
        "main_effect_reobserved": normalized["main_effect_observed"],
        "physical_m68000_execution_observed": False,
        "pass_claimed": False,
        "final_pass_claimed": False,
        "effect_ack_done_claimed": False,
    }


def execute_pure_reference_ring(observation: dict[str, Any]) -> dict[str, Any]:
    receipt = select_complete_plan(observation)
    state = dict(receipt["observation"])
    trace: list[dict[str, Any]] = []
    terminal = receipt["plan"]["terminal"]

    for step in receipt["plan"]["steps"]:
        before = dict(state)
        if step == "REBASE":
            state["base_current"] = True
            state["integrity_current"] = False
            state["gates_terminal"] = False
            state["gates_non_adverse"] = False
            state["mergeable"] = False
        elif step == "REPAIR":
            state["gates_terminal"] = False
            state["gates_non_adverse"] = False
            state["mergeable"] = False
        elif step == "MATERIALIZE":
            state["integrity_current"] = True
        elif step == "VERIFY":
            state["gates_terminal"] = True
            state["gates_non_adverse"] = True
            state["mergeable"] = True
        elif step == "MERGE":
            if not state["authority_available"]:
                raise AssertionError("pure adapter refused merge without authority")
            if not (
                state["base_current"]
                and state["integrity_current"]
                and state["gates_terminal"]
                and state["gates_non_adverse"]
                and state["mergeable"]
            ):
                raise AssertionError("pure adapter refused merge before readiness")
            state["main_effect_observed"] = True
        elif step == "REQUEST_AUTHORITY":
            terminal = "PRECISE_EXTERNAL_HOLD"
        elif step == "PERSIST_INVALID_OBSERVATION":
            terminal = "HOLD_INVALID"
        elif step in {
            "REOBSERVE_MAIN_EFFECT",
            "COLLECT",
            "PERSIST",
            "RELEASE",
        }:
            pass
        else:
            raise ValueError(f"unknown Spark plan step: {step}")
        trace.append({"step": step, "before": before, "after": dict(state)})

    if terminal == "COMPLETE_OR_FAIL_CLOSED":
        terminal = "COMPLETE" if state["main_effect_observed"] else "HOLD_DIVERGED"
    receipt["pure_reference_execution"] = {
        "trace": trace,
        "final_state": state,
        "terminal": terminal,
        "ordered_completion_observed": terminal in {
            "COMPLETE",
            "PRECISE_EXTERNAL_HOLD",
            "HOLD_INVALID",
        },
    }
    receipt["host_effects_executed"] = False
    receipt["main_effect_reobserved"] = state["main_effect_observed"]
    receipt["receipt_sha256"] = hashlib.sha256(_canonical_json(receipt)).hexdigest()
    return receipt


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observation", type=Path, required=True)
    parser.add_argument("--pure-reference-ring", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    observation = json.loads(args.observation.read_text(encoding="utf-8"))
    if args.pure_reference_ring:
        result = execute_pure_reference_ring(observation)
    else:
        result = select_complete_plan(observation)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2 if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
