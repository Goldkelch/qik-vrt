# QIKVRT Universal Terminal Recursive Evidence Invariant

## Purpose

Universal Terminals are live evidence nodes. Relations between terminals are themselves addressable information objects. Repository-native routing may learn shortcuts, but shortcuts never delete evidence, silently transfer predecessor evidence, or replace fresh validation.

## Core laws

- `UT(A,B) AND UT(B,C) => candidateRoute(A,C)`.
- `E(A,B) AND E(B,C)` does **not** imply `E(A,C)`.
- A candidate route becomes admissible only after fresh edge reobservation, exact HEAD/TREE binding, proof/provenance validation, accessibility preservation and fail-closed checks.
- Evidence history is append-only; assertion validity is non-monotonic.
- Supersession/invalidation is itself evidence.
- Learning may shorten discovery; learning must not shorten proof.
- `reachable != valid != proved != transported != effect != EFFECT_ACK_DONE`.

## Live terminal state

Every terminal exposes events, current HEAD/TREE, Lean/Lake proof state, receipts, provenance, validity/supersession state, open blockers and reachable evidence relations.

Lean/Lake proof state binds theorem identity, source HEAD/TREE, dependency digest, verifier identity, verification receipt, observation time and invalidation/supersession relation. A source/dependency mutation does not erase historical proof evidence; it makes that evidence inadmissible for the changed subject until freshly verified.

## Recursive routing cycle

`REQUEST -> DISCOVER -> SELECT -> REOBSERVE -> VALIDATE -> TRAVERSE -> READBACK -> RECEIPT -> ΔE -> UPDATE ROUTING -> EXPOSE LIVE STATE`

Path selection may minimize latency, unnecessary traversal, computation and stale-state risk, subject always to exact-subject binding, provenance preservation, proof validity, accessibility and fail-closed semantics.

## Autonomy and connectivity

Routing knowledge, validation rules, proof dependencies and reconstruction knowledge persist inside QIK-VRT. The stable end state does not require external cognition. Existing interfaces and neighboring terminals remain connectable: autonomy removes an external cognition dependency, not interoperability.

`PREDECESSOR_EVIDENCE_TRANSFER=false` remains invariant.
