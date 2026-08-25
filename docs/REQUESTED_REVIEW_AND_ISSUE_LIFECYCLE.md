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
eligible same-repository pull request supplied by an exact native event or an
explicit exact-PR-and-head dispatch, whose bytes can be observed. An explicit human
review request remains a useful event signal, but it is not an execution
prerequisite.

An explicit dispatch of that executor is a technical-review action only. Its
completed manual workflow run is intentionally not a source for the required
Code-Owner status; an operator who needs that status reobserved dispatches
`QIKVRT required code-owner review` separately with the same exact PR number.

For every review, the executor must act without deliberate queueing:

1. reobserve the repository role, current base commit and tree, exact candidate head and tree, changed paths, comments, prior reviews, unresolved threads, every queued or active competing writer, supersession state and every applicable exact-head gate;
2. inspect the actual diff and record concrete findings;
3. return one of `APPROVE`, `REQUEST_CHANGES`, or `COMMENT_WITH_BLOCKER` as soon as the evidence supports that disposition;
4. sort and bind the reviewed scope, hash that scope and the exact diff bytes, and derive one SHA-256 review fingerprint from the canonical trusted evaluator/workflow blobs, repository, pull-request eligibility and draft state, base, head, tree, scope, declared and observed diff, discussion, latest gate identity/attempt/jobs and active-writer binding;
5. derive exactly one causal next action using the D0 mapping below;
6. distinguish an automated technical Mesh disposition from a natural-person or independent Code-Owner disposition and from GitHub's account-level review state.

Every exact event also produces a canonical `review_intake` bound into the
receipt fingerprint. It records the native event-payload SHA-256, event action,
event actor, explicitly requested user or team, one declared reason label and the policy-derived
priority class/rank; the receipt separately binds the current observed
requested-reviewer set. It is not an
unconstrained user input. The only current reason labels are:

- `qikvrt-review:security` → `SECURITY_OR_INTEGRITY`;
- `qikvrt-review:owner` → `OWNER_DECISION`;
- `qikvrt-review:standard` → `STANDARD`.

No reason label remains `UNSPECIFIED`; two or more of these labels are a
fail-closed `REVIEW_REASON_AMBIGUOUS`, never an invented priority. A priority
is then derived in this fixed order: security/integrity requests by the
Product Owner or required Code Owner (`P0`), Product Owner → required Code
Owner (`P1`), required-Code-Owner target (`P2`), another explicit review
request (`P3`), and any other exact automatic reobservation (`P4`). A
`review_request_removed` event is an automatic reobservation only; it is not
treated as an active request. If a `review_requested` target has disappeared
before the exact observation, the receipt is `REVIEW_REQUEST_STALE / D0=2`;
the former request is never silently carried forward.

GitHub Actions can bind and classify one event but offers no cross-event
priority ordering or native delivery identifier. The Actions receipt therefore
states that limitation explicitly. A real ordering across concurrent requests
requires the separately provisioned GitHub App webhook broker described in
`docs/QIKVRT_GITHUB_APP_TARGET_BLUEPRINT.md`; it must order signed native
deliveries by the policy rank and delivery-time/id tie-break without cancelling
an in-progress exact review. Neither a scheduled scan, a rotating PR selector,
nor an Actions-only pseudo-queue is permitted.

The exact role-local receipt is appended on
`refs/heads/qikvrt/mesh-review-ledger-v1`. Its paths are:

- `state/mesh/reviews/pr-<N>/<head>/<fingerprint>.json`
- `state/mesh/reviews/pr-<N>/<head>/<fingerprint>.chunks.json`
- `state/mesh/reviews/pr-<N>/<head>/<fingerprint>.chunks/<zero-padded-index>.bin`

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
`pull_request_review_thread` workflow trigger. A resolve/unresolve-only thread
transition is therefore `UNOBSERVABLE_WITHOUT_EXACT_EVENT`: it does not permit
a scheduled scan, a rotating candidate selection, a review dispatch, or a
metadata mutation. The next exact repository event or explicit dispatch may
reobserve a bound subject; no prior evidence is transferred.

The complete diff is transported as ordered, content-addressed packets of at
most 1 MiB. Its canonical manifest binds an explicit packet count, every
offset, packet byte count and packet SHA-256, the total byte count and total
SHA-256, the deterministic packet paths and a SHA-256 over the canonical
manifest projection. The receiver rejects a missing, reordered, altered,
oversized or surplus packet, a manifest-path mismatch, or a manifest whose
digest does not match. Only after every packet reconstructs the total digest
does the ledger accept the review package. The bounded transport therefore
does not turn a complete 2 MiB-plus diff into `REVIEW_BYTES_UNAVAILABLE`; it
does not silently lose the handoff, invent a favorable result, or reuse an
earlier receipt. Head, tree, scope, diff, policy or intake drift still
invalidates the receipt.

The ledger is initialized as an orphan root commit containing only the first
exact receipt and diff; it therefore does not copy a predecessor repository
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
The stored receipt must also verify its own seal; the stored manifest must be
byte-identical to the sealed canonical transport manifest; and the stored
ordered packets must reassemble to the regenerated diff byte for byte and to
its total SHA-256. Any disagreement stops the next mutation and remains
`HOLD_UNVERIFIED`.

The same pull-request head may be reviewed again only when its causal evidence
fingerprint changed, for example because a required workflow attempt, active
writer, discussion thread or applicable gate changed. An identical fingerprint
is an idempotent `D0=0 NOOP`, never a duplicate receipt.

Review receipts and review-diff manifests/packets are never committed to the
reviewed candidate branch or to `main`. Doing so would mutate the reviewed
head, immediately stale its evidence and create a recursive evidence-commit/
review loop. The candidate base, head, tree, scope and diff are therefore
unchanged by feedback persistence.

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

The separately versioned `OWNER-NATIVE-ACCOUNT-REVIEW-AUTOMATION-V1` does not
change that `github-actions[bot]` boundary. It permits a second, explicit
adapter only when GitHub receives a self-identifying `type=User` credential for
the selected repository account and returns that exact account in the review
readback. The adapter uses `Goldkelch` or `ingolf-lohmann` solely as the
non-author counterpart, never exposes its credential to candidate bytes, and
keeps the account credentials in separate signer jobs. Its review body is
marked as delegated account automation; it is not an independent
natural-person review and does not create merge, release, publication,
deployment, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE` authority. The full
provisioning and fail-closed checks are in
`docs/DELEGATED_NATIVE_ACCOUNT_REVIEW_AUTOMATION.md`.

The platform-effective repository-reviewer set is `Goldkelch` and
`ingolf-lohmann`.  The pull-request author is removed from the eligible set for
that pull request, so the other configured account is the required counterpart.
Ingolf Lohmann as a natural person does not perform these reviews.  ChatGPT may
produce a clearly attributed technical disposition but does not normally supply
the native repository-account approval.  Account labels establish only the
platform signer recorded by GitHub; they do not prove distinct natural persons
or organizational independence.

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
