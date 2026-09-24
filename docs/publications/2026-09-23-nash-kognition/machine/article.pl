% qikvrt_nash_cognition_article_v1
author('Ingolf Lohmann').
publication_id(qikvrt_nash_cognition_local_stability_v1).
canonical_language(de).
date_published('2026-09-23').

not_implies(local_stability, global_correctness).
not_equals(local_effect_ack_done, universal_effect_ack_done).
not_equals(unchanged, done).
not_equals(experience, interpretation).
not_equals(interpretation, empirically_confirmed_external_effect).

deadlock_or_equilibrium_diagnosis :-
    stable,
    work_remaining,
    \+ progress_edge.

search_for_missing_transition :-
    deadlock_or_equilibrium_diagnosis.

preserve_evidence_classes :-
    experience,
    unresolved_interpretation.

nash_relation(structural_analogy).
deadlock_is_nash_equilibrium(false).

runtime_order([compile,bind,resolve,execute,test,observe,readback,accept,effect_ack_done]).
