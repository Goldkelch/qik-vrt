# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Validate a QIK-VRT numeric contract and execute its exact MAC reference."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "examples/numeric_contract_int8_mac_v1.json"


class ContractError(ValueError):
    """A numeric contract is incomplete, inconsistent, or violated."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ContractError(message)


def read_contract(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "contract must contain one JSON object")
    return value


def canonical_payload(contract: dict[str, Any]) -> bytes:
    payload = dict(contract)
    payload.pop("numeric_contract_digest", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def contract_digest(contract: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_payload(contract)).hexdigest()


def signed_bounds(width: int) -> tuple[int, int]:
    require(width >= 2, "signed width must be at least two bits")
    return -(1 << (width - 1)), (1 << (width - 1)) - 1


def validate(contract: dict[str, Any]) -> dict[str, Any]:
    require(contract.get("schema") == "qikvrt.numeric-contract.v1", "schema drifted")
    domain = contract["domain"]
    width = domain["operand_width_bits"]
    low, high = signed_bounds(width)
    require(domain == {"signed": True, "operand_width_bits": width, "minimum_integer": low, "maximum_integer": high}, "domain is not the complete signed integer range")
    require(contract["operations"] == ["multiply", "accumulate"], "operation order drifted")
    require(contract["absolute_error_limit"] == "0", "exact accumulator requires zero error")
    require(contract["overflow"] == "trap", "only fail-closed overflow is admitted")
    require(contract["rounding"] in {"nearest_even", "toward_zero"}, "rounding rule unsupported")
    scale = contract["scale_plan"]
    require(scale["accumulator_fraction_bits"] == 2 * scale["operand_fraction_bits"], "product scale is inconsistent")
    plan = contract["accumulation_plan"]
    require(plan["round_once"] is True, "intermediate rounding is forbidden")
    acc_low, acc_high = signed_bounds(plan["accumulator_width_bits"])
    worst_product = max(abs(low * low), abs(low * high), abs(high * high))
    require(plan["maximum_terms"] * worst_product <= acc_high, "declared maximum_terms can overflow")
    boundary = contract["claim_boundary"]
    for name in ("synthesis_observed", "physical_hardware_execution_observed", "performance_superiority_observed"):
        require(boundary[name] is False, f"unsupported claim broadened: {name}")
    observed = contract.get("numeric_contract_digest")
    expected = contract_digest(contract)
    require(observed == expected, f"numeric_contract_digest mismatch: expected {expected}")
    return {"schema": "qikvrt.numeric-contract-validation.v1", "numeric_contract_digest": expected, "state": "OBSERVE", "claims": boundary}


def exact_mac(pairs: Iterable[tuple[int, int]], *, operand_width: int, accumulator_width: int) -> int:
    operand_low, operand_high = signed_bounds(operand_width)
    accumulator_low, accumulator_high = signed_bounds(accumulator_width)
    total = 0
    for index, (left, right) in enumerate(pairs):
        require(operand_low <= left <= operand_high, f"left operand out of range at term {index}")
        require(operand_low <= right <= operand_high, f"right operand out of range at term {index}")
        candidate = total + left * right
        require(accumulator_low <= candidate <= accumulator_high, f"accumulator overflow at term {index}")
        total = candidate
    return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "digest", "mac"))
    parser.add_argument("--contract", type=pathlib.Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--pairs", default="[]", help="JSON array of [left,right] integer pairs")
    args = parser.parse_args(argv)
    contract = read_contract(args.contract)
    if args.command == "digest":
        print(contract_digest(contract))
        return 0
    report = validate(contract)
    if args.command == "validate":
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    pairs = json.loads(args.pairs)
    require(isinstance(pairs, list), "pairs must be a JSON array")
    result = exact_mac(
        [(int(item[0]), int(item[1])) for item in pairs],
        operand_width=contract["domain"]["operand_width_bits"],
        accumulator_width=contract["accumulation_plan"]["accumulator_width_bits"],
    )
    print(json.dumps({"accumulator_integer": result, "fraction_bits": contract["scale_plan"]["accumulator_fraction_bits"], "numeric_contract_digest": report["numeric_contract_digest"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
