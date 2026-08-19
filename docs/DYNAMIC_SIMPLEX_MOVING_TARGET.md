# QIK-VRT Dynamic Simplex for a Moving Target

This work unit introduces a bounded optimization primitive for dynamic, self-reflective repository state.

The classical simplex intuition is retained only at the level that is useful here: an explicitly materialized feasible region is represented by vertices and adjacency edges, a linear objective is evaluated, and a deterministic pivot is permitted only to an adjacent feasible vertex with strict improvement. QIK-VRT adds the moving-target boundary: every decision is bound to one observed target generation and becomes invalid when that target drifts.

```text
OBSERVE
→ BIND SNAPSHOT
→ EVALUATE FEASIBLE ADJACENT VERTICES
→ PIVOT / NOOP / HOLD / REOBSERVE
→ separately authorized execution
→ EFFECT REOBSERVATION
→ NEW SNAPSHOT
→ REAPPLICATION
```

The algorithm therefore never equates an optimization recommendation with execution authority. `PIVOT` means that the bound snapshot contains a uniquely selected improving move under the declared objective; it does not mean that an external effect has happened. `REOBSERVE` means that the optimization target has moved since the currently bound observation. `HOLD` is fail-closed when evidence is incomplete. `NOOP` is the local evidence-bound fixpoint.

## Why this is useful

A repository mesh, runtime, compiler, terminal or distributed system is not a static optimization tableau. The act of executing work changes the next admissible state. Consequently, optimization must be iterative and reflexive rather than a one-shot minimization.

The intended QIK-VRT pattern is:

- freeze enough state to make one decision reproducible;
- optimize only within that bound snapshot;
- keep causally independent evaluation parallel;
- perform effects only through their separate authority boundary;
- reobserve after the effect;
- rebuild the optimization problem from the new state;
- stop when no justified strict improvement remains.

This is the technical form of the "photograph and darkroom" analogy: the world is not stopped; a bounded representation is developed, used, and then checked again against the world that continued to move.

## Scientific boundary

This component is a deterministic software optimization policy. It does not establish claims about thermodynamics, quantum gravity, information-energy equivalence, or physical cosmology. Those connections may motivate separate research hypotheses, but require their own formal and empirical evidence.

## Repository invariants

`Kausalitaet != Sequenz`  
`REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED`  
`TRANSPORT_ACK != EFFECT_ACK`  
`Identitaet != Gleichheit`  
`Integration != Einebnung`  
`Regeneration != Kopie`

Authority and Mirror may evaluate the same canonical optimizer while preserving distinct role-local state. Whole-tree equality is not required for role correctness.
