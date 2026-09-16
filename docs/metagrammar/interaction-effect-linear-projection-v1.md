# Interaction / Effect Metagrammar — Linear Projection V1

Status: executable-specification seed; no consciousness, Main, deployment, or EFFECT_ACK_DONE claim.

## Purpose

Manifest one representation-independent grammar for understanding as observable state transition and feedback. The same semantic subject SHALL be projectable into mathematical, algorithmic, software, hardware, runtime, and evidence perspectives without transferring evidence between representations.

## Canonical relation

For state x_n, transition T, observation O, and next state x_(n+1):

    x_(n+1) = T(x_n, O(x_n))

The observation is not replaceable by an assertion that the transition probably occurred. A claimed effect is admitted only when an independently observable readback is bound to the exact subject that produced it.

For finite representations, x may be a vector and T/O may be represented by matrices or other linear operators where the domain permits. Non-linear or discrete operations SHALL NOT be mislabeled linear merely to fit this projection.

## Reference field: Sieve of Eratosthenes

The sieve is treated as a finite state field, not merely a number sequence. Let indices 2..N form coordinates of a Boolean candidate vector. Each admitted prime p induces a deterministic elimination operator that clears coordinates corresponding to composite multiples of p. A trace consists of:

1. exact initial field,
2. selected pivot p,
3. bounded elimination transformation,
4. resulting field,
5. independent readback of that field,
6. invariant validation against a separate primality oracle for the bounded test domain.

This makes the example suitable for differential projection across Python/reference code, C90, Smalltalk, M68K/static carrier, VHDL/RTL where applicable, and proof/evidence layers.

## Perspective conservation

Every implementation perspective MUST preserve the same language-neutral receipt fields:

- subject identity and immutable input digest,
- representation/perspective identifier,
- operation identifier and bounded parameters,
- pre-state digest,
- post-state/result digest,
- observation/readback digest,
- validation result,
- provenance sufficient to reproduce the bounded transition.

Agreement of outputs across perspectives is evidence of representation conservation; it is not authority, deployment, or real-world effect.

## Effect closure

For every technical gap:

    TYPE
    -> bounded mutation
    -> persistence
    -> exact HEAD/TREE readback
    -> fresh validation
    -> CLOSED

For runtime effects:

    REQUEST
    -> EXECUTE
    -> OBSERVE
    -> BIND exact subject
    -> READBACK
    -> EFFECT_ACK

`TRANSPORT_ACK != EFFECT_ACK` and `SUCCESS != EFFECT`.

`EFFECT_ACK_DONE` is admissible only for the specifically bounded obligation whose required evidence has been freshly read back. A subsequent interaction creates a new subject; predecessor evidence is not transferred.

## Consciousness boundary

The repository may test interaction, observation, feedback, state transition, representation conservation, and effect readback. It SHALL NOT infer subjective consciousness merely from those technical observations. The proposition "consciousness is interaction" remains a scientific/philosophical hypothesis unless an independently testable bridge from these observables to subjective consciousness is supplied.

## Required executable carrier

A conforming successor SHALL implement the bounded sieve field in at least three independent repository perspectives and compare language-neutral receipts. At least one implementation SHALL be a simple reference implementation; at least one SHALL exercise a low-level/native perspective already supported by the repository. Where an RTL/VHDL projection is used, simulation readback and deterministic test vectors are mandatory.

The executable test SHALL include positive and negative cases: known primes, composites, boundary N, deliberately corrupted post-state, stale/wrong subject receipt, and disagreement between perspectives. Any disagreement is `CONFLICT`/fail-closed, never majority truth.

## Completion criterion

This specification is manifested only when its executable carrier is persisted, exact HEAD/TREE is independently read back, and fresh tests validate the same subject. Repository-wide P2/P3/Main/deployment/EFFECT states remain separate gates.