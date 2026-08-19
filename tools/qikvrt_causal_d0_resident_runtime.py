#!/usr/bin/env python3
"""Resident event-driven runtime for the QIK-VRT Causal D0 ABI.

The runtime blocks on events; HOLD never means busy polling.  It is deliberately
transport-neutral: stdin JSONL is the first terminal adapter, while the causal
classification and D0 ABI remain reusable by native backends.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import IO, Iterable

NOOP = 0
HOLD = 1
REOBSERVE = 2
REQUEST_AUTHORITY = 3

STATE_NAMES = {
    NOOP: "NOOP",
    HOLD: "HOLD",
    REOBSERVE: "REOBSERVE",
    REQUEST_AUTHORITY: "REQUEST_AUTHORITY",
}


@dataclass(frozen=True)
class Decision:
    d0: int
    state: str
    reason: str

    def as_dict(self) -> dict[str, object]:
        return {"d0": self.d0, "state": self.state, "reason": self.reason}


def classify(event: dict[str, object]) -> Decision:
    """Lower one observed event into the four-state causal ABI."""
    if event.get("authority_required") is True and event.get("authority_bound") is not True:
        return Decision(REQUEST_AUTHORITY, STATE_NAMES[REQUEST_AUTHORITY], "AUTHORITY_NOT_BOUND")
    if event.get("evidence_stale") is True or event.get("new_evidence") is True:
        return Decision(REOBSERVE, STATE_NAMES[REOBSERVE], "EVIDENCE_REOBSERVATION_REQUIRED")
    if event.get("prerequisite_missing") is True or event.get("work_active") is True:
        return Decision(HOLD, STATE_NAMES[HOLD], "WAIT_FOR_CAUSALLY_RELEVANT_EVENT")
    return Decision(NOOP, STATE_NAMES[NOOP], "STATE_CONSISTENT")


def productive_effect_allowed(decision: Decision, effect_ack: str | None) -> bool:
    return decision.d0 == NOOP and effect_ack == "DONE"


def process_events(lines: Iterable[str], output: IO[str]) -> int:
    """Block in the caller's iterator and process exactly one transition per event."""
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        event = json.loads(raw)
        if not isinstance(event, dict):
            raise ValueError("event must be a JSON object")
        decision = classify(event)
        receipt = {
            "event": event,
            "decision": decision.as_dict(),
            "productive_effect_allowed": productive_effect_allowed(
                decision, event.get("effect_ack") if isinstance(event.get("effect_ack"), str) else None
            ),
        }
        output.write(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
        output.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="process one JSON event and exit")
    args = parser.parse_args(argv)
    if args.once:
        line = sys.stdin.readline()
        return process_events([line], sys.stdout)
    # Resident mode: readline blocks until an event arrives. No timer and no busy loop.
    return process_events(sys.stdin, sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
