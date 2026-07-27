<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# QIK-VRT Anticipation and Trend Model

## Normative statement

Anticipation is the repository-native derivation of the next valid state from an ordered set of verified observations, their state differences, the resulting trend and the applicable transition rules.

Anticipation is not a guess. It is a versioned, evidence-bound repository state.

## Canonical chain

`STATE -> DIFFERENCE -> INFORMATION -> TREND -> DERIVATIVES -> ANTICIPATED_STATE -> NEXT_EFFECT -> EXECUTION -> RECEIPT -> NEW_STATE`

## State observations

Each observation binds a repository projection to a revision, timestamp and SHA-256 digest. At least two observations are required to establish a difference. At least three ordered observations are required to classify a directional trend beyond a single transition. Four ordered observations form the first operational trend pyramid used by the reference implementation:

1. state level;
2. first difference;
3. trend over differences;
4. anticipation of the next valid state.

Additional observations extend the pyramid and permit higher-order discrete derivatives.

## Discrete derivatives

For ordered repository states `S_0 ... S_n`:

- order 0 is the observed state;
- order 1 is the verified state difference;
- order 2 is the change of the state difference;
- order 3 and above are higher changes of change.

The implementation stores derivatives as explicit records. It never treats an absent derivative as zero.

## Deterministic anticipation

The canonical anticipation record contains exactly one `anticipated_state` and exactly one `next_effect` for the active productive chain. Competing effects remain outside the canonical state until ordering rules select one.

Ordering is defined by:

1. safety and integrity prerequisites;
2. unresolved blocker removal;
3. completion of the earliest open productive-chain transition;
4. Authority integration;
5. Mirror verification;
6. publication projection;
7. next Work Unit.

This removes ambiguous `or` semantics from the active state. Alternatives may exist in analysis, but the repository publishes one selected next effect.

## Productive progress

Activity is not progress. Productive progress advances the evidence-bearing chain:

`Issue -> Work Unit -> Code -> Tests -> green mandatory gates -> Merge -> Authority -> Mirror -> next Work Unit`

A comment, issue or metadata commit does not set `productive_progress=true` unless it advances this chain.

## Stall state

A stall exists when the productive-chain position remains unchanged across the configured observation window and the selected next effect has no verified execution receipt.

The stall record contains:

- concrete failure class;
- structural cause;
- selected minimal next effect;
- executor capability;
- dispatch status;
- required owner action.

## Closed observation loop

After each dispatch the repository performs a new observation. The new observation is a distinct measurement point. The observer compares it with the previous verified state and then materializes a new trend, anticipation and next effect.

`OBSERVE -> DERIVE -> SELECT -> DISPATCH -> OBSERVE`

The loop terminates only in `KERNEL_VERIFIZIERTER_ABSCHLUSS` with complete receipts and verified Authority/Mirror state.

## Component independence

The anticipation engine is a capability, not an identity-bound actor. Any conforming implementation may replace the current planner, model, service or human operator.

`NO_COMPONENT_IDENTITY_DEPENDENCY`

The repository remains operational after removal of the original assistant when a replacement implementation satisfies the same schemas, transition rules, tests and receipts.

## Public projections

The canonical state is projected through:

- `anticipation/current.json`;
- `anticipation/history.jsonl`;
- `anticipation/trends.json`;
- `anticipation/derivatives.json`;
- `anticipation/next-effect.json`;
- RCP resources under `/.well-known/rcp` and `/rcp/anticipation`;
- GitHub-native JSON files and workflow dispatch;
- Zenodo publication metadata and evidence packages;
- IETF draft source and rendered validation evidence.

All projections derive from the same canonical state and carry source revision and SHA-256 bindings.

## Failure classes

- `INSUFFICIENT_VERIFIED_OBSERVATIONS`
- `STATE_DIGEST_MISMATCH`
- `TREND_DERIVATION_NONDETERMINISTIC`
- `NEXT_EFFECT_NOT_SELECTED`
- `NEXT_EFFECT_NOT_DISPATCHED`
- `EXECUTION_RECEIPT_MISSING`
- `PRODUCTIVE_CHAIN_STALLED`
- `AUTHORITY_MIRROR_STATE_DIVERGENCE`
- `PROJECTION_STALE`
- `COMPONENT_IDENTITY_DEPENDENCY_DETECTED`

## Acceptance criteria

1. Schema validation succeeds for every materialized anticipation state.
2. Repeated input observations produce byte-identical derived state.
3. Fewer than two observations fail closed.
4. Activity without productive-chain advancement is classified as non-progress.
5. Exactly one canonical next effect is selected.
6. Every dispatched effect causes a subsequent observation.
7. Authority and Mirror expose compatible state projections.
8. Zenodo and IETF projections carry the same canonical state digest.
9. Replacement of the planner implementation leaves conformance tests green.
10. No PASS or EFFECT_ACK_DONE is emitted before kernel receipts and pair verification exist.

Status remains `EFFECT_ACK_CONTINUE` until these criteria are evidenced.
