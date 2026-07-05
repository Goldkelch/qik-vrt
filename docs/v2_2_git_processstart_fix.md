# QIKVRT ODU V2.3 PowerShell 5.1 Git CLI Fix

V2.1 remained BLOCK because the Windows-side git init path still invoked git through a helper using a parameter named `Args`. In PowerShell this collides conceptually with the automatic `$args` variable and was not acceptable for a release/publish path.

V2.3 replaces the helper with `Invoke-GitSafe -GitArgs ...` and uses `System.Diagnostics.PowerShell 5.1 call operator.ArgumentList` to pass arguments to git.exe exactly as distinct arguments.

Additional evidence: `qikvrt/sandbox_git_local_execution_report_v2_3.json` records a real sandbox execution of local Git init/config/add/commit/tag commands. GitHub remote push/release cannot be performed in this sandbox without the owner's GitHub token and network-authorized target repository.

Status: V2.3 supersedes V2.1.
