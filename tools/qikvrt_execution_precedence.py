# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
"""Fail-closed verifier for QIK-VRT execution precedence.

The execution relation is a strict partial order. Unspecified relations are not
interpreted heuristically: they remain HOLD_UNVERIFIED unless independence is
explicitly declared after a common barrier.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


class PrecedenceError(ValueError):
    pass


def load_policy(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PrecedenceError("policy must be a JSON object")
    validate_policy(value)
    return value


def validate_policy(policy: Mapping[str, Any]) -> None:
    if policy.get("schema") != "qikvrt_execution_precedence_v1":
        raise PrecedenceError("unexpected schema")
    semantics = policy.get("semantics")
    if not isinstance(semantics, Mapping):
        raise PrecedenceError("semantics missing")
    if semantics.get("relation_type") != "strict_partial_order":
        raise PrecedenceError("execution relation must be strict_partial_order")
    if semantics.get("unspecified_relation") != "HOLD_UNVERIFIED":
        raise PrecedenceError("unspecified relation must fail closed")
    if semantics.get("predecessor_evidence_transfer") is not False:
        raise PrecedenceError("predecessor evidence transfer must be false")

    spine = policy.get("canonical_spine")
    phases = policy.get("phases")
    if not isinstance(spine, list) or not spine or len(spine) != len(set(spine)):
        raise PrecedenceError("canonical_spine must contain unique nodes")
    if not isinstance(phases, Mapping) or any(node not in phases for node in spine):
        raise PrecedenceError("every spine node must be declared")

    known = set(phases)
    edges: set[tuple[str, str]] = set()
    for node, spec in phases.items():
        if not isinstance(spec, Mapping):
            raise PrecedenceError(f"{node}: invalid phase")
        requires = spec.get("requires")
        if not isinstance(requires, list):
            raise PrecedenceError(f"{node}: requires must be list")
        for predecessor in requires:
            if predecessor not in known:
                raise PrecedenceError(f"{node}: unknown predecessor {predecessor}")
            if predecessor == node:
                raise PrecedenceError(f"{node}: self-edge forbidden")
            edges.add((predecessor, node))

    # Kahn topological check: any cycle makes the control relation unusable.
    incoming = {node: 0 for node in known}
    outgoing = {node: [] for node in known}
    for a, b in edges:
        outgoing[a].append(b)
        incoming[b] += 1
    ready = [node for node, degree in incoming.items() if degree == 0]
    visited = 0
    while ready:
        node = ready.pop()
        visited += 1
        for successor in outgoing[node]:
            incoming[successor] -= 1
            if incoming[successor] == 0:
                ready.append(successor)
    if visited != len(known):
        raise PrecedenceError("precedence graph contains a cycle")

    fanout = policy.get("external_fanout")
    if not isinstance(fanout, Mapping):
        raise PrecedenceError("external_fanout missing")
    barrier = fanout.get("barrier")
    if barrier not in known:
        raise PrecedenceError("fanout barrier must be a declared phase")
    if fanout.get("cross_edge_order") != "NONE_AFTER_COMMON_BARRIER":
        raise PrecedenceError("external edges must declare independence explicitly")
    fanout_edges = fanout.get("edges")
    if not isinstance(fanout_edges, Mapping) or not fanout_edges:
        raise PrecedenceError("external fanout edges missing")
    for ident, spec in fanout_edges.items():
        if not isinstance(spec, Mapping) or spec.get("requires") != [barrier]:
            raise PrecedenceError(f"{ident}: must depend exactly on common barrier")


def next_eligible(policy: Mapping[str, Any], states: Mapping[str, str]) -> dict[str, Any]:
    """Return exact eligible nodes from declared predecessor state only.

    SATISFIED is the only predecessor value that opens a successor. Unknown,
    absent, stale, failed or unbound predecessors fail closed.
    """
    validate_policy(policy)
    phases = policy["phases"]
    eligible: list[str] = []
    blocked: dict[str, list[str]] = {}

    for node in policy["canonical_spine"]:
        state = states.get(node, "UNKNOWN")
        if state == "SATISFIED":
            continue
        predecessors = phases[node]["requires"]
        unsatisfied = [p for p in predecessors if states.get(p) != "SATISFIED"]
        if unsatisfied:
            blocked[node] = unsatisfied
        else:
            eligible.append(node)
            # The canonical spine has one next causal node. Do not skip ahead.
            break

    fanout = policy["external_fanout"]
    barrier = fanout["barrier"]
    if states.get(barrier) == "SATISFIED":
        for node in fanout["edges"]:
            if states.get(node) != "SATISFIED":
                eligible.append(node)

    return {
        "schema": "qikvrt_execution_precedence_disposition_v1",
        "eligible": eligible,
        "blocked": blocked,
        "hold_unverified": not bool(eligible),
    }
