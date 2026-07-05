[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'github_zenodo_release_publish.ps1'
& powershell -NoProfile -ExecutionPolicy Bypass -File $script -LocalGitSelfTestOnly
exit $LASTEXITCODE
