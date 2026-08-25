<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Requested review and issue lifecycle

## Owner rule

Product Owner Ingolf Lohmann requires every eligible repository candidate,
requested repository reviews and registered GitHub issues to receive a prompt,
evidence-bound disposition instead of remaining indefinitely pending. A human
review request is not a prerequisite for the repository Mesh to review an
eligible same-repository pull request.

This contract applies to `Goldkelch/qik-vrt` and `ingolf-lohmann/qik-vrt`. It is repository-internal governance. It does not bypass GitHub account rules, branch protection, required checks, external credentials, publication boundaries, or the distinction between a natural-person decision and the GitHub identity that signs an API event.

## Repository-Mesh self-review feedback plane

The existing `QIKVRT requested review executor` is the role-local Mesh
self-review feedback plane. It runs from trusted repository code for every
eligible same-repository pull request whose bytes can be observed. An explicit
human review request remains a useful event signal, but it is not an execution
prerequisite.

For every review, the executor must act without deliberate queueing:

1. reobserve the repository role, current base commit and tree, exact candidate head and tree, changed paths, comments, prior reviews, unresolved threads, every queued or active competing writer, supersession state and every applicable exact-head gate;
2. inspect the actual diff and record concrete findings;
3. return one of `APPROVE`, `REQUEST_CHANGES`, or `COMMENT_WITH_BLOCKER` as soon as the evidence supports that disposition;
4. sort and bind the reviewed scope, hash that scope and the exact diff bytes, and derive one SHA-256 review fingerprint from the canonical trusted evaluator/workflow blobs, repository, pull-request eligibility and draft state, base, head, tree, scope, declared and observed diff, discussion, latest gate identity/attempt/jobs and active-writer binding;
5. derive exactly one causal next action using the D0 mapping below;
6. distinguish an automated technical Mesh disposition from a natural-person or independent Code-Owner disposition and from GitHub's account-level review state.

The exact role-local receipt is appended on
`refs/heads/qikvrt/mesh-review-ledger-v1`. Its paths are:

- `state/mesh/reviews/pr-<N>/<head>/<fingerprint>.json`
- `state/mesh/reviews/pr-<N>/<head>/<fingerprint>.diff`

New receipts declare `qikvrt_mesh_review_diff_manifest_v1`; the `.diff` path
then contains canonical JSON rather than raw candidate bytes. The manifest
describes at most 64 contiguous chunks named
`<diff_path>.part-<zero-padded-index>`. Every non-final chunk is exactly 1 MiB,
the final chunk is between one byte and 1 MiB, and the bounded aggregate is at
most 64 MiB. Exact non-boolean integer fields, canonical names, per-chunk
SHA-256, full length and full SHA-256 are validated before any chunk is
fetched. Only receipts without a transport-format marker retain legacy raw
`.diff` compatibility; an invalid declared manifest never falls back to raw.

The trusted-main observer is the only producer of this envelope. It requires
its local checkout SHA and tree to equal the reobserved `main`, binds the
evaluator and workflow blobs, derives the complete NUL-delimited path scope
from local Git without the pull-request-files API cap, and never imports or
executes candidate code. Gate evidence is accepted only with the trusted
workflow ID and path, the `pull_request` event, the exact candidate head and
the complete canonical job projection. A successful required run must contain
at least one completed successful job; a skipped-only required run is
`ZERO_EXECUTED_JOB_GATE`, never success. Issue comments, reviews, review comments and thread state
are represented by canonical IDs, timestamps, states and body hashes. The
Mesh bot's own marked `COMMENT` projection is excluded from that causal
discussion set so feedback does not invalidate itself recursively.
Issue-comment events enter the trusted executor directly; review and inline
review-comment mutations enter through the permissionless Code-Owner observer's
completed workflow signal. GitHub Actions exposes no native
`pull_request_review_thread` workflow trigger, so a resolve/unresolve-only
thread transition is detected by a schedule that starts a rotating scan every
five minutes. With multiple eligible pull requests this is not a five-minute
per-PR latency guarantee. That platform gap is recorded honestly; it is not
described as immediate event delivery and it never permits stale evidence to
authorize a mutation.

The ledger is initialized as an orphan root commit containing only the first
exact receipt, diff manifest and chunks; it therefore does not copy a predecessor repository
tree into the evidence plane. It is append-only. Its sole writer uses a non-force,
fast-forward compare-and-swap against the reobserved ledger head. A competing
write, missing predecessor, non-fast-forward update, or post-review subject
drift yields `HOLD`; it never yields a replacement receipt or a force update.
Receipts are role-local and cannot be transferred between Authority, Mirror or
another Mesh node as if the review had executed there.

The observer regenerates the complete snapshot, diff and receipt before the
ledger read, immediately before and after ledger initialization or compare-and-
swap, and before and after each PR-comment or status mutation. Both the
evidence fingerprint and sealed receipt-payload hash must remain byte-exact.
The stored receipt must also verify its own seal, and strict reconstruction of
the stored manifest/chunks must equal the regenerated diff byte for byte. Any disagreement stops the next
mutation and remains `HOLD_UNVERIFIED`.

The same pull-request head may be reviewed again only when its causal evidence
fingerprint changed, for example because a required workflow attempt, active
writer, discussion thread or applicable gate changed. An identical fingerprint
is an idempotent `D0=0 NOOP`, never a duplicate receipt.

Review receipts and `review.diff` are never committed to the reviewed candidate
branch or to `main`. Doing so would mutate the reviewed head, immediately stale
its evidence and create a recursive evidence-commit/review loop. The candidate
base, head, tree, scope and diff are therefore unchanged by feedback
persistence.

After the ledger receipt has been written and read back byte-exactly, the same
result may be projected as an Actions artifact, the exact-head status
`QIKVRT requested review execution`, and a pull-request `COMMENT`. Those are
projections of the receipt, not competing authorities. Existing downstream
controllers consume the workflow-completion and status transition and derive
their already bounded continuation; the feedback plane does not create a
parallel action router. A status is only a projection: immediately before any
promotion effect, the promotion controller must load the full-fingerprint
receipt and diff from the role-local ledger and regenerate them through the
same trusted-main observer. A stale same-head status never authorizes an
action. Any eligibility, base, head, tree, scope, diff, discussion, gate,
writer, fingerprint or receipt-payload mismatch remains `HOLD_UNVERIFIED`.
The pull-request title and body digests are part of the fingerprint, so an
`edited` event cannot reuse a prior same-head receipt or status.

The existing GitHub pull-merge REST operation compares the requested PR head
but has no compare-and-swap input for the reobserved base. It therefore cannot
prove that the checked base becomes the merge commit's immediate first parent
(`HEAD^1`) if `main` advances concurrently. Automated merge is fail-closed and
disabled. A technically favorable Mesh receipt derives only
`REQUEST_HISTORY_PRESERVING_EXACT_BASE_CAS_AUTHORITY`; it does not imply a
merge. Automatic draft-to-ready reclassification is also disabled: GitHub
offers no atomic expected-base-and-head compare-and-swap for that mutation,
and a `GITHUB_TOKEN`-authored `ready_for_review` event cannot establish the
required follow-on workflow cycle. A favorable draft review therefore derives
only `REQUEST_HISTORY_PRESERVING_READY_RECLASSIFICATION_AUTHORITY`, bound to
the trusted `github-actions[bot]` self-heal PR-body marker, same-repository
`automation/self-heal-*` head, unchanged marker-body digest and exact base/head.

The causal review states are fixed:

- `D0=0 NOOP`: the identical exact receipt is already persisted, or no new review action exists;
- `D0=1 HOLD`: an applicable gate is active or adverse, a finding or unresolved thread remains, the receipt is invalid, or the ledger compare-and-swap conflicts;
- `D0=2 REOBSERVE`: exact evidence is missing, stale, untrusted, zero-job, or the base, head, tree, scope or diff drifted;
- `D0=3 REQUEST_AUTHORITY`: the Mesh disposition supports continuation, but an exact independent Code-Owner disposition or another required authority is missing or stale.

A requested review may not be replaced by repeated requests, reminders, or status commentary when the connected client can inspect the candidate itself. A review may remain pending only for a precise blocker such as missing bytes, head drift, unavailable required evidence, unresolved security or rights questions, or a platform identity rule that prevents the requested account-level event.

The automated Mesh signer is `github-actions[bot]` and may submit only a
`COMMENT` review event. It must never submit `APPROVE` or `REQUEST_CHANGES` as
though it were the requested human, impersonate another GitHub identity, or
claim that GitHub recorded `APPROVED` when the platform stored `COMMENTED`.
The substantive automated finding is persisted accurately together with the
platform state. It never satisfies, replaces, weakens or transfers the separate
exact-head independent Code-Owner gate.

Review completion and feedback persistence do not themselves authorize merge,
promotion, release, deployment, Zenodo, DOI, IETF, `PASS`, `FINAL_PASS`,
`EFFECT_ACK_DONE`, Authority/Mirror equality, scientific confirmation or an
external effect. Every such completion claim remains false in the receipt.

## Issues

Every observed open issue must have a current repository-native lifecycle disposition. The allowed dispositions are:

- `EXECUTE_NOW`: the request is clear, supported, and technically actionable; begin or continue the smallest bounded work unit;
- `CLARIFICATION_REQUIRED`: a specific ambiguity prevents safe execution; record the minimum missing information and ask only the bounded clarification required;
- `BLOCKED_WITH_NEXT_ACTION`: the issue is valid but a precise internal or external blocker exists; record evidence, owner, retry condition, and the next technically possible action;
- `CLOSE_COMPLETED`: the requested result is already fully evidenced or has been completed through a canonical successor;
- `CLOSE_NOT_PLANNED`: the request is understood but intentionally outside the supported or authorized scope;
- `CLOSE_INVALID_OR_UNSUPPORTED`: the request is not reproducible, not traceable to evidence, internally contradictory, untrue, or technically unsupported.

An issue must not remain open merely because it is old, broad, inconvenient, or repeatedly retried. If actionable, it must progress. If unclear, it must be concretized. If completed, superseded, invalid, unsupported, or not planned, it must be closed with a concise evidence-bound reason. Closure is reversible, must preserve the discussion and provenance, and must not be used to hide a real unresolved defect.

No issue may be left in an unclassified waiting state. A `BLOCKED_WITH_NEXT_ACTION` disposition is not a generic parking state: it requires a deterministic failure class, evidence references, and a single continuation path.

## Execution and reporting

The fastest verified path is mandatory. Existing scripts, work units, review evidence, and issue-agent infrastructure must be reused before parallel machinery is created. Activity without a changed lifecycle predicate is not progress.

Report only material changes: a new disposition, a resolved or newly evidenced blocker, a head or scope change, a completed work unit, a closure, or a promotion-ready result. Preserve fail-closed scientific, provenance, security, rights, and external-effect boundaries.

## Machine authority

The normative machine-readable policy is
`policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json`. The natural-person
delegations are
`state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json`
and
`state/authorization/delegations/OWNER_MESH_REPOSITORY_SELF_REVIEW_FEEDBACK_V1.json`.
