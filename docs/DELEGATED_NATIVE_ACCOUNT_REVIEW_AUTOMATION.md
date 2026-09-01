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
review`.

## Current fail-closed runtime state

Both native-account signer jobs are hard-disabled with `if: false`, reference
no account or activation secret, and cannot post a review.  The no-secret
planner remains available for technical evidence, while required-gate success
comes only from a current-head, unmarked human approval by the eligible
non-author Code Owner.  The exact blocker for native-account mutation is
`AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED`.

An Environment reference and a nonempty secret do not prove the credential's
scope: if an Environment secret is absent, GitHub expressions can resolve a
same-named repository or organization secret.  Reactivation is forbidden until
a dedicated settings reader performs a fresh effect-local readback proving the
protected main-only Environment, the expected Environment secret names, the
complete absence of the same and legacy names at broader scopes, and the exact
App/Ruleset authority.  The checked-in delegation receipt is not a substitute
for that live readback.

## One-time platform provisioning

Provision only after the exact implementation has reached trusted `main`.
Create the protected GitHub environment `qikvrt-native-review-authority`,
restrict its selected deployment branch to `main`, and put the following
secrets **only** in that environment; values must never be put in
the repository, an artifact, issue, pull request, or chat transcript.

| Secret | Account / value | Minimum access |
| --- | --- | --- |
| `QIKVRT_ENV_GOLDKELCH_REVIEW_TOKEN` | a self-identifying GitHub **User** credential for `Goldkelch` | Metadata read, Pull requests write, scoped only to the role-local QIK-VRT repository |
| `QIKVRT_ENV_INGOLF_LOHMANN_REVIEW_TOKEN` | a self-identifying GitHub **User** credential for `ingolf-lohmann` | Metadata read, Pull requests write, scoped only to the role-local QIK-VRT repository |
| `QIKVRT_ENV_NATIVE_ACCOUNT_REVIEW_ACTIVATION` | literal value `enabled` | explicit enable switch; remove or change it to stop later projections |

An Authority administrator must read the repository owner login, numeric ID
and type, environment, deployment-branch rule, and environment secret-name
list back through GitHub. The legacy names and all three new names must be
absent at repository scope. For an Organization owner, the same names must be
absent from a complete organization-secret inventory; for a User owner the
receipt instead binds `NOT_APPLICABLE_USER_OWNER` and must not claim an
organization inventory. The
workflow's `environment:` key does not create or prove those platform
settings.  Until that readback exists, the exact state is
`AUTHORITY_SECRET_ENVIRONMENT_NOT_VERIFIED` and no native review is authorized.

Any future reactivated signer must verify `/user` returns the exact expected login and `type=User`,
then checks that account's collaborator permission.  An App installation token,
`github-actions[bot]`, a bot account, a mismatched credential, an absent
credential, or ChatGPT is rejected before the review POST.  The two account
tokens are intentionally never materialized in the same job.

The active `main` ruleset must also require all of the following before the
independent human Code Owner gate can succeed:

- at least one approving review;
- Code Owner review;
- stale-review dismissal on push; and
- last-push approval.

The automation does not set those platform settings itself.  They require the
account that holds repository administration. A missing or weaker rule makes
a `TECHNICAL_CONTINUE` plan fail closed before native mapping. Automation never
posts an approval regardless of rule state.

## Per-event execution

For one completed native technical-review run, the planner:

1. permits a `TECHNICAL_CONTINUE` plan for the exact
   `pull_request_target.review_requested` intake to the configured
   counterpart, or for one later trusted exact executor event while that same
   counterpart remains in the live requested-reviewer set. Every such
   follow-up is bound through one immutable artifact whose name, receipt,
   fingerprint, PR, head, trusted workflow identity, and live reobservation
   agree. A non-request event without the still-live counterpart is no effect;
   unbound receipts are no effect; only the later successful signer preflight
   can map that plan to a native `COMMENT` event;
2. downloads the exact executor artifact and rereads its immutable ledger
   receipt, manifest, ordered packets, and ledger commit;
3. checks byte-canonical chunk reassembly and fresh base/head/tree/diff/
   fingerprint reobservation;
4. chooses only the non-author counterpart and preserves any unmarked manual
   exact-head review by that account;
5. retains `TECHNICAL_CONTINUE` in the sealed no-secret plan and maps it to
   GitHub's non-decisive `COMMENT` event only after signer preflight; it maps
   `REQUEST_CHANGES` to `REQUEST_CHANGES` at the same boundary.
   `COMMENT_WITH_BLOCKER` also maps to `REQUEST_CHANGES`, rather than a mere
   comment. `WAIT` is no effect. Historical automation-marked `APPROVED`
   reviews are predecessor-only technical evidence: they are never renewed,
   adopted as current Authority, or used to satisfy the required gate.
   Unmarked manual reviews are still preserved;
6. rereads the PR, commit, reviews, token identity, and permission immediately
   before the sole POST; a `TECHNICAL_CONTINUE` comment additionally requires
   the counterpart still to be present in the current `requested_reviewers`;
   and
7. verifies the returned review identity, state, exact commit, marker and
   fingerprint, then rereads base/head/tree.

Every delegated body is marked
`qikvrt-delegated-native-account-review:v1` and states that it is a delegated
platform-account action, not an independent natural-person review.  A repeated
identical fingerprint is a no-op.  Head, tree, base, receipt, transport,
target, credential, permission, manual-review, or post-effect drift stops the
projection.

Every marked review, including a historical marked `APPROVED` review, is
ineligible for required-gate success. That status can succeed only from the
latest current-head, unmarked human `APPROVED` review of an eligible non-author
Code Owner. An unmarked current `CHANGES_REQUESTED` review remains adverse.

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
