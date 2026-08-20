#!/usr/bin/env python3
"""QIK-VRT bounded dynamic-simplex repository optimizer.

This module does not implement the textbook linear-programming simplex method.
It implements the repository-specific "dynamic simplex" defined by
state/autonomy/DYNAMIC_SIMPLEX_OPTIMIZER_V1.json: a finite set of admissible
repository moves (vertices) is filtered by hard invariants and ranked by a
lexicographic objective vector. At most one move is selected per cycle.

The optimizer emits a plan/receipt only. It never implies review authority,
merge, publication, EFFECT_ACK_DONE, or any external effect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from typing import Any, Iterable

OBJECTIVE_ORDER = (
    "correctness_defects",
    "unsafe_authority_or_effect_inference",
    "self_continuation_liveness_gap",
    "exact_head_integrity_gap",
    "activity_without_effect",
    "deterministic_latency_or_resource_waste",
    "avoidable_complexity",
    "testability_observability_durability_gap",
    "publication_opportunity_gap",
)

D0_NOOP = 0
D0_HOLD = 1
D0_REOBSERVE = 2
D0_REQUEST_AUTHORITY = 3

D0_NAMES = {
    D0_NOOP: "NOOP",
    D0_HOLD: "HOLD",
    D0_REOBSERVE: "REOBSERVE",
    D0_REQUEST_AUTHORITY: "REQUEST_AUTHORITY",
}

CAUSAL_FINGERPRINT_FIELDS = (
    "binding",
    "stage_states",
    "first_blocker",
    "next_effect",
    "role_local_state",
)


@dataclass(frozen=True)
class Vertex:
    move_id: str
    delta: tuple[int, ...]
    constraints: dict[str, bool]
    requires_authority: bool
    metadata: dict[str, Any]

    @classmethod
    def from_obj(cls, obj: dict[str, Any]) -> "Vertex":
        move_id = obj.get("id")
        if not isinstance(move_id, str) or not move_id:
            raise ValueError("candidate id must be a non-empty string")
        raw_delta = obj.get("delta")
        if not isinstance(raw_delta, dict):
            raise ValueError(f"candidate {move_id}: delta must be an object")
        delta: list[int] = []
        for key in OBJECTIVE_ORDER:
            value = raw_delta.get(key, 0)
            if not isinstance(value, int):
                raise ValueError(f"candidate {move_id}: delta[{key}] must be int")
            delta.append(value)
        constraints = obj.get("constraints", {})
        if not isinstance(constraints, dict) or any(not isinstance(v, bool) for v in constraints.values()):
            raise ValueError(f"candidate {move_id}: constraints must map names to booleans")
        requires_authority = obj.get("requires_authority", False)
        if not isinstance(requires_authority, bool):
            raise ValueError(f"candidate {move_id}: requires_authority must be bool")
        metadata = obj.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError(f"candidate {move_id}: metadata must be an object")
        return cls(move_id, tuple(delta), dict(constraints), requires_authority, dict(metadata))


def causal_fingerprint(state: dict[str, Any]) -> str:
    """Hash only causally relevant fields; activity-only fields are excluded."""
    bound = {key: state.get(key) for key in CAUSAL_FINGERPRINT_FIELDS}
    payload = json.dumps(bound, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def lexicographically_improves(delta: tuple[int, ...]) -> bool:
    """True iff first non-zero objective delta is negative."""
    for value in delta:
        if value < 0:
            return True
        if value > 0:
            return False
    return False


def admissible(vertex: Vertex) -> bool:
    return all(vertex.constraints.values())


def choose_vertex(candidates: Iterable[Vertex]) -> Vertex | None:
    viable = [v for v in candidates if admissible(v) and lexicographically_improves(v.delta)]
    if not viable:
        return None
    return min(viable, key=lambda v: (v.delta, v.move_id))


def publication_worthy(record: dict[str, Any]) -> bool:
    required_true = (
        "novel_result_or_reusable_method",
        "exact_repository_provenance",
        "reproducible_evidence",
        "explicit_formal_empirical_interpretive_boundaries",
        "archival_package_with_checksums_and_metadata",
    )
    if any(record.get(key) is not True for key in required_true):
        return False
    blockers = record.get("claim_affecting_correctness_blockers", [])
    return isinstance(blockers, list) and len(blockers) == 0


def decide(state: dict[str, Any]) -> dict[str, Any]:
    if state.get("observation_stale") is True:
        return receipt(state, D0_REOBSERVE, "OBSERVATION_STALE", None)

    raw_candidates = state.get("candidates", [])
    if not isinstance(raw_candidates, list):
        raise ValueError("candidates must be an array")
    candidates = [Vertex.from_obj(obj) for obj in raw_candidates]
    selected = choose_vertex(candidates)

    if selected is None:
        return receipt(state, D0_NOOP, "NO_ADMISSIBLE_CAUSAL_IMPROVEMENT", None)

    authority_bound = state.get("authority_bound", False)
    if selected.requires_authority and authority_bound is not True:
        return receipt(state, D0_REQUEST_AUTHORITY, "BEST_MOVE_REQUIRES_AUTHORITY", selected)

    if state.get("active_work") is True or state.get("external_prerequisite_missing") is True:
        return receipt(state, D0_HOLD, "CAUSALLY_RELEVANT_PREREQUISITE_PENDING", selected)

    # A safe bounded move has been selected, but the optimizer itself is not the
    # effect executor. HOLD makes the handoff explicit until an executor consumes
    # the plan and a later cycle reobserves the resulting state.
    return receipt(state, D0_HOLD, "BOUNDED_MOVE_SELECTED_EXECUTION_PENDING", selected)


def receipt(state: dict[str, Any], d0: int, reason: str, selected: Vertex | None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": "qikvrt.dynamic-simplex-receipt.v1",
        "causal_fingerprint": causal_fingerprint(state),
        "d0": d0,
        "state": D0_NAMES[d0],
        "reason": reason,
        "selected_move": None,
        "optimizer_effect_ack": False,
        "independent_review_authority_implied": False,
        "publication_effect_implied": False,
    }
    if selected is not None:
        result["selected_move"] = {
            "id": selected.move_id,
            "delta": {key: selected.delta[i] for i, key in enumerate(OBJECTIVE_ORDER)},
            "requires_authority": selected.requires_authority,
            "metadata": selected.metadata,
        }
    publication = state.get("publication")
    if isinstance(publication, dict):
        result["publication_worthy"] = publication_worthy(publication)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", help="JSON state file; stdin when omitted")
    args = parser.parse_args(argv)
    if args.path:
        with open(args.path, "r", encoding="utf-8") as fh:
            state = json.load(fh)
    else:
        state = json.load(sys.stdin)
    if not isinstance(state, dict):
        raise ValueError("optimizer state must be a JSON object")
    json.dump(decide(state), sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
