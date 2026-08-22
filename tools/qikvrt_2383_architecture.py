#!/usr/bin/env python3
"""Fail-closed verifier for QIKVRT_2383_VIRTUAL_M68000_ARCHITECTURE_V1.

The verifier intentionally keeps these relations distinct:

* 2**3 == 8 states;
* an octet is 8 bits and has 2**8 == 256 values;
* 8**3 == 512, not 256;
* a virtual reference-interpreter witness is not physical M68000 execution;
* a middleware/interface model is not an observed quantum effect.

A successful process exit means that the HOLD_UNVERIFIED contract is internally
consistent. It never upgrades the architecture to PASS, FINAL_PASS, merge, or
EFFECT_ACK_DONE.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence


SCHEMA = "QIKVRT_2383_VIRTUAL_M68000_ARCHITECTURE_V1"
STATUS = "HOLD_UNVERIFIED"
MOVEQ_MASK = 0xF100
MOVEQ_OPCODE = 0x7000
RTS_OPCODE = 0x4E75


class ContractError(ValueError):
    """Raised when the architecture contract stops being fail-closed."""


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def default_spec_path() -> Path:
    return repository_root() / "spec" / "architecture" / f"{SCHEMA}.json"


def load_contract(path: Path | str | None = None) -> Dict[str, Any]:
    contract_path = Path(path) if path is not None else default_spec_path()
    with contract_path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ContractError("contract root must be a JSON object")
    return value


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractError(f"{name} must be an object")
    return value


def _sequence(value: Any, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ContractError(f"{name} must be an array")
    return value


def _require_false(mapping: Mapping[str, Any], keys: Iterable[str], prefix: str) -> None:
    for key in keys:
        if mapping.get(key) is not False:
            raise ContractError(f"{prefix}.{key} must remain false")


def verified_arithmetic() -> Dict[str, int]:
    return {
        "two_pow_three": 2**3,
        "two_pow_eight": 2**8,
        "eight_pow_three": 8**3,
    }


def decode_words(machine_code_hex: str) -> List[int]:
    if not isinstance(machine_code_hex, str):
        raise ContractError("machine code must be hexadecimal text")
    try:
        payload = bytes.fromhex(machine_code_hex)
    except ValueError as exc:
        raise ContractError("machine code is not valid hexadecimal") from exc
    if not payload or len(payload) % 2:
        raise ContractError("M68000 machine code must contain complete 16-bit words")
    return [int.from_bytes(payload[index : index + 2], "big") for index in range(0, len(payload), 2)]


def emulate_m68000_capsule(machine_code_hex: str) -> Dict[str, Any]:
    """Execute the bounded MOVEQ/RTS witness in a tiny reference interpreter.

    This is deliberately not a full Motorola 68000 emulator. Unsupported words,
    missing RTS, or bytes after RTS fail closed.
    """

    initial: Dict[str, int] = {f"D{index}": 0x11110000 + index for index in range(8)}
    registers: MutableMapping[str, int] = dict(initial)
    words = decode_words(machine_code_hex)
    trace: List[Dict[str, Any]] = []
    halted = False

    for index, word in enumerate(words):
        if halted:
            raise ContractError("machine code contains words after RTS")
        if word == RTS_OPCODE:
            halted = True
            trace.append({"pc_word": index, "opcode": f"{word:04x}", "operation": "RTS"})
            continue
        if word & MOVEQ_MASK == MOVEQ_OPCODE:
            register_index = (word >> 9) & 0x7
            immediate = word & 0xFF
            if immediate & 0x80:
                immediate -= 0x100
            register = f"D{register_index}"
            registers[register] = immediate
            trace.append(
                {
                    "pc_word": index,
                    "opcode": f"{word:04x}",
                    "operation": "MOVEQ",
                    "register": register,
                    "value": immediate,
                }
            )
            continue
        raise ContractError(f"unsupported M68000 opcode {word:04x} at word {index}")

    if not halted:
        raise ContractError("M68000 capsule did not terminate with RTS")

    return {
        "kind": "REFERENCE_INTERPRETER_ONLY",
        "initial_registers": initial,
        "final_registers": dict(registers),
        "trace": trace,
        "physical_execution_observed": False,
    }


def validate_contract(contract: Mapping[str, Any]) -> Dict[str, Any]:
    if contract.get("schema") != SCHEMA:
        raise ContractError(f"schema must be {SCHEMA}")
    if contract.get("status") != STATUS:
        raise ContractError(f"status must remain {STATUS}")

    literal = _mapping(contract.get("literal_claims"), "literal_claims")
    if literal.get("architecture_label") != "2-3-8-3":
        raise ContractError("architecture label must remain 2-3-8-3")
    if literal.get("ring_count") != 3:
        raise ContractError("the unresolved contract must retain three structural rings")
    if literal.get("binary_alphabet_cardinality") != 2:
        raise ContractError("binary alphabet cardinality must be two")

    actual_arithmetic = verified_arithmetic()
    declared_arithmetic = _mapping(contract.get("verified_arithmetic"), "verified_arithmetic")
    if dict(declared_arithmetic) != actual_arithmetic:
        raise ContractError(
            "verified_arithmetic must equal 2^3=8, 2^8=256, and 8^3=512"
        )
    if actual_arithmetic["eight_pow_three"] == 256:
        raise ContractError("impossible arithmetic branch accepted: 8^3 cannot equal 256")

    blocked = _sequence(contract.get("blocked_equivalences"), "blocked_equivalences")
    blockers = {
        item.get("blocker")
        for item in blocked
        if isinstance(item, Mapping) and isinstance(item.get("blocker"), str)
    }
    required_blockers = {
        "ARITHMETIC_CONTRADICTION",
        "CARDINALITY_WIDTH_CONFLATION",
        "VIRTUAL_NOT_PHYSICAL",
        "MODEL_NOT_EFFECT",
    }
    missing_blockers = sorted(required_blockers - blockers)
    if missing_blockers:
        raise ContractError(f"missing fail-closed blockers: {missing_blockers}")

    resolutions = _sequence(contract.get("owner_resolution_required"), "owner_resolution_required")
    resolution_ids = {
        item.get("id") for item in resolutions if isinstance(item, Mapping) and item.get("id")
    }
    if resolution_ids != {"R1_256_RELATION", "R2_FINAL_THREE"}:
        raise ContractError("both exact owner resolutions must remain open")

    witness = _mapping(contract.get("m68000_witness"), "m68000_witness")
    if witness.get("kind") != "REFERENCE_INTERPRETER_ONLY":
        raise ContractError("M68000 witness must remain reference-interpreter-only")
    machine = emulate_m68000_capsule(str(witness.get("machine_code_hex_big_endian", "")))

    tuple_values = list(_sequence(witness.get("tuple"), "m68000_witness.tuple"))
    tuple_registers = list(
        _sequence(witness.get("tuple_registers"), "m68000_witness.tuple_registers")
    )
    if tuple_values != [2, 3, 8, 3] or tuple_registers != ["D4", "D5", "D6", "D7"]:
        raise ContractError("M68000 witness must bind 2-3-8-3 to D4-D7")
    observed_tuple = [machine["final_registers"][register] for register in tuple_registers]
    if observed_tuple != tuple_values:
        raise ContractError("M68000 reference interpreter did not materialize 2-3-8-3")

    preserved = list(
        _sequence(witness.get("preserved_registers"), "m68000_witness.preserved_registers")
    )
    if preserved != ["D0", "D1", "D2", "D3"]:
        raise ContractError("D0-D3 preservation contract changed")
    for register in preserved:
        if machine["final_registers"][register] != machine["initial_registers"][register]:
            raise ContractError(f"M68000 witness mutated reserved register {register}")
    _require_false(
        witness,
        ["physical_m68000_execution_observed", "hatari_execution_observed"],
        "m68000_witness",
    )

    boundaries = _mapping(contract.get("proof_boundaries"), "proof_boundaries")
    if boundaries.get("formal_arithmetic_checked") is not True:
        raise ContractError("formal arithmetic must be checked")
    if boundaries.get("virtual_m68000_capsule_checked") is not True:
        raise ContractError("virtual M68000 capsule must be checked")
    _require_false(
        boundaries,
        [
            "architecture_semantics_resolved",
            "physical_m68000_execution_observed",
            "quantum_computation_observed",
            "empirical_physics_claimed",
        ],
        "proof_boundaries",
    )

    closure = _mapping(contract.get("closure"), "closure")
    _require_false(closure, ["pass", "final_pass", "merge_claimed", "effect_ack_done"], "closure")

    return {
        "schema": SCHEMA,
        "status": STATUS,
        "verified_arithmetic": actual_arithmetic,
        "first_deterministic_blocker": "ARITHMETIC_CONTRADICTION",
        "blockers": sorted(blockers),
        "owner_resolution_required": sorted(str(value) for value in resolution_ids),
        "m68000_witness": {
            "kind": machine["kind"],
            "machine_code_hex_big_endian": witness["machine_code_hex_big_endian"],
            "tuple_registers": tuple_registers,
            "tuple": observed_tuple,
            "preserved_registers": preserved,
            "physical_execution_observed": False,
        },
        "pass": False,
        "final_pass": False,
        "effect_ack_done": False,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=default_spec_path())
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = validate_contract(load_contract(args.spec))
    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
