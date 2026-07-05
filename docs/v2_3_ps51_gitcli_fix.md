# QIKVRT ODU V2.3 PowerShell 5.1 Git CLI Fix

V2.2 is BLOCK because `System.Diagnostics.ProcessStartInfo.ArgumentList` is not available in Windows PowerShell 5.1/.NET Framework environments.

V2.3 replaces the Git execution helper with a Windows PowerShell 5.1 compatible call-operator invocation:

```powershell
function Invoke-GitSafe {
  param([string[]]$GitArgs, [string]$BlockMessage)
  $gitCommand = Get-Command git
  $gitExe = $gitCommand.Source
  $output = & $gitExe @GitArgs 2>&1
}
```

Required gate order under Windows:

1. `POWERSHELL_PARSE_CHECK_ONLY.cmd`
2. `GIT_INVOCATION_SELFTEST.cmd`
3. `GITHUB_DRY_RUN_VERIFY_ONLY.cmd`
4. `GITHUB_ZENODO_UPLOAD_AND_PUBLISH.cmd`

GitHub live publishing remains owner-side only because it requires a valid owner GitHub token with repository contents write access.
