from tools.temdd_language import (
    DONE,
    HOLD_ACTUAL_STATE_UNCOVERED,
    HOLD_AUTHORITY_REQUIRED,
    HOLD_EVIDENCE_INCONSISTENT,
    HOLD_HARD_OBLIGATION,
    HOLD_REQUIREMENT_NOT_ESTABLISHED,
    HOLD_SUBJECT_UNBOUND,
    HOLD_UNVERIFIED,
    CompletionEvidence,
    after_mutation,
    evaluate_completion,
    requirement_transition_allowed,
)


def complete(**overrides):
    values = {
        "knowledge_region_nonempty": True,
        "knowledge_subset_goal": True,
        "exact_subject_bound": True,
        "actual_covered": True,
        "unresolved_hard_obligation": False,
        "authorized_completion": True,
    }
    values.update(overrides)
    return CompletionEvidence(**values)


def test_authorized_alternative_solution_can_be_done():
    assert evaluate_completion(complete()) == DONE


def test_green_checks_wrong_subject_must_not_done():
    assert evaluate_completion(complete(exact_subject_bound=False)) == HOLD_SUBJECT_UNBOUND


def test_stale_receipt_after_mutation_must_not_done():
    assert after_mutation(DONE) == HOLD_UNVERIFIED


def test_empty_or_contradictory_evidence_must_not_done():
    assert (
        evaluate_completion(complete(knowledge_region_nonempty=False))
        == HOLD_EVIDENCE_INCONSISTENT
    )


def test_knowledge_region_with_counterexample_must_not_done():
    assert (
        evaluate_completion(complete(knowledge_subset_goal=False))
        == HOLD_REQUIREMENT_NOT_ESTABLISHED
    )


def test_actual_state_outside_evidence_must_not_done():
    assert evaluate_completion(complete(actual_covered=False)) == HOLD_ACTUAL_STATE_UNCOVERED


def test_unresolved_hard_obligation_must_not_done():
    assert (
        evaluate_completion(complete(unresolved_hard_obligation=True))
        == HOLD_HARD_OBLIGATION
    )


def test_missing_completion_authority_must_not_done():
    assert (
        evaluate_completion(complete(authorized_completion=False))
        == HOLD_AUTHORITY_REQUIRED
    )


def test_unauthorized_requirement_change_must_not_be_adopted():
    assert not requirement_transition_allowed(unchanged=False, explicitly_authorized=False)


def test_explicit_authority_can_adopt_requirement_change():
    assert requirement_transition_allowed(unchanged=False, explicitly_authorized=True)


def test_unchanged_requirement_needs_no_mutation_authority():
    assert requirement_transition_allowed(unchanged=True, explicitly_authorized=False)
