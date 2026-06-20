param([string]$Root, [string]$OriginInput)
$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($Root)) { $Root = Split-Path -Parent $PSScriptRoot }
. (Join-Path $PSScriptRoot 'qikvrt_common_windows.ps1')
Write-Host "QIKVRT V45.20 real GitHub document persistence release wrapper"
Write-Host "WARNING: real state-changing effects: git init/fetch/clean checkout/overlay commit/push/tag/release/upload. No force tag. No asset clobber."
Write-Host "Required exact confirmation: JA, ICH AKZEPTIERE"
$confirm = Read-Host "Type exact confirmation now"
if ($confirm -ne 'JA, ICH AKZEPTIERE') {
  New-Item -ItemType Directory -Force -Path (Join-Path $Root 'state') | Out-Null
  $rej = @{ status='BLOCK'; reason='EXACT_CONFIRMATION_NOT_SUPPLIED'; supplied=$confirm; required='JA, ICH AKZEPTIERE'; timestamp=(Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json -Depth 5
  Set-Content -LiteralPath (Join-Path $Root 'state/rejected_acceptance_record.v45.20.json') -Value $rej -Encoding UTF8
  QFail "required exact confirmation was not supplied"
}
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'state') | Out-Null
$acc = @{ status='ACCEPTED'; scope='QIKVRT V45.20 document persistence safe GitHub release-probe repair real GitHub merge/release'; accepted_by='Ingolf Lohmann'; timestamp=(Get-Date).ToUniversalTime().ToString('o'); exact_confirmation=$confirm } | ConvertTo-Json -Depth 5
Set-Content -LiteralPath (Join-Path $Root 'state/owner_acceptance_record.v45.20.json') -Value $acc -Encoding UTF8
QPass "owner acceptance persisted"
$env:QIKVRT_ENABLE_REAL_GITHUB_EFFECTS = 'YES'

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'qikvrt_v45_20_package_selftest_windows.ps1') -Root $Root
if ($LASTEXITCODE -ne 0) { QFail "package selftest failed" }
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'qikvrt_v45_20_local_verify_windows.ps1') -Root $Root
if ($LASTEXITCODE -ne 0) { QFail "local verify failed" }

$originUrl = Normalize-Origin $OriginInput
$tag = 'v45.20'
$releaseTitle = 'QIKVRT V45.20 Document Persistence Safe Release Probe Repair Release'
$bundle = Join-Path $Root 'dist/QIKVRT_V45_20_DOCUMENTS_BUNDLE.zip'
$bundleSha = Get-SHA256 $bundle
$tmp = Join-Path ([System.IO.Path]::GetTempPath()) ('qikvrt_v45_20_' + [guid]::NewGuid().ToString('N'))
$overlay = Join-Path $tmp 'package_overlay'
New-Item -ItemType Directory -Force -Path $overlay | Out-Null
Copy-Overlay $Root $overlay
QPass "package overlay staged before git clean/checkout: $overlay"

& git --version | Out-Host; if ($LASTEXITCODE -ne 0) { QFail "git unavailable" }
& gh --version | Out-Host; if ($LASTEXITCODE -ne 0) { QFail "gh unavailable" }
Set-Location $Root
if (!(Test-Path -LiteralPath (Join-Path $Root '.git') -PathType Container)) {
  QContinue "no .git repository found; initializing local Git repository"
  Invoke-QikvrtGit 'init'
}
Invoke-QikvrtGit 'config' '--local' 'user.name' 'Ingolf Lohmann'
Invoke-QikvrtGit 'config' '--local' 'user.email' 'ingolf.lohmann@web.de'
Invoke-QikvrtGit 'config' '--local' 'core.autocrlf' 'false'
Invoke-QikvrtGit 'config' '--local' 'core.safecrlf' 'false'
Assert-GitInvocationLayer
$hasOrigin = Test-QikvrtGitRemoteExists 'origin'
if (!$hasOrigin) {
  Invoke-QikvrtGit 'remote' 'add' 'origin' $originUrl
  QPass "git origin added: $originUrl"
} else {
  $existingOrigin = Get-QikvrtGitRemoteUrl 'origin'
  QPass "git origin already configured: $existingOrigin"
}
Invoke-QikvrtGit 'fetch' 'origin' 'main'
QContinue "cleaning extracted package files before checkout of origin/main"
& git reset --hard | Out-Host
if ($LASTEXITCODE -ne 0) { QFail "git reset --hard failed" }
& git clean -fdx | Out-Host
if ($LASTEXITCODE -ne 0) { QFail "git clean -fdx failed" }
QPass "working tree cleaned before origin/main checkout"
Invoke-QikvrtGit 'checkout' '-B' 'main' 'origin/main'
QPass "origin/main checked out as canonical base"
Copy-Overlay $overlay $Root
QPass "V45.20 document persistence overlay restored after origin/main checkout"
Invoke-QikvrtGit 'add' '-A'
$status = (& git status --porcelain)
if ($status) {
  Invoke-QikvrtGit 'commit' '-m' 'QIKVRT V45.20 persist quantum-gravity documents and repair safe GitHub release probe layer'
  QPass "V45.20 document persistence Release probe repair commit created"
} else { QPass "no local changes to commit" }
$head = (& git rev-parse HEAD).Trim()
& git merge-base --is-ancestor origin/main HEAD
if ($LASTEXITCODE -ne 0) { QFail "origin/main is not ancestor of HEAD; refusing push" }
Invoke-QikvrtGit 'push' '-u' 'origin' 'main'
$remoteTag = (& git ls-remote --tags origin $tag)
if ($remoteTag) {
  $remoteTagSha = ($remoteTag -split '\s+')[0]
  if ($remoteTagSha -ne $head) { QFail "tag $tag already exists at different sha $remoteTagSha; refusing force update to $head" }
  QPass "remote tag already points to HEAD: $tag"
} else {
  Invoke-QikvrtGit 'tag' $tag
  Invoke-QikvrtGit 'push' 'origin' $tag
  QPass "immutable tag created and pushed: $tag"
}
Assert-QikvrtGitHubReleaseProbeLayer
if (Test-QikvrtGitHubReleaseExists $tag) {
  QPass "GitHub release already exists: $tag"
} else {
  QContinue "GitHub release does not exist yet; creating release: $tag"
  Invoke-QikvrtGH 'release' 'create' $tag '--title' $releaseTitle '--notes' 'QIKVRT V45.20 persists four QIK-VRT/quantum-gravity PDF documents and repairs the V45.19 gh release view NativeCommandError before release create. No force tag. No asset clobber.'
  QPass "GitHub release created: $tag"
} 
Verify-Asset-NoClobber $tag $bundle $bundleSha (Join-Path $tmp 'download_bundle')
Verify-Asset-NoClobber $tag (Join-Path $Root 'dist/QIKVRT_V45_20_DOCUMENTS_BUNDLE.zip.sha256') (Get-SHA256 (Join-Path $Root 'dist/QIKVRT_V45_20_DOCUMENTS_BUNDLE.zip.sha256')) (Join-Path $tmp 'download_sha')
Verify-Asset-NoClobber $tag (Join-Path $Root 'dist/QIKVRT_V45_20_DOCUMENTS_BUNDLE.zip.manifest.json') (Get-SHA256 (Join-Path $Root 'dist/QIKVRT_V45_20_DOCUMENTS_BUNDLE.zip.manifest.json')) (Join-Path $tmp 'download_manifest')
$ev = @{ status='PASS'; version='V45.20'; tag=$tag; head=$head; origin=$originUrl; bundle_sha256=$bundleSha; repaired_error='BLOCK_GH_RELEASE_VIEW_NATIVE_COMMAND_ERROR_BEFORE_RELEASE_CREATE'; release_url='https://github.com/Goldkelch/qik-vrt/releases/tag/v45.20'; timestamp=(Get-Date).ToUniversalTime().ToString('o') } | ConvertTo-Json -Depth 5
New-Item -ItemType Directory -Force -Path (Join-Path $Root 'audit') | Out-Null
Set-Content -LiteralPath (Join-Path $Root 'audit/github_remote_effect_evidence.v45.20.json') -Value $ev -Encoding UTF8
QPass "real GitHub document persistence evidence persisted locally and release assets verified"
exit 0
