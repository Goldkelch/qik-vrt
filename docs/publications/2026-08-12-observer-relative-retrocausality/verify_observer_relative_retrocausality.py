#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Copyright 2026 Ingolf Lohmann.
"""Check the finite QIK-VRT observer-relative retrocausality witness.

The checker proves no statement by naming it.  It evaluates the exact finite
witness used in the accompanying paper and fails unless every declared
predicate holds.  It uses only the Python standard library and performs no
network or external-system effect.
"""

from __future__ import annotations

import json
import math
from itertools import product


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def canonical_report() -> dict[str, object]:
    events = {
        "emit_old": 0,
        "emit_new": 1,
        "receive_new": 2,
        "receive_old": 3,
    }
    records = {
        "old": {
            "source_event": "emit_old",
            "source_mark": 10,
            "payload": 0,
            "receive_event": "receive_old",
            "observer_proper_time": 101,
        },
        "new": {
            "source_event": "emit_new",
            "source_mark": 20,
            "payload": 1,
            "receive_event": "receive_new",
            "observer_proper_time": 100,
        },
    }

    require(events["emit_old"] < events["emit_new"], "source order failed")
    require(
        events["emit_old"] < events["receive_old"],
        "old record was not emitted before reception",
    )
    require(
        events["emit_new"] < events["receive_new"],
        "new record was not emitted before reception",
    )
    require(
        events["receive_new"] < events["receive_old"],
        "reception did not overtake the source order",
    )

    first = records["new"]
    second = records["old"]
    delta_tau = second["observer_proper_time"] - first["observer_proper_time"]
    delta_theta = second["source_mark"] - first["source_mark"]
    information_slope = delta_theta / delta_tau
    require(delta_tau > 0, "observer proper time is not increasing")
    require(delta_theta < 0, "source-reference direction is not decreasing")
    require(information_slope < 0, "information-time slope is not negative")

    histories_before = list(product((0, 1), repeat=2))
    histories_after_new = [h for h in histories_before if h[1] == first["payload"]]
    histories_after_old = [h for h in histories_after_new if h[0] == second["payload"]]
    require(
        len(histories_after_new) < len(histories_before),
        "new record is not information-bearing",
    )
    require(
        len(histories_after_old) < len(histories_after_new),
        "old record is not information-bearing",
    )

    observer_o_prime = {
        "old_proper_time": 200,
        "new_proper_time": 201,
    }
    o_prime_delta_tau = (
        observer_o_prime["new_proper_time"] - observer_o_prime["old_proper_time"]
    )
    o_prime_delta_theta = records["new"]["source_mark"] - records["old"]["source_mark"]
    o_prime_slope = o_prime_delta_theta / o_prime_delta_tau
    require(o_prime_slope > 0, "second observer should see aligned ordering")

    # Units with c = 1: old emission t=0, path length=3; new emission t=1,
    # path length=1.  Both propagation durations are positive and the newer
    # record arrives at t=2 before the older record at t=3.
    physical = {
        "c": 1,
        "old_emission_time": 0,
        "new_emission_time": 1,
        "old_path_length": 3,
        "new_path_length": 1,
    }
    physical["old_arrival_time"] = (
        physical["old_emission_time"] + physical["old_path_length"] / physical["c"]
    )
    physical["new_arrival_time"] = (
        physical["new_emission_time"] + physical["new_path_length"] / physical["c"]
    )
    require(physical["old_path_length"] > 0, "old path is not future-directed")
    require(physical["new_path_length"] > 0, "new path is not future-directed")
    require(
        physical["new_arrival_time"] < physical["old_arrival_time"],
        "physical latency witness does not overtake",
    )

    # Complementary conditional fringes cancel in the unconditioned marginal.
    phase_samples = [0.0, math.pi / 4, math.pi / 2, math.pi, 3 * math.pi / 2]
    marginal_samples = []
    for phase in phase_samples:
        conditional_one = (1.0 + math.cos(phase)) / 2.0
        conditional_two = (1.0 - math.cos(phase)) / 2.0
        marginal = 0.5 * conditional_one + 0.5 * conditional_two
        require(math.isclose(marginal, 0.5, abs_tol=1e-12), "no-signalling marginal failed")
        marginal_samples.append(
            {
                "phase": phase,
                "conditional_one": conditional_one,
                "conditional_two": conditional_two,
                "unconditioned_marginal": marginal,
            }
        )

    return {
        "schema": "qikvrt_observer_relative_retrocausality_witness_v1",
        "result": "VERIFIED_FOR_DECLARED_OPERATIONAL_MODEL",
        "definition": {
            "retrograde": "observer proper time increases while bound source mark decreases",
            "ordinal_form": "receive(new) precedes receive(old) while source(old) precedes source(new)",
        },
        "host_event_order": events,
        "records": records,
        "observer_o": {
            "reception_sequence": ["new", "old"],
            "delta_proper_time": delta_tau,
            "delta_source_mark": delta_theta,
            "information_time_slope": information_slope,
            "retrograde": True,
        },
        "observer_o_prime": {
            "reception_sequence": ["old", "new"],
            "delta_proper_time": o_prime_delta_tau,
            "delta_source_mark": o_prime_delta_theta,
            "information_time_slope": o_prime_slope,
            "retrograde": False,
        },
        "information_fibres": {
            "before": histories_before,
            "after_new_record": histories_after_new,
            "after_old_record": histories_after_old,
            "strict_refinement_each_step": True,
        },
        "future_directed_physical_latency_witness": physical,
        "delayed_context_no_signalling_check": {
            "model": "equal mixture of complementary conditional fringes",
            "samples": marginal_samples,
            "local_marginal_constant": True,
        },
        "verified_predicates": [
            "HOST_ORDER_ACYCLIC",
            "EACH_SOURCE_PRECEDES_ITS_RECEPTION",
            "OBSERVER_PROPER_TIME_STRICTLY_INCREASES",
            "EACH_RECORD_STRICTLY_REFINES_ADMISSIBLE_HISTORIES",
            "RECEPTION_ORDER_INVERTS_BOUND_SOURCE_ORDER_FOR_OBSERVER_O",
            "INFORMATION_TIME_SLOPE_NEGATIVE_FOR_OBSERVER_O",
            "SECOND_OBSERVER_CAN_HAVE_POSITIVE_ORIENTATION",
            "PHYSICAL_PATH_DELAYS_POSITIVE_AND_OVERTAKING_REALIZED",
            "COMPLEMENTARY_CONDITIONAL_PATTERNS_CANCEL_IN_LOCAL_MARGINAL",
        ],
        "not_claimed": [
            "PROPER_TIME_RUNS_BACKWARD",
            "A_RECORD_IS_RECEIVED_BEFORE_ITS_EMISSION",
            "HOST_CAUSAL_LOOP_EXISTS",
            "PAST_RAW_RECORD_IS_OVERWRITTEN",
            "CONTROLLABLE_SIGNAL_TO_OWN_CAUSAL_PAST",
            "QIK_VRT_IS_UNIQUELY_SELECTED_BY_QUANTUM_EXPERIMENTS",
            "UNIVERSE_WIDE_CORRESPONDENCE_IS_PROVED_BY_THIS_FINITE_WITNESS",
        ],
    }


def main() -> int:
    print(json.dumps(canonical_report(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
