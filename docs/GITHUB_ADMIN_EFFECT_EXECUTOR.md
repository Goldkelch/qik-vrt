# QIK-VRT GitHub Administration Effect Executor

## Purpose

This component closes the gap between repository-authorized administration effects and GitHub settings that cannot be represented by source commits. It is a narrow effect transport, not a general-purpose privileged shell.

The first supported transaction is the exact update of repository Ruleset `19344903` (`QIK-VRT main protection`) so that `main` requires one approval, Code Owner review, dismissal of stale approvals after pushes, and approval of the most recent reviewable push.

## Autonomous continuation integration

The executor is part of the bounded autonomous-continuation architecture. The active controller delegation remains `OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V2.json` for compatibility with the existing self-heal parser and is extended by `OWNER_AUTONOMOUS_REPOSITORY_CONTINUATION_V3.json`.

The extension authorizes the repository to continue uniquely determined repository-internal implementation, testing, verification, integrity materialization, reviewable successor generation and repository-defined Product-Owner dispositions without repeatedly asking the Product Owner. A GitHub administration mutation is still permitted only when a separate exact request binds the resource, expected live state, desired state, authorization and `force=false`.

This autonomy does not synthesize human identity. A required independent Code Owner approval, human acoustic verification, physical measurement, independent empirical replication, credential bootstrap or genuinely non-equivalent Product-Owner choice remains a fail-closed stop condition. A technical bot review is never an independent Code Owner review.

## Transaction

Every effect is executed as:

`EXACT_REQUEST -> BOUND_ADMIN_PRINCIPAL -> SHORT_LIVED_INSTALLATION_TOKEN -> LIVE_GET -> COMPARE_AND_SWAP -> ALLOWLISTED_PATCH -> FULL_PUT -> LIVE_GET -> VERIFIED_RECEIPT`

A drifted ruleset, missing credential, unsupported field, unexpected ruleset identity, API failure, wrong installation principal, or failed post-effect observation yields `HOLD` and no success claim.

The executor preserves every rule and pull-request parameter not named by the request. It does not synthesize a replacement source commit, review, merge or branch update.

## Bound administration principal

The initial request binds the existing GitHub App installation account `Goldkelch`, exact installation ID `147849532`, repository `Goldkelch/qik-vrt`, and required permission `administration:write`.

The workflow accepts only a short-lived installation token generated from `QIKVRT_ADMIN_APP_CLIENT_ID` plus `QIKVRT_ADMIN_APP_PRIVATE_KEY` using the pinned official `actions/create-github-app-token` action. The action requests only `Administration: write` for `qik-vrt`; the workflow verifies that its `installation-id` output equals `147849532` before any Ruleset PUT. No persistent PAT fallback exists in the normal effect lane.

Credentials are runtime-only. No credential is committed, printed, uploaded, hashed into a receipt, or copied to another persistent store.

If the bound app credentials are absent, the executor emits `BOUND_ADMIN_APP_CREDENTIAL_NOT_BOOTSTRAPPED` and performs no effect. If the installation lacks the requested permission, token generation fails before the effect. This is an infrastructure boundary, not a source-code substitute.

## Continuous behavior

`.github/workflows/qikvrt_github_admin_effect_executor.yml` validates the contract on pull requests and runs the effect path on non-PR events. It is scheduled every five minutes, reacts to relevant pushes, and can be manually dispatched. Concurrency is repository-global with `cancel-in-progress: false`, giving the admin-effect lane one writer.

The trusted implementation branch `agent/github-admin-effect-executor-v1` is intentionally included in the push trigger so an exact Product-Owner-authorized administration request can be bootstrapped and verified before promotion to `main`. A branch push does not relax any request binding: the same bound installation, compare-and-swap precondition, allowlist, `force=false`, post-effect GET and verified receipt remain mandatory.

The general repository-native continuation remains provided by the autonomous self-heal, PR continuation, expected-head promotion, workflow executor and watchdog mechanisms declared from `/AI`. Together they are required to continue deterministic work without Product-Owner reinteraction until a declared stop condition is reached.

Once a request has been applied, later executions detect the desired live state and return `ALREADY_APPLIED` without issuing another PUT.

## Current exact request

`state/admin_effects/requests/RULESET_19344903_CODE_OWNER_ENFORCEMENT_V1.json` binds:

- repository `Goldkelch/qik-vrt`;
- bound installation account `Goldkelch`;
- bound installation ID `147849532`;
- required permission `administration:write`;
- Ruleset `19344903`, name `QIK-VRT main protection`;
- active branch target `refs/heads/main`;
- expected current values `0 / false / false / false`;
- desired values `1 / true / true / true`;
- `force=false`.

The request is separately bound to Product-Owner authorization `PO-2026-08-17-GITHUB-ADMIN-EFFECT-EXECUTOR-V1`.

## Evidence boundary

`APPLIED_VERIFIED` proves only that GitHub returned the requested ruleset state after the PUT. It does not itself approve a pull request, make CI green, merge code, deploy software, publish an artifact, establish a scientific claim, or imply `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

## Exact continuation trigger — 2026-08-19

The live requested-review gate on trusted successor PR `#723` reobserved `CODE_OWNER_RULE_NOT_ENFORCED` at exact head `766e363ddc61c7f8bdec3f3f11264521359a7cca`. The Product Owner then instructed the already authorized repository work to be completed.

This documentation-only branch update deliberately triggers the bounded non-PR executor on `agent/github-admin-effect-executor-v1-trusted-successor`. It does not widen the request. The executor may act only if the bound installation credentials exist, the live Ruleset still matches `expected_before`, and the full post-effect observation matches `desired_after`; otherwise it must emit the corresponding fail-closed receipt.
