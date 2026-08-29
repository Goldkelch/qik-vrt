# Deterministic repository-native issue intake

## Purpose

The issue-agent control plane prevents an owner work order from disappearing behind an optional
external model admission failure. It is event-driven and fail-closed. It materializes one exact
event and classifies it through a versioned repository handler when possible. Candidate-eligible
admission or closure results run a finite quadratic read/verify/plan epoch and create at most one
immutable candidate; redirects, rejections, unavailable inference, and blocking results stop at the
prepared evidence artifact.

This control plane is not a general coding agent. `EXECUTE_NOW` means that a bounded work unit was
admitted. It does not mean that the requested substantive implementation, article, formal proof,
merge, publication, deployment, or physical effect occurred. A substantive handler must have a
separately registered executor and digest-bound work products before completion can be claimed.
This revision registers exactly one fixed `(handler_id, handler_sha256)` pair in
`state/autonomy/ISSUE_AGENT_TYPED_EXECUTOR_CONTRACT_V1.json`: the root-blocker handler may produce
only an exact-main, bounded control-plane attestation. That attestation is not arbitrary issue-body
execution and is expressly not repair completion. Every other handler remains unmapped and must
stop at `HOLD_EXECUTOR_NOT_REGISTERED`.

## Events and exact binding

`issue-autonomous-processing.yml` accepts:

- `issues` actions `opened`, `reopened`, and `edited`;
- marker-shaped non-pull-request `issue_comment` actions `created` and `edited` from a trusted
  actor; only exactly one registered marker whose selected author is also trusted is
  candidate-eligible, while unknown, ambiguous, or untrusted marker authors fail closed;
- a direct owner `workflow_dispatch` that reobserves an exact issue and optional comment.

There is no cron, backlog scan, blind retry, mutable work branch, or forced update of an existing
ref. A direct manual dispatch of the main processing workflow is the only repository-native manual
replay path. The former resume wrapper was removed because a nested dispatch changes the platform
actor to `github-actions[bot]` and cannot preserve owner authority truthfully.

Every request fingerprint is SHA-256 over a canonical binding that includes the event and action,
issue number, selected-source timestamp, exact comment identity when applicable, actor, selected
author and association, selected-body digest, issue snapshot, deterministic context, Authority head
and tree, policy, registry, issue-agent code set, and canonically sorted active mesh nodes. Issue-body
fields must equal the bound issue snapshot. Comment URLs must match repository, issue, and comment
id. The Git head, tree, policy, registry, and code blobs are rederived before acceptance. The
fingerprint intentionally identifies the exact request rather than optional-model output. If an
immutable candidate already exists for that fingerprint, its validated stored status and
disposition are authoritative for reuse. A fresh optional-model result cannot change the class,
draft mode, or review boundary of that existing ref. A create race is resolved by the same rule.

For webhook events, the immutable event issue projection is compared with a fresh live GitHub
projection before materialization. Comment identity remains GitHub-platform provenance; binding the
observation does not convert it into a general physical or semantic claim.

## Handler order and model boundary

Routing order is fixed:

1. a structured external-agent failure is redirected without a candidate;
2. a registered typed owner marker is handled deterministically;
3. an unauthorized, unknown, or ambiguous marker is rejected deterministically;
4. only an untyped request may use the optional GitHub Models handler;
5. unavailable or malformed optional-model output becomes a canonical blocker and no candidate.

Handler id, descriptor, SHA-256, evaluation mode, disposition, reason, next action, and gate are
recomputed by the trusted validator. They are not trusted merely because `ANSWER.md` and
`STATUS.json` agree. `DONE` and `ISOLATE` are not issue-intake gate results.

## Finite N-squared epoch

The active node set is `Authority ∪ ACTIVE registry nodes`, sorted canonically. One epoch admits at
most 16 nodes and 256 lanes. For `N` nodes, lane `row * N + column` is emitted exactly once. Each
GitHub matrix job materializes and verifies one source/target-specific local handoff plan and binds
the request, event, context, answer, evaluation, epoch, matrix, lane, run id, and run attempt. The
plan explicitly records whether the relation is self or cross-repository, but it does not contact
the target repository or execute an arbitrary handler task. The surrounding control plane may
contact the Authority repository to read the issue, create one immutable candidate ref and PR, and
dispatch exact-head CI.

Fan-in accepts exactly the row-major lane set. A missing, duplicate, surplus, foreign, or changed
receipt produces `HOLD`. The repository-read-only candidate verifier later reobserves the exact issue-agent run
attempt and requires the full canonical set of successful lane job names; files alone are not
treated as independent runtime attestation.

## One candidate-ref writer

Only `candidate-writer` has `contents: write`. It reobserves Authority main, validates the reduced
bundle, regenerates and verifies the repository integrity trio, creates one single-parent commit,
and atomically creates:

```text
issue-agent/<issue>/<full-64-hex-fingerprint>
```

The transport is a Git push with an empty expected remote lease. That lease can create an absent
ref but cannot update an existing ref. If another identical event wins the race, the losing run may
reuse it only after proving one parent equals the bound Authority head, the diff is limited to the
epoch plus the integrity trio, global integrity verifies, the bundle validates, and the request
fingerprint is identical. The writer then derives disposition and candidate class from the selected
immutable bundle, never from a competing fresh inference.

The evidence path is:

```text
evidence/issues/<issue>/epochs/<full-64-hex-fingerprint>/
├── REQUEST.json
├── REQUEST.sha256
├── EVENT.json
├── EVENT.sha256
├── CONTEXT.md
├── ANSWER.md
├── EVALUATION.json
├── EVALUATION.sha256
├── STATUS.json
├── WORK_EPOCH.json
├── WORK_EPOCH.sha256
├── MATRIX.json
├── MATRIX.sha256
├── LANE_RECEIPTS.json
├── LANE_RECEIPTS.sha256
├── FANIN.json
└── FANIN.sha256
```

The writer creates or reobserves one exact PR and bot-authored issue receipt. Since events created
with `GITHUB_TOKEN` do not reliably start another workflow, it explicitly dispatches `QIKVRT CI`
at the reobserved candidate branch. Zero-job, skipped, cancelled, action-required, stale-head, or
failed runs are never success.

## Terminal and Authority boundaries

`issue-agent-autofinish.yml` is repository-read-only: it does not mutate Git refs, issues, or pull
requests, but it emits an Actions artifact and job summary as declared transport effects. It is
triggered by the exact explicitly dispatched
`QIKVRT CI` `workflow_run`, an exact PR/review event, or manual exact reobservation. It checks the
same-repository one-parent candidate, current Authority base, candidate and global integrity, the
successful CI run and jobs, and the successful N-squared issue-agent run and lane jobs. A work
admission must remain draft. An exact `(handler_id, handler_sha256)` registry match yields
`READY_FOR_EXACT_HEAD_EXECUTOR_DISPATCH`; an unmapped handler yields
`HOLD_EXECUTOR_NOT_REGISTERED`. The only current match is the fixed root-control-plane attestation
executor, whose output is an immutable draft candidate and not repair completion. A
receipt-eligible closure candidate must be non-draft and additionally requires exact-head
repository-account approval and no unresolved review threads. A newly exposed candidate already
observed after Authority-main drift is created as a draft `HOLD`. Every stale-base candidate is
`HOLD` and not verifier-eligible, even if a previously opened PR remains non-draft. Mutable
observations are repeated immediately before receipt emission.

The work-admission receipt binds the handler id and digest, selected work-order payload digest,
registry and registry-entry digests, trusted executor controller and workflow blobs, and exact
verifier workflow run/attempt provenance. The event-driven executor reobserves the attempt-qualified
artifact and candidate bytes, executes trusted current-main code only, and permits one create-only
`issue-executor/<issue>/<execution-id>` ref plus a draft PR. Candidate or issue-body code is never
executed. Sequential delivery reuses an existing semantically identical result; a collision holds.

GitHub Actions has no native review-thread-resolution trigger. If resolving the last thread is the
last state change, the external webhook integration or a direct manual exact dispatch must cause
reobservation; the repository does not claim an event it did not receive.

The handoff states are `READY_FOR_EXACT_HEAD_EXECUTOR_DISPATCH` for the one registered fixed
attestation, `HOLD_EXECUTOR_NOT_REGISTERED` for all unmapped admitted work, and
`READY_FOR_SEPARATE_EXPECTED_HEAD_AUTHORITY_DECISION` for a reviewed closure candidate. None of
these states is Authority-main takeover or substantive completion. No workflow here merges, closes
an issue, synchronizes a mirror, tags, publishes, deploys, or claims `PASS`, `FINAL_PASS`, or
general `EFFECT_ACK_DONE`.
