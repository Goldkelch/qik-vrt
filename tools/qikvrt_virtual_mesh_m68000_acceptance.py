#!/usr/bin/env python3
"""Execute all proof-bound QIK-VRT M68000 kernels as one virtual Mesh path."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_RELATIVE = Path("runtime/m68000/QIKVRT_COMPILED_KERNELS_V1.json")
EXPECTED_IDS = (
    "lean_gate_v1",
    "lean_v2_d3_step_v1",
    "lean_v2_mesh_recovery_v1",
    "lean_spark_branch_plan_v1",
)
EXPECTED_TOTAL_BYTES = 202


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _repository_path(root: Path, value: str) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / value).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise ValueError(f"registry path escapes repository: {value}")
    return candidate


def load_registry(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, bytes]]:
    registry_path = root / REGISTRY_RELATIVE
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema") != "QIKVRT_COMPILED_M68000_KERNEL_REGISTRY_V1":
        raise ValueError("unexpected compiled-kernel registry schema")
    if registry.get("target") != "Motorola 68000":
        raise ValueError("unexpected compiled-kernel target")
    entries = registry.get("kernels")
    if not isinstance(entries, list):
        raise ValueError("registry kernels must be a list")
    ids = tuple(entry.get("id") for entry in entries)
    if ids != EXPECTED_IDS:
        raise ValueError(f"compiled-kernel inventory differs: {ids!r}")

    loaded: dict[str, bytes] = {}
    for entry in entries:
        kernel_id = entry["id"]
        hex_path = _repository_path(root, entry["hex_path"])
        proof_path = _repository_path(root, entry["proof_source"])
        if not proof_path.is_file():
            raise ValueError(f"proof source absent for {kernel_id}: {proof_path}")
        raw_hex = "".join(hex_path.read_text(encoding="ascii").split())
        if not raw_hex or len(raw_hex) % 2:
            raise ValueError(f"invalid hex payload for {kernel_id}")
        try:
            machine = bytes.fromhex(raw_hex)
        except ValueError as exc:
            raise ValueError(f"invalid hex payload for {kernel_id}") from exc
        if len(machine) != entry["machine_bytes"]:
            raise ValueError(f"machine byte count differs for {kernel_id}")
        loaded[kernel_id] = machine
    if sum(map(len, loaded.values())) != EXPECTED_TOTAL_BYTES:
        raise ValueError("compiled-kernel byte total differs")
    return registry, loaded


def _compiler_modules(root: Path) -> tuple[ModuleType, ModuleType, ModuleType, ModuleType]:
    tools = root / "tools"
    return (
        _load_module("qikvrt_lean_gate_m68000_compiler_runtime", tools / "qikvrt_lean_gate_m68000_compiler.py"),
        _load_module("qikvrt_lean_v2_m68000_d3_compiler_runtime", tools / "qikvrt_lean_v2_m68000_d3_compiler.py"),
        _load_module("qikvrt_lean_v2_m68000_mesh_recovery_compiler_runtime", tools / "qikvrt_lean_v2_m68000_mesh_recovery_compiler.py"),
        _load_module("qikvrt_spark_branch_m68000_compiler_runtime", tools / "qikvrt_spark_branch_m68000_compiler.py"),
    )


def execute_virtual_mesh(iterations: int = 1, root: Path = ROOT) -> dict[str, Any]:
    if iterations < 1:
        raise ValueError("iterations must be positive")
    registry, kernels = load_registry(root)
    gate, d3, recovery, spark = _compiler_modules(root)

    expected_bytes = {
        "lean_gate_v1": gate.compile_kernel(),
        "lean_v2_d3_step_v1": d3.MACHINE,
        "lean_v2_mesh_recovery_v1": recovery.MACHINE,
        "lean_spark_branch_plan_v1": spark.MACHINE,
    }
    for kernel_id, expected in expected_bytes.items():
        if kernels[kernel_id] != expected:
            raise ValueError(f"registered bytes differ from compiler: {kernel_id}")

    gate_instruction_count = 0
    d3_instruction_count = 0
    recovery_instruction_count = 0
    spark_instruction_count = 0
    witness = 0xA5
    observed_recovery: list[dict[str, int]] = []
    observed_spark: list[dict[str, int]] = []

    spark_report = spark.verify_exhaustive(kernels["lean_spark_branch_plan_v1"])
    if spark_report["verified_flag_bytes"] != 256:
        raise AssertionError("Spark exhaustive verification incomplete")

    for _ in range(iterations):
        gate_result, count = gate.execute_kernel(kernels["lean_gate_v1"], 0b01)
        gate_instruction_count += count
        if gate_result != gate.GATE_PASS:
            raise AssertionError(("gate", gate.GATE_PASS, gate_result))

        decision = 2
        phase = 0
        for expected_phase in (1, 2, 0):
            decision_out, phase, witness_out, count = d3.execute(
                kernels["lean_v2_d3_step_v1"], decision, phase, witness
            )
            d3_instruction_count += count
            if (decision_out, phase, witness_out) != (decision, expected_phase, witness):
                raise AssertionError(("d3_step", decision_out, phase, witness_out))

        recovery_expectations = ((0, 0), (3, 0), (4, 1), (6, 1), (7, 2), (255, 2))
        observed_recovery = []
        for cutpoint, expected in recovery_expectations:
            actual, count = recovery.execute(kernels["lean_v2_mesh_recovery_v1"], cutpoint)
            recovery_instruction_count += count
            if actual != expected:
                raise AssertionError(("recovery", cutpoint, expected, actual))
            observed_recovery.append({"cutpoint": cutpoint, "recovery_choice": actual})

        spark_expectations = ((1, 1), (2, 0), (124, 11), (252, 10), (248, 2))
        observed_spark = []
        for flags, expected in spark_expectations:
            actual, count = spark.execute_kernel(kernels["lean_spark_branch_plan_v1"], flags)
            spark_instruction_count += count
            if actual != expected:
                raise AssertionError(("spark", flags, expected, actual))
            observed_spark.append({"observation_flags": flags, "plan_code": actual})

    registry_bytes = (root / REGISTRY_RELATIVE).read_bytes()
    return {
        "schema": "QIKVRT_VIRTUAL_MESH_M68000_ACCEPTANCE_V2",
        "iterations": iterations,
        "registry_schema": registry["schema"],
        "registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
        "kernel_ids": list(EXPECTED_IDS),
        "kernel_sha256": {key: hashlib.sha256(value).hexdigest() for key, value in kernels.items()},
        "compiled_machine_bytes_total": sum(map(len, kernels.values())),
        "gate": {"input_certificate_bits": 1, "output_gate": gate.GATE_PASS, "dynamic_instructions": gate_instruction_count},
        "d3_lifecycle": {"decision_code": 2, "completed_ied_cycles": iterations, "final_phase_code": 0, "witness_byte": witness, "d3_preserved": True, "dynamic_instructions": d3_instruction_count},
        "mesh_recovery": {"observations_per_iteration": 6, "last_observations": observed_recovery, "dynamic_instructions": recovery_instruction_count},
        "spark_branch": {"complete_plan_passes": iterations * len(observed_spark), "last_observations": observed_spark, "exhaustive_flag_bytes_verified": 256, "max_dynamic_instructions": spark_report["max_dynamic_instructions"], "dynamic_instructions": spark_instruction_count},
        "compiled_kernel_registry_loaded": True,
        "registered_machine_bytes_executed": True,
        "higher_level_rule_reinterpreted_for_decision": False,
        "semantic_abis_kept_distinct": True,
        "virtual_m68000_execution_observed": True,
        "complete_branch_plan_selected_by_m68000": True,
        "host_github_effect_executed_by_m68000": False,
        "physical_m68000_execution_observed": False,
        "physical_speedup_measured": False,
        "workflow_accelerated_by_m68000": False,
        "pass_claimed": False,
        "final_pass_claimed": False,
        "effect_ack_done_claimed": False,
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(execute_virtual_mesh(args.iterations), ensure_ascii=False, sort_keys=True, indent=2 if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
