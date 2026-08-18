# Role-local identity and reflexive regeneration

QIK-VRT distinguishes shared canonical structure from role-local mutable state.

## Invariants

- `Kausalität ≠ Sequenz`.
- `Identität ≠ Gleichheit`.
- `Integration ≠ Einebnung`.
- `Regeneration ≠ Kopie`.
- `Evolution ≠ Wiederholung`.

Whole-tree equality is evidence about a bound pair of trees; it is not a requirement that future Authority and Mirror states remain byte-identical when their declared roles require different live state.

A regeneration pass MUST preserve every difference that is causally necessary for identity, role, liveness, authority, or function. It MAY normalize differences that are not semantically relevant, but MUST NOT erase role-local state merely to restore whole-tree equality.

The operational rule is:

> So much equality as required for interoperability; so much difference as necessary for identity, causality, and function.

## Authority and Mirror

Shared policy and reproducible source can be equal across Authority and Mirror. A Mirror registered as an active Mesh node can additionally require role-local liveness records. Those records are not evidence that the shared source contract has drifted; they are state required by the Mirror role.

Therefore:

`Shared(Authority) = Shared(Mirror)` may coexist with `Local(Authority) ≠ Local(Mirror)`.

A historical whole-tree equality receipt remains valid for the exact heads and trees to which it was bound. A later role-local divergence does not retroactively falsify it.

## Phoenix consequence

The Phoenix ash state must retain causally relevant identity differences. Regeneration reconstructs a valid next state from canonical evidence and role bindings; it does not clone one role over another. If a proposed regeneration would remove state that an active role contract requires, the cycle MUST `HOLD` or materialize the smallest authorized role-local repair rather than flattening the difference.
