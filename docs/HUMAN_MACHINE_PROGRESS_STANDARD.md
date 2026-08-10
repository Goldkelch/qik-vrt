# QIK-VRT Human–Machine Progress Standard

Status: normative repository standard  
Version: 2.0

## Purpose

Every externally meaningful repository operation MUST remain visible to the human operator. The client MUST emit a complete progress frame immediately before and immediately after every discrete GitHub action, and whenever an observed workflow, job, or step changes state.

A later summary does not compensate for a missing frame. Prose does not replace execution telemetry.

## Non-recursive telemetry boundary

The GitHub reads and writes used solely to observe or persist a progress frame form one atomic telemetry cycle. They do not recursively require progress frames of their own; otherwise no finite implementation could persist the first frame. All task-advancing GitHub operations outside that atomic telemetry cycle remain subject to the before-and-after frame rule.

## Required frame

```text
Repository: <owner/name>
Branch: <branch-or-ref>
Commit: <sha-or-pending>
Operation: <precise operation>
Frame: <monotonic sequence> — <transition kind>

[██████████░░░░░░░░░░] 50%

✓ completed gate or action
⟳ running gate or action
□ pending gate or action
✗ failed gate or action
! blocked gate or action

BLOCKER: <none or exact blocker>
NEXT: <next executable action>
STATUS = IDLE | RUNNING | WAITING | PASS | BLOCK | FAIL | TIMEOUT | CANCELLED
```

The percentage is relative progress over declared gates or observed steps, not an elapsed-time prediction. A visual percentage never proves correctness.

## Discrete GitHub actions

The frame boundary applies to every client operation that advances or verifies the task, including:

1. branch or ref creation/update;
2. file create/read/update/delete used for the task;
3. commit, pull-request, review, merge, tag, release, or publication operations;
4. workflow/run/job/step observation and log or artifact inspection;
5. status, check, integrity, provenance, proof, and deployment verification; and
6. retry, repair, synchronization, or mirror operations.

Multiple task-advancing GitHub actions MUST NOT be batched behind one progress frame.

## Workflow observation contract

A persistent watcher MUST:

1. use a repository/PR-scoped concurrency group so watchers never overlap;
2. complete one observation cycle before starting another;
3. observe the newest relevant run per workflow and every exposed job and step;
4. persist a fresh full frame whenever the workflow/job/step state signature changes;
5. suppress unchanged duplicate frames;
6. wait five seconds only after the prior frame has been persisted and only while work remains active; and
7. finish with a terminal frame containing decisive run, job, check, and evidence identifiers.

The human projection MUST be available in the repository-native client surface, at minimum a persistent pull-request comment and the GitHub Actions step summary. Machine state MUST conform to `schemas/human_machine_progress.schema.json`.

That schema preserves `qikvrt_human_machine_progress_v1` for live workflow
frames and defines `qikvrt-ai-progress/3.1` for durable root handoff snapshots.
A durable snapshot may carry several explicitly bounded scopes; a nested
scope-specific `PASS` never promotes an incomplete sibling scope or the
top-level repository effect state.

Version 3.1 makes projection-input evidence portable between canonical
repositories with different commit histories. The committed capsule is an
exact selected-path Git-object closure, not a worktree copy or a network
fallback. Its commit, tree, path, mode, blob, size, SHA-256 and capsule-file
bindings are verified offline; available local Git objects are a mandatory
second check. This proves only the declared historical projection inputs.

## Tracked status artifacts

`AI_PROGRESS.json` and `AI_STATUS.md` are durable handoff snapshots. When no repository operation owns them, they MUST be `IDLE` or terminal. A tracked root snapshot MUST NOT remain falsely `RUNNING`, `WAITING`, or `PENDING` after its owner has ended.

Live workflow frames may be persisted by `QIKVRT live status watch`, but a
branch-level watcher is telemetry only. Exact PR, check, merge, promotion, or
synchronization claims require evidence bound to the current commit and run.
The tracked root snapshots identify the last stable handoff state without
promoting watcher output into exact-head proof.

## Repository runtime authority

The repository is the durable runtime authority. Chat sessions and individual artificial-cognitive clients are disposable transport surfaces. The repository MUST accumulate and version:

- exact tool and dependency locks;
- checksums, provenance, and licenses;
- bootstrap and recovery logic;
- positive, negative, integrity, and security tests;
- runtime-cache contracts and receipts;
- progress and failure diagnostics; and
- verified improvements to ordering, reuse, throughput, and recovery.

Existing components MUST be reused, extended, parameterized, generalized, or refactored before parallel machinery is created.

## Cache semantics

Verified tool archives, wheelhouses, package stores, and build products MAY be reused through exact-key caches. Cache hits accelerate execution but never replace current-tree proof, integrity, provenance, security, review, or release gates. Credentials and mutable authentication state MUST never enter a cache.

A cold cache and a warm cache MUST preserve the same correctness semantics. Missing cache content may reduce throughput; it must not remove reproducible capability while the locked upstream material remains available.

## Deadlock-preventive workflow orchestration

Every workflow in the exact Git tree MUST declare a repository-scoped
`concurrency` group and an explicit `cancel-in-progress` policy. Every job MUST
declare `timeout-minutes` in the closed interval 1 through 360. Job `needs`
edges and `workflow_run` edges MUST form directed acyclic graphs. The workflow
executor snapshot audits these properties from exact Git blobs, so an
unbounded or cyclic workflow cannot produce a valid structural receipt.

Repository work is acquired in the single total lane order declared by
`state/autonomy/WORKFLOW_EXECUTOR_MESH_CONTRACT_V1.json`. A work item that is
waiting, blocked, or complete MUST NOT retain a live lease. Leases are bound to
one owner, one exact conflict scope, one state signature, and a caller-supplied
observation epoch; they expire after at most 900 seconds. Renewal without a
changed state signature is quarantined. These rules remove hold-and-wait and
circular-wait from the repository scheduler model, while explicit job bounds
remove an indefinitely retained execution slot.

`AUTHORITY_CANDIDATE` work MAY run in up to four path-disjoint conflict
components. The three generated integrity projections do not create a semantic
conflict by themselves because every candidate regenerates and verifies them
before integration. Actual semantic path overlap, an active scope-bound lease,
or a serialized lane remains exclusive. A blocked component and a rejected
dependency cycle MUST NOT stall an independent component. Selection is stable
by oldest progress epoch and then work ID, preventing a permanently blocked
lowest-numbered pull request from starving unrelated work.

Authority promotion, Mirror porting and promotion, mesh-node connection, and
external effects remain serialized. Mirror work requires a completed Authority
dependency. The three intentional cross-workflow Reserve/Finalize concurrency
groups are enumerated in the contract; any other duplicated group blocks the
topology audit.

This is a deadlock-prevention guarantee for repository-controlled scheduling
under the declared finite timeout and lease assumptions. It does not assert
that GitHub, a network, a runner, or another external service can never become
unavailable. Such unavailability is a bounded or fail-closed blocker and never
authorizes an integrity, promotion, publication, or completion claim.

## Terminal semantics

`PASS` is scope-bound and requires referenced evidence. Terminal `PASS` is forbidden while any required gate remains pending, running, failed, blocked, or unverified. A concrete repairable failure remains an active persistence run; the client continues repair rather than returning explanatory prose as a substitute for execution.
