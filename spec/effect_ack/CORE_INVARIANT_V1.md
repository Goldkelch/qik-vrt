# QIK-VRT Core Invariant — independent multi-carrier contract v1

Status: normative finite core contract for cross-conformance.

This contract is deliberately language-neutral. C90, Motorola 68000 assembly,
Smalltalk, TEMDD, Lean, and Ada/SPARK are consumers of this contract; none of
them defines the semantics of another carrier.

## Sort separation

`TRANSPORT_ACK` is an observation at a transport/execution boundary.
`Effect_State` is a five-valued authorization decision:
`EFFECT_NACK`, `EFFECT_ACK_CONTINUE`, `EFFECT_ACK_DONE`,
`EFFECT_ACK_ISOLATE`, or `EFFECT_ACK_BLOCK`.

```text
TRANSPORT_ACK does not imply EFFECT_ACK_DONE
ordinary_release(state) iff state == EFFECT_ACK_DONE
```

## Finite core decision

The bounded proof domain is four booleans:
`transport_ack, block_required, isolate_required, release_ready`.

```text
if not transport_ack:   EFFECT_NACK
else if block_required: EFFECT_ACK_BLOCK
else if isolate_required: EFFECT_ACK_ISOLATE
else if release_ready:  EFFECT_ACK_DONE
else:                   EFFECT_ACK_CONTINUE
```

The 16 exhaustive rows are frozen in `vectors.json`.

## Independence criterion

Cross-conformance PASS requires, on one exact HEAD/TREE: C90, MC68000 under
QEMU, Smalltalk in pinned Pharo, TEMDD semantic relations, Lean kernel proofs,
and Ada/SPARK plus GNATprove. The cross-runner compares each executable carrier
to `vectors.json`, never to another carrier. Agreement by majority is not an
oracle; any divergence is HOLD.

This proves the finite core separation and release rule, not the complete wire
protocol. Authentication, freshness, exact-subject, evidence, responsibility,
policy, deployment, publication and public readback remain separate obligations.
A mutation creates a new subject and requires fresh proof.

## Cross-checking and evidence boundary

The neutral vector bytes are unchanged and pinned by SHA-256
`e44b421ef862629b1f24ec02a8ddbc8dc0b763548ac0aa17f1c52f84e63182bc`.
Comparator v2 requires exactly five executable output streams (C90, MC68000,
Smalltalk, Ada/SPARK, and Lean), plus the TEMDD relation carrier. Each supplies
both decision state and ordinary-release value for all 16 distinct inputs.
An always-block implementation fails the positive release case. Missing or
duplicate carriers, missing or duplicate inputs, and changed oracle bytes fail.

For this bounded TEMDD carrier, `maps_to` is the total function from the 16
input keys to decision states; `permits_ordinary_release` is the total function
from the five state names to `true` or `false`. The existing TEMDD v1 adapter
parses these declarations. The comparator evaluates their finite lookup
semantics without reading contract outputs or other carriers. Every relation
must be `TRUE` and `FRESH`; conflicting or duplicate sources fail. This is a
finite relational interpretation, not a claim about TEMDD's full event/effect
runtime or the validators that establish truth and freshness outside the model.

Lean checks its theorems with warnings as errors, records their axiom
dependencies, and executes the same Lean `decide` function over the entire
domain. GNATprove remains a separate proof step with unproved checks and
warnings treated as errors. Full proof-log digests are bound in the report.
Markers and logs are trusted-workflow receipts; their text alone does not
authenticate a compiler, proof checker, or execution. Check the source,
workflow, exact commit/tree, run identity and complete logs together.

Cross-language agreement does not establish independent authorship or external
reproduction. A reviewer who did not author the carriers/oracle must separately
reproduce the run and inspect the spec-to-oracle correspondence before that
stronger claim is made. The current finite-core claim also does not establish
the abstraction from every predicate in the full EFFECT_ACK protocol to these
four booleans. No forecast-market resolution follows from this CI result alone.
