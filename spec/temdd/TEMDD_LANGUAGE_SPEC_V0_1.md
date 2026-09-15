# TEMDD Language Specification v0.1

Status: executable bootstrap candidate
Authority: Goldkelch/qik-vrt

TEMDD (Tested Event Model Driven Development) is the executable metaprogramming language of QIK-VRT. Its normative lifecycle is `REQUEST -> EXECUTE -> FOLLOW -> LEARN -> SUCCESSOR -> ... -> DONE`.

## Normative invariants
T01 Evidence is exact-subject typed and cannot transfer to another head/tree/scope.
T02 Mutation creates a successor subject and invalidates dependent validation/review evidence.
T03 TRANSPORT_ACK != EFFECT_ACK.
T04 RESULT != EFFECT.
T05 HOLD and CONTINUE are nonterminal and are never NOOP.
T06 Open productive work excludes DONE.
T07 External effects require admitted exact-scope authority.
T08 Committed effects require fresh post-effect readback.
T09 Missing, stale, conflicting, malformed or indeterminate critical evidence fails closed.
T10 Unknown critical effect state blocks the protected effect.
T11 Learning constructs a successor; it cannot rewrite evidence to self-certify.
T12 DONE is constructible only from the complete declared DoD using fresh bound evidence.

## Core objects
`authority`, `subject`, `request`, `event`, `test`, `evidence`, `model`, `effect`, `hold`, `learn`, `successor`, and `done` are semantic objects rather than conventions. Models are not silently promoted to evidence. Effects have prepare/authorize/commit/readback boundaries.

## Execution
TEMDD is event-driven. Scheduling and polling are outer-layer transports, not kernel semantics. A runtime consumes an event, performs a finite transition, emits evidence/effect/successor intents and becomes quiescent. WAIT/HOLD, queued work, open PRs, unmerged productive branches, failed gates, missing releases, and missing effect readback cannot become NOOP or DONE.

## Compilation
`TEMDD source -> parser -> typed AST/IR -> conformance -> backend`.
Initial backends: Python reference, Smalltalk live objects, C90 deterministic runtime, M68000 fixed relations, Lean obligations. Translators preserve subject identity, provenance, authority, status, effect state and required readback. Semantic loss is a compile-time BLOCK; backend disagreement is a BLOCK.

## Self-improvement
`S --learn--> S'`. S' is a new exact subject. Evidence for S is not validation for S'. Fresh conformance and deployment evidence is mandatory before adoption.

## Continuous deployment
`parse -> elaborate -> conformance -> differential backends -> formal obligations -> reproducible build -> candidate deploy/readback -> authorized promotion -> production readback`. No stage implies a later stage.

## Canonical QIK-VRT DoD
`ZERO_BUGS && ALL_PULL_REQUESTS_REGARDED && ALL_BRANCHES_REGARDED && ALL_PRODUCTIVE_BRANCHES_MERGED && FRESH_EXACT_MAIN_VALIDATION_PASS && FRESH_EFFECT_READBACK`.

v0.1 is deliberately a bootstrap language. `BOOTSTRAP_CONFORMANT` and `STABLE_LANGUAGE` are distinct claims; stable status requires executable Smalltalk and M68000 gates, compiled Lean obligations, reproducible release and production effect readback.
