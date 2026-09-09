# Scoped GitHub App route for main-ruleset reconciliation

`QIKVRT autonomous ruleset effect loop` is the sole repository workflow that
may invoke the ruleset reconciler with write authority. Its unprivileged
`QIKVRT ruleset effect dispatch bridge` only binds the canonical required-review
subject and dispatches that one writer; the five-minute reflexive watchdog can
also dispatch the distinct exact-`MAIN` reobservation subject. Neither
dispatcher receives the App token or invokes `--apply`. This is an installation
contract, not evidence that an App,
permission, secret, ruleset change, review, merge, release, or other effect
already exists.

## One repository, one narrow permission

Install a dedicated GitHub App only on `Goldkelch/qik-vrt`. Its repository
permission is **Administration: read/write** plus GitHub's implicit metadata
read. Do not give this App contents, issues, pull-request, status, Actions,
organization, or foreign-repository permissions. The regular job token keeps
those ordinary control-plane calls; the App token is passed only as
`QIKVRT_RULESET_ADMIN_TOKEN` to `tools/qikvrt_ruleset_reconcile.py`. The mint
action explicitly requests only `permission-administration: write`; it does
not inherit a broad App permission set.

Repository configuration names are deliberately non-secret identifiers:

- Repository variable: `QIKVRT_RULESET_APP_ID`
- Repository Action secret: `QIKVRT_RULESET_APP_PRIVATE_KEY`

`QIKVRT_RULESET_ADMIN_TOKEN` is intentionally not configured as a fallback.
A missing App configuration is a `REQUEST_AUTHORITY`; a failed token mint,
failed or indeterminate configuration check, rejected permission, API failure,
ETag change, or mismatching readback is a failing `HOLD`. Neither outcome may silently fall through to a legacy
long-lived credential. A durable exact-PR/head/policy receipt is written only
after a same-run `CURRENT` post-effect readback, is bound to the bot author,
full PR/base/head tuple, policy and reconciliation-receipt SHA, and never
suppresses a fresh App-token API readback. `REQUEST_AUTHORITY` and `HOLD` are
failing workflow states; the PR continuation comment is a separately guarded
nonterminal control-plane record.

The scheduled `MAIN` subject is bound immediately before dispatch and again
before `--apply` to the exact `main` SHA and policy SHA-256. The watchdog does
not call the ruleset API and does not carry App authority. It dispatches no
second main-mode run while one is queued or active, and Main mode emits only a
post-`CURRENT` workflow artifact receipt—no PR comment, review, or status.

## Required effect proof

After the installation is present, trusted `main` must produce this exact
sequence:

1. Mint a short-lived installation token scoped to `Goldkelch/qik-vrt`.
2. Authenticated GET of ruleset `19344903`.
3. Compare against `policy/GITHUB_MAIN_RULESET_V1.json`.
4. If drift exists, conditionally PUT with the observed ETag.
5. Authenticated GET readback that proves the exact desired state.

Only missing App configuration or an unavailable dedicated credential is
`REQUEST_AUTHORITY`. Rejected credentials, HTTP/API failures, ETag changes,
and mismatching readback remain a failing `HOLD`; none of these can be
converted to a green workflow outcome.

No step in this route creates a release, merges a pull request, approves a
review, bypasses a ruleset, or claims `PASS`, `FINAL_PASS`, or
`EFFECT_ACK_DONE`.
