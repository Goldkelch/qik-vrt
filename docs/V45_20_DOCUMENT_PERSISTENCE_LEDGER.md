# QIKVRT V45.20 Document Persistence and Release Probe Repair Ledger

## Purpose

Persist the four QIK-VRT / quantum-gravity documents across repository layers and repair the V45.17 Windows Git invocation failure.

## Persisted documents

| File | SHA256 | Bytes |
|---|---:|---:|
| `documents/qikvrt_quantengravitation/QIKVRT_Fixpunktbeweis_final.pdf` | `bf6521828db3ea52d67868b1c8ba09b0c0256562f684231df6833b1f68c2d55e` | 240385 |
| `documents/qikvrt_quantengravitation/QIKVRT_Quantenkausalitaet_Quantengravitation_Vorlesung_Semester1.pdf` | `32895b7f36c0b2aaca679b27298a8eee824196391dd2125423f08f37ea24e08d` | 135423 |
| `documents/qikvrt_quantengravitation/quantengravitation_bekannte_mathematik_physik_semester2_v5.pdf` | `377bc53f444e12aeaedc237a71a4eec64c1c76d49dc2b2a9a9debfef72fcab1c` | 143664 |
| `documents/qikvrt_quantengravitation/quantengravitation_semester3_abschluss_beweis_v3.pdf` | `0e7e17798a764299a4228df15f77ff1a623aedaa768f067c7889f67c83204a4b` | 141774 |


## Bundle

`dist/QIKVRT_V45_20_DOCUMENTS_BUNDLE.zip`

SHA256: `bafb3727b08bb130b415235aea56e2afc9f151ff89319d0eb577186ad372b0f9`

## Repaired V45.17 failure

Error class: `BLOCK_GIT_INVOCATION_EMPTY_ARGUMENT_VECTOR_FROM_POWERSHELL_ARGS_COLLISION`

Observed: the V45.17 remote wrapper reached the Git bootstrap phase and then invoked `git` without the intended subcommand, producing Git's generic usage text and `args=` in the BLOCK line.

Repair: V45.20 replaces the helper layer with `Invoke-QikvrtGit` / `Invoke-QikvrtGH`, using `ValueFromRemainingArguments`, a non-reserved parameter name, and an explicit zero-argument guard.

## Release rules

- exact Product Owner acceptance before effect
- origin/main canonical base
- clean checkout overlay staging
- no force-tag update
- no asset clobber
- release asset hash verification


## V45.20 Release Probe Repair

V45.18 exposed `BLOCK_GIT_REMOTE_GET_URL_ORIGIN_NATIVE_COMMAND_ERROR_BEFORE_BOOTSTRAP`: PowerShell treated `git remote get-url origin` stderr as a terminating native-command error when origin did not yet exist. V45.20 persists this as an error class and replaces the probe with `Test-QikvrtGitRemoteExists` based on `git remote` listing.


## V45.20 Safe GitHub Release Probe Repair

V45.19 exposed `BLOCK_GH_RELEASE_VIEW_NATIVE_COMMAND_ERROR_BEFORE_RELEASE_CREATE`: after successful main push and tag push, the missing release condition from `gh release view` was treated as a terminating PowerShell NativeCommandError. V45.20 persists this error class and uses a safe release-existence probe that turns a missing release into the intended `gh release create` path.
