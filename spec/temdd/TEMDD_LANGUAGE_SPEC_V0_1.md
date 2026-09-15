# TEMDD Language Specification v0.1

Status: executable bootstrap candidate. Authority: Goldkelch/qik-vrt.

TEMDD (Tested Event Model Driven Development) is the executable metaprogramming language of QIK-VRT. Its lifecycle is `REQUEST -> EXECUTE -> FOLLOW -> LEARN -> SUCCESSOR -> ... -> DONE`.

## Normative invariants
T01 Evidence is exact-subject typed and cannot transfer to another head/tree/scope. T02 Mutation creates a successor and invalidates dependent evidence. T03 TRANSPORT_ACK != EFFECT_ACK. T04 RESULT != EFFECT. T05 HOLD/CONTINUE are nonterminal and never NOOP. T06 Open productive work excludes DONE. T07 External effects require exact-scope authority. T08 Committed effects require fresh readback. T09 Missing/stale/conflicting/malformed/indeterminate critical evidence fails closed. T10 Unknown critical effect state blocks. T11 Learning constructs a successor and cannot self-certify. T12 DONE requires the complete declared DoD from fresh bound evidence.

## Semantic objects
`authority`, `subject`, `request`, `event`, `test`, `evidence`, `model`, `effect`, `hold`, `learn`, `successor`, `done`. Models are not evidence. Effects have prepare/authorize/commit/readback boundaries.

## Execution
TEMDD is event-driven. Scheduling and polling are outer-layer transports, not kernel semantics. A runtime consumes one event, performs a finite transition, emits evidence/effect/successor intents and becomes quiescent. WAIT/HOLD, queued work, open PRs, unmerged productive branches, failed gates, missing releases and missing effect readback cannot become NOOP or DONE.

## Compilation
`TEMDD source -> parser -> typed AST/IR -> conformance -> backend`. Initial backends are Python reference, Smalltalk live objects, C90 deterministic runtime, M68000 fixed relations and Lean obligations. Translators preserve subject identity, provenance, authority, status, effect state and readback obligations. Semantic loss or backend disagreement is BLOCK.

## Self-improvement
`S --learn--> S'`. S' is a new exact subject. Evidence for S is not validation for S'. Fresh conformance and deployment evidence is mandatory before adoption.

## Continuous deployment
`parse -> elaborate -> conformance -> differential backends -> formal obligations -> reproducible build -> candidate deploy/readback -> authorized promotion -> production readback`. No stage implies a later stage.

## Canonical QIK-VRT DoD
`ZERO_BUGS && ALL_PULL_REQUESTS_REGARDED && ALL_BRANCHES_REGARDED && ALL_PRODUCTIVE_BRANCHES_MERGED && FRESH_EXACT_MAIN_VALIDATION_PASS && FRESH_EFFECT_READBACK`.

## Bootstrap boundary
v0.1 distinguishes BOOTSTRAP_CONFORMANT from STABLE_LANGUAGE. Stable status requires executable Smalltalk and M68000 gates, compiled Lean obligations, reproducible release, Main adoption and fresh production effect readback. Version labels and successful transport/build jobs cannot manufacture these claims. Intermediate states are observable but are not a return condition; the return condition is the full declared DoD.
