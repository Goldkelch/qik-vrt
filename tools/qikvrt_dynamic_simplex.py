#!/usr/bin/env python3
"""Deterministic moving-target simplex-style optimizer for QIK-VRT.

A snapshot defines a finite admissible vertex set and a linear objective. The
optimizer never treats sequence as causality and never carries a decision across
snapshot drift. It emits one of NOOP, HOLD, REOBSERVE, or PIVOT.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ACTIONS = {"NOOP", "HOLD", "REOBSERVE", "PIVOT"}


def canonical_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    from_vertex: str | None
    to_vertex: str | None
    objective_before: float | None
    objective_after: float | None
    snapshot_digest: str

    def as_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _validate(snapshot: dict[str, Any]) -> None:
    required = {"schema", "target_generation", "observed_generation", "objective", "current_vertex", "vertices", "edges"}
    if set(snapshot) != required:
        raise ValueError("non-canonical snapshot fields")
    if snapshot["schema"] != "qikvrt_dynamic_simplex_snapshot_v1":
        raise ValueError("unsupported snapshot schema")
    objective = snapshot["objective"]
    if not isinstance(objective, dict) or not objective or not all(isinstance(k, str) and isinstance(v, (int, float)) for k, v in objective.items()):
        raise ValueError("invalid objective")
    vertices = snapshot["vertices"]
    if not isinstance(vertices, dict) or not vertices:
        raise ValueError("vertices absent")
    if snapshot["current_vertex"] not in vertices:
        raise ValueError("current vertex absent")
    dims = set(objective)
    for name, vertex in vertices.items():
        if not isinstance(name, str) or not isinstance(vertex, dict):
            raise ValueError("invalid vertex")
        if set(vertex) != {"metrics", "feasible", "evidence_bound"}:
            raise ValueError("non-canonical vertex")
        if set(vertex["metrics"]) != dims or not all(isinstance(x, (int, float)) for x in vertex["metrics"].values()):
            raise ValueError("metric mismatch")
        if not isinstance(vertex["feasible"], bool) or not isinstance(vertex["evidence_bound"], bool):
            raise ValueError("invalid guards")
    edges = snapshot["edges"]
    if not isinstance(edges, list):
        raise ValueError("invalid edges")
    for edge in edges:
        if not isinstance(edge, list) or len(edge) != 2 or edge[0] not in vertices or edge[1] not in vertices:
            raise ValueError("invalid edge")


def score(snapshot: dict[str, Any], vertex_name: str) -> float:
    weights = snapshot["objective"]
    metrics = snapshot["vertices"][vertex_name]["metrics"]
    return float(sum(float(weights[k]) * float(metrics[k]) for k in weights))


def decide(snapshot: dict[str, Any]) -> Decision:
    _validate(snapshot)
    digest = canonical_digest(snapshot)
    current = snapshot["current_vertex"]
    if snapshot["target_generation"] != snapshot["observed_generation"]:
        return Decision("REOBSERVE", "MOVING_TARGET_DRIFT", current, None, score(snapshot, current), None, digest)
    cur = snapshot["vertices"][current]
    if not cur["evidence_bound"]:
        return Decision("HOLD", "CURRENT_VERTEX_EVIDENCE_UNBOUND", current, None, score(snapshot, current), None, digest)
    neighbors = sorted({b if a == current else a for a, b in snapshot["edges"] if a == current or b == current})
    admissible = [n for n in neighbors if snapshot["vertices"][n]["feasible"] and snapshot["vertices"][n]["evidence_bound"]]
    before = score(snapshot, current)
    improving = [(score(snapshot, n), n) for n in admissible if score(snapshot, n) < before]
    if not improving:
        return Decision("NOOP", "LOCAL_EVIDENCE_BOUND_FIXPOINT", current, current, before, before, digest)
    after, target = min(improving, key=lambda item: (item[0], item[1]))
    return Decision("PIVOT", "STRICT_OBJECTIVE_IMPROVEMENT", current, target, before, after, digest)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    print(json.dumps(decide(snapshot).as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
