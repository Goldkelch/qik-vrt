[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Target = Join-Path $PSScriptRoot 'github_zenodo_release_publish.ps1'
if (-not (Test-Path -LiteralPath $Target)) {
  Write-Host "BLOCK: target script missing: $Target" -ForegroundColor Red
  exit 1
}
$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile($Target, [ref]$tokens, [ref]$errors) | Out-Null
if ($errors -and $errors.Count -gt 0) {
  Write-Host 'BLOCK: PowerShell parser errors in tools\github_zenodo_release_publish.ps1' -ForegroundColor Red
  foreach ($e in $errors) { Write-Host ($e.ToString()) -ForegroundColor Red }
  exit 1
}
$txt = Get-Content -LiteralPath $Target -Raw
foreach ($bad in @('function\s+\w+function','Invoke-GitHubUploadfunction','\[string\[\]\]\$Args','&\s*git\s+@Args','Invoke-GitSafe\s+-Args\s+@\(','ProcessStartInfo','\.ArgumentList')) {
  if ($txt -match $bad) {
    Write-Host "BLOCK: forbidden PowerShell/Git wrapper pattern remains: $bad" -ForegroundColor Red
    exit 1
  }
}
foreach ($need in @('function Invoke-GitSafe','[string[]]$GitArgs','& $gitExe @GitArgs','LocalGitSelfTestOnly','404 treated as expected absence','No GitHub Git-Blobs API used')) {
  if ($txt.IndexOf($need) -lt 0) {
    Write-Host "BLOCK: required V2.3 PowerShell 5.1 Git fragment missing: $need" -ForegroundColor Red
    exit 1
  }
}
Write-Host 'PASS PowerShell parser accepted V2.3 github_zenodo_release_publish.ps1 and V2.2 ArgumentList path is absent' -ForegroundColor Green
exit 0
