# QIK-VRT GitHub Administration Effect Executor

## Purpose

This component closes the gap between repository-authorized administration effects and GitHub settings that cannot be represented by source commits. It is a narrow effect transport, not a general-purpose privileged shell.

The first supported transaction is the exact update of repository Ruleset `19344903` (`QIK-VRT main protection`) so that `main` requires one approval, Code Owner review, dismissal of stale approvals after pushes, and approval of the most recent reviewable push.

## Transaction

Every effect is executed as:

`EXACT_REQUEST -> BOUND_ADMIN_PRINCIPAL -> SHORT_LIVED_INSTALLATION_TOKEN -> LIVE_GET -> COMPARE_AND_SWAP -> ALLOWLISTED_PATCH -> FULL_PUT -> LIVE_GET -> VERIFIED_RECEIPT`

A drifted ruleset, missing credential bootstrap, installation mismatch, missing Administration write permission, unsupported field, unexpected ruleset identity, API failure, or failed post-effect observation yields `HOLD` and no success claim.

The executor preserves every rule and pull-request parameter not named by the request. It does not synthesize a replacement source commit, review, merge or branch update.

## Bound administration principal

The current exact request binds the already observed GitHub App installation on account `Goldkelch`:

- account: `Goldkelch`;
- installation ID: `147849532`;
- repository: `Goldkelch/qik-vrt`;
- required permission: repository `Administration: write`.

The workflow uses the pinned official `actions/create-github-app-token` action. It requests a repository-scoped short-lived token with `permission-administration: write` and verifies that the action output `installation-id` equals `147849532` before any Ruleset PUT is permitted. GitHub rejects token creation when the selected installation does not possess the requested permission.

The only credential bootstrap for the normal effect lane is the app client ID in repository variable `QIKVRT_ADMIN_APP_CLIENT_ID` and the corresponding private key in repository secret `QIKVRT_ADMIN_APP_PRIVATE_KEY`. No persistent PAT fallback is used by this lane. The short-lived token is masked and revoked by the token action after the job. No credential is committed, printed, uploaded, hashed into a receipt, or copied to another persistent store.

If those app credentials are absent, the executor emits `BOUND_ADMIN_APP_CREDENTIAL_NOT_BOOTSTRAPPED` and performs no effect. If the installed app lacks `Administration: write`, token creation fails before the effect step. These are infrastructure bootstrap/permission states, not source defects.

## Continuous behavior

`.github/workflows/qikvrt_github_admin_effect_executor.yml` validates the contract on pull requests and runs the effect path on non-PR events. It is scheduled every five minutes, reacts to relevant pushes, and can be manually dispatched. Concurrency is repository-global with `cancel-in-progress: false`, giving the admin-effect lane one writer.

Once a request has been applied, later executions detect the desired live state and return `ALREADY_APPLIED` without issuing another PUT.

## Current exact request

`state/admin_effects/requests/RULESET_19344903_CODE_OWNER_ENFORCEMENT_V1.json` binds:

- repository `Goldkelch/qik-vrt`;
- admin principal `Goldkelch` installation `147849532`;
- Ruleset `19344903`, name `QIK-VRT main protection`;
- active branch target `refs/heads/main`;
- expected current values `0 / false / false / false`;
- desired values `1 / true / true / true`;
- `force=false`.

The request is separately bound to Product-Owner authorization `PO-2026-08-17-GITHUB-ADMIN-EFFECT-EXECUTOR-V1`.

## Evidence boundary

`APPLIED_VERIFIED` proves only that the bound administration transport caused GitHub to return the requested ruleset state after the PUT. It does not itself approve a pull request, make CI green, merge code, deploy software, publish an artifact, establish a scientific claim, or imply `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.
