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

`EXACT_REQUEST -> BOUND_ADMIN_TOKEN -> GET /user -> PRINCIPAL_MATCH -> LIVE_RULESET_GET -> COMPARE_AND_SWAP -> ALLOWLISTED_PATCH -> FULL_PUT -> LIVE_RULESET_GET -> VERIFIED_RECEIPT`

A drifted ruleset, missing credential, unsupported field, unexpected ruleset identity, mismatched live account, API failure, insufficient token permission, or failed post-effect observation yields `HOLD` and no success claim.

The executor preserves every rule and pull-request parameter not named by the request. It does not synthesize a replacement source commit, review, merge or branch update.

## Bound administration principal

The exact request binds:

- account `Goldkelch`;
- repository `Goldkelch/qik-vrt`;
- credential kind `FINE_GRAINED_PERSONAL_ACCESS_TOKEN`;
- runtime secret `QIKVRT_GITHUB_ADMIN_TOKEN`;
- required repository permission `administration:write`.

Before reading or changing the Ruleset, the executor calls `GET /user` with the runtime token and requires the returned login to be `Goldkelch`. The subsequent Ruleset endpoint itself enforces whether the token has `Administration: write` for the exact repository.

The token must be fine-grained to `Goldkelch/qik-vrt`, carry only the necessary repository administration permission, have a bounded lifetime, and be stored solely as the encrypted Actions secret `QIKVRT_GITHUB_ADMIN_TOKEN`. It is never committed, printed, uploaded, hashed into a receipt, or copied to another persistent store.

If the token is absent, the executor emits `BOUND_ADMIN_TOKEN_NOT_BOOTSTRAPPED` and performs no Ruleset request. If the token identifies another account, it emits an identity-mismatch HOLD before the Ruleset GET. If it lacks the required permission, GitHub rejects the Ruleset endpoint and no PUT is accepted.

## Corrected bootstrap boundary

An earlier candidate bound installation ID `147849532` and expected the repository to supply that GitHub App's client ID and private key. Live reobservation established that this installation is the already connected third-party GitHub integration. Its private key is controlled by the app owner, not by this repository or the `Goldkelch` account, and therefore cannot be truthfully bootstrapped as a repository secret.

That impossible credential assumption has been removed. The corrected path uses an owner-controlled fine-grained token, which GitHub explicitly accepts for repository Ruleset updates when it has `Administration: write`.

## Continuous behavior

`.github/workflows/qikvrt_github_admin_effect_executor.yml` validates the contract on pull requests and runs the effect path on non-PR events. It is scheduled every five minutes, reacts to relevant pushes, and can be manually dispatched. Concurrency is repository-global with `cancel-in-progress: false`, giving the admin-effect lane one writer.

The trusted implementation branches are intentionally included in the push trigger so an exact Product-Owner-authorized administration request can be bootstrapped and verified before promotion to `main`. A branch push does not relax any request binding: principal identity, compare-and-swap precondition, allowlist, `force=false`, post-effect GET and verified receipt remain mandatory.

The general repository-native continuation remains provided by the autonomous self-heal, PR continuation, expected-head promotion, workflow executor and watchdog mechanisms declared from `/AI`. Together they continue deterministic work without Product-Owner reinteraction until a declared stop condition is reached.

Once a request has been applied, later executions detect the desired live state and return `ALREADY_APPLIED` without issuing another PUT.

## Current exact request

`state/admin_effects/requests/RULESET_19344903_CODE_OWNER_ENFORCEMENT_V1.json` binds:

- repository `Goldkelch/qik-vrt`;
- live principal `Goldkelch`;
- credential kind `FINE_GRAINED_PERSONAL_ACCESS_TOKEN`;
- secret name `QIKVRT_GITHUB_ADMIN_TOKEN`;
- required permission `administration:write`;
- Ruleset `19344903`, name `QIK-VRT main protection`;
- active branch target `refs/heads/main`;
- expected current values `0 / false / false / false`;
- desired values `1 / true / true / true`;
- `force=false`.

The request is separately bound to Product-Owner authorization `PO-2026-08-17-GITHUB-ADMIN-EFFECT-EXECUTOR-V1`.

## Evidence boundary

`APPLIED_VERIFIED` proves only that GitHub returned the requested Ruleset state after the PUT. It does not itself approve a pull request, make CI green, merge code, deploy software, publish an artifact, establish a scientific claim, or imply `PASS`, `FINAL_PASS`, or `EFFECT_ACK_DONE`.

## Exact continuation state — 2026-08-19

The live requested-review gate on trusted invariant successor PR `#723` reobserved `CODE_OWNER_RULE_NOT_ENFORCED` at exact head `766e363ddc61c7f8bdec3f3f11264521359a7cca`.

The first administration-effect execution then proved the original app-key bootstrap impossible and emitted a redacted HOLD without attempting a PUT. The repaired executor reduces the external bootstrap to one feasible, exactly named repository secret: `QIKVRT_GITHUB_ADMIN_TOKEN`.

Until that secret contains a `Goldkelch` fine-grained token with `Administration: write` for `Goldkelch/qik-vrt`, the correct state remains `HOLD`. Once present, the scheduled or pushed executor must reverify identity and live state before applying the four allowlisted parameters.
