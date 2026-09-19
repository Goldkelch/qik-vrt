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
