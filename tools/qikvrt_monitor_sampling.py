#!/usr/bin/env python3
"""QIK-VRT universal monitor sampling admission and adaptive rate control.

Nyquist/Shannon is applied only when a finite maximum material-transition
frequency is explicitly bound. Unknown/unbounded sources require event-driven
observation or fail closed. Sampling order never establishes causality/effect.

The adaptive controller borrows the *rate-control principle* from variable-
bitrate codecs: allocate more observation/transport budget when the monitored
signal or medium becomes harder, and less when it becomes quiet/easy. It is not
a claim that monitor sampling is an audio codec.
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


@dataclass(frozen=True)
class AdaptiveRateDecision:
    sample_hz: float
    transport_units_per_second: float
    redundancy_factor: float
    degraded: bool
    disposition: str


def _unit_interval(value: float, label: str) -> float:
    if not math.isfinite(value) or value < 0.0 or value > 1.0:
        raise ValueError(f"{label} must be finite in [0,1]")
    return value


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


def adaptive_rate(*, source_max_hz: float, change_density: float, loss_rate: float,
                  jitter_pressure: float, latency_pressure: float,
                  evidence_criticality: float, channel_capacity_units_per_second: float,
                  guard_factor: float = 2.5) -> AdaptiveRateDecision:
    """Compute a deterministic adaptive observation/transport allocation.

    - `source_max_hz` binds the hard reconstruction floor.
    - `change_density` increases sampling pressure when material transitions cluster.
    - loss/jitter increase redundancy rather than silently reducing fidelity.
    - latency/evidence criticality increase observation pressure.
    - if channel capacity cannot sustain the resulting minimum, fail closed as
      a degraded monitor instead of pretending complete observation.
    """
    if not math.isfinite(source_max_hz) or source_max_hz <= 0:
        raise ValueError("source_max_hz must be finite and > 0")
    if not math.isfinite(channel_capacity_units_per_second) or channel_capacity_units_per_second <= 0:
        raise ValueError("channel_capacity_units_per_second must be finite and > 0")
    if not math.isfinite(guard_factor) or guard_factor < 2.0:
        raise ValueError("guard_factor must be finite and >= 2")

    change = _unit_interval(change_density, "change_density")
    loss = _unit_interval(loss_rate, "loss_rate")
    jitter = _unit_interval(jitter_pressure, "jitter_pressure")
    latency = _unit_interval(latency_pressure, "latency_pressure")
    criticality = _unit_interval(evidence_criticality, "evidence_criticality")

    nyquist_floor = 2.0 * source_max_hz
    guarded_floor = guard_factor * source_max_hz

    # Complexity pressure is bounded and monotone. It can increase allocation,
    # never relax the reconstruction floor.
    observation_pressure = 1.0 + 0.75 * change + 0.50 * latency + 0.75 * criticality
    requested_sample_hz = max(guarded_floor, nyquist_floor * observation_pressure)

    # Medium impairment is answered by redundancy/FEC/retransmission budget,
    # not by silently lowering observation rate. Bound amplification to 3x.
    redundancy = min(3.0, 1.0 + 1.5 * loss + 0.75 * jitter)
    transport = requested_sample_hz * redundancy

    if transport > channel_capacity_units_per_second:
        # Capacity shortage is explicit evidence degradation. Preserve the hard
        # observation floor if possible, but never claim completeness.
        sustainable_sample = channel_capacity_units_per_second / redundancy
        disposition = (
            "HOLD_CHANNEL_CAPACITY_BELOW_NYQUIST"
            if sustainable_sample < nyquist_floor
            else "DEGRADED_GUARD_MARGIN_NOT_SUSTAINABLE"
        )
        return AdaptiveRateDecision(
            sample_hz=sustainable_sample,
            transport_units_per_second=channel_capacity_units_per_second,
            redundancy_factor=redundancy,
            degraded=True,
            disposition=disposition,
        )

    return AdaptiveRateDecision(
        sample_hz=requested_sample_hz,
        transport_units_per_second=transport,
        redundancy_factor=redundancy,
        degraded=False,
        disposition="ADAPTIVE_RATE_ADMITTED",
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-max-hz", type=float)
    p.add_argument("--sample-hz", type=float)
    p.add_argument("--event-driven", action="store_true")
    p.add_argument("--guard-factor", type=float, default=2.5)
    p.add_argument("--adaptive", action="store_true")
    p.add_argument("--change-density", type=float, default=0.0)
    p.add_argument("--loss-rate", type=float, default=0.0)
    p.add_argument("--jitter-pressure", type=float, default=0.0)
    p.add_argument("--latency-pressure", type=float, default=0.0)
    p.add_argument("--evidence-criticality", type=float, default=0.0)
    p.add_argument("--channel-capacity", type=float)
    args = p.parse_args()
    try:
        if args.adaptive:
            if args.source_max_hz is None or args.channel_capacity is None:
                raise ValueError("adaptive mode requires --source-max-hz and --channel-capacity")
            result = adaptive_rate(
                source_max_hz=args.source_max_hz,
                change_density=args.change_density,
                loss_rate=args.loss_rate,
                jitter_pressure=args.jitter_pressure,
                latency_pressure=args.latency_pressure,
                evidence_criticality=args.evidence_criticality,
                channel_capacity_units_per_second=args.channel_capacity,
                guard_factor=args.guard_factor,
            )
            print(json.dumps(asdict(result), sort_keys=True))
            return 2 if result.degraded else 0
        result = evaluate(source_max_hz=args.source_max_hz, sample_hz=args.sample_hz,
                          event_driven=args.event_driven, guard_factor=args.guard_factor)
    except ValueError as exc:
        print(json.dumps({"admitted": False, "disposition": "HOLD_INVALID_SAMPLING_MODEL", "error": str(exc)}))
        return 2
    print(json.dumps(asdict(result), sort_keys=True))
    return 0 if result.admitted else 2


if __name__ == "__main__":
    raise SystemExit(main())
