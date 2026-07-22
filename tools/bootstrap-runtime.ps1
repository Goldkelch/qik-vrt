<#
SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
Copyright 2026 Ingolf Lohmann.
#>
[CmdletBinding()]
param(
    [switch]$CheckOnly,
    [switch]$Install,
    [switch]$AcceptThirdParty,
    [ValidateSet('core', 'ietf', 'formal', 'audio', 'publication', 'all')]
    [string]$Profile = 'ietf',
    [string]$CacheDir = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Xml2rfcVersion = '3.34.0'
$PythonRendererVersion = '3.12.13'
$Xml2rfcLock = Join-Path $RepoRoot 'runtime\toolchains\requirements-xml2rfc-3.34.0.txt'
$script:TempDir = $null
$script:VenvPath = $null
$script:VenvBackup = $null
$script:InstallInProgress = $false
$script:PipExit = 0
$script:Overall = 0

if ([string]::IsNullOrWhiteSpace($CacheDir)) {
    if ([string]::IsNullOrWhiteSpace($env:QIKVRT_TOOLCHAIN_CACHE)) {
        $CacheDir = Join-Path $RepoRoot '.qikvrt\toolchains'
    } else {
        $CacheDir = $env:QIKVRT_TOOLCHAIN_CACHE
    }
}

function Remove-StagingDirectory {
    if ($script:InstallInProgress -and $null -ne $script:VenvPath) {
        if (Test-Path -LiteralPath $script:VenvPath) {
            Remove-Item -LiteralPath $script:VenvPath -Recurse -Force
        }
        if ($null -ne $script:VenvBackup -and (Test-Path -LiteralPath $script:VenvBackup)) {
            Move-Item -LiteralPath $script:VenvBackup -Destination $script:VenvPath
        }
        # Make cleanup idempotent: Stop-Block and the top-level finally may
        # both call this function for the same failed derivation.
        $script:InstallInProgress = $false
        $script:VenvBackup = $null
        $script:VenvPath = $null
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

function Set-Continue([string]$Message) {
    Write-Warning "CONTINUE: $Message"
    $script:Overall = 20
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

function Test-PythonCompatible([string]$Path, [string[]]$Prefix) {
    try {
        & $Path @Prefix -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Test-PythonRendererExact([string]$Path, [string[]]$Prefix) {
    try {
        & $Path @Prefix -I -c 'import platform, sys; raise SystemExit(0 if platform.python_version() == sys.argv[1] else 1)' $PythonRendererVersion *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Test-Python312([string]$Path, [string[]]$Prefix) {
    try {
        & $Path @Prefix -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)' *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Test-PythonPackageExact([string]$Path, [string[]]$Prefix, [string]$Package, [string]$Version) {
    try {
        & $Path @Prefix -c 'import importlib.metadata as m, sys; raise SystemExit(0 if m.version(sys.argv[1]) == sys.argv[2] else 1)' $Package $Version *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Test-Xml2rfcModuleCliExact([string]$Path, [string[]]$Prefix) {
    try {
        $output = @(& $Path @Prefix -m xml2rfc.run --version 2>$null)
        return ($LASTEXITCODE -eq 0 -and $output.Count -gt 0 -and [string]$output[0] -eq "xml2rfc $Xml2rfcVersion")
    } catch { return $false }
}

function Test-Xml2rfcCommandExact([string]$Path) {
    try {
        $output = @(& $Path --version 2>$null)
        return ($LASTEXITCODE -eq 0 -and $output.Count -gt 0 -and [string]$output[0] -eq "xml2rfc $Xml2rfcVersion")
    } catch { return $false }
}

function Get-CompatiblePython([switch]$Exact312, [switch]$RendererExact) {
    if (-not [string]::IsNullOrWhiteSpace($env:QIKVRT_PYTHON)) {
        $ok = if ($RendererExact) {
            Test-PythonRendererExact -Path $env:QIKVRT_PYTHON -Prefix @()
        } elseif ($Exact312) {
            Test-Python312 -Path $env:QIKVRT_PYTHON -Prefix @()
        } else {
            Test-PythonCompatible -Path $env:QIKVRT_PYTHON -Prefix @()
        }
        if (-not $ok) { Stop-Block 'QIKVRT_PYTHON does not satisfy the requested Python contract' }
        return [pscustomobject]@{ Path = $env:QIKVRT_PYTHON; Prefix = @() }
    }

    $names = if ($Exact312 -or $RendererExact) { @('python3.12', 'python', 'python3') } else { @('python', 'python3') }
    foreach ($name in $names) {
        $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $command) {
            $ok = if ($RendererExact) {
                Test-PythonRendererExact -Path $command.Source -Prefix @()
            } elseif ($Exact312) {
                Test-Python312 -Path $command.Source -Prefix @()
            } else {
                Test-PythonCompatible -Path $command.Source -Prefix @()
            }
            if ($ok) { return [pscustomobject]@{ Path = $command.Source; Prefix = @() } }
        }
    }

    $launcher = Get-Command py -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $launcher) {
        $prefix = if ($Exact312 -or $RendererExact) { @('-3.12') } else { @('-3') }
        $ok = if ($RendererExact) {
            Test-PythonRendererExact -Path $launcher.Source -Prefix $prefix
        } elseif ($Exact312) {
            Test-Python312 -Path $launcher.Source -Prefix $prefix
        } else {
            Test-PythonCompatible -Path $launcher.Source -Prefix $prefix
        }
        if ($ok) { return [pscustomobject]@{ Path = $launcher.Source; Prefix = $prefix } }
    }
    return $null
}

function Invoke-IsolatedPip([string]$Path, [string[]]$Prefix, [string[]]$PipArguments) {
    $names = @('PIP_CONFIG_FILE', 'PIP_INDEX_URL', 'PIP_EXTRA_INDEX_URL', 'PIP_TRUSTED_HOST',
        'PIP_FIND_LINKS', 'PIP_NO_INDEX', 'PIP_REQUIRE_VIRTUALENV', 'PIP_DISABLE_PIP_VERSION_CHECK',
        'PIP_NO_INPUT', 'PYTHONNOUSERSITE', 'PYTHONPATH', 'PYTHONHOME')
    $saved = @{}
    foreach ($name in $names) {
        $saved[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
        [Environment]::SetEnvironmentVariable($name, $null, 'Process')
    }
    $env:PIP_CONFIG_FILE = 'NUL'
    $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
    $env:PIP_NO_INPUT = '1'
    $env:PYTHONNOUSERSITE = '1'
    try {
        & $Path @Prefix -I -m pip --isolated --disable-pip-version-check @PipArguments
        $script:PipExit = $LASTEXITCODE
    } catch {
        $script:PipExit = 1
    } finally {
        foreach ($name in $names) {
            [Environment]::SetEnvironmentVariable($name, $saved[$name], 'Process')
        }
    }
}

function Test-LockedEnvironmentExact([string]$PythonPath) {
    $code = 'import importlib.metadata as m,pathlib,re,sys; c=lambda s:re.sub(r"[-_.]+","-",s).lower(); e={c(x.group(1)):x.group(2) for line in pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if (x:=re.match(r"^([A-Za-z0-9_.-]+)==([^ \\]+)",line))}; a={c(d.metadata["Name"]):d.version for d in m.distributions()}; raise SystemExit(0 if all(a.get(k)==v for k,v in e.items()) and not(set(a)-set(e)-{"pip","setuptools"}) else 1)'
    try {
        & $PythonPath -I -c $code $Xml2rfcLock *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Test-Node24 {
    $node = Get-Command node -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $node) { return $false }
    try {
        $version = [string](& ($node.Source) --version 2>$null | Select-Object -First 1)
        return ($LASTEXITCODE -eq 0 -and $version -match '^v24\.')
    } catch { return $false }
}

function Test-NodePackage([string]$Directory, [string]$Package, [string]$Version) {
    Push-Location $Directory
    try {
        & node -e 'const [name,want]=process.argv.slice(1); const p=require(`./node_modules/${name}/package.json`); process.exit(p.version===want?0:1)' $Package $Version *> $null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false } finally { Pop-Location }
}

function Test-C90Compiler {
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($env:CC)) { $candidates += $env:CC }
    $candidates += @('cl', 'clang-cl', 'clang', 'gcc', 'cc')
    $source = Join-Path ([IO.Path]::GetTempPath()) ('qikvrt-c90-' + [guid]::NewGuid().ToString('N') + '.c')
    [IO.File]::WriteAllText($source, "int main(void) { return 0; }`n", [Text.Encoding]::ASCII)
    try {
        foreach ($name in $candidates) {
            $command = Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($null -eq $command) { continue }
            $leaf = [IO.Path]::GetFileNameWithoutExtension($command.Source).ToLowerInvariant()
            if ($leaf -eq 'cl' -or $leaf -eq 'clang-cl') {
                & ($command.Source) /nologo /W4 /WX /TC /Zs $source *> $null
            } else {
                & ($command.Source) -std=c90 -pedantic -Wall -Wextra -Werror -fsyntax-only $source *> $null
            }
            if ($LASTEXITCODE -eq 0) { return $command.Source }
        }
    } finally {
        Remove-Item -LiteralPath $source -Force -ErrorAction SilentlyContinue
    }
    return $null
}

function Test-CoreProfile {
    $compiler = Test-C90Compiler
    if ($null -eq $compiler) {
        Set-Continue 'core: strict ANSI-C90 compiler contract is unavailable; automatic installation is not supported'
    } else {
        Write-Output "PASS: core ANSI-C90 compiler contract: $compiler"
    }
}

function Test-IetfProfile {
    if (-not (Test-Path -LiteralPath $Xml2rfcLock -PathType Leaf)) { Stop-Block "missing xml2rfc lock: $Xml2rfcLock" }
    $pins = @(Get-Content -LiteralPath $Xml2rfcLock | Where-Object { $_ -match '^[A-Za-z0-9_.-]+==' })
    if ($pins.Count -ne 19) { Stop-Block 'xml2rfc lock must contain exactly 19 pinned packages' }
    if (-not ($pins | Where-Object { $_ -match ('^xml2rfc==' + [regex]::Escape($Xml2rfcVersion) + '\s+\\$') })) {
        Stop-Block "xml2rfc lock does not pin version $Xml2rfcVersion"
    }
    if ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString() -ne 'X64') {
        Set-Continue 'ietf: the locked xml2rfc wheel set targets x64 runners'
        return
    }

    $XmlRoot = Join-Path $CacheDir "xml2rfc\$Xml2rfcVersion\python-$PythonRendererVersion\windows-amd64"
    $XmlCache = Join-Path $XmlRoot 'venv'
    $Wheelhouse = Join-Path $XmlRoot 'wheelhouse'
    $CachedPython = Join-Path $XmlCache 'Scripts\python.exe'
    $CachedXml2rfc = Join-Path $XmlCache 'Scripts\xml2rfc.exe'
    $CompleteMarker = Join-Path $XmlRoot 'COMPLETE'
    Assert-NoReparseChain $XmlRoot

    if (-not $Install) {
        # Never execute a restored venv in check-only mode. Explicit install
        # rebuilds it from hash-verified wheels first.
        Set-Continue "ietf: fresh hash-locked derivation of xml2rfc $Xml2rfcVersion / Python $PythonRendererVersion is required"
        return
    }
    $python = Get-CompatiblePython -RendererExact
    if ($null -eq $python) { Stop-Block "exactly Python $PythonRendererVersion is required to install the IETF renderer" }
    Assert-NoReparseChain (Join-Path $CacheDir 'xml2rfc')
    New-Item -ItemType Directory -Force -Path $XmlRoot | Out-Null
    Assert-NoReparseChain $XmlRoot
    $script:TempDir = Join-Path $XmlRoot ('.install-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $script:TempDir | Out-Null
    $VerifiedWheelhouse = Join-Path $script:TempDir 'verified-wheelhouse'
    New-Item -ItemType Directory -Path $VerifiedWheelhouse | Out-Null

    if (Test-Path -LiteralPath $Wheelhouse -PathType Container) {
        Assert-NoReparseChain $Wheelhouse
        Invoke-IsolatedPip -Path $python.Path -Prefix $python.Prefix -PipArguments @(
            'download', '--no-index', '--find-links', $Wheelhouse, '--dest', $VerifiedWheelhouse,
            '--only-binary=:all:', '--require-hashes', '--no-deps', '-r', $Xml2rfcLock)
        if ($script:PipExit -ne 0) { Stop-Block 'cached wheelhouse failed hash-locked offline verification' }
    } else {
        if (Test-Path -LiteralPath $Wheelhouse) { Stop-Block 'renderer wheelhouse is not a regular directory' }
        Invoke-IsolatedPip -Path $python.Path -Prefix $python.Prefix -PipArguments @(
            'download', '--index-url', 'https://pypi.org/simple', '--dest', $VerifiedWheelhouse,
            '--only-binary=:all:', '--require-hashes', '--no-deps', '-r', $Xml2rfcLock)
        if ($script:PipExit -ne 0) { Stop-Block 'hash-locked renderer wheel download failed' }
        Move-Item -LiteralPath $VerifiedWheelhouse -Destination $Wheelhouse
        $VerifiedWheelhouse = $Wheelhouse
    }

    # Actions restores only the verified wheelhouse. Every explicit install
    # derives the venv again at its final console-launcher path.
    $script:VenvPath = $XmlCache
    $script:InstallInProgress = $true
    if (Test-Path -LiteralPath $XmlCache) {
        $item = Get-Item -LiteralPath $XmlCache -Force
        if (-not $item.PSIsContainer -or (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)) {
            Stop-Block 'renderer venv is not a regular directory'
        }
        $script:VenvBackup = Join-Path $script:TempDir 'previous-venv'
        Move-Item -LiteralPath $XmlCache -Destination $script:VenvBackup
    }
    # Failure-only regression hook; it exercises outer-finally restoration and
    # cannot bypass a renderer check.
    if ($env:QIKVRT_TEST_FAIL_XML_AFTER_VENV_BACKUP -eq '1') {
        throw 'test-requested unexpected failure after renderer venv backup'
    }
    $pythonPath = $python.Path
    $pythonPrefix = @($python.Prefix)
    & $pythonPath @pythonPrefix -I -m venv --copies $XmlCache
    if ($LASTEXITCODE -ne 0) { Stop-Block 'could not create xml2rfc virtual environment' }
    $CachedPython = Join-Path $XmlCache 'Scripts\python.exe'
    $CachedXml2rfc = Join-Path $XmlCache 'Scripts\xml2rfc.exe'
    Invoke-IsolatedPip -Path $CachedPython -Prefix @() -PipArguments @(
        'install', '--no-index', '--find-links', $VerifiedWheelhouse, '--only-binary=:all:',
        '--require-hashes', '--no-deps', '--require-virtualenv', '-r', $Xml2rfcLock)
    if ($script:PipExit -ne 0) { Stop-Block 'hash-locked offline xml2rfc installation failed' }
    if (-not (Test-PythonRendererExact -Path $CachedPython -Prefix @())) { Stop-Block "installed renderer is not bound to Python $PythonRendererVersion" }
    if (-not (Test-LockedEnvironmentExact $CachedPython)) { Stop-Block 'installed renderer does not contain exactly the locked package set' }
    if (-not (Test-PythonPackageExact -Path $CachedPython -Prefix @() -Package xml2rfc -Version $Xml2rfcVersion)) { Stop-Block "installed xml2rfc metadata is not exactly $Xml2rfcVersion" }
    if (-not (Test-PythonPackageExact -Path $CachedPython -Prefix @() -Package pypdf -Version '6.10.0')) { Stop-Block 'installed pypdf metadata is not exactly 6.10.0' }
    if (-not (Test-Xml2rfcCommandExact $CachedXml2rfc)) { Stop-Block 'installed xml2rfc command failed its exact-version execution check' }
    $lockHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Xml2rfcLock).Hash.ToLowerInvariant()
    Set-Content -LiteralPath $CompleteMarker -Encoding ASCII -Value @(
        "xml2rfc=$Xml2rfcVersion",
        "python=$PythonRendererVersion",
        'platform=windows-amd64',
        "lock_sha256=$lockHash",
        'derivation=verified-wheelhouse')
    $script:VenvBackup = $null
    $script:InstallInProgress = $false
    Remove-Item -LiteralPath $script:TempDir -Recurse -Force
    $script:TempDir = $null
    Write-Output "PASS: xml2rfc $Xml2rfcVersion on Python $PythonRendererVersion (fresh hash-locked derivation): $CachedXml2rfc"
}

function Test-FormalProfile {
    $python = Get-CompatiblePython -Exact312
    if ($null -eq $python) {
        Set-Continue 'formal: Python 3.12.x is absent; automatic installation is not supported'
    } elseif (-not (Test-PythonPackageExact -Path $python.Path -Prefix $python.Prefix -Package pytest -Version '9.1.1')) {
        Set-Continue 'formal: pytest 9.1.1 is absent from Python 3.12; automatic installation is not supported'
    } else {
        Write-Output "PASS: formal Python 3.12 + pytest 9.1.1: $($python.Path)"
    }

    $formalRoot = Join-Path $RepoRoot 'formalization\QIKVRT_Formalization_v1.0'
    if (-not (Test-Node24)) {
        Set-Continue 'formal: Node 24.x is absent; automatic installation is not supported'
    } elseif (-not (Test-NodePackage -Directory $formalRoot -Package zod -Version '4.1.12')) {
        Set-Continue 'formal: installed Zod 4.1.12 is absent; run the reviewed npm lock installation'
    } else {
        Write-Output 'PASS: formal Node 24 + Zod 4.1.12'
    }

    $lean = Get-Command lean -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $lake = Get-Command lake -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $lean -or $null -eq $lake) {
        Set-Continue 'formal: Lean 4.19.0 and Lake are absent; automatic installation is not supported'
    } else {
        $leanVersion = [string](& ($lean.Source) --version 2>$null | Select-Object -First 1)
        if ($leanVersion -notmatch 'version 4\.19\.0') {
            Set-Continue 'formal: Lean is present but not version 4.19.0'
        } else {
            Write-Output 'PASS: formal Lean 4.19.0 + Lake'
        }
    }
}

function Test-AudioProfile {
    $audioRoot = Join-Path $RepoRoot 'tools\offline-audio-transcription'
    if (-not (Test-Node24)) {
        Set-Continue 'audio: Node 24.x is absent; automatic installation is not supported'
    } elseif (-not (Test-NodePackage -Directory $audioRoot -Package sherpa-onnx-node -Version '1.13.4')) {
        Set-Continue 'audio: installed sherpa-onnx-node 1.13.4 is absent; run the reviewed npm lock installation'
    } else {
        Write-Output 'PASS: audio Node 24 + sherpa-onnx-node 1.13.4'
    }

    $ffmpeg = Get-Command ffmpeg -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $ffprobe = Get-Command ffprobe -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $ffmpeg -or $null -eq $ffprobe) {
        Set-Continue 'audio: FFmpeg and FFprobe are required; automatic installation is not supported'
        return
    }
    $ffmpegLine = [string](& ($ffmpeg.Source) -version 2>$null | Select-Object -First 1)
    $ffprobeLine = [string](& ($ffprobe.Source) -version 2>$null | Select-Object -First 1)
    $ffmpegMatch = [regex]::Match($ffmpegLine, '^ffmpeg version ([^ ]+)')
    $ffprobeMatch = [regex]::Match($ffprobeLine, '^ffprobe version ([^ ]+)')
    if (-not $ffmpegMatch.Success -or -not $ffprobeMatch.Success -or $ffmpegMatch.Groups[1].Value -ne $ffprobeMatch.Groups[1].Value) {
        Set-Continue 'audio: FFmpeg and FFprobe must report the same non-empty version'
    } else {
        Write-Output "PASS: audio FFmpeg/FFprobe $($ffmpegMatch.Groups[1].Value)"
    }
}

function Test-PublicationProfile {
    $missing = @()
    foreach ($name in @('xelatex', 'pdftotext', 'pdftoppm')) {
        if ($null -eq (Get-Command $name -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1)) {
            $missing += $name
        }
    }
    if ($missing.Count -gt 0) {
        Set-Continue "publication: missing operator-managed tools: $($missing -join ', ')"
        return
    }
    Write-Output 'PASS: publication XeLaTeX + Poppler command contract'
}

try {
    if ($CheckOnly -and $Install) { Stop-Block '-CheckOnly and -Install are mutually exclusive' }
    if ($Install -and -not $AcceptThirdParty) { Stop-Block '-Install requires -AcceptThirdParty' }
    Assert-NoReparseChain $CacheDir

    $ghArgs = @('-CacheDir', $CacheDir)
    if ($Install) { $ghArgs += @('-Install', '-AcceptThirdParty') } else { $ghArgs += '-CheckOnly' }
    $powerShellExe = (Get-Process -Id $PID).Path
    & $powerShellExe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'bootstrap-gh.ps1') @ghArgs
    $ghExit = $LASTEXITCODE
    if ($ghExit -ne 0 -and $ghExit -ne 20) { exit $ghExit }
    if ($ghExit -eq 20) { $script:Overall = 20 }

    switch ($Profile) {
        'core' { Test-CoreProfile }
        'ietf' { Test-IetfProfile }
        'formal' { Test-FormalProfile }
        'audio' { Test-AudioProfile }
        'publication' { Test-PublicationProfile }
        'all' {
            Test-CoreProfile
            Test-IetfProfile
            Test-FormalProfile
            Test-AudioProfile
            Test-PublicationProfile
        }
    }
    exit $script:Overall
} finally {
    # Handles unexpected terminating errors, Ctrl+C/Stop where PowerShell
    # unwinds finally blocks, and the ordinary no-op success path.
    Remove-StagingDirectory
}
