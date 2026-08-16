<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Requested review and issue lifecycle

## Owner rule

Product Owner Ingolf Lohmann requires requested repository reviews and registered GitHub issues to receive a prompt, evidence-bound disposition instead of remaining indefinitely pending.

This contract applies to `Goldkelch/qik-vrt` and `ingolf-lohmann/qik-vrt`. It is repository-internal governance. It does not bypass GitHub account rules, branch protection, required checks, external credentials, publication boundaries, or the distinction between a natural-person decision and the GitHub identity that signs an API event.

## Requested reviews

When a review is requested, a conforming repository client or agent must act without deliberate queueing:

1. reobserve the current base, exact head, tree, changed paths, comments, prior reviews, unresolved threads, competing writers, and the observable Actions checks plus legacy statuses on the head and current test-merge contexts;
2. inspect the actual diff and record concrete findings;
3. return one of `APPROVE`, `REQUEST_CHANGES`, or `COMMENT_WITH_BLOCKER` as soon as the evidence supports that disposition;
4. bind the result to the exact base, head, tree, and reviewed scope;
5. distinguish a substantive Product-Owner or technical disposition from GitHub's account-level review state.

A requested review may not be replaced by repeated requests, reminders, or status commentary when the connected client can inspect the candidate itself. A review may remain pending only for a precise blocker such as missing bytes, head drift, unavailable required evidence, unresolved security or rights questions, or a platform identity rule that prevents the requested account-level event.

A client must never impersonate another GitHub identity or claim that GitHub recorded `APPROVED` when the platform stored only `COMMENTED`. In that case the substantive finding and Product-Owner disposition must still be persisted accurately, together with the platform limitation.

Review completion does not itself authorize merge, promotion, release, deployment, Zenodo, DOI, IETF, `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

### Executable review lifecycle

`tools/qikvrt_requested_review_snapshot.py`,
`tools/qikvrt_requested_review_lifecycle.py`, and
`tools/qikvrt_requested_review_target.py`,
`.github/workflows/qikvrt_requested_review_signal.yml`, and
`.github/workflows/qikvrt_requested_review_lifecycle.yml` implement the
immediate lifecycle check. A `pull_request_review` signal has zero token
permissions, no checkout, no artifact and no candidate-code execution in its
trusted default-branch definition. GitHub evaluates that event's workflow from
the PR merge context, however, so the signal is deliberately **not** a security
authority: it may be changed by a same-repository candidate. The trusted
executor consumes no output, artifact, candidate byte, shell fragment or runner
property from it. Repository Actions settings must separately prevent
untrusted-PR token escalation and self-hosted-runner use. Its completion only
prompts the separate write-capable executor, which runs and checks out the
exact SHA of its own trusted default-branch workflow definition and resolves
the current open PR again through GitHub APIs.

For a `workflow_run` trigger, the executor never treats `head_sha` as a PR
branch head. It re-fetches GitHub's run record, binds its repository, name and
workflow path, requires exactly one GitHub-supplied PR association, and then
re-reads the open PR. It reobserves after every listed PR workflow completion,
on legacy status events, and in a bounded default-branch periodic reconciliation
pass; the schedule is a liveness fallback, not a latency guarantee. A watched
workflow name can also complete for `push`, dispatch, schedule, or another
workflow event; anything other than the explicitly bound PR source event is a
safe no-op, rather than a failed lifecycle execution.

The snapshotter reobserves the current and candidate base, head and tree,
GitHub test-merge SHA, diff, changed paths, comments, reviews, user and team
request add/remove/re-request history, unresolved threads, competing or
superseded state, and check runs plus legacy statuses on both head and
test-merge contexts. It preserves the latest request event generation and
accepts a review only when it follows that request. It reads the PR identity
again after the expensive observations; any intervening state, base, ref, head,
tree, test-merge or PR-activity change is a fail-closed drift rather than a
mixed snapshot. Before and after a review write it reobserves again and binds
the review to `commit_id`.

When no requested eligible reviewer has recorded an exact-head `APPROVE`,
`REQUEST_CHANGES`, or structured `COMMENT_WITH_BLOCKER` disposition, it writes
one deduplicated exact-binding `COMMENT_WITH_BLOCKER` review and fails the
lifecycle check until the condition changes. A structured reviewer blocker must
begin with the exact first line
`<!-- qikvrt-review-disposition:COMMENT_WITH_BLOCKER -->`; a quoted or negated
word in prose is not a disposition. A recorded `REQUEST_CHANGES` or
`COMMENT_WITH_BLOCKER` completes this lifecycle disposition but does not make
the candidate merge-ready. A later unstructured `COMMENTED` review does not
erase an earlier substantive disposition; a later substantive review replaces
it, and an explicit later `DISMISSED` review invalidates it.

A lifecycle marker is accepted for deduplication only when it is a
`COMMENTED`, exact-head review attributed by GitHub to `github-actions[bot]`
or the recorded Product Owner account `ingolf-lohmann`; copied marker text
from another actor cannot suppress the lifecycle event. Team-only requests
fail closed with `UNSUPPORTED_REQUESTED_TEAM_REVIEWER` until a repository
member-to-account mapping is defined.

The automated blocker record begins with the structured
`<!-- qikvrt-review-disposition:COMMENT_WITH_BLOCKER -->` token. Its full
scope remains inside the exact binding hash; the rendered review body uses a
bounded JSON-escaped, Markdown-inert inline-code excerpt for PR-controlled
paths, states, details and gate metadata and refuses a body over 60,000 UTF-8
bytes. This prevents a large or adversarial path/check value from forging
Markdown or making the mandatory record unpostable.

The gate observation is deliberately limited to current GitHub Actions check
runs and legacy commit statuses that the executor can observe on the exact
head/test-merge contexts. It does not infer the platform's protected required
check set, branch-protection enforcement, mergeability, or review readiness.
Consequently, an observed-green lifecycle result is never a claim that all
platform-required checks exist or pass.

Changed paths and the rendered GitHub diff are also bounded observations, not
an assumption of unlimited API completeness. The snapshotter requires the PR's
declared `changed_files` count to match the paginated files response, refuses
the documented 3,000-file API boundary, and accepts a rendered diff only below
the documented file, line and byte boundaries (including the 500 KiB
per-file bound, enforced conservatively as a total bound) with one true `diff --git`
header per changed file. A mismatch or boundary condition fails closed rather
than binding an incomplete scope as exact review evidence.

The executor never auto-approves, auto-merges or impersonates a Code Owner.
Its purpose is to turn an otherwise silent pending review into a prompt,
traceable GitHub review event and a deterministic status, not to fabricate a
human account-level approval.

### Bootstrap boundary

GitHub activates `workflow_dispatch`, `workflow_run`, and status-event
workflows only when their definitions exist on the default branch.
Consequently, the pull request that introduces this executor cannot use the
new executor to review itself before merge. Its required bootstrap is a fresh,
exact-head human Product-Owner `COMMENT_WITH_BLOCKER` review record. That
bootstrap is still not an account-level Code Owner approval, does not make the
candidate ready, and does not authorize any merge or external effect.

The default-branch reconciliation schedule also covers legitimate cases where
a candidate changes, disables or renames the unprivileged signal workflow, or
where GitHub cannot deliver a prompt PR-target event. It is an eventual
reobservation mechanism, not evidence that an immediate event occurred.

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

The normative machine-readable policy is `policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json`. The natural-person delegation is `state/authorization/delegations/OWNER_REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json`.
