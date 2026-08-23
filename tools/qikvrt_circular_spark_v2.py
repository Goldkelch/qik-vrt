#!/usr/bin/env python3
"""Execute one bounded circular QIK-VRT Spark architecture reference cycle.

The cycle alternates virtual compiler/interpreter roles with two Motorola 68000
execution roles. In this repository-native reference path, M68000 bytes execute
through bounded opcode interpreters. Host/Git effects are represented by the
pure deterministic adapter and are never promoted into real effects.

A real branch closes only when a separately authorized host adapter executes
the selected plan and exact main effect is reobserved.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE_PATH = (
    ROOT / "runtime/m68000/QIKVRT_CIRCULAR_SPARK_ARCHITECTURE_V2.json"
)
PLAN_TOOL = ROOT / "tools/qikvrt_spark_branch_work_unit.py"
CLOSURE_TOOL = ROOT / "tools/qikvrt_spark_branch.py"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_architecture() -> dict[str, Any]:
    value = json.loads(ARCHITECTURE_PATH.read_text(encoding="utf-8"))
    if value.get("schema") != "QIKVRT_CIRCULAR_SPARK_ARCHITECTURE_V2":
        raise ValueError("unexpected circular Spark schema")
    scale = value["scale"]
    if scale["sequence"] != [0, 1, 2, 8, 256]:
        raise ValueError("Spark scale sequence differs")
    if scale["macro_ring_bits"] != 256 ** 3:
        raise ValueError("macro ring width differs")
    if scale["macro_ring_bytes"] != (256 ** 3) // 8:
        raise ValueError("macro ring byte count differs")
    cardinality = scale["macro_ring_state_cardinality"]
    if (
        cardinality["expression"] != "2^(256^3)"
        or cardinality["base"] != 2
        or cardinality["exponent_bits"] != 256 ** 3
        or cardinality["materialized_or_enumerated"]
    ):
        raise ValueError("symbolic macro-state cardinality differs")
    return value


def fixture_observation(mode: str) -> dict[str, bool]:
    base = {
        "malformed_or_scope_invalid": False,
        "main_effect_observed": False,
        "base_current": True,
        "integrity_current": True,
        "gates_terminal": True,
        "gates_non_adverse": True,
        "mergeable": True,
        "authority_available": True,
    }
    if mode == "complete":
        return base
    if mode == "rebase":
        return {
            **base,
            "base_current": False,
            "integrity_current": False,
            "gates_terminal": False,
            "gates_non_adverse": False,
            "mergeable": False,
        }
    if mode == "no-authority":
        return {**base, "authority_available": False}
    if mode == "invalid":
        return {**base, "malformed_or_scope_invalid": True}
    raise ValueError(mode)


def _closure_flags(terminal: str) -> int:
    if terminal == "COMPLETE":
        return 0x0F
    if terminal == "PRECISE_EXTERNAL_HOLD":
        return 0x2F
    if terminal == "HOLD_INVALID":
        return 0x8F
    return 0x1F


def run_reference_cycle(observation: dict[str, Any]) -> dict[str, Any]:
    architecture = load_architecture()
    plan = _load("qikvrt_spark_plan_v2_runtime", PLAN_TOOL)
    closure = _load("qikvrt_spark_closure_v2_runtime", CLOSURE_TOOL)

    plan_receipt = plan.execute_pure_reference_ring(observation)
    pure = plan_receipt["pure_reference_execution"]
    terminal = pure["terminal"]
    d3 = int(plan_receipt["observation_sha256"][:2], 16)
    flags = _closure_flags(terminal)
    d0, d1, d2, d3_after, dynamic = closure.execute(
        closure.MACHINE, flags, d3
    )
    expected = closure.reference(flags, d3)
    if (d0, d1, d2, d3_after) != expected:
        raise AssertionError((expected, (d0, d1, d2, d3_after)))

    expected_decision = {
        "COMPLETE": closure.NOOP,
        "PRECISE_EXTERNAL_HOLD": closure.REQUEST_AUTHORITY,
        "HOLD_INVALID": closure.HOLD,
        "HOLD_DIVERGED": closure.REOBSERVE,
    }[terminal]
    if d0 != expected_decision:
        raise AssertionError((terminal, expected_decision, d0))

    trace = [
        {
            "phase": "VIRTUAL_COMPILER",
            "compiled_once": True,
            "runtime_compiler_invocations": 0,
        },
        {
            "phase": "PHYSICAL_M68000_PLAN_ROLE",
            "evidence_class": "VIRTUAL_BOUNDED_OPCODE_EXECUTION",
            "spark_core_passes": plan_receipt["spark_core_passes"],
            "plan_id": plan_receipt["plan"]["id"],
            "dynamic_m68000_instructions": plan_receipt[
                "dynamic_m68000_instructions"
            ],
        },
        {
            "phase": "VIRTUAL_INTERPRETER_EFFECT_ADAPTER",
            "adapter": "PURE_REFERENCE_ONLY",
            "host_effects_executed": False,
            "steps": [item["step"] for item in pure["trace"]],
        },
        {
            "phase": "PHYSICAL_M68000_CLOSURE_ROLE",
            "evidence_class": "VIRTUAL_BOUNDED_OPCODE_EXECUTION",
            "decision_code": d0,
            "completion_witness": d1,
            "machine_owned_active": d2,
            "dynamic_m68000_instructions": dynamic,
        },
        {
            "phase": "VIRTUAL_REOBSERVATION",
            "terminal": terminal,
            "ordered_completion_reference_observed": pure[
                "ordered_completion_observed"
            ],
        },
        {
            "phase": "QUIESCENCE_OR_NEXT_ACTIVATION",
            "quiescent": terminal in {
                "COMPLETE",
                "PRECISE_EXTERNAL_HOLD",
                "HOLD_INVALID",
            },
        },
    ]

    canonical = (
        json.dumps(
            {
                "architecture": architecture["schema"],
                "observation": plan_receipt["observation"],
                "plan": plan_receipt["plan"]["id"],
                "terminal": terminal,
                "d3": d3_after,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")

    return {
        "schema": "QIKVRT_CIRCULAR_SPARK_REFERENCE_CYCLE_V2",
        "architecture": architecture["schema"],
        "scale_sequence": architecture["scale"]["sequence"],
        "macro_ring_bits": architecture["scale"]["macro_ring_bits"],
        "macro_ring_bytes": architecture["scale"]["macro_ring_bytes"],
        "macro_state_cardinality_expression": architecture["scale"][
            "macro_ring_state_cardinality"
        ]["expression"],
        "branch_work_units_admitted": 1,
        "complete_branch_plans_selected": 1,
        "spark_plan_passes": 1,
        "spark_closure_passes": 1,
        "spark_core_cycle_count": 1,
        "selected_plan": plan_receipt["plan"]["id"],
        "reference_terminal": terminal,
        "d3_before": d3,
        "d3_after": d3_after,
        "d3_preserved": d3 == d3_after,
        "trace": trace,
        "compiled_bytes_loaded_once": True,
        "runtime_compiler_invocations": 0,
        "higher_level_rule_reinterpreted_per_machine_pass": False,
        "virtual_compiler_observed": True,
        "virtual_interpreter_observed": True,
        "virtual_m68000_execution_observed": True,
        "host_effects_executed": False,
        "authority_main_effect": False,
        "hatari_m68000_execution_observed_for_new_spark_kernels": False,
        "physical_m68000_execution_observed": False,
        "physical_speedup_ratio_measured": False,
        "receipt_sha256": hashlib.sha256(canonical).hexdigest(),
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("complete", "rebase", "no-authority", "invalid"),
        default="complete",
    )
    parser.add_argument("--observation", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    observation = (
        json.loads(args.observation.read_text(encoding="utf-8"))
        if args.observation
        else fixture_observation(args.mode)
    )
    report = run_reference_cycle(observation)
    print(
        json.dumps(
            report,
            ensure_ascii=False,
            sort_keys=True,
            indent=2 if args.json else None,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
