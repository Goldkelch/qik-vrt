# QIKVRT ODU V2.7 PowerShell 5.1 Git CLI Windows Package

This package supersedes V2.1. V2.7 replaces the failing Windows PowerShell Git invocation helper with `System.Diagnostics.PowerShell 5.1 call operator.ArgumentList` and `-GitArgs`, contains the primary PDF artifact, and uses GitHub Release publication as the Zenodo integration trigger. No Zenodo API token is used.

Recommended Windows order:

1. `POWERSHELL_PARSE_CHECK_ONLY.cmd`
2. `GIT_INVOCATION_SELFTEST.cmd`
3. `GITHUB_DRY_RUN_VERIFY_ONLY.cmd`
4. `GITHUB_ZENODO_UPLOAD_AND_PUBLISH.cmd`

Zenodo requires that the target GitHub repository is enabled in the Zenodo GitHub integration before the GitHub Release is processed by Zenodo.

# QIKVRT ODU V2.7 GitHub-only Zenodo Release Package

Author: Ingolf Lohmann

This Windows-safe QIKVRT repository contains the Zenodo PDF artifact and the operative article/insight corpus for the Ontologie des Unterschieds.

## Primary PDF artifact

- `assets/pdf/odu_proof.pdf`
- SHA256: `2382b5d4970559bc28649a6deb6797fe867fc70439140e4cf1c1e59964a37de6`

## Owner-side GitHub-only Zenodo workflow

This version assumes the owner has a GitHub token, not a Zenodo token.

1. Enable the target repository once in Zenodo's GitHub integration web UI.
2. Extract this ZIP under Windows.
3. Run `GITHUB_DRY_RUN_VERIFY_ONLY.cmd`.
4. Set or enter `GITHUB_TOKEN`, `GITHUB_OWNER`, `GITHUB_REPO`.
5. Run `GITHUB_ZENODO_UPLOAD_AND_PUBLISH.cmd`.
6. The script publishes a GitHub Release and uploads PDF/bundle release assets.
7. Zenodo automatically archives the release if the GitHub integration is enabled for that repository.

## Important boundary

No Zenodo API token is used. A GitHub token cannot directly publish to the Zenodo REST deposit API. Publication to Zenodo occurs through Zenodo's GitHub integration after the GitHub Release is published.

## QIKVRT status

`V1_6_GITHUB_TOKEN_ONLY_ZENODO_INTEGRATION_PATH | WINDOWS_SAFE | PDF_INCLUDED | RELEASE_PUBLISH_SCRIPT_INCLUDED | NO_ZENODO_TOKEN_ASSUMPTION`


## V2.7 correction

V1.6 is BLOCKED by a Windows PowerShell path-normalization bug in `TrimStart`. V2.7 fixes relative-path generation in `tools/github_zenodo_release_publish.ps1` by using `[char]92` and `[char]47` and adds verifier gates preventing the same bug from returning.


## V2.7 field correction

V2.7 replaces V1.7 after owner-side GitHub API field error `403 Resource not accessible by personal access token` at the GitHub Git-Blobs endpoint. V2.7 uses Git CLI branch/tag push and GitHub Release publishing. A token without repository `Contents: read and write` permission will still be blocked by GitHub; the script now fails before misleading continuation and explains the required permission.


## V2.7 critical fix

V2.7 blocked on an expected GitHub `404 Not Found` when checking for an existing release by tag. V2.7 treats that 404 as the normal absence of a release and proceeds to create the GitHub Release.

Run order under Windows:

1. `GITHUB_DRY_RUN_VERIFY_ONLY.cmd`
2. Set `GITHUB_OWNER`, `GITHUB_REPO`, optional `GITHUB_TAG`, and `GITHUB_TOKEN`.
3. `GITHUB_ZENODO_UPLOAD_AND_PUBLISH.cmd`
4. Check GitHub Release and Zenodo GitHub-integration ingestion.

No Zenodo API token is used. GitHub token must have write access to the repository contents/releases.


## V2.7 Parser-Fix

V2.7 ersetzt V1.9 wegen eines PowerShell-Parserfehlers in der Invoke-GitHubUpload-Funktion. Zusätzlich enthalten: `POWERSHELL_PARSE_CHECK_ONLY.cmd`.


## V2.7 correction

V2.0 is BLOCK due to PowerShell positional array binding in Invoke-GitSafe. V2.7 fixes all Git calls to named parameter invocation and adds `GIT_INVOCATION_SELFTEST.cmd`.


## V2.7 correction

V2.2 is BLOCK on Windows PowerShell 5.1 because `ProcessStartInfo.ArgumentList` may not exist. V2.7 removes that API and uses `& $gitExe @GitArgs` with an explicit `-GitArgs` parameter. Local Git substrate was executed in the sandbox; GitHub remote publish remains owner-side only.


## V2.7 GitHub authentication correction

V2.7 supersedes V2.3 after `remote: invalid credentials`. Git transport now uses a GitHub Basic Authorization extraHeader and a non-mutating `GITHUB_AUTH_PREFLIGHT_ONLY.cmd` gate before any mutating upload/publish operation.


## V2.7 correction

V2.7 fixes the Windows PowerShell `NativeCommandError` caused by normal Git progress written to stderr, e.g. `From https://github.com/...` during fetch. Git commands are now executed through a stderr-capturing wrapper and evaluated by exit code, not by stderr presence.


## V2.7 correction

V2.7 adds an early GitHub authorization preflight. If the token is authenticated as `Goldkelch` but the target is `ingolf-lohmann/qik-vrt` and Goldkelch has no write permission, the workflow BLOCKs before local publish worktree creation. Use a writer token, grant write access, or target the Zenodo-enabled repository owned by the authenticated account.
