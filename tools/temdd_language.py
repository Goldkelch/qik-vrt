from __future__ import annotations

from dataclasses import dataclass


DONE = "DONE"
HOLD_EVIDENCE_INCONSISTENT = "HOLD_EVIDENCE_INCONSISTENT"
HOLD_SUBJECT_UNBOUND = "HOLD_SUBJECT_UNBOUND"
HOLD_ACTUAL_STATE_UNCOVERED = "HOLD_ACTUAL_STATE_UNCOVERED"
HOLD_REQUIREMENT_NOT_ESTABLISHED = "HOLD_REQUIREMENT_NOT_ESTABLISHED"
HOLD_HARD_OBLIGATION = "HOLD_HARD_OBLIGATION"
HOLD_AUTHORITY_REQUIRED = "HOLD_AUTHORITY_REQUIRED"
HOLD_UNVERIFIED = "HOLD_UNVERIFIED"


@dataclass(frozen=True)
class CompletionEvidence:
    knowledge_region_nonempty: bool
    knowledge_subset_goal: bool
    exact_subject_bound: bool
    actual_covered: bool
    unresolved_hard_obligation: bool = False
    authorized_completion: bool = True


def evaluate_completion(evidence: CompletionEvidence) -> str:
    """Evaluate the fail-closed TEMDD completion contract.

    The ordering is diagnostic only. `DONE` is returned exactly when all hard
    completion obligations hold. This function does not imply review approval,
    merge, publication, FINAL_PASS, empirical truth, or EFFECT_ACK_DONE.
    """
    if not evidence.knowledge_region_nonempty:
        return HOLD_EVIDENCE_INCONSISTENT
    if not evidence.exact_subject_bound:
        return HOLD_SUBJECT_UNBOUND
    if not evidence.actual_covered:
        return HOLD_ACTUAL_STATE_UNCOVERED
    if not evidence.knowledge_subset_goal:
        return HOLD_REQUIREMENT_NOT_ESTABLISHED
    if evidence.unresolved_hard_obligation:
        return HOLD_HARD_OBLIGATION
    if not evidence.authorized_completion:
        return HOLD_AUTHORITY_REQUIRED
    return DONE


def after_mutation(previous_status: str) -> str:
    """Every mutation invalidates previous completion evidence."""
    del previous_status
    return HOLD_UNVERIFIED


def requirement_transition_allowed(*, unchanged: bool, explicitly_authorized: bool) -> bool:
    """A requirement may remain unchanged or change only with explicit authority."""
    return unchanged or explicitly_authorized
