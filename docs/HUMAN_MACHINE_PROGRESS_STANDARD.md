# QIK-VRT Human–Machine Progress Standard

Status: normative repository standard  
Version: 2.1

## Purpose

Every externally meaningful repository operation MUST remain visible to the human operator. The client MUST emit a complete progress frame immediately before and immediately after every discrete GitHub action, and whenever an observed workflow, job, or step changes state.

A later summary does not compensate for a missing frame. Prose does not replace execution telemetry.

## Operational foundation

The working method begins with an explicit, inspectable distinction: inputs,
states, effects, evidence and unknowns must not be collapsed into one label.
`0` is the neutral element of addition and `1` the neutral element of
multiplication; these are the basic algebraic reference points used here to
keep identity, composition and change distinct. The operational path is:

```text
UNTERSCHIED → INFORMATION → RELATION → KAUSALORDNUNG →
MODELL → IMPLEMENTIERUNG → TEST → DOKUMENTATION → EVIDENZ → RÜCKBEZUG
```

This standard does not itself prove a mathematical, physical, legal or
scientific claim. Formal derivations, empirical observations and normative
decisions retain their separately bound evidence and review requirements.

## Definition of Ready

Before implementation, a change has a bounded scope, current source/ref,
observable acceptance criteria, risk and effect classification, applicable test
plan, documentation plan, provenance/rights considerations and known
authorization limits. Missing information is a `HOLD` or `BLOCK`, not an
invitation to invent requirements.

## Test-first engineering loop

For behavior changes, establish the smallest reproducible positive or negative
test first; implement until it passes; then refactor while all applicable tests
remain green. Choose the smallest relevant mix of unit, contract, integration,
security, accessibility, browser, workflow and end-to-end tests. Existing
regressions remain binding when their source, behavior and safety boundary
still apply.

## Repository delivery closure

An authorized repository mutation reaches the scoped state
`REPOSITORY_DELIVERY_VERIFIED` only after all applicable gates complete in this
order:

```text
SCOPE_AND_IMPLEMENTATION_BOUND
→ TARGETED_REGRESSION
→ DOCUMENTATION_DISPOSITION
→ REPOSITORY_INTEGRITY_MATERIALIZED
→ EXACT_HEAD_TEST_GATE
→ REMOTE_REF_REOBSERVED
```

Documentation is complete only when it has been updated for the behavioral
change or explicitly marked `NOT_APPLICABLE` with a reason. Integrity is
complete only after regeneration for intentional changed bytes and verification
of the final candidate. Remote reobservation binds repository, target ref,
head SHA, root tree and observation time after the requested push, merge or
other repository effect. A local commit, push, merge, green unrelated run, or
zero exit code alone does not establish delivery closure.

For public browser interfaces, the applicable closure additionally records
source/security regression, live page load, intended interaction, declared
CORS/same-origin reads, rejection of forbidden input, and opt-in voice/device
behavior. A denied microphone, unavailable speech engine or unobserved audio
output is a bounded result, not a failure to be hidden or a success to be
claimed.

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

## Terminal semantics

`PASS` is scope-bound and requires referenced evidence. Terminal `PASS` is forbidden while any required gate remains pending, running, failed, blocked, or unverified. A concrete repairable failure remains an active persistence run; the client continues repair rather than returning explanatory prose as a substitute for execution.
