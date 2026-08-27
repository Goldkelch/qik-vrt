# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate the inside-out QIK-VRT evidence-fixpoint carrier."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "state/fixpoints/QIKVRT_QUANTUM_CAUSAL_NEUTRON_STAR_EVIDENCE_FIXPOINT_SET_V1.json"
STATUS_PATH = ROOT / "docs/terminal/quantum-causal-neutron-star/status.json"
EXPECTED_LAYERS = ["BIT_CELL", "TICK_RECEIPT", "METATRANSISTOR", "VHDL_RTL", "M68000_ABI", "SECTOR", "SHELL", "NEUTRON_STAR_MESH", "TERMINAL_PROJECTION", "AUTHORITY_REOBSERVATION"]
EXPECTED_SOURCE_DIGESTS = {
    "state/fixpoints/TICK_RECEIPT_COMPILER_V1.yaml": "13aaa23ce1cb408bc5644bc7422b55a1aa07ed1c41834f40643c053d69ef363f",
    "schemas/qikvrt_tick_receipt_v1.schema.json": "fde9b8470daf10948e9745d499856e642f547181580c4d82777a6e9107a46c3e",
}

class ValidationError(ValueError):
    pass

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)

def read_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value

def sha256_path(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_source_contracts(contract: dict[str, Any]) -> None:
    declared = {item["path"]: item["sha256"] for item in contract["source_contracts"]}
    require(declared == EXPECTED_SOURCE_DIGESTS, "source-contract declaration drifted")
    for relative, expected in EXPECTED_SOURCE_DIGESTS.items():
        require(sha256_path(ROOT / relative) == expected, f"digest mismatch: {relative}")
    schema = read_json(ROOT / "schemas/qikvrt_tick_receipt_v1.schema.json")
    require(schema["properties"]["state"]["enum"] == ["OBSERVE", "HOLD", "CONTINUE"], "receipt states drifted")
    require(schema["properties"]["completion_claims"]["const"] == {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False}, "receipt claims drifted")
    yaml_text = (ROOT / "state/fixpoints/TICK_RECEIPT_COMPILER_V1.yaml").read_text(encoding="utf-8")
    for marker in ("mode: READ_ONLY", "parent_and_child_must_differ: true", "parent_history_mutation: FORBIDDEN", "predecessor_evidence_transfer: FORBIDDEN", "missing_or_drifted_input: HOLD", "external_effect: FORBIDDEN"):
        require(marker in yaml_text, f"missing compiler marker: {marker}")

def validate_layers(contract: dict[str, Any]) -> None:
    layers = contract["inside_out_layers"]
    require([item["ordinal"] for item in layers] == list(range(len(EXPECTED_LAYERS))), "layer ordinals drifted")
    require([item["id"] for item in layers] == EXPECTED_LAYERS, "inside-out order drifted")
    require(all(item["claim_class"] == "SOFTWARE_ARCHITECTURE_INVARIANT" for item in layers), "claim class broadened")

def validate_vhdl(contract: dict[str, Any]) -> None:
    profile = contract["vhdl_profile"]
    require(profile["literal_cpu_machine_code"] is False, "VHDL is not CPU machine code")
    require(profile["completion_outputs_hard_false"] is True, "completion fence opened")
    require(profile["carrier_width_bits"] == {"minimum": 8, "maximum": 256}, "carrier width drifted")
    package = (ROOT / "hardware/vhdl/qikvrt_metatransistor_pkg.vhd").read_text(encoding="utf-8")
    cell = (ROOT / "hardware/vhdl/qikvrt_metatransistor.vhd").read_text(encoding="utf-8")
    mesh = (ROOT / "hardware/vhdl/qikvrt_neutron_star_mesh.vhd").read_text(encoding="utf-8")
    tb = (ROOT / "hardware/vhdl/tb_qikvrt_metatransistor.vhd").read_text(encoding="utf-8")
    require("QIKVRT_RESERVED" in package and "when others" in package and "return QIKVRT_HOLD" in package, "reserved fail-closed state missing")
    for assignment in ("pass_o            <= '0';", "final_pass_o      <= '0';", "effect_ack_done_o <= '0';"):
        require(assignment in cell, f"missing hard-false output: {assignment}")
    require("carrier_o <= carrier_i;" in mesh, "lossless carrier wire missing")
    require("assert pass_value = '0'" in tb, "negative claim test missing")

def validate_boundaries(contract: dict[str, Any]) -> None:
    boundary = contract["claim_boundary"]
    for key in ("vhdl_analysis_observed", "vhdl_elaboration_observed", "synthesis_observed", "place_and_route_observed", "fpga_bitstream_observed", "asic_layout_observed", "physical_hardware_execution_observed", "physical_m68000_execution_observed", "quantum_state_simulation_observed", "astrophysical_neutron_star_simulation_observed", "physical_quantum_causality_established"):
        require(boundary[key] is False, f"unsupported claim broadened: {key}")
    require(boundary["quantum_causality_class"] == "QUANTUM_CAUSALITY_HYPOTHESIS", "quantum class broadened")
    require(boundary["physical_mapping_class"] == "PHYSICAL_MAPPING_HYPOTHESIS", "physical class broadened")
    require(contract["completion_claims"] == {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False}, "completion boundary drifted")

def validate_terminal(contract: dict[str, Any]) -> None:
    status = read_json(STATUS_PATH)
    require(status["schema"] == "qikvrt.quantum-causal-neutron-star-terminal.v1", "terminal schema drifted")
    require(status["layer_order"] == EXPECTED_LAYERS, "terminal layer order drifted")
    require(status["mode"] == "PUBLIC_GET_ONLY", "terminal write boundary opened")
    require(status["background_polling"] is False, "background polling enabled")
    require(status["completion_claims"] == contract["completion_claims"], "terminal claims disagree")

def validate() -> dict[str, Any]:
    contract = read_json(CONTRACT_PATH)
    require(contract["schema"] == "qikvrt.quantum-causal-neutron-star-evidence-fixpoint-set.v1", "contract schema drifted")
    validate_source_contracts(contract)
    validate_layers(contract)
    validate_vhdl(contract)
    validate_boundaries(contract)
    validate_terminal(contract)
    return {"schema": "qikvrt.quantum-causal-neutron-star-validation.v1", "state": "OBSERVE", "layer_order": EXPECTED_LAYERS, "source_sha256": EXPECTED_SOURCE_DIGESTS, "claims": {"PASS": False, "FINAL_PASS": False, "EFFECT_ACK_DONE": False, "synthesis_observed": False, "physical_hardware_execution_observed": False, "physical_quantum_causality_established": False}}

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate",))
    args = parser.parse_args(argv)
    print(json.dumps(validate(), indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
