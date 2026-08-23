# Mesh Autonomous Deterministic Repair V1

## Purpose

This work unit closes the bounded gap between detecting a deterministic repository
problem and executing one safe repair without waiting for an external operator.

The controller is deliberately not a universal code-generating agent. It solves
registered deterministic classes and preserves an exact fail-closed `HOLD` for
unknown or executed failures. This keeps the following distinctions intact:

```text
REQUESTED != EXECUTED != OBSERVED != ACKNOWLEDGED
CAUSALITY != SEQUENCE
AUTHORITY_MAIN != MIRROR_MAIN
```

## Repair classes

The current policy registers four executable classes:

1. A latest `action_required` workflow with zero jobs, or a head with no exact-head
   observation, dispatches trusted exact-head verification and the bounded named
   gate surface.
2. A recoverable dispatch-only error may be re-dispatched; an executed verifier
   failure remains `HOLD`.
3. A registered repository-integrity projection drift dispatches the existing
   repository-native materializer.
4. A conflict-free internal PR that is behind current Authority main may receive
   one history-preserving merge/rebind. The rebind is accepted only when its
   resulting PR-relative file set stays within the original PR scope plus the
   canonical Integrity trio and all repository tests pass.

Every run performs at most one repair action.

## Productive mutation boundary

Only the current-main rebind action mutates a PR branch in this controller. It:

- operates only on an open same-repository PR;
- reobserves the literal remote source head before work;
- uses a global serialized workflow lease with `cancel-in-progress: false`;
- performs a non-force merge of current `main`;
- regenerates and verifies repository Integrity;
- runs the complete repository gates;
- rejects every path outside the original PR scope plus the exact Integrity trio;
- reobserves the original remote source head immediately before commit/push;
- pushes only a history-preserving descendant;
- dispatches fresh exact-head verification for the resulting head.

It never merges a PR into `main`, never submits an independent review, and never
executes publication, deployment, general Effect-Acknowledgement, or physical
hardware effects.

## Unknown problems

An executed failure without a registered repair recipe remains:

```text
HOLD / EXECUTED_FAILURE_REQUIRES_REPAIR_RECIPE
```

This is intentional. Autonomous repair must not turn uncertainty into a blind
retry or silently fabricate source code, review authority, external effects, or
physical observations. New deterministic repair classes are added as explicit,
tested recipes.

## Expected operational effect

For the recurring bot-materialization pattern:

```text
semantic head
  -> repository Integrity materialization
  -> bot-authored exact head
  -> action_required / zero jobs
```

the controller revalidates the current branch, publishes an idempotence status,
and explicitly dispatches trusted exact-head verification plus the bounded named
gate surface. Because `workflow_dispatch` and `repository_dispatch` are explicit
execution edges, the repaired tree no longer depends on an owner-authored zero-diff
carrier merely to obtain fresh execution.

This is a repository-internal execution repair. It is not a merge, approval,
release, publication, deployment, general network claim, physical-hardware claim,
`PASS`, `FINAL_PASS`, or general Effect-Acknowledgement.
