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
   one history-preserving server-side current-main update through GitHub's
   `update-branch` endpoint with an exact expected-head compare-and-swap.

Every run performs at most one repair action.

## Privileged execution boundary

The `pull_request_target` controller never checks out or executes candidate code.
This is a hard invariant. Discovery reads only GitHub metadata and exact refs from
the trusted current-main workflow definition.

For a stale, conflict-free internal PR, the controller:

- verifies that the PR head repository is the Authority repository;
- reobserves the literal remote source head;
- records the exact pre-rebind PR file set;
- verifies that Authority `main` still equals the trusted checked-out main commit;
- calls GitHub's server-side `update-branch` endpoint with `expected_head_sha`;
- reobserves the new branch head;
- requires the PR-relative file set to remain byte-for-byte the same list;
- verifies that the new head contains the exact Authority commit selected by the
  controller;
- dispatches fresh exact-head verification for the new head.

The controller does not clone or run the candidate with a write token, does not
construct the merge locally, does not force-push, and does not interpret a
successful rebind as successful candidate tests. The resulting head must execute
fresh repository gates in its own bounded exact-head context.

## Other productive mutation boundaries

Repository Integrity drift is delegated to the existing registered materializer;
the Mesh repair controller does not write the projection files itself. The global
controller is serialized with `cancel-in-progress: false` and permits at most one
repair action per run.

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
