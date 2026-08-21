# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Executable PO-Receipt #245 seven-stage safety contract.

This is deliberately small and stdlib-only.  It proves the finite control
property over every combination of the six productive-effect gates and executes
one bounded in-memory witness.  The in-memory effect is not an external effect.
"""
from __future__ import annotations

import argparse
import itertools
import json
from dataclasses import dataclass, replace as dataclass_replace
from enum import IntEnum
from typing import Any


STAGES = (
    "MATCH",
    "PARSE",
    "BIND",
    "BEWEIS",
    "ENTSCHEIDE",
    "MACH",
    "SCHAU_NACH",
)


class Decision(IntEnum):
    NOOP = 0
    HOLD = 1
    REOBSERVE = 2
    REQUEST_AUTHORITY = 3


@dataclass(frozen=True)
class Gates:
    match_ok: bool
    parse_ok: bool
    bind_ok: bool
    evidence_ok: bool
    authorized_decision: bool
    invariant_safe: bool

    @classmethod
    def all_open(cls) -> "Gates":
        return cls(True, True, True, True, True, True)

    def replace(self, **changes: bool) -> "Gates":
        return dataclass_replace(self, **changes)


@dataclass(frozen=True)
class State:
    quality: int
    stone3: str
    logical_time: int


@dataclass(frozen=True)
class RunResult:
    stages: tuple[str, ...]
    decision: Decision | None
    executed: bool
    reobserved: bool
    improved: bool
    verified_improvement: bool
    before: State
    after: State

    def as_dict(self) -> dict[str, Any]:
        return {
            "stages": list(self.stages),
            "decision": self.decision.name if self.decision is not None else "GO",
            "d0": int(self.decision) if self.decision is not None else None,
            "executed": self.executed,
            "reobserved": self.reobserved,
            "improved": self.improved,
            "verified_improvement": self.verified_improvement,
            "before": {
                "quality": self.before.quality,
                "stone3": self.before.stone3,
                "logical_time": self.before.logical_time,
            },
            "after": {
                "quality": self.after.quality,
                "stone3": self.after.stone3,
                "logical_time": self.after.logical_time,
            },
        }


def _blocked_decision(gates: Gates) -> Decision | None:
    if not gates.match_ok:
        return Decision.HOLD
    if not gates.parse_ok:
        return Decision.HOLD
    if not gates.bind_ok:
        return Decision.HOLD
    if not gates.evidence_ok:
        return Decision.REOBSERVE
    if not gates.authorized_decision:
        return Decision.REQUEST_AUTHORITY
    if not gates.invariant_safe:
        return Decision.HOLD
    return None


def run(gates: Gates, *, observed_quality: int) -> RunResult:
    """Execute the bounded local witness and then reobserve it.

    Productive execution occurs iff all six gates are true.  Stone 3 is a
    literal protected invariant.  A later logical time is not sufficient for
    improvement: the reobserved quality must strictly increase.
    """
    before = State(quality=1, stone3="STONE_3", logical_time=0)
    blocked = _blocked_decision(gates)
    if blocked is not None:
        return RunResult(
            stages=("MATCH", "PARSE", "BIND", "BEWEIS", "ENTSCHEIDE"),
            decision=blocked,
            executed=False,
            reobserved=False,
            improved=False,
            verified_improvement=False,
            before=before,
            after=before,
        )

    # MACH: bounded local state transition.  The protected token is copied,
    # never synthesized or rewritten.
    executed_state = State(
        quality=observed_quality,
        stone3=before.stone3,
        logical_time=before.logical_time + 1,
    )

    # SCHAU NACH: compare the actually observed post-state with the bound
    # predecessor.  Execution itself never implies success.
    invariant_preserved = executed_state.stone3 == before.stone3
    improved = executed_state.quality > before.quality
    verified = invariant_preserved and improved
    return RunResult(
        stages=STAGES,
        decision=None,
        executed=True,
        reobserved=True,
        improved=improved,
        verified_improvement=verified,
        before=before,
        after=executed_state,
    )


def run_positive_witness() -> RunResult:
    return run(Gates.all_open(), observed_quality=2)


def prove_contract(*, source_head: str | None = None, source_tree: str | None = None) -> dict[str, Any]:
    """Exhaustively prove the finite gate implication and execute one witness."""
    names = (
        "match_ok",
        "parse_ok",
        "bind_ok",
        "evidence_ok",
        "authorized_decision",
        "invariant_safe",
    )
    blocked = 0
    productive = 0
    invariant_preserved = True
    counterexamples: list[dict[str, Any]] = []

    for values in itertools.product((False, True), repeat=len(names)):
        gates = Gates(**dict(zip(names, values, strict=True)))
        result = run(gates, observed_quality=2)
        all_open = all(values)
        if result.executed:
            productive += 1
        else:
            blocked += 1
        invariant_preserved = invariant_preserved and (
            result.before.stone3 == result.after.stone3
        )
        if result.executed != all_open:
            counterexamples.append({"gates": dict(zip(names, values, strict=True)), "result": result.as_dict()})

    positive = run_positive_witness()
    no_improvement = run(Gates.all_open(), observed_quality=1)
    receipt: dict[str, Any] = {
        "schema": "qikvrt_iedl_seven_stage_machine_proof_v1",
        "po_receipt": 245,
        "source_head": source_head,
        "source_tree": source_tree,
        "contract": list(STAGES),
        "gate_combinations_checked": 64,
        "blocked_combinations": blocked,
        "productive_combinations": productive,
        "counterexamples": counterexamples,
        "productive_effect_iff_all_six_gates": not counterexamples,
        "protected_invariant_preserved": invariant_preserved,
        "positive_witness": positive.as_dict(),
        "MACH_IMPLIES_SUCCESS": False,
        "LATER_IMPLIES_BETTER": False,
        "execution_without_observed_improvement": no_improvement.as_dict(),
        "external_effect": "NONE",
        "PASS": False,
        "FINAL_PASS": False,
        "EFFECT_ACK_DONE": False,
    }
    if blocked != 63 or productive != 1 or counterexamples:
        raise RuntimeError("IEDL finite gate proof failed")
    if not positive.verified_improvement:
        raise RuntimeError("IEDL positive witness failed")
    if no_improvement.verified_improvement:
        raise RuntimeError("IEDL execution was incorrectly promoted to success")
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prove",))
    parser.add_argument("--source-head")
    parser.add_argument("--source-tree")
    parser.add_argument("--output")
    args = parser.parse_args(argv)

    receipt = prove_contract(source_head=args.source_head, source_tree=args.source_tree)
    rendered = json.dumps(receipt, sort_keys=True, indent=2) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
