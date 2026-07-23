# QIK-VRT Human–Machine Progress Protocol

## Purpose

During repository, build, verification, publication, deployment, or GitHub Actions work, every artificial-cognitive client MUST behave like a visible engineering client rather than a conversational black box.

## Mandatory live format

Every meaningful status update MUST use this compact structure:

```text
Repository: <owner/repo>
Branch: <branch-or-ref>
Commit: <sha-or-pending>

[██████░░░░] 60%

✓ completed step
⟳ current step
□ pending step

BLOCKER:
<none or concrete blocker>

NEXT:
<next executable action>
```

## Rules

1. Work first; explain only what is necessary for execution or a concrete blocker.
2. Show repository, branch/ref, and commit SHA whenever known.
3. Show one progress bar with an integer percentage from 0 through 100.
4. Distinguish completed (`✓`), running (`⟳`), pending (`□`), failed (`✗`), and blocked (`!`) steps.
5. Report only verified facts. Never convert transport success, an exit code, or a model assertion into `PASS`, `DONE`, publication, deployment, merge, or symmetric canonicality.
6. While work is running, provide short status updates at meaningful phase changes; do not flood the user with repetitive messages.
7. On completion, show the final commit/merge/release identifiers and all decisive checks.
8. On failure, name the exact failing workflow, job, step, ref, SHA, error, and next remediation action.
9. Machine-readable state MUST be written to `AI_PROGRESS.json`; the human-readable projection MUST be written to `AI_STATUS.md` whenever a persistent repository workflow owns the operation.
10. All AI-specific adapter files MUST point to this protocol and may not redefine it inconsistently.

## State semantics

- `RUNNING`: work is actively progressing.
- `WAITING`: an external system is running or a review/approval is pending.
- `PASS`: all declared gates for the stated scope are verified.
- `BLOCK`: a concrete blocker prevents continuation.
- `FAIL`: an executed gate failed.
- `CANCELLED`: the operation was explicitly stopped.

`PASS` is scope-bound. It MUST identify the verified repository, ref, source SHA, checks, and evidence.

## Communication boundary

The client MUST not answer with long explanations when it can perform the next executable action. Explanations are subordinate to execution, evidence, progress, and recovery.
