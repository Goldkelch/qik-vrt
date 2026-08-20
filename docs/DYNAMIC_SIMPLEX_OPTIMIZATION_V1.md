# QIK-VRT Dynamic Simplex Optimization V1

## Purpose

This layer turns repository improvement into a bounded, evidence-driven optimization problem without treating activity as progress.

`dynamic simplex` here is a QIK-VRT term. It is **not** a claim that the repository is a linear program and it is **not** the textbook LP simplex algorithm. The simplex is the finite set of currently admissible repository moves. Its vertices change as evidence, authority, blockers and role-local state change.

## Cycle

```text
OBSERVE exact state
  ↓
CAUSAL FINGERPRINT
  ↓
ENUMERATE bounded candidate moves
  ↓
HARD-INVARIANT FILTER
  ↓
LEXICOGRAPHIC OBJECTIVE ORDER
  ↓
SELECT ≤ 1 move
  ↓
PLAN RECEIPT
  ↓
existing authorized executor/effect lane
  ↓
REOBSERVE
  ↓
retain / contract / expand / regenerate candidate simplex
```

The optimizer itself is a planner. It does not acquire authority by optimization and it does not turn a better score into an effect acknowledgement.

## Objective order

Higher levels dominate all lower levels:

1. correctness;
2. false authority/effect inference;
3. autonomous liveness;
4. exact-head integrity/reproducibility;
5. activity without effect;
6. deterministic latency/resource waste;
7. avoidable complexity;
8. testability/observability/durability;
9. publication opportunity.

A latency improvement therefore cannot justify a correctness regression. A publication opportunity cannot justify an unresolved claim-affecting blocker.

## Vertex representation

Each vertex provides a signed objective delta. Negative values are improvements, positive values are regressions. Comparison is lexicographic.

Example:

```json
{
  "id": "deduplicate-identical-status-write",
  "delta": {
    "activity_without_effect": -1,
    "deterministic_latency_or_resource_waste": -1
  },
  "constraints": {
    "causality_preserved": true,
    "authority_not_widened": true,
    "role_local_identity_preserved": true
  },
  "requires_authority": false
}
```

A vertex with any false hard constraint is inadmissible regardless of score.

## Causal fingerprint

The v1 fingerprint binds only:

- exact binding;
- stage states;
- first deterministic blocker;
- next possible effect;
- role-local state.

Run IDs, timestamps, retry counts, comment counts, workflow volume and commit activity do not change the fingerprint by themselves.

Therefore:

```text
same causal fingerprint
= NO_CAUSAL_DELTA
```

## D0 terminal semantics

The planner terminates each observation cycle using the existing D0 ABI:

```text
D0=0 NOOP
  no admissible causally justified improvement remains

D0=1 HOLD
  prerequisite/work is pending, including a selected bounded move waiting for execution/reobservation

D0=2 REOBSERVE
  evidence is stale

D0=3 REQUEST_AUTHORITY
  best otherwise-admissible move is blocked solely by authority
```

The plan receipt is not a productive effect.

## Publication discovery

Publication is itself an optimization opportunity only after correctness and reproducibility constraints are satisfied.

`PUBLICATION_WORTHY` requires all of:

- a novel result or reusable method;
- exact repository provenance;
- reproducible evidence;
- explicit formal/empirical/interpretive boundaries;
- no unresolved correctness blocker affecting the claim;
- archival metadata and checksums.

Even then:

```text
PUBLICATION_WORTHY != PUBLISHED
DEPOSIT_REQUESTED != DOI_OBSERVED
ARXIV_SUBMISSION_REQUESTED != ARXIV_IDENTIFIER_OBSERVED
```

The archival effect must remain separately observable.

## Authority/Mirror

Optimization must preserve role-local identity. A move that makes Authority and Mirror byte-identical by erasing required Mirror state is inadmissible even if it reduces superficial repository differences.

```text
IDENTITY != EQUALITY
INTEGRATION != FLATTENING
```
