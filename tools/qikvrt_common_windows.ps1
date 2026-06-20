$ErrorActionPreference = "Stop"
function QFail([string]$msg) { Write-Host "BLOCK $msg"; exit 1 }
function QPass([string]$msg) { Write-Host "PASS $msg" }
function QContinue([string]$msg) { Write-Host "CONTINUE $msg" }
function Require-File([string]$p) { if (!(Test-Path -LiteralPath $p -PathType Leaf)) { QFail "required file missing: $p" } else { QPass "required file present: $p" } }
function Require-Dir([string]$p) { if (!(Test-Path -LiteralPath $p -PathType Container)) { QFail "required directory missing: $p" } else { QPass "required directory present: $p" } }
function Get-SHA256([string]$p) { return (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLowerInvariant() }
function Invoke-QikvrtGit {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$GitArgs)
  if ($null -eq $GitArgs -or $GitArgs.Count -eq 0) { QFail "git invocation blocked: empty argument vector" }
  & git @GitArgs
  if ($LASTEXITCODE -ne 0) { QFail "git failed rc=$LASTEXITCODE args=$($GitArgs -join ' ')" }
}
function Invoke-QikvrtGH {
  param([Parameter(ValueFromRemainingArguments=$true)][string[]]$GhArgs)
  if ($null -eq $GhArgs -or $GhArgs.Count -eq 0) { QFail "gh invocation blocked: empty argument vector" }
  & gh @GhArgs
  if ($LASTEXITCODE -ne 0) { QFail "gh failed rc=$LASTEXITCODE args=$($GhArgs -join ' ')" }
}
function Normalize-Origin([string]$o) {
  if ([string]::IsNullOrWhiteSpace($o)) { $o = "Goldkelch/qik-vrt" }
  $o = $o.Trim()
  if ($o -match '^https://github.com/.+/.+(\.git)?$') { if ($o.EndsWith('.git')) { return $o } else { return "$o.git" } }
  if ($o -match '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') { return "https://github.com/$o.git" }
  QFail "invalid origin format: $o"
}
function Copy-Overlay([string]$src, [string]$dst) {
  if (!(Test-Path -LiteralPath $src -PathType Container)) { QFail "overlay source missing: $src" }
  Get-ChildItem -LiteralPath $src -Force | ForEach-Object {
    if ($_.Name -eq '.git') { return }
    Copy-Item -LiteralPath $_.FullName -Destination $dst -Recurse -Force
  }
}
function Verify-Asset-NoClobber([string]$tag, [string]$assetPath, [string]$expectedSha, [string]$tmpDir) {
  $assetName = Split-Path -Leaf $assetPath
  $assetList = (& gh release view $tag --json assets --jq '.assets[].name' 2>$null)
  if ($LASTEXITCODE -ne 0) { QFail "cannot view release assets for $tag" }
  if ($assetList -contains $assetName) {
    QContinue "asset exists; download-verify without clobber: $assetName"
    New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
    & gh release download $tag --pattern $assetName --dir $tmpDir --clobber | Out-Host
    if ($LASTEXITCODE -ne 0) { QFail "asset download failed: $assetName" }
    $downloaded = Join-Path $tmpDir $assetName
    if (!(Test-Path -LiteralPath $downloaded -PathType Leaf)) { QFail "downloaded asset missing: $downloaded" }
    $got = Get-SHA256 $downloaded
    if ($got -ne $expectedSha) { QFail "existing asset hash mismatch: $assetName got=$got expected=$expectedSha" }
    QPass "existing asset hash verified: $assetName"
  } else {
    Invoke-QikvrtGH 'release' 'upload' $tag $assetPath
    QPass "uploaded asset: $assetName"
  }
}

function Test-QikvrtGitRemoteExists {
  param([string]$Name)
  if ([string]::IsNullOrWhiteSpace($Name)) { QFail "git remote existence check blocked: empty remote name" }
  $remoteList = @(& git remote)
  if ($LASTEXITCODE -ne 0) { QFail "git remote list failed rc=$LASTEXITCODE" }
  foreach ($r in $remoteList) { if ($r.Trim() -eq $Name) { return $true } }
  return $false
}
function Get-QikvrtGitRemoteUrl {
  param([string]$Name)
  if (-not (Test-QikvrtGitRemoteExists $Name)) { return $null }
  $url = (& git remote get-url $Name 2>$null)
  if ($LASTEXITCODE -ne 0) { QFail "git remote get-url failed for existing remote: $Name" }
  return ($url | Select-Object -First 1).Trim()
}

function Assert-GitInvocationLayer {
  $cmd = Get-Command Invoke-QikvrtGit -ErrorAction Stop
  Invoke-QikvrtGit '--version'
  
  if (Test-QikvrtGitRemoteExists 'origin') { QContinue "origin already exists during Git invocation selftest" } else { QPass "safe missing-origin probe ok" }
  QPass "Git invocation and safe origin probe layer selftest ok"
}


function Test-QikvrtGitHubReleaseExists {
  param([string]$Tag)
  if ([string]::IsNullOrWhiteSpace($Tag)) { QFail "GitHub release existence check blocked: empty tag" }
  # Use cmd.exe redirection to avoid PowerShell NativeCommandError when gh writes "release not found" to stderr.
  & cmd.exe /d /c "gh release view $Tag >NUL 2>NUL"
  $rc = $LASTEXITCODE
  if ($rc -eq 0) { return $true }
  return $false
}
function Assert-QikvrtGitHubReleaseProbeLayer {
  $probeSource = (Get-Command Test-QikvrtGitHubReleaseExists -ErrorAction Stop).ScriptBlock.ToString()
  if ($probeSource -notmatch 'cmd.exe') { QFail 'safe GitHub release probe must use cmd.exe redirection' }
  QPass 'GitHub release probe layer selftest ok'
}

