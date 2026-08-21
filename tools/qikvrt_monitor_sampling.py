#!/usr/bin/env python3
"""QIK-VRT universal monitor sampling admission.

Nyquist/Shannon is applied only when a finite maximum material-transition
frequency is explicitly bound. Unknown/unbounded sources require event-driven
observation or fail closed. Sampling order never establishes causality/effect.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class SamplingDecision:
    mode: str
    source_max_hz: float | None
    sample_hz: float | None
    guard_factor: float
    minimum_hz: float | None
    nyquist_boundary_hz: float | None
    admitted: bool
    completeness_claim_allowed: bool
    disposition: str


def evaluate(*, source_max_hz: float | None, sample_hz: float | None,
             event_driven: bool, guard_factor: float = 2.5) -> SamplingDecision:
    if not math.isfinite(guard_factor) or guard_factor < 2.0:
        raise ValueError("guard_factor must be finite and >= 2")
    if source_max_hz is not None and (not math.isfinite(source_max_hz) or source_max_hz <= 0):
        raise ValueError("source_max_hz must be finite and > 0")
    if sample_hz is not None and (not math.isfinite(sample_hz) or sample_hz <= 0):
        raise ValueError("sample_hz must be finite and > 0")

    if source_max_hz is None:
        if event_driven:
            return SamplingDecision("EVENT_DRIVEN", None, sample_hz, guard_factor, None, None,
                                    True, False, "EVENT_DRIVEN_BOUND_UNKNOWN_GAP_REOBSERVE_REQUIRED")
        return SamplingDecision("POLLING", None, sample_hz, guard_factor, None, None,
                                False, False, "HOLD_SAMPLING_BOUND_UNKNOWN")

    boundary = 2.0 * source_max_hz
    minimum = guard_factor * source_max_hz
    if event_driven:
        return SamplingDecision("EVENT_DRIVEN", source_max_hz, sample_hz, guard_factor, minimum, boundary,
                                True, False, "EVENT_DRIVEN_PRIMARY_POLLING_OPTIONAL")
    if sample_hz is None:
        return SamplingDecision("POLLING", source_max_hz, None, guard_factor, minimum, boundary,
                                False, False, "HOLD_SAMPLE_RATE_MISSING")
    if sample_hz < boundary:
        return SamplingDecision("POLLING", source_max_hz, sample_hz, guard_factor, minimum, boundary,
                                False, False, "HOLD_BELOW_NYQUIST")
    if sample_hz < minimum:
        return SamplingDecision("POLLING", source_max_hz, sample_hz, guard_factor, minimum, boundary,
                                True, True, "NYQUIST_BOUNDARY_MET_GUARD_MARGIN_NOT_MET")
    return SamplingDecision("POLLING", source_max_hz, sample_hz, guard_factor, minimum, boundary,
                            True, True, "ADMITTED_WITH_GUARD_MARGIN")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-max-hz", type=float)
    p.add_argument("--sample-hz", type=float)
    p.add_argument("--event-driven", action="store_true")
    p.add_argument("--guard-factor", type=float, default=2.5)
    args = p.parse_args()
    try:
        result = evaluate(source_max_hz=args.source_max_hz, sample_hz=args.sample_hz,
                          event_driven=args.event_driven, guard_factor=args.guard_factor)
    except ValueError as exc:
        print(json.dumps({"admitted": False, "disposition": "HOLD_INVALID_SAMPLING_MODEL", "error": str(exc)}))
        return 2
    print(json.dumps(asdict(result), sort_keys=True))
    return 0 if result.admitted else 2


if __name__ == "__main__":
    raise SystemExit(main())
