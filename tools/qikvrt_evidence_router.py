#!/usr/bin/env python3
"""Pure fail-closed routing core for addressable QIK-VRT evidence relations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, order=True)
class Relation:
    source: str
    target: str
    receipt: str
    exact_subject: str
    provenance: str
    cost: int = 1
    observed: bool = False
    valid: bool = False
    proved: bool = False

    def __post_init__(self) -> None:
        if not all((self.source, self.target, self.receipt, self.exact_subject, self.provenance)):
            raise ValueError("ADDRESSABLE_PROVENANCE_REQUIRED")
        if self.cost < 0:
            raise ValueError("NONNEGATIVE_COST_REQUIRED")


@dataclass(frozen=True)
class CandidateRoute:
    nodes: tuple[str, ...]
    receipts: tuple[str, ...]
    cost: int


@dataclass(frozen=True)
class AdmissibleRoute:
    candidate: CandidateRoute
    exact_subjects: tuple[str, ...]
    provenance: tuple[str, ...]


def candidate_route(a_to_b: Relation, b_to_c: Relation) -> CandidateRoute:
    if a_to_b.target != b_to_c.source:
        raise ValueError("RELATIONS_NOT_COMPOSABLE")
    return CandidateRoute(
        nodes=(a_to_b.source, a_to_b.target, b_to_c.target),
        receipts=(a_to_b.receipt, b_to_c.receipt),
        cost=a_to_b.cost + b_to_c.cost,
    )


def validate_candidate(candidate: CandidateRoute, relations: Iterable[Relation]) -> AdmissibleRoute:
    by_receipt = {relation.receipt: relation for relation in relations}
    if len(by_receipt) != len(tuple(relations)):
        raise ValueError("RECEIPT_IDENTITY_AMBIGUOUS")
    selected = []
    for receipt in candidate.receipts:
        relation = by_receipt.get(receipt)
        if relation is None:
            raise ValueError("REQUIRED_RELATION_MISSING")
        if not relation.observed:
            raise ValueError("REQUIRED_RELATION_NOT_FRESHLY_OBSERVED")
        if not relation.valid:
            raise ValueError("REQUIRED_RELATION_NOT_CURRENTLY_VALID")
        if not relation.proved:
            raise ValueError("REQUIRED_RELATION_NOT_PROVED")
        selected.append(relation)
    nodes = tuple([selected[0].source] + [relation.target for relation in selected]) if selected else ()
    if nodes != candidate.nodes:
        raise ValueError("CANDIDATE_SUBJECT_DRIFT")
    return AdmissibleRoute(
        candidate=candidate,
        exact_subjects=tuple(relation.exact_subject for relation in selected),
        provenance=tuple(relation.provenance for relation in selected),
    )


def evidence_transitive(*_relations: Relation) -> bool:
    """Evidence transitivity is intentionally never inferred."""
    return False


def best_admissible_route(candidates: Iterable[CandidateRoute], relations: Iterable[Relation]) -> AdmissibleRoute:
    relations = tuple(relations)
    admissible = []
    for candidate in candidates:
        try:
            admissible.append(validate_candidate(candidate, relations))
        except ValueError:
            continue
    if not admissible:
        raise ValueError("NO_ADMISSIBLE_ROUTE")
    return min(admissible, key=lambda route: (route.candidate.cost, route.candidate.nodes, route.candidate.receipts))
