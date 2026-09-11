# TEMDD Language V1 — completion contract

**TEMDD** means **Tested Event Model Driven Development**.

The execution rule is:

`Request -> Execute -> Follow -> Learn -> Repeat Until Done`.

This document defines the first executable core of the TEMDD Language. It is
additive to the existing QIK-VRT control plane. It does not redefine workflow
success, review, merge, publication, `PASS`, `FINAL_PASS`, or
`EFFECT_ACK_DONE`.

## 1. Goal and knowledge regions

A requirement `R` denotes the admissible goal region:

`GR(R) = { s | s satisfies R }`.

Bound evidence `E` denotes the states still compatible with the observations:

`K(E) = { s | s is compatible with E }`.

Evidence is consistent when `K(E)` is nonempty.

## 2. Completion

For an exact subject, TEMDD V1 defines completion by four hard obligations:

1. `K(E)` is nonempty;
2. every state in `K(E)` is inside `GR(R)`;
3. the evidence is bound to exactly the subject for which completion is claimed;
4. the actual state is covered by `K(E)`.

In compact form:

`DONE(R,E,S) = Consistent(E) AND K(E) subset GR(R) AND Bound(E,S) AND ActualCovered(E,S)`.

The actual-state consequence is then sound:

`DONE(R,E,S) AND actual in K(E) => actual satisfies R`.

## 3. Fail-closed boundary

Evidence does not transfer by default. Any subject mutation invalidates the
previous completion evidence and returns the new subject to `HOLD_UNVERIFIED`.
This is the semantic reason for the already established QIK-VRT exact-head
reobservation boundary.

A green workflow on the wrong subject is therefore not `DONE`. A stale receipt
on a mutated subject is not `DONE`. Missing or contradictory evidence is not
success and is not silently treated as failure of the requirement itself; it is
a HOLD condition.

## 4. Requirement authority

`Learn` may improve the model and may discover that a requirement needs
refinement, but it may not silently weaken the success definition in order to
make completion true.

A requirement transition is admissible only when the requirement is unchanged
or an explicit authority authorizes the change.

This prevents an autonomous executor from proving its own success by changing
what success means after observing a failure.

## 5. Soundness versus liveness

This first kernel formalizes sound completion, not eventual completion.

`DONE => requirement satisfied` is a safety/soundness statement.

It does not prove that a valid target state is reachable or that repeated
Request/Execute/Follow/Learn steps will terminate. Reachability, fairness and
convergence remain separate liveness proof obligations.

Correct HOLD therefore remains distinct from progress and from eventual DONE.

## 6. Evidence classes remain separate

The language preserves the existing QIK-VRT evidence boundaries:

- formal proof is not a runtime observation;
- a deterministic test is not a formal proof;
- transport acknowledgement is not effect acknowledgement;
- sequence is not causality;
- intent is not authority;
- `PASS` is not `DONE`;
- `DONE` is not `FINAL_PASS`;
- `DONE` is not publication;
- `DONE` is not `EFFECT_ACK_DONE`.

No implicit evidence-class promotion is permitted.

## 7. Negative regressions

The V1 executable reference must fail closed for at least these cases:

- green checks on the wrong subject;
- stale evidence after mutation;
- empty or contradictory evidence;
- a knowledge region containing a counterexample outside the goal region;
- an actual state not covered by the evidence model;
- unresolved hard obligations;
- missing completion authority;
- unauthorized requirement mutation.

An alternative implementation is allowed to complete when all hard obligations
hold. TEMDD constrains the admissible result space; it does not prescribe one
unique implementation.

## 8. Formal surface

The Lean kernel is:

`formalization/QIKVRT_Formalization_v2.0/QIKVRTFormalization/TEMDD/Completion.lean`.

It formalizes the definitions and local theorems for consistency, soundness,
exact binding, actual-state coverage, mutation invalidation, requirement-change
authority and safe transitions.

The machine-readable policy is `policy/TEMDD_LANGUAGE_V1.json`. The Python
reference semantics are in `tools/temdd_language.py`, with negative regression
coverage in `tests/test_temdd_language.py`.

The presence of these files on a branch is not itself proof that `lake build`,
tests, repository integrity materialization, review or external effects have
succeeded. Those claims require fresh exact-subject evidence.

## 9. Normative principle

> Do not claim, decide, or act more strongly than exact-bound evidence supports.

This is the first executable TEMDD Language completion contract. Further
language layers may add richer event syntax, causal models, probabilistic risk,
proof/evidence typing and liveness calculus without weakening this boundary.
