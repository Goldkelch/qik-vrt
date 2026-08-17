# QIK-VRT GitHub Administration Effect Executor

## Purpose

This component closes the gap between repository-authorized administration effects and GitHub settings that cannot be represented by source commits. It is a narrow effect transport, not a general-purpose privileged shell.

The first supported transaction is the exact update of repository Ruleset `19344903` (`QIK-VRT main protection`) so that `main` requires one approval, Code Owner review, dismissal of stale approvals after pushes, and approval of the most recent reviewable push.

## Transaction

Every effect is executed as:

`EXACT_REQUEST -> LIVE_GET -> COMPARE_AND_SWAP -> ALLOWLISTED_PATCH -> FULL_PUT -> LIVE_GET -> VERIFIED_RECEIPT`

A drifted ruleset, missing credential, unsupported field, unexpected ruleset identity, API failure, or failed post-effect observation yields `HOLD` and no success claim.

The executor preserves every rule and pull-request parameter not named by the request. It does not synthesize a replacement source commit, review, merge or branch update.

## Credential bootstrap

The runtime credential is supplied only as the Actions secret `QIKVRT_GITHUB_ADMIN_TOKEN`. It must be a least-privilege GitHub App installation token or fine-grained token with repository **Administration: write** capability for the exact target repository. The token is never committed, printed, uploaded, hashed into a receipt, or copied to another persistent store.

If the secret is absent, the scheduled executor emits `ADMIN_CREDENTIAL_NOT_BOOTSTRAPPED` and performs no effect. This is a one-time infrastructure bootstrap, not a source defect.

## Continuous behavior

`.github/workflows/qikvrt_github_admin_effect_executor.yml` validates the contract on pull requests and runs the effect path on non-PR events. It is scheduled every five minutes, reacts to relevant pushes, and can be manually dispatched. Concurrency is repository-global with `cancel-in-progress: false`, giving the admin-effect lane one writer.

Once a request has been applied, later executions detect the desired live state and return `ALREADY_APPLIED` without issuing another PUT.

## Current exact request

`state/admin_effects/requests/RULESET_19344903_CODE_OWNER_ENFORCEMENT_V1.json` binds:

- repository `Goldkelch/qik-vrt`;
- Ruleset `19344903`, name `QIK-VRT main protection`;
- active branch target `refs/heads/main`;
- expected current values `0 / false / false / false`;
- desired values `1 / true / true / true`;
- `force=false`.

The request is separately bound to Product-Owner authorization `PO-2026-08-17-GITHUB-ADMIN-EFFECT-EXECUTOR-V1`.

## Evidence boundary

`APPLIED_VERIFIED` proves only that GitHub returned the requested ruleset state after the PUT. It does not itself approve a pull request, make CI green, merge code, deploy software, publish an artifact, establish a scientific claim, or imply `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.
