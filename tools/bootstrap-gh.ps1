<#
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann.
#>
[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$Install,
    [switch]$AcceptThirdParty,
    [string]$CacheDir = '',
    [string]$ArchiveFile = '',
    [switch]$PrintPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$Version = '2.96.0'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Checksums = Join-Path $RepoRoot 'runtime\toolchains\gh-2.96.0-checksums.txt'
$script:TempDir = $null
$script:RollbackCacheRoot = $false
$script:InstalledCacheRoot = $null

if ([string]::IsNullOrWhiteSpace($CacheDir)) {
    if ([string]::IsNullOrWhiteSpace($env:QIKVRT_TOOLCHAIN_CACHE)) {
        $CacheDir = Join-Path $RepoRoot '.qikvrt\toolchains'
    } else {
        $CacheDir = $env:QIKVRT_TOOLCHAIN_CACHE
    }
}

function Show-Usage {
    @'
Usage: tools\bootstrap-gh.ps1 [-CheckOnly] [-Install]
       [-AcceptThirdParty] [-CacheDir PATH] [-ArchiveFile PATH] [-PrintPath]

The default is an offline, non-mutating exact-version check. -Install also
requires -AcceptThirdParty. Authentication is intentionally not performed.

Exit status: 0 PASS, 20 CONTINUE (runtime absent), 1 BLOCK.
'@ | Write-Output
}

function Remove-StagingDirectory {
    if ($script:RollbackCacheRoot -and $null -ne $script:InstalledCacheRoot) {
        if (Test-Path -LiteralPath $script:InstalledCacheRoot) {
            Remove-Item -LiteralPath $script:InstalledCacheRoot -Recurse -Force
        }
        $script:RollbackCacheRoot = $false
        $script:InstalledCacheRoot = $null
    }
    if ($null -ne $script:TempDir -and (Test-Path -LiteralPath $script:TempDir)) {
        Remove-Item -LiteralPath $script:TempDir -Recurse -Force
        $script:TempDir = $null
    }
}

function Stop-Block([string]$Message) {
    Remove-StagingDirectory
    Write-Error "BLOCK: $Message"
    exit 1
}

function Stop-Continue([string]$Message) {
    Write-Warning "CONTINUE: $Message"
    exit 20
}

function Assert-NoReparseChain([string]$Path) {
    $cursor = [IO.Path]::GetFullPath($Path)
    while (-not [string]::IsNullOrWhiteSpace($cursor)) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                Stop-Block "cache path contains a reparse point: $cursor"
            }
        }
        $parent = [IO.Path]::GetDirectoryName($cursor)
        if ([string]::IsNullOrWhiteSpace($parent) -or $parent -eq $cursor) { break }
        $cursor = $parent
    }
}

function Test-ExactVersion([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    try {
        $output = @(& $Path --version 2>$null)
        if ($LASTEXITCODE -ne 0 -or $output.Count -eq 0) { return $false }
        return ([string]$output[0] -eq "gh version $Version (2026-07-02)")
    } catch {
        return $false
    }
}

function Get-ExpectedArchiveHash([string]$Archive) {
    foreach ($line in Get-Content -LiteralPath $Checksums) {
        if ($line -match ('^([0-9a-f]{64})\s+' + [regex]::Escape($Archive) + '$')) {
            return $Matches[1]
        }
    }
    return $null
}

function Assert-CachedDerivation([string]$Candidate, [string]$CachedArchive, [string]$ExpectedArchiveHash) {
    if (-not (Test-Path -LiteralPath $CachedArchive -PathType Leaf)) {
        Stop-Block "cached GitHub CLI archive is missing: $CachedArchive"
    }
    $actualArchiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $CachedArchive).Hash.ToLowerInvariant()
    if ($actualArchiveHash -ne $ExpectedArchiveHash) { Stop-Block 'cached GitHub CLI archive checksum mismatch' }

    # Re-extract the repo-hash-anchored archive and compare executable bytes.
    # A cache receipt and --version output are not sufficient authorities.
    $verifyDir = Join-Path ([IO.Path]::GetTempPath()) ('qikvrt-gh-verify-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $verifyDir | Out-Null
    try {
        Expand-Archive -LiteralPath $CachedArchive -DestinationPath $verifyDir
        $derived = Join-Path $verifyDir "gh_${Version}_windows_${Arch}\bin\gh.exe"
        if (-not (Test-Path -LiteralPath $derived -PathType Leaf)) {
            Stop-Block 'repo-anchored archive does not contain the expected GitHub CLI executable'
        }
        $derivedHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $derived).Hash.ToLowerInvariant()
        $candidateHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Candidate).Hash.ToLowerInvariant()
        if ($candidateHash -ne $derivedHash) {
            Stop-Block 'cached GitHub CLI executable is not derived from the repo-anchored archive'
        }
    } finally {
        Remove-Item -LiteralPath $verifyDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    if (-not (Test-ExactVersion $Candidate)) { Stop-Block 'cached GitHub CLI failed the exact-version execution check' }
}

function Write-Pass([string]$Path, [string]$SourceName) {
    if ($PrintPath) {
        Write-Output $Path
    } else {
        Write-Output "PASS: GitHub CLI $Version ($SourceName): $Path"
    }
    exit 0
}

if ($CheckOnly -and $Install) { Stop-Block '-CheckOnly and -Install are mutually exclusive' }
if (-not (Test-Path -LiteralPath $Checksums -PathType Leaf)) { Stop-Block "missing checksum authority: $Checksums" }

if (-not [System.Runtime.InteropServices.RuntimeInformation]::IsOSPlatform(
        [System.Runtime.InteropServices.OSPlatform]::Windows)) {
    Stop-Continue 'the PowerShell bootstrap currently targets Windows; use bootstrap-gh.sh on POSIX'
}

switch ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()) {
    'X64' { $Arch = 'amd64' }
    'Arm64' { $Arch = 'arm64' }
    default { Stop-Continue 'no locked Windows GitHub CLI asset exists for this architecture' }
}

$Target = "windows-$Arch"
$Archive = "gh_${Version}_windows_${Arch}.zip"
$ExpectedArchiveHash = Get-ExpectedArchiveHash $Archive
if ([string]::IsNullOrWhiteSpace($ExpectedArchiveHash)) { Stop-Block "no checksum is locked for $Archive" }

if (-not $Install -and -not [string]::IsNullOrWhiteSpace($env:QIKVRT_GH)) {
    if (-not (Test-ExactVersion $env:QIKVRT_GH)) { Stop-Block "QIKVRT_GH is not executable GitHub CLI $Version" }
    Write-Pass $env:QIKVRT_GH 'explicit'
}

$CacheRoot = Join-Path $CacheDir "gh\$Version\$Target"
$CachedGh = Join-Path $CacheRoot 'bin\gh.exe'
$CachedArchive = Join-Path $CacheRoot "archive\$Archive"
Assert-NoReparseChain $CacheDir
Assert-NoReparseChain $CacheRoot
if (Test-Path -LiteralPath $CachedGh) {
    Assert-NoReparseChain $CachedGh
    Assert-CachedDerivation -Candidate $CachedGh -CachedArchive $CachedArchive -ExpectedArchiveHash $ExpectedArchiveHash
    Write-Pass $CachedGh 'verified-cache'
}

if (-not $Install) {
    $systemGh = Get-Command gh -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $systemGh -and (Test-ExactVersion $systemGh.Source)) {
        Write-Pass $systemGh.Source 'system'
    }
}

if (-not $Install) { Stop-Continue "GitHub CLI $Version is not available; rerun with explicit installation consent" }
if (-not $AcceptThirdParty) { Stop-Block '-Install requires -AcceptThirdParty' }
if (Test-Path -LiteralPath $CacheRoot) { Stop-Block "refusing to replace an incomplete GitHub CLI cache: $CacheRoot" }
if (Test-Path -LiteralPath $CacheDir) {
    $cacheItem = Get-Item -LiteralPath $CacheDir -Force
    if (($cacheItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { Stop-Block 'toolchain cache directory must not be a reparse point' }
}

try {
$versionRoot = Join-Path $CacheDir "gh\$Version"
New-Item -ItemType Directory -Force -Path $versionRoot | Out-Null
Assert-NoReparseChain $versionRoot
$script:TempDir = Join-Path $versionRoot ('.install-' + $Target + '-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $script:TempDir | Out-Null
$Downloaded = Join-Path $script:TempDir $Archive
$Url = "https://github.com/cli/cli/releases/download/v$Version/$Archive"

if (-not [string]::IsNullOrWhiteSpace($ArchiveFile)) {
    if (-not (Test-Path -LiteralPath $ArchiveFile -PathType Leaf)) {
        Stop-Block '-ArchiveFile must name a regular file'
    }
    $archiveItem = Get-Item -LiteralPath $ArchiveFile -Force
    if (($archiveItem.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        Stop-Block '-ArchiveFile must not be a reparse point'
    }
    Copy-Item -LiteralPath $ArchiveFile -Destination $Downloaded
} else {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Downloaded
    } catch {
        Stop-Block "GitHub CLI download failed: $($_.Exception.Message)"
    }
}
$actualArchiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Downloaded).Hash.ToLowerInvariant()
if ($actualArchiveHash -ne $ExpectedArchiveHash) { Stop-Block 'downloaded GitHub CLI archive checksum mismatch' }

$ExtractDir = Join-Path $script:TempDir 'extracted'
New-Item -ItemType Directory -Path $ExtractDir | Out-Null
try {
    Expand-Archive -LiteralPath $Downloaded -DestinationPath $ExtractDir
} catch {
    Stop-Block "GitHub CLI archive extraction failed: $($_.Exception.Message)"
}
$ExtractedGh = Join-Path $ExtractDir "gh_${Version}_windows_${Arch}\bin\gh.exe"
if (-not (Test-ExactVersion $ExtractedGh)) { Stop-Block 'extracted GitHub CLI failed the exact-version execution check' }

$Stage = Join-Path $script:TempDir 'stage'
New-Item -ItemType Directory -Path (Join-Path $Stage 'bin') | Out-Null
New-Item -ItemType Directory -Path (Join-Path $Stage 'archive') | Out-Null
Copy-Item -LiteralPath $ExtractedGh -Destination (Join-Path $Stage 'bin\gh.exe')
Copy-Item -LiteralPath $Downloaded -Destination (Join-Path $Stage "archive\$Archive")
$binaryHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $ExtractedGh).Hash.ToLowerInvariant()
Set-Content -LiteralPath (Join-Path $Stage 'bin\gh.exe.sha256') -Encoding ASCII -Value $binaryHash
# Failure-only regression hook for unexpected errors before the final move.
# The outer finally must remove staging; no cache root exists at this point.
if ($env:QIKVRT_TEST_FAIL_GH_PRE_MOVE -eq '1') {
    throw 'test-requested unexpected failure before final GitHub CLI cache move'
}
$script:RollbackCacheRoot = $true
$script:InstalledCacheRoot = $CacheRoot
try {
    Move-Item -LiteralPath $Stage -Destination $CacheRoot
    # Failure-only regression hook; it cannot bypass verification.
    if ($env:QIKVRT_TEST_FAIL_GH_FINAL_VERIFY -eq '1') {
        Stop-Block 'test-requested failure before final GitHub CLI cache verification'
    }
    Assert-CachedDerivation -Candidate $CachedGh -CachedArchive $CachedArchive -ExpectedArchiveHash $ExpectedArchiveHash
    $script:RollbackCacheRoot = $false
    $script:InstalledCacheRoot = $null
} catch {
    Stop-Block "final GitHub CLI cache installation failed: $($_.Exception.Message)"
}
Remove-StagingDirectory
Write-Pass $CachedGh 'installed-verified-cache'
} finally {
    # Idempotent for the normal path and for Stop-Block; essential for
    # unexpected Cmdlet errors anywhere after staging begins.
    Remove-StagingDirectory
}
