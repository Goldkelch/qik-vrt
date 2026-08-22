#!/usr/bin/env python3
"""Executable D3 ring-lifecycle model with host and M68000-lowering equivalence.

Truth boundaries:
- D3 0->1 activates one virtual work ring.
- D3 1->0 quiesces that ring after result collection, persistence, and release.
- QUIESCENCE != FAILURE != GLOBAL_HALT.
- 2^8 == 256 is byte-state cardinality; RING_2=256 bits is an independent
  virtual architecture rule.
- M68000 lowering is executed by a bounded reference interpreter only and is
  not physical Motorola 68000 execution.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import Iterable, Sequence

MOVEQ_MASK = 0xF100
MOVEQ_OPCODE = 0x7000
RTS_OPCODE = 0x4E75
D3 = 3


class LifecycleError(ValueError):
    pass


class Phase(str, Enum):
    QUIESCENT = "QUIESCENT"
    ACTIVE = "ACTIVE"


@dataclass(frozen=True)
class Event:
    operation: str
    d3_before: int
    d3_after: int
    ring: int


@dataclass
class Machine:
    d3: int = 0
    phase: Phase = Phase.QUIESCENT
    active_ring: int = 0
    result_collected: bool = False
    persisted: bool = False
    resources_released: bool = True
    global_halt: bool = False
    owner_interrupt: bool = False

    def activate(self, ring: int) -> Event:
        if self.phase is not Phase.QUIESCENT or self.d3 != 0:
            raise LifecycleError("activation requires D3=0 QUIESCENT")
        if ring < 1:
            raise LifecycleError("ring index must be positive")
        before = self.d3
        self.d3 = 1
        self.phase = Phase.ACTIVE
        self.active_ring = ring
        self.result_collected = False
        self.persisted = False
        self.resources_released = False
        return Event("ACTIVATE", before, self.d3, ring)

    def collect_result(self) -> Event:
        self._require_active("result collection")
        self.result_collected = True
        return Event("COLLECT_RESULT", self.d3, self.d3, self.active_ring)

    def persist(self) -> Event:
        self._require_active("persistence")
        if not self.result_collected:
            raise LifecycleError("persistence requires collected result")
        self.persisted = True
        return Event("PERSIST", self.d3, self.d3, self.active_ring)

    def release_resources(self) -> Event:
        self._require_active("resource release")
        if not self.persisted:
            raise LifecycleError("resource release requires persistence")
        self.resources_released = True
        return Event("RELEASE_RESOURCES", self.d3, self.d3, self.active_ring)

    def quiesce(self) -> Event:
        self._require_active("quiescence")
        if not (self.result_collected and self.persisted and self.resources_released):
            raise LifecycleError("quiescence requires collect -> persist -> release")
        before = self.d3
        ring = self.active_ring
        self.d3 = 0
        self.phase = Phase.QUIESCENT
        self.active_ring = 0
        return Event("QUIESCE", before, self.d3, ring)

    def _require_active(self, operation: str) -> None:
        if self.phase is not Phase.ACTIVE or self.d3 != 1:
            raise LifecycleError(f"{operation} requires D3=1 ACTIVE")


def ring_width_bits(ring: int) -> int:
    """Return virtual width for the bound first three rings.

    RING_1 = 2^3 = 8 bits.
    RING_2 = 256 bits by explicit virtual architecture rule.
    RING_3 = 256^3 bits by explicit recursive architecture rule.
    """
    if ring == 1:
        return 2**3
    if ring == 2:
        return 256
    if ring == 3:
        return 256**3
    raise LifecycleError("only bound rings 1..3 have exact widths")


def byte_state_cardinality() -> int:
    return 2**8


def reference_run(rings: Iterable[int] = (1, 2, 3)) -> dict:
    machine = Machine()
    events: list[Event] = []
    widths: list[int] = []
    for ring in rings:
        widths.append(ring_width_bits(ring))
        events.append(machine.activate(ring))
        events.append(machine.collect_result())
        events.append(machine.persist())
        events.append(machine.release_resources())
        events.append(machine.quiesce())
    return {
        "backend": "PYTHON_REFERENCE_MODEL",
        "events": [asdict(event) for event in events],
        "ring_width_bits": widths,
        "byte_state_cardinality": byte_state_cardinality(),
        "final": machine_snapshot(machine),
        "claims": claims(),
    }


def machine_snapshot(machine: Machine) -> dict:
    return {
        "d3": machine.d3,
        "phase": machine.phase.value,
        "active_ring": machine.active_ring,
        "result_collected": machine.result_collected,
        "persisted": machine.persisted,
        "resources_released": machine.resources_released,
        "global_halt": machine.global_halt,
        "owner_interrupt": machine.owner_interrupt,
    }


def claims() -> dict:
    return {
        "QUIESCENCE_EQUALS_FAILURE": False,
        "QUIESCENCE_EQUALS_GLOBAL_HALT": False,
        "D3_ZERO_REQUIRES_OWNER_INTERRUPT": False,
        "BYTE_256_STATES_EQUALS_256_BITS": False,
        "PHYSICAL_M68000_EXECUTION_OBSERVED": False,
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
    }


def moveq(register: int, immediate: int) -> int:
    if not 0 <= register <= 7:
        raise LifecycleError("MOVEQ register out of range")
    if not -128 <= immediate <= 127:
        raise LifecycleError("MOVEQ immediate out of range")
    return MOVEQ_OPCODE | (register << 9) | (immediate & 0xFF)


def lower_d3_lifecycle_to_m68000(rings: Sequence[int] = (1, 2, 3)) -> bytes:
    """Lower the D3 activation/quiescence boundary to executable M68000 words.

    Per ring, MOVEQ #1,D3 represents ACTIVATE and MOVEQ #0,D3 represents
    QUIESCE. Collection/persistence/release are repository/host side effects and
    remain explicit preconditions of QUIESCE, not fabricated M68000 effects.
    """
    words: list[int] = []
    for ring in rings:
        ring_width_bits(ring)  # fail closed if unbound
        words.extend((moveq(D3, 1), moveq(D3, 0)))
    words.append(RTS_OPCODE)
    return b"".join(word.to_bytes(2, "big") for word in words)


def execute_m68000_lifecycle(payload: bytes) -> dict:
    if not payload or len(payload) % 2:
        raise LifecycleError("M68000 payload must contain complete words")
    d3 = 0
    transitions: list[dict] = []
    halted = False
    ring = 1
    expecting_activation = True
    for pc in range(0, len(payload), 2):
        word = int.from_bytes(payload[pc:pc+2], "big")
        if halted:
            raise LifecycleError("words after RTS")
        if word == RTS_OPCODE:
            if not expecting_activation:
                raise LifecycleError("RTS while ring remains active")
            halted = True
            continue
        if word & MOVEQ_MASK != MOVEQ_OPCODE:
            raise LifecycleError(f"unsupported M68000 word {word:04x}")
        register = (word >> 9) & 7
        immediate = word & 0xFF
        if immediate & 0x80:
            immediate -= 256
        if register != D3 or immediate not in (0, 1):
            raise LifecycleError("lowering may only MOVEQ #0/#1,D3")
        before = d3
        if expecting_activation:
            if immediate != 1 or d3 != 0:
                raise LifecycleError("expected D3 0->1 activation")
            operation = "ACTIVATE"
            d3 = 1
            expecting_activation = False
        else:
            if immediate != 0 or d3 != 1:
                raise LifecycleError("expected D3 1->0 quiescence")
            operation = "QUIESCE"
            d3 = 0
            expecting_activation = True
        transitions.append({
            "operation": operation,
            "d3_before": before,
            "d3_after": d3,
            "ring": ring,
        })
        if operation == "QUIESCE":
            ring += 1
    if not halted:
        raise LifecycleError("M68000 lifecycle did not terminate with RTS")
    return {
        "backend": "M68000_REFERENCE_INTERPRETER",
        "machine_code_hex_big_endian": payload.hex(),
        "transitions": transitions,
        "final_d3": d3,
        "physical_execution_observed": False,
    }


def lifecycle_boundary(events: Sequence[dict]) -> list[dict]:
    return [event for event in events if event["operation"] in ("ACTIVATE", "QUIESCE")]


def equivalence_report() -> dict:
    reference = reference_run()
    lowered = execute_m68000_lifecycle(lower_d3_lifecycle_to_m68000())
    reference_boundary = lifecycle_boundary(reference["events"])
    equivalent = reference_boundary == lowered["transitions"]
    if not equivalent:
        raise LifecycleError("reference and M68000 lifecycle boundaries diverged")
    return {
        "schema": "QIKVRT_D3_RING_LIFECYCLE_EQUIVALENCE_V1",
        "reference_backend": reference["backend"],
        "m68000_backend": lowered["backend"],
        "equivalent_boundary": equivalent,
        "reference_boundary": reference_boundary,
        "m68000_machine_code_hex_big_endian": lowered["machine_code_hex_big_endian"],
        "ring_width_bits": reference["ring_width_bits"],
        "byte_state_cardinality": reference["byte_state_cardinality"],
        "final_d3": reference["final"]["d3"],
        "claims": claims(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    value = equivalence_report()
    print(json.dumps(value, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
