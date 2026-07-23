# QIK-VRT Human–Machine Progress Protocol

## Purpose

During repository, build, verification, publication, deployment, or GitHub Actions work, every artificial-cognitive client MUST behave like a visible engineering client rather than a conversational black box.

The normative authority is `docs/HUMAN_MACHINE_PROGRESS_STANDARD.md`. The machine-readable contract is `policy/HUMAN_MACHINE_PROGRESS_PROTOCOL.json`, and each machine frame conforms to `schemas/human_machine_progress.schema.json`.

## Mandatory live format

Immediately before and immediately after every task-advancing GitHub action, and whenever an observed workflow, job, or step changes state, the client MUST emit a fresh complete progress frame:

```text
Repository: <owner/repo>
Branch: <branch-or-ref>
Commit: <sha-or-pending>
Operation: <precise operation>
Frame: <sequence> — <transition kind>

[██████░░░░] 60%

✓ completed step
⟳ current step
□ pending step
✗ failed step
! blocked step

BLOCKER: <none or concrete blocker>
NEXT: <next executable action>
STATUS = IDLE | RUNNING | WAITING | PASS | BLOCK | FAIL | TIMEOUT | CANCELLED
```

A GitHub action includes every connector/API mutation or read that advances or verifies the task: branch creation, file operations, commit, pull request, workflow observation, job or log inspection, review, merge, ref update, release, publication, synchronization, and verification. Silence between such actions is prohibited. A later summary does not compensate for a missing intermediate frame.

## Non-recursive telemetry boundary

The GitHub reads and writes used only to observe or persist one frame form one atomic telemetry cycle. They do not recursively require their own frames; otherwise no implementation could emit its first frame. This exception does not cover task-advancing GitHub operations.

## Rules

1. Work first; explain only what is necessary for execution or a concrete blocker.
2. Show repository, branch/ref, commit SHA, operation, sequence, and transition kind whenever known.
3. Show one progress bar with an integer percentage from 0 through 100.
4. Distinguish completed (`✓`), running (`⟳`), pending (`□`), failed (`✗`), and blocked (`!`) steps.
5. Report only verified facts. Never convert transport success, an exit code, or a model assertion into `PASS`, `DONE`, publication, deployment, merge, or symmetric canonicality.
6. Emit a complete frame before and after every discrete GitHub action and at every workflow/job/step state transition. No batching, omission, or replacement by prose is permitted.
7. Observation cycles are serial and non-overlapping. A changed frame is persisted before the next cycle; while work remains active, the next cycle begins only after a five-second pause.
8. On completion, show the final commit/merge/release identifiers and all decisive checks.
9. On failure, name the exact failing workflow, job, step, ref, SHA, error, and next remediation action.
10. `AI_PROGRESS.json` and `AI_STATUS.md` are durable root snapshots. They are `IDLE` or terminal whenever no persistent owner is active; stale `RUNNING` or `WAITING` snapshots are prohibited.
11. Live workflow state is persisted in one pull-request comment and in the GitHub Actions step summary by `QIKVRT live status watch`.
12. All AI-specific adapter files point to the canonical `/AI` handoff and may not redefine this protocol inconsistently.
13. `REUSE_BEFORE_CREATE` applies to status handling: existing status emitters, observers, workflows, projections, schemas, and tests are extended before a parallel mechanism is introduced.

## Repository runtime objective

The repository is the durable runtime authority. Chat sessions are disposable transport surfaces. Required tools, exact versions, checksums, bootstrap logic, cache contracts, provenance, tests, runtime receipts, and recovery procedures accumulate in the repository so that a new authorized client can reconstruct the runtime without prior conversation memory.

The repository runtime improves cumulatively by reusing and refining existing components. Tool caches accelerate execution, while committed locks, manifests, provenance, bootstrap code, and acceptance tests preserve reproducibility. Credentials, mutable authentication state, and unverified binaries never become runtime-cache authority.

## State semantics

- `IDLE`: the tracked handoff is ready and no persistent operation owns it.
- `RUNNING`: work is actively progressing.
- `WAITING`: an external system is running or a review/approval is pending.
- `PASS`: all declared gates for the stated scope are verified.
- `BLOCK`: a concrete blocker prevents continuation.
- `FAIL`: an executed gate failed.
- `TIMEOUT`: the declared observation or execution window ended without terminal verification.
- `CANCELLED`: the operation was explicitly stopped.

`PASS` is scope-bound. It identifies the verified repository, ref, source SHA, checks, and evidence. Visual progress never proves correctness.

## Communication boundary

Compact execution telemetry is mandatory during a persistence run and is not a final conversational return. Explanatory conversation remains subordinate to execution, evidence, progress, recovery, and the verified terminal state.
