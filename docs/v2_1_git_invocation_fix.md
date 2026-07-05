# V2.3 Git Invocation Fix

V2.0 is BLOCK because the PowerShell call pattern

```powershell
Invoke-GitSafe @('-C', $workDir, 'init') 'git init failed.'
```

allowed positional array binding to concatenate the block message into the Git argument vector on Windows PowerShell, making `git init` receive invalid extra arguments and print the Git usage help.

V2.3 replaces all Git helper calls with named parameter invocation:

```powershell
Invoke-GitSafe -Args @('-C', $workDir, 'init') -BlockMessage 'git init failed.'
```

New gate: `GIT_INVOCATION_SELFTEST.cmd` runs the same helper call against a temporary local directory and verifies that `.git` is created.

Status: V2.0 BLOCK, V2.3 replaces V2.0.
