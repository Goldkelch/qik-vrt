"""Repository-native recursive evidence routing core.

Routing knowledge may shorten discovery, never proof.  This module deliberately
contains no network/model dependency: callers supply live reobservation and
validation functions and persist returned receipts in the repository-native
ledger.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from heapq import heappop, heappush
from typing import Callable, Iterable, Mapping, Sequence


class Validity(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    UNBOUND = "UNBOUND"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class Subject:
    node: str
    head: str
    tree: str


@dataclass(frozen=True)
class EvidenceEdge:
    source: Subject
    target: Subject
    scope: str
    provenance: tuple[str, ...]
    observed_at: str
    validity: Validity
    proof_receipt: str | None = None
    superseded_by: str | None = None
    latency: float = 1.0
    computation: float = 1.0
    stale_risk: float = 0.0

    @property
    def admissible_hint(self) -> bool:
        return (
            self.validity is Validity.VALID
            and bool(self.provenance)
            and bool(self.source.head and self.source.tree)
            and bool(self.target.head and self.target.tree)
            and self.superseded_by is None
        )


@dataclass(frozen=True)
class RouteReceipt:
    requested_scope: str
    path: tuple[EvidenceEdge, ...]
    freshly_validated: bool
    provenance_chain: tuple[str, ...]


class NoAdmissibleRoute(RuntimeError):
    pass


Reobserve = Callable[[EvidenceEdge], EvidenceEdge]
Validate = Callable[[EvidenceEdge], bool]


@dataclass
class RecursiveEvidenceRouter:
    edges: list[EvidenceEdge] = field(default_factory=list)

    def learn(self, delta: Iterable[EvidenceEdge]) -> None:
        """Append evidence; never delete historical edges."""
        self.edges.extend(delta)

    def candidate_route(self, source: Subject, target: Subject, scope: str) -> tuple[EvidenceEdge, ...]:
        """Find a cheap candidate. Candidate routing is not evidence admission."""
        adjacency: dict[Subject, list[EvidenceEdge]] = {}
        for edge in self.edges:
            if edge.scope == scope and edge.admissible_hint:
                adjacency.setdefault(edge.source, []).append(edge)

        queue: list[tuple[float, int, Subject, tuple[EvidenceEdge, ...]]] = []
        serial = 0
        heappush(queue, (0.0, serial, source, ()))
        best: dict[Subject, float] = {source: 0.0}
        while queue:
            cost, _, node, path = heappop(queue)
            if node == target:
                return path
            if cost > best.get(node, float("inf")):
                continue
            for edge in adjacency.get(node, ()):
                new_cost = cost + edge.latency + edge.computation + edge.stale_risk
                if new_cost < best.get(edge.target, float("inf")):
                    best[edge.target] = new_cost
                    serial += 1
                    heappush(queue, (new_cost, serial, edge.target, path + (edge,)))
        raise NoAdmissibleRoute(f"no candidate route for scope={scope!r}")

    def traverse(
        self,
        source: Subject,
        target: Subject,
        scope: str,
        *,
        reobserve: Reobserve,
        validate: Validate,
    ) -> RouteReceipt:
        """Freshly reobserve every selected edge; fail closed on any drift."""
        candidate = self.candidate_route(source, target, scope)
        fresh: list[EvidenceEdge] = []
        provenance: list[str] = []
        expected_source = source
        for cached in candidate:
            observed = reobserve(cached)
            if observed.source != expected_source:
                raise NoAdmissibleRoute("subject-chain drift")
            if observed.validity is not Validity.VALID or observed.superseded_by is not None:
                raise NoAdmissibleRoute(f"non-current edge: {observed.validity}")
            if not validate(observed):
                raise NoAdmissibleRoute("proof/provenance validation failed")
            fresh.append(observed)
            provenance.extend(observed.provenance)
            expected_source = observed.target
        if expected_source != target:
            raise NoAdmissibleRoute("target binding drift")
        return RouteReceipt(scope, tuple(fresh), True, tuple(provenance))
