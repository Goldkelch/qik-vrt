# Autonomous issue processing contract

## Effect

Every newly opened, reopened, or edited non-pull-request issue triggers the repository-native issue processor. Existing issues can be processed through `workflow_dispatch` with their issue number.

The processor:

1. fetches the authoritative GitHub issue payload;
2. materializes a canonical request and SHA-256 evidence;
3. gathers deterministic, size-bounded repository context;
4. compiles only a deterministic, schema- and policy-bounded work-unit disposition;
5. emits truthful status metadata;
6. validates the evidence bundle and no-false-pass rules;
7. creates or updates `issue-agent/<number>`;
8. opens a reviewable pull request;
9. comments the status and PR URL on the issue.

## Non-negotiable gates

- No automatic merge.
- No automatic issue closure.
- Unknown or unsupported prose never becomes an invented executable patch.
- A request without an allowlisted deterministic handler becomes `BLOCKED_WITH_NEXT_ACTION` with a precise reason and next native event.
- Generated work remains non-terminal until exact-head checks and independent authority establish a stronger state.
- The issue payload and its digest remain part of the committed evidence.
- Formal derivation, repository evidence, hypothesis, and empirical confirmation remain distinguishable.

## Authentication and deterministic compilation

The workflow uses GitHub's ephemeral `GITHUB_TOKEN` with only the repository permissions needed for its repository effects: `actions: write`, `contents: write`, `issues: write`, and `pull-requests: write`. It does not request `models: read` and does not invoke GitHub Models or another external inference endpoint.

`scripts/issue_agent/compile.py` admits only deterministic handlers. Currently the ruleset/GitHub-App authority class is recognized and yields `MISSING_GITHUB_APP_RULESET_AUTHORITY`; unrecognized requests yield `UNSUPPORTED_DETERMINISTIC_WORK_UNIT`. Both are fail-closed `BLOCKED_WITH_NEXT_ACTION` dispositions rather than fabricated implementation claims.

## Processing an existing issue

Run **Autonomous issue processing** with the issue number when an explicit native dispatch is required for an issue that predates the workflow. Normal progression remains event-driven; no polling loop or blind retry is introduced.

After persisting the issue candidate, the processor sends exactly one native
dispatch to the existing completion-authority observer, binding issue number,
pull-request number and head. It rereads the unchanged candidate and records
`HOLD_UNVERIFIED / AWAIT_EXACT_OBSERVER_RECEIPT`; dispatch acceptance does not
complete the issue or its review/Main-integration obligation. It does not scan
workflow runs, sleep, impose a queue deadline or retry an uncertain dispatch.

The observer owns the receiving event and its completion, including delayed
execution. It rejects a mismatched PR/head, binds the live base SHA, publishes
the existing issue receipt and reads back its complete body and signer. It
reobserves the same repository/PR/base/head before and after publication.
Only that exact receipt supplies the observer result; required review and
protected Main adoption remain separate native actions.

## Evidence location

Each processing run writes:

```text
evidence/issues/<number>/
├── REQUEST.json
├── REQUEST.sha256
├── CONTEXT.md
├── ANSWER.md
└── STATUS.json
```

The generated branch and PR are work products, not evidence of correctness by themselves. Exact-head validation, required review, promotion, external publication and effect readback remain distinct evidence classes.
