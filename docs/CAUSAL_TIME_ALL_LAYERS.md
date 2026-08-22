# QIK-VRT Causal Time Across All Layers V1

## Core

The smallest invariant is not a clock. It is the preservation of the difference between causal binding and mere ordering.

```text
1 - 0 = 1        distinction
1 - 1 = 0        eliminated difference for equal values
x = y            relation in a bound domain

RELATION != CAUSALITY
CAUSALITY != SEQUENCE
TIMESTAMP_ORDER != CAUSAL_ORDER
LATER != CAUSED_BY
```

A relation, source position, timestamp, later observation, deterministic serialization or larger numeric value does not create a causal edge.

## Layer propagation

```text
FORMAL DISTINCTION
  -> METAGRAMMAR
  -> EXPLICIT CAUSE BINDING
  -> CAUSAL IR / PARTIAL ORDER
  -> DETERMINISTIC VALID SERIALIZATION
  -> ANSI-C89 FRONTEND / VALIDATED PLAN
  -> M68000 MACHINE WITNESS
  -> MEGA-ST RUNTIME
  -> TEMDD EVENT MODEL
  -> REPOSITORY EVIDENCE
  -> MESH COORDINATION
  -> EMPIRICAL REOBSERVATION
  -> PHILOSOPHICAL INTERPRETATION
```

Every arrow is a typed bridge. No higher layer may silently strengthen the evidence class of a lower layer.

## Causal time

Within QIK-VRT, `CAUSAL_TIME` is an order/projection derived from explicitly bound causal transitions. It is not defined by wall-clock succession alone.

```text
CAUSE(A,B) may constrain ORDER(A,B)
ORDER(A,B) does not imply CAUSE(A,B)
```

Wall-clock timestamps remain useful evidence metadata for freshness, replay protection and observation history. They do not establish causation.

## Motorola 68000 projection

The existing decision ABI remains intact:

```text
D0 = decision: 0 NOOP, 1 HOLD, 2 REOBSERVE, 3 REQUEST_AUTHORITY
D1 = semantic witness flags
D2 = effect lifecycle
```

The opt-in `--causal-time-v3` profile adds:

```text
D3 = 0  no explicit predecessor is bound
D3 = 1  an explicit predecessor is bound
```

This is intentionally the smallest machine-visible causal-order witness. `D3` is **not** a timestamp, duration, success flag, quality score, authority token or empirical proof of physical causality.

For `BOUND`, `EFFECT OBSERVED`, `CAUSE r0`, `NEXT REOBSERVE`, the IR is:

```text
MOVEQ D1 15
MOVEQ D2 3
MOVEQ D3 1
MOVEQ D0 2
RTS
```

and the raw big-endian M68000 bytes are:

```text
72 0F 74 03 76 01 70 02 4E 75
```

With no explicit predecessor, the corresponding D3 witness is zero; absence of a predecessor is not silently converted into non-causality of the physical world, only absence of that causal binding in this plan.

## Repository and mesh

Repository commit order, workflow run order, PR number, timestamp and later head do not themselves establish semantic causality or improvement.

```text
NEWER_HEAD != BETTER_HEAD
LATER_RUN != STRONGER_EVIDENCE
MERGED_AFTER != CAUSED_BY
REQUESTED != EXECUTED
EXECUTED != OBSERVED
OBSERVED != ACKNOWLEDGED
```

Mesh nodes may exchange and corroborate causal bindings, but plurality, consensus and temporal order do not manufacture truth.

## Largest boundary

The same distinction may be used as a philosophical interpretation of time, cognition or the universe. That interpretation remains separate from empirical physics.

QIK-VRT does not infer from this implementation that physical time is identical to causal order, that quantum causality has been empirically established, that machine consciousness exists, or that physical Mega-ST hardware executed these bytes. Such claims require their own models and observations.
