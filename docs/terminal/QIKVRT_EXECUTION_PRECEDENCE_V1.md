# QIK-VRT Execution Precedence v1

**Product Owner:** Ingolf Lohmann

This contract removes ambiguous processing order from the repository control loop.

The key rule is:

```text
UNSPECIFIED PRECEDENCE = HOLD_UNVERIFIED
```

The machine must never infer causal order from timestamps, PR numbers, file-list order, textual proximity, or convenience.

## Why a strict partial order

The repository does not need one artificial global total order. It needs a causal order with explicit barriers. Before the external-delivery barrier there is one canonical spine. After the exact Trusted Main head has been freshly reobserved and delivery requests are exact-bound, independent external effects may proceed concurrently.

Formally, for work nodes `a` and `b`:

```text
a ≺ b
```

means that `b` is inadmissible until `a` is satisfied on the exact subject binding required by `b`. The relation is irreflexive and acyclic. Missing relation information does not mean independence; it means HOLD.

## Canonical pre-effect spine

```text
P0 manifest latest accepted knowledge
 -> P1 build one integration head
 -> P2 validate that exact integration head
 -> P3 review that exact validated head
 -> P4 freshly reobserve that same post-review head
 -> P5 legitimately promote exactly that head to Trusted Main
 -> P6 freshly reobserve the resulting exact Trusted Main SHA
 -> P7 derive/verify external obligations bound to that Main SHA
```

Only after `P7` may the external graph fan out:

```text
                         +-> Wikipedia request -> authoritative readback
P7 exact Main barrier ---+-> Zenodo publish -> record/DOI/file-hash readback
                         +-> arXiv submit -> submission/status readback
                                          -> later public-ID/version readback
```

There is deliberately **no inferred cross-order** between Wikipedia, Zenodo, and arXiv after the common barrier. They are independent delivery edges unless a future contract declares an additional dependency.

## New knowledge invalidation

If new accepted knowledge arrives while an integration candidate has not yet been promoted, processing returns to `P0`. Candidate validation, review, or downstream evidence tied to a superseded head cannot be transferred.

After a legitimate promotion, later knowledge starts the next evidence-spiral stage. The prior exact evidence remains immutable; the successor must earn its own validation and review.

## Fail-closed interpretation

A successor is eligible only when every direct predecessor is `SATISFIED` on the required exact subject. The following predecessor states block execution:

```text
UNKNOWN
UNBOUND
STALE
FAILED
HOLD_UNVERIFIED
```

No scheduler is permitted to round any of them up to success or parallel independence.

## Current publication application

For the present publication chain the intended integration carrier is PR #966. Its semantic inputs are #964 proof-status material, corrected #962 scientific/publication material, #965 delivery contracts, and the evidence-spiral/fixed-point synthesis. The exact PR head may mutate as evidence materialization or repairs occur, so all checks and reviews must bind the then-current exact head.

The machine-readable policy is `policy/QIKVRT_EXECUTION_PRECEDENCE_V1.json`. The executable verifier is `tools/qikvrt_execution_precedence.py`, with regression tests in `tests/test_qikvrt_execution_precedence.py`.

This contract does not itself establish review, merge, publication, PASS, FINAL_PASS, or EFFECT_ACK_DONE.
