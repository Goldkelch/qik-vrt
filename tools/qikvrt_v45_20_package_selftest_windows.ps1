param([string]$Root)
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = Split-Path -Parent $PSScriptRoot }
. (Join-Path $PSScriptRoot 'qikvrt_common_windows.ps1')
$required = @(
 'tools\qikvrt_v45_20_local_verify_windows.ps1',
 'tools\qikvrt_v45_20_document_persistence_release_windows.ps1',
 'tools\qikvrt_v45_20_package_selftest_windows.ps1',
 'tools\qikvrt_common_windows.ps1',
 'QIKVRT_V45_20_RUN_LOCAL_VERIFY.cmd',
 'QIKVRT_V45_20_REAL_GITHUB_RELEASE.cmd'
)
foreach ($r in $required) { Require-File (Join-Path $Root $r) }
$common = Get-Content -LiteralPath (Join-Path $Root 'tools\qikvrt_common_windows.ps1') -Raw
$releaseScript = Get-Content -LiteralPath (Join-Path $Root 'tools\qikvrt_v45_20_document_persistence_release_windows.ps1') -Raw
if ($common -match 'function\s+Run-Git\s*\(\s*\[string\[\]\]\$args\s*\)') { QFail 'legacy Run-Git $args collision pattern still present' }
if ($common -notmatch 'ValueFromRemainingArguments') { QFail 'ValueFromRemainingArguments guard missing' }
if ($common -notmatch 'empty argument vector') { QFail 'zero-argument git/gh guard missing' }

if ($common -notmatch 'Test-QikvrtGitRemoteExists') { QFail 'safe origin remote existence guard missing' }
if ($common -match 'git remote get-url origin \*>') { QFail 'unsafe native stderr origin probe still present' }

if ($releaseScript -match 'gh release view \$tag \*>') { QFail 'unsafe GitHub release view native probe still present' }
if ($common -notmatch 'Test-QikvrtGitHubReleaseExists') { QFail 'safe GitHub release-existence probe missing' }
if ($common -notmatch 'cmd.exe /d /c') { QFail 'safe GitHub release probe must use cmd.exe /d /c redirection' }
QPass 'QIKVRT V45.20 package wrapper, Git invocation, safe origin probe and safe release probe selftest ok'
exit 0
