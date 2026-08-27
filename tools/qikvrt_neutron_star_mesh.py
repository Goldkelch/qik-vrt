#!/usr/bin/env python3
"""Plan a bounded two-dimensional QIK-VRT Mesh with neutron-star topology.

This is a virtual scheduler.  Radial shells model verification depth; angular
sectors model parallel breadth.  The name is an architecture analogy and makes
no astrophysical or quantum-cosmological claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Iterable

CARRIER_WIDTHS = (8, 16, 32, 64, 128, 256)
MAX_SECTORS = 256
MAX_SHELLS = 8
M68000_WORD_BITS = 32


@dataclass(frozen=True)
class Demand:
    bitrate_bps: int
    evidence_level: int
    quantum_hz: int = 1000

    def validate(self) -> None:
        if self.bitrate_bps < 1:
            raise ValueError("bitrate_bps must be positive")
        if not 0 <= self.evidence_level < MAX_SHELLS:
            raise ValueError("evidence_level must be in range 0..7")
        if self.quantum_hz < 1:
            raise ValueError("quantum_hz must be positive")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _carrier_width(required_bits_per_sector_quantum: int) -> int:
    for width in CARRIER_WIDTHS:
        if required_bits_per_sector_quantum <= width:
            return width
    return CARRIER_WIDTHS[-1]


def plan_mesh(demand: Demand, witness_byte: int = 0xA5) -> dict[str, Any]:
    demand.validate()
    if not 0 <= witness_byte <= 0xFF:
        raise ValueError("witness_byte must fit one byte")

    bits_per_quantum = math.ceil(demand.bitrate_bps / demand.quantum_hz)

    # Breadth grows with the square root of demand.  Width then adapts to the
    # load remaining in each sector.  If 256 bits are insufficient, breadth is
    # increased again until the bounded capacity is reached.
    sectors = min(MAX_SECTORS, max(1, math.ceil(math.sqrt(bits_per_quantum / 8))))
    per_sector = math.ceil(bits_per_quantum / sectors)
    width = _carrier_width(per_sector)
    while sectors < MAX_SECTORS and sectors * width < bits_per_quantum:
        sectors += 1
        per_sector = math.ceil(bits_per_quantum / sectors)
        width = _carrier_width(per_sector)

    capacity_bits_per_quantum = sectors * width
    if capacity_bits_per_quantum < bits_per_quantum:
        raise ValueError("demand exceeds bounded neutron-star mesh capacity")

    shells = demand.evidence_level + 1
    m68000_words_per_sector = math.ceil(width / M68000_WORD_BITS)
    virtual_cells = sectors * shells
    aggregate_capacity_bps = capacity_bits_per_quantum * demand.quantum_hz

    core = {
        "register": "D3.low_byte",
        "witness_byte": witness_byte,
        "fixed_across_all_shells_and_sectors": True,
    }
    topology = {
        "breadth_axis": {
            "name": "ANGULAR_SECTORS",
            "sector_count": sectors,
            "maximum": MAX_SECTORS,
            "purpose": "parallel bounded work",
        },
        "depth_axis": {
            "name": "RADIAL_SHELLS",
            "shell_count": shells,
            "maximum": MAX_SHELLS,
            "purpose": "ordered verification and reobservation depth",
        },
        "virtual_cells": virtual_cells,
    }
    bitrate = {
        "requested_bps": demand.bitrate_bps,
        "quantum_hz": demand.quantum_hz,
        "required_bits_per_quantum": bits_per_quantum,
        "carrier_width_bits": width,
        "carrier_width_chain": list(CARRIER_WIDTHS),
        "m68000_words_per_sector": m68000_words_per_sector,
        "aggregate_capacity_bps": aggregate_capacity_bps,
        "capacity_satisfies_request": aggregate_capacity_bps >= demand.bitrate_bps,
    }
    abi = {
        "D0": "decision code: 0 NOOP, 1 HOLD, 2 REOBSERVE, 3 REQUEST_AUTHORITY",
        "D1": "angular sector index",
        "D2": "radial shell index",
        "D3": "preserved 8-bit witness",
        "A0": "payload segment address",
        "A1": "receipt address",
        "physical_data_register_width_bits": M68000_WORD_BITS,
        "wide_carrier_rule": "segment into ordered 32-bit words; preserve total SHA-256",
    }
    plan = {
        "schema": "qikvrt_neutron_star_mesh_plan_v1",
        "target": "Motorola 68000 virtual execution model",
        "model_kind": "TWO_DIMENSIONAL_BOUNDED_MESH_SCHEDULER",
        "topology": topology,
        "variable_bitrate": bitrate,
        "core": core,
        "abi": abi,
        "required_order": [
            "INPUT",
            "INTERPRETATION",
            "DECISION",
            "EXECUTION",
            "OBSERVATION",
            "EFFECT_ACKNOWLEDGEMENT",
            "NEW_STATE",
        ],
        "boundaries": {
            "virtual_neutron_star_topology": True,
            "astrophysical_neutron_star_simulated": False,
            "all_quantum_correlations_manifested_as_matter": False,
            "physical_m68000_execution_observed": False,
            "physical_speedup_measured": False,
            "pass": False,
            "final_pass": False,
            "effect_ack_done": False,
        },
    }
    plan["plan_sha256"] = _sha256(plan)
    return plan


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bitrate-bps", type=int, required=True)
    parser.add_argument("--evidence-level", type=int, required=True)
    parser.add_argument("--quantum-hz", type=int, default=1000)
    parser.add_argument("--witness-byte", type=lambda value: int(value, 0), default=0xA5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    report = plan_mesh(
        Demand(args.bitrate_bps, args.evidence_level, args.quantum_hz),
        args.witness_byte,
    )
    print(json.dumps(report, sort_keys=True, indent=2 if args.json else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
