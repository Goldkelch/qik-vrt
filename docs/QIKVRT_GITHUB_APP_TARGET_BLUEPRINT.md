# QIK-VRT GitHub App target blueprint

The repository Actions executor can classify one exact event but GitHub Actions
does not provide a native cross-event priority queue, native webhook delivery
identifier, or a `pull_request_review_thread` workflow trigger. A repository-
scoped GitHub App webhook broker is therefore required before claiming that
multiple requested reviews are ordered by requester, target and reason.

This blueprint is a provisioning contract, not evidence that such an App is
installed, running, authorized, or has produced any review. Until its exact
delivery evidence exists, Actions must report
`GITHUB_ACTIONS_NO_CROSS_EVENT_PRIORITY_GUARANTEE` and must not simulate a
queue with a schedule, global PR scan, rotating selector, or cancellation of
an in-progress review.

## Least-privilege installation

Install the App only on `Goldkelch/qik-vrt` (and, when separately authorized,
`ingolf-lohmann/qik-vrt`). It must reject a delivery whose repository identity
is not the installation repository.

Required repository permissions:

- Contents: read/write — only for the role-local append-only intake/receipt
  evidence ref, with non-force compare-and-swap;
- Actions: read/write — only to observe workflows and dispatch one exact
  trusted-main continuation;
- Pull requests: read/write — read exact request/review state; write only a
  technical `COMMENT` projection when the existing Mesh policy permits it;
- Commit statuses: read/write — exact-head status projection only;
- Metadata: read.

The App must not use broad organization administration, issues write, workflow
file mutation, repository deletion, code-owner impersonation, or credentials
for any foreign repository.

## Native event intake and replay boundary

Subscribe to these GitHub App webhook events:

- `pull_request` — including `review_requested`, `review_request_removed`,
  `labeled`, `unlabeled`, head synchronization and PR metadata changes;
- `pull_request_review` and `pull_request_review_comment` — reobservation
  signals only;
- `pull_request_review_thread` — resolve/unresolve transitions that GitHub
  Actions cannot natively receive.

For every delivery, the broker must first verify `X-Hub-Signature-256` over
the raw body. It must retain and deduplicate the exact
`X-GitHub-Delivery`, the delivery timestamp, raw-body SHA-256, repository
full name, installation id, event name and action. Duplicate delivery ids
must be idempotent; a reused id with different bound bytes is a fail-closed
replay/collision. The broker never trusts a user-supplied priority, free-text
reason, branch name, or unverified PR number.

## Exact intake contract

After reobserving the current PR, base and candidate head, the broker derives
the same `review_intake` specified by
`policy/REQUESTED_REVIEW_AND_ISSUE_LIFECYCLE_V1.json#/review_intake_priority`.
The persisted signed envelope must contain at least:

```json
{
  "schema": "qikvrt_github_app_review_intake_v1",
  "repository": "owner/name",
  "installation_id": 0,
  "delivery_id": "X-GitHub-Delivery",
  "delivery_timestamp": "RFC3339 UTC",
  "raw_body_sha256": "sha256",
  "event_name": "pull_request|pull_request_review|pull_request_review_thread",
  "event_action": "native action",
  "pr_number": 0,
  "expected_base_sha": "git sha1",
  "expected_head_sha": "git sha1",
  "event_actor": "GitHub login or null",
  "requested_reviewer": "GitHub login or null",
  "requested_team": "team slug or null",
  "reason_label": "declared label or null",
  "priority_class": "P0..P4",
  "priority_rank": 0,
  "policy_sha256": "sha256"
}
```

The reason comes only from the closed label vocabulary in the policy. Missing
reason is `UNSPECIFIED`; conflicting reason labels are fail-closed. The
priority is rederived by the broker and independently revalidated by trusted
repository code. A caller cannot elevate itself by putting a value in the
dispatch body.

## Ordering and handoff

The broker owns one bounded, append-only delivery queue. It orders only
*pending* valid envelopes by `priority_rank`, then delivery timestamp, then
`X-GitHub-Delivery`; it never cancels or rewrites an in-progress exact review.
It may dispatch the next item only after the prior receipt is persisted or has
an explicit fail-closed terminal handoff. A queue item whose expected base,
head, tree, label evidence, policy digest or requester/target fields drifted
must be reobserved rather than promoted from stale evidence.

The dispatch adapter must be implemented as a separately authenticated,
trusted-main entrypoint. It must accept only a broker-proven envelope and
exact PR/head, and must pass it into the existing `QIKVRT requested review
executor`; an ordinary `repository_dispatch` or manual workflow input alone
is not sufficient proof of GitHub-App origin. This repository does not yet
contain that deployed broker or authenticated adapter.

## Delegated native-account projection

The broker and an Actions workflow are not `Goldkelch` or
`ingolf-lohmann`. Their technical projections remain `COMMENT`-only. A
separate owner delegation may nevertheless permit a self-identifying GitHub
**User** credential for one of those two accounts to submit an exact platform
review on that account's behalf. This is not identity substitution: the POST
must be authenticated by that account's credential and GitHub must read back
the same `type=User` login. It is also not an independent natural-person
review.

`OWNER-NATIVE-ACCOUNT-REVIEW-AUTOMATION-V1` and
`docs/DELEGATED_NATIVE_ACCOUNT_REVIEW_AUTOMATION.md` define the narrowly
allowed per-event adapter. It runs only from trusted `main`, never checks out
or executes candidate bytes while a credential is present, requires the
non-author configured counterpart, exact ledger transport and receipt
reverification, a fresh pre-POST base/head/tree/fingerprint reobservation,
and a post-POST readback. A missing, wrong, App, bot, or insufficiently
privileged credential is a no-effect hold. The two account credentials are
separated into mutually exclusive signer jobs.

This adapter does not make Actions a cross-event priority queue. It must not
claim the delivery signature, replay protection, timestamp ordering, or
global prioritization that still requires the signed webhook broker above.

## Identity and effect boundary

The App is not `Goldkelch`. It may project only the already-authorized
technical `COMMENT` review under its real App identity (or allow the existing
`github-actions[bot]` technical projection). It must never submit `APPROVE` or
`REQUEST_CHANGES` as Goldkelch, claim an independent Code-Owner approval,
merge, publish, deploy, or assert `PASS`, `FINAL_PASS`, or
`EFFECT_ACK_DONE`.

Native branch protection remains a separate platform effect: the target
Ruleset must independently require one approval, Code Owner review, stale
review dismissal and last-push approval. A broker receipt or technical comment
does not satisfy that rule.
