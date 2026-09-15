# QIKVRT Evidence History / Current Validity Invariant V1

Status: FROZEN SEMANTIC INVARIANT

## Canonical rule

> Historische Evidenz darf bleiben. Aktuelle Gültigkeit muss immer wieder frisch verdient werden.

Formally:

```text
EVIDENCE_HISTORY      monotonic / append-preserved
CURRENT_VALIDITY      non-monotonic / requires fresh validation
PREDECESSOR_TRANSFER  forbidden
SUCCESS               != EFFECT
```

For repository evidence sets:

```text
E_(t+1) ⊇ E_t
```

This monotonicity applies to evidence history, not to truth or current admissibility.
An assertion, proof, receipt, review, relation or EFFECT_ACK remains historically
addressable after a later mutation, while its current status may become:

```text
CONFIRMED
STALE
REFUTED
SUPERSEDED
SCOPE_NARROWED
```

No historical witness may satisfy a missing predicate for a later exact subject.
For every new HEAD/TREE, current validity is earned by fresh subject-local
observation and validation.

## D.o.D. consequence

Historical witnesses may explain provenance and accelerate reconstruction, but
QIKVRT_DOD == DONE only when the entire D.o.D. conjunction is freshly true at
the same final Main HEAD/TREE, including the required real effect readback.

## Evolution rule

This V1 object is immutable historical evidence. Future learning MUST NOT
silently rewrite or delete it. A future semantic change may only be represented
by an additional versioned successor that explicitly binds this V1 and records
one of: SUPERSEDED, REFUTED, or SCOPE_NARROWED, including rationale and fresh
evidence. The bytes and provenance of V1 remain addressable.

This rule applies recursively to its own successors.
