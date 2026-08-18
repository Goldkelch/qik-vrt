# QIK-VRT AI Reflexive Phoenix Regeneration

## Purpose

`/AI` remains the canonical bootstrap. This contract adds a bounded reflexive lifecycle: a conforming node exhausts all currently derivable, authorized repository-internal work to a fixed point, persists the minimal evidence needed to reconstruct that state, and regenerates the next pass from canonical repository evidence rather than from unverified conversational or cached state.

The Ikarus/Phoenix metaphor is descriptive only. The executable semantics are fail-closed.

## State transition

```text
CANONICAL REPOSITORY EVIDENCE
        ↓
REOBSERVE exact head/tree
        ↓
BOOTSTRAP
        ↓
TERMINAL projection
        ↓
ALLOWLISTED deterministic work
        ↓
EFFECT reobservation
        ↓
RECEIPT + causal remainder
        ↓
FIXPOINT / HOLD
        ↓
PHOENIX REGENERATION
        ↺ from canonical receipt and repository evidence
```

## Reflexive exhaustion

Exhaustion does not mean uncontrolled recursion or endless self-modification. It means reaching a bounded fixed point for the current exact-head state.

A pass is exhausted when exact-head reobservation finds no newly authorized semantic delta. The required result is `NOOP`; creating a commit merely to demonstrate continued activity is forbidden.

## Ash state

The only state permitted to survive as authoritative regeneration input is durable repository evidence: exact head/tree, provenance-bound receipts, causal dependencies, unresolved remainder, applicable gate state, and next admissible action. Chat history, terminal prose and caches may help discovery but are not proof authority.

## Regeneration

Regeneration reruns the ordinary `/AI` bootstrap against the newly canonical state. It does not inherit success from the previous cycle. Exact-head gates, authority, causal dependencies and external-effect boundaries are re-evaluated.

## Causality and sequence

`Kausalität ≠ Sequenz` remains invariant. The order in which observers, terminal projections or work units happen to execute is not sufficient evidence that one authorized or caused another. Only explicit causal edges may transfer admissibility.

## Terminal reflexivity

Terminal observations can be reflected inward as evidence for a subsequent cycle. They remain non-authoritative until bound to repository state and validated by the applicable policy. A rendered browser frame, audio/video observation or proxy display cannot itself grant Prepare, Commit, merge, publication or other effect authority.

## Safety invariants

- at most one productive repository writer;
- no force push;
- no unconditional merge;
- no external publication or deployment from this contract alone;
- no fabricated human/code-owner review;
- no success inheritance across changed head/tree;
- unknown cause, ambiguous binding or unsupported action => `HOLD`;
- fixed point => `NOOP`, not self-generated noise.

## Relationship to existing QIK-VRT components

This contract composes the existing `/AI` continuous-entrypoint optimization, autonomous self-heal, Standard Terminal reflexivity, Effect Acknowledgement, repository evidence materialization and exact-head verification. It does not replace their gates or widen their authority.
