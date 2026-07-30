<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright 2026 Ingolf Lohmann.
-->

# QIK-VRT Global System Closure v1

## Bounded closure contract

QIK-VRT is externally treatable as one closed repository process only when
every interaction advances the same canonical chain and produces one
checkable successor state:

`INTERACTION -> EVIDENCE -> WORK_UNIT -> CANDIDATE -> GATES -> EFFECT_ACK -> EFFECT -> RECEIPT -> OBSERVATION`

“One system” means one entrypoint, one ordered productive chain, one selected
next effect per scope, and hash-linked receipts. It does not require a
single-file implementation. Internal implementations remain replaceable
capabilities.

This contract is a repository-control specification. It is not a theorem that
every historical or physical claim is true, and it does not expand the finite
`qikvrt-global-claim-scope-v1` completion receipt.

## Monotone, measured advancement

A candidate advances this closure scope only when:

1. at least one declared integer gate metric increases and none decreases; or
2. the canonical metric map is byte-stable and the transition is recorded as
   `BYTE_STABLE_NO_OP`.

A regression is rejected rather than made canonical. Metrics establish only
their declared bounded comparison; they do not prove hidden quality,
completeness, safety, consensus, or eventual termination.

## Persistence and recovery

Each transition is a small, content-addressed checkpoint that binds its
predecessor:

1. `CONTRACT_BOUND`
2. `ANTICIPATION_MATERIALIZED`
3. `EFFECT_INTENTS_GATED`
4. `CANDIDATE_VERIFIED`
5. `AUTHORITY_OBSERVED`
6. `MIRROR_OBSERVED`
7. `RECEIPT_CLOSED`

Before an external mutation, a local candidate may be abandoned or reverted.
After a possibly executed remote mutation, the system must not claim rollback.
It observes the external state read-only and continues through idempotent replay
or forward repair.

## Effect boundary

The existing five-state EFFECT_ACK implementation remains the only ordinary
release gate. Observation and anticipation may produce evidence, projections,
work units, and inert effect intents; they cannot manufacture
`EFFECT_ACK_DONE`.

Every external effect still requires fresh effect-specific evaluation,
provenance and responsibility binding, the applicable gates, explicit human
authorization, and a subsequent effect receipt. A due time, workflow success,
transport acknowledgement, or local zero exit code is not effect permission.

Target/time/payload envelope validation is deliberately separable from this
core. A concrete target, dispatch record, or publication queue is not part of
the closure-core projection.

## Generic targeted-effect envelope

`schemas/qikvrt-targeted-effect-envelope.schema.json` and
`tools/qikvrt_targeted_effect.py` define a generic outer envelope around an
unchanged EFFECT_ACK record. The evaluator binds one payload, one canonical
node GUID, one repository/ref tuple, exact registry bytes, one non-empty time
window, one predecessor checkpoint and an optional fresh effect-specific
protocol.

It accepts only an inert tracked dispatch state. A valid result can become
`ELIGIBLE_FOR_SEPARATELY_AUTHORIZED_DISPATCH`, but the evaluator never attempts
that dispatch and never treats eligibility, scheduler due state, or transport
acknowledgement as authorization. No concrete node, live window, payload,
evaluation, or dispatch receipt is tracked by this generic layer.

## Current-main projection

`tools/qikvrt_anticipation.py` consumes an input bound to the current Authority
status files and a named Git tree. It deterministically materializes:

- `anticipation/current.json`
- `anticipation/history.jsonl`
- `anticipation/trends.json`
- `anticipation/derivatives.json`
- `anticipation/next-effect.json`
- `receipts/anticipation/0001-contract-bound.json`
- `receipts/anticipation/0002-anticipation-materialized.json`

The projection is scope-qualified and remains
`EFFECT_ACK_CONTINUE`. It does not dispatch, merge, synchronize repositories,
publish to Zenodo, or infer repository-wide completion. The next effect is a
proposal for the earliest safe incomplete persistence stage.

## Supersession boundary

The concrete PR-202 evidence, historical PR-203 trees, old live target
envelope, old target evaluation, old Zenodo queue, and their receipts remain
historical evidence only. Their hashes and remote gates do not transfer to this
current-main candidate.
