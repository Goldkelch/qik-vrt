<!--
SPDX-License-Identifier: CC-BY-NC-ND-4.0
Copyright (c) 2026 Ingolf Lohmann.
-->

# Delegated native-account review automation

`Goldkelch` and `ingolf-lohmann` are the platform-effective repository
reviewer accounts.  For a pull request authored by either account, only the
other account can be selected.  The natural person Ingolf Lohmann abstains
from these native reviews; ChatGPT and `github-actions[bot]` remain technical
observers and do not substitute for either platform account.

The trusted-main `QIKVRT requested review executor` remains secret-free and
can only produce its technical `COMMENT` projection.  A completed exact
receipt then enters the no-secret planner in `QIKVRT required code-owner
review`.  Only a separated signer job may use the selected account's
credential, and it rechecks the platform identity immediately before posting.

## One-time platform provisioning

Provision only after the exact implementation has reached trusted `main`.
The following GitHub Actions secrets are required; values must never be put in
the repository, an artifact, issue, pull request, or chat transcript.

| Secret | Account / value | Minimum access |
| --- | --- | --- |
| `QIKVRT_GOLDKELCH_REVIEW_TOKEN` | a self-identifying GitHub **User** credential for `Goldkelch` | Metadata read, Pull requests write, scoped only to the role-local QIK-VRT repository |
| `QIKVRT_INGOLF_LOHMANN_REVIEW_TOKEN` | a self-identifying GitHub **User** credential for `ingolf-lohmann` | Metadata read, Pull requests write, scoped only to the role-local QIK-VRT repository |
| `QIKVRT_NATIVE_ACCOUNT_REVIEW_ACTIVATION` | literal value `enabled` | explicit enable switch; remove or change it to stop later projections |

The signer verifies `/user` returns the exact expected login and `type=User`,
then checks that account's collaborator permission.  An App installation token,
`github-actions[bot]`, a bot account, a mismatched credential, an absent
credential, or ChatGPT is rejected before the review POST.  The two account
tokens are intentionally never materialized in the same job.

The active `main` ruleset must also require all of the following before an
automated `APPROVE` may be posted:

- at least one approving review;
- Code Owner review;
- stale-review dismissal on push; and
- last-push approval.

The automation does not set those platform settings itself.  They require the
account that holds repository administration.  A missing or weaker rule makes
an `APPROVE` plan fail closed; no approval is posted.

## Per-event execution

For one completed native technical-review run, the planner:

1. permits an `APPROVE` for the exact
   `pull_request_target.review_requested` intake to the configured
   counterpart, or for one later trusted exact executor event while that same
   counterpart remains in the live requested-reviewer set. Every such
   follow-up is bound through one immutable artifact whose name, receipt,
   fingerprint, PR, head, trusted workflow identity, and live reobservation
   agree. A non-request event without the still-live counterpart can only
   enter the separate stale-approval retraction path; unbound receipts are no
   effect;
2. downloads the exact executor artifact and rereads its immutable ledger
   receipt, manifest, ordered packets, and ledger commit;
3. checks byte-canonical chunk reassembly and fresh base/head/tree/diff/
   fingerprint reobservation;
4. chooses only the non-author counterpart and preserves any unmarked manual
   exact-head review by that account;
5. maps `APPROVE` to `APPROVE` and `REQUEST_CHANGES` to `REQUEST_CHANGES`.
   `COMMENT_WITH_BLOCKER` also maps to `REQUEST_CHANGES`, rather than a mere
   comment, so a fresh blocker cannot leave an earlier same-head delegated
   approval decisive. A negative projection from a non-request event is
   limited to retracting a prior same-head **delegated** approval after one
   exact trusted `pull_request_target`, `issue_comment`, or `workflow_run`
   event. `WAIT` is otherwise no effect; in that narrow retraction case the
   signer records a marked `REQUEST_CHANGES` retraction. The signer rereads
   the latest marked native state and does nothing if that old approval is no
   longer decisive. Unmarked manual reviews are still preserved;
6. rereads the PR, commit, reviews, token identity, and permission immediately
   before the sole POST; an `APPROVE` additionally requires the counterpart
   still to be present in the current `requested_reviewers`; and
7. verifies the returned review identity, state, exact commit, marker and
   fingerprint, then rereads base/head/tree.

Every delegated body is marked
`qikvrt-delegated-native-account-review:v1` and states that it is a delegated
platform-account action, not an independent natural-person review.  A repeated
identical fingerprint is a no-op.  Head, tree, base, receipt, transport,
target, credential, permission, manual-review, or post-effect drift stops the
projection.

This per-event adapter does not supply the cross-event ordering guarantee that
only a separately provisioned signed GitHub App webhook broker can provide.
The App blueprint remains authoritative for delivery signature, replay and
priority-queue requirements.  Neither adapter authorizes merge, ruleset
weakening, deployment, publication, license/right changes, `PASS`,
`FINAL_PASS`, or `EFFECT_ACK_DONE`.

The trusted-main delegation file is part of every sealed plan and is read again
by the signer immediately before the POST. Changing its state to `REVOKED`, or
changing any of its bound owner/identity scope, stops future postings even if
the activation secret remains `enabled`.
