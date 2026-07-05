# V2.5 Git stderr capture fix

## BLOCK corrected from V2.4

V2.4 reached GitHub REST token preflight and Git HTTPS transport preflight, then failed during a Git command because Git writes normal progress output such as `From https://github.com/...` to stderr. Windows PowerShell surfaced native stderr as `NativeCommandError`, even when the Git process itself may be successful.

## V2.5 correction

The Git wrapper no longer uses `& git ... 2>&1` for operational Git commands. It uses a Windows PowerShell 5.1-compatible `Start-Process` execution path with stdout and stderr redirected to temporary files. Only the Git process exit code decides PASS/BLOCK; stderr progress is recorded as non-fatal informational output.

## Status

- V2.4 = BLOCK: `POWERSHELL_NATIVE_STDERR_PROGRESS_TREATED_AS_ERROR`
- V2.5 = candidate fix: `GIT_STDERR_CAPTURE_BY_EXITCODE`
- Remote GitHub publish still requires owner-side `GITHUB_TOKEN` and enabled Zenodo GitHub integration.
