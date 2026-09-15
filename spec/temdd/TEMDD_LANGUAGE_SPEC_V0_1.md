# TEMDD Language Specification v0.1

Status: executable bootstrap candidate
Authority: Goldkelch/qik-vrt

TEMDD (Tested Event Model Driven Development) is the executable metaprogramming language of QIK-VRT. Its normative lifecycle is:

`REQUEST -> EXECUTE -> FOLLOW -> LEARN -> SUCCESSOR -> ... -> DONE`

## Semantic invariants

T01 Exact subject: evidence is parameterized by its exact subject and cannot be transferred to a different head/tree/scope.
T02 Mutation creates a successor subject and invalidates dependent validation/review evidence.
T03 TRANSPORT_ACK is not EFFECT_ACK.
T04 RESULT is not EFFECT.
T05 HOLD and CONTINUE are nonterminal states and are not NOOP.
T06 Any open productive work excludes DONE.
T07 An external effect requires explicit authority admitted for its exact scope.
T08 A committed effect requires fresh post-effect readback.
T09 Missing, stale, conflicting, malformed or indeterminate critical evidence fails closed.
T10 Unknown critical effect state blocks the protected effect.
T11 Learning creates a new successor; a program cannot rewrite evidence to validate itself.
T12 DONE is constructible only when the declared Definition of Done evaluates true from fresh bound evidence.

## Core semantic objects

- `authority`: actor/policy allowed to authorize an effect.
- `subject`: immutable identity of the object being evaluated.
- `request`: desired target state and acceptance predicate.
- `event`: immutable trigger carrying provenance.
- `test`: deterministic or explicitly empirical predicate over a bound subject.
- `evidence`: immutable observation with origin, digest, freshness and subject binding.
- `model`: typed representation used for decisions; never silently promoted to evidence.
- `effect`: requested external mutation with prepare/authorize/commit/readback phases.
- `hold`: fail-closed nonterminal state with an explicit reactivation event.
- `learn`: derivation of a bounded successor from observed evidence.
- `successor`: new exact subject produced by a mutation or learned repair.
- `done`: proof object for the complete declared DoD, never a boolean convention.

## Execution model

TEMDD is event-driven. Scheduling and polling are outer-layer transport mechanisms and are not part of the language kernel. A conforming runtime consumes one event, evaluates a finite transition, emits evidence/effect intents/successor intents, and returns to a quiescent state.

A runtime MUST NOT convert WAIT/HOLD, queued work, an open PR, an unmerged productive branch, a failed gate, missing release, or missing effect readback into NOOP or DONE.

## Compiler contract

The canonical pipeline is:

`TEMDD source -> parser -> typed AST -> canonical IR -> conformance tests -> backend`

Initial backends are Python reference execution, Smalltalk live object execution, C90 portable deterministic execution, M68000 fixed-relation execution, and Lean semantic obligations. All backends consume the same canonical vectors. Backend disagreement is a BLOCK.

A compiler/translator MUST preserve subject identity, evidence provenance, authority boundary, uncertainty/status, effect state and required readback. Loss of a required semantic field is a compile-time error.

## Self-improvement contract

Self-improvement is successor construction, not in-place self-certification:

`S --learn--> S'`

Evidence for S is not validation evidence for S'. S' must pass fresh conformance and deployment gates before adoption.

## Continuous deployment contract

`parse -> elaborate -> conformance -> differential backends -> formal obligations -> reproducible build -> candidate deploy -> candidate readback -> authorized promotion -> production readback`

No stage implies a later stage. Production DONE requires the declared production effect predicate.

## QIK-VRT canonical DoD

The first production program uses:

`ZERO_BUGS && ALL_PULL_REQUESTS_REGARDED && ALL_BRANCHES_REGARDED && ALL_PRODUCTIVE_BRANCHES_MERGED && FRESH_EXACT_MAIN_VALIDATION_PASS && FRESH_EFFECT_READBACK`

This specification is deliberately small enough to bootstrap. v0.1 does not claim that every future TEMDD construct is already specified.