@echo off
setlocal EnableExtensions
set "QIKVRT_ROOT=%~dp0"
if "%QIKVRT_ROOT:~-1%"=="\" set "QIKVRT_ROOT=%QIKVRT_ROOT:~0,-1%"
cd /d "%QIKVRT_ROOT%"
echo QIKVRT V45.11 real GitHub merge commit push release wrapper - local git identity/bootstrap/origin safe
echo.
echo WARNING: This wrapper can perform real state-changing GitHub effects:
echo   local git init when .git is missing
echo   git add / commit
echo   git remote add origin when you provide a remote URL/OWNER/REPO
echo   git push branch and tag
echo   gh release create / upload / download-verify
echo.
echo Required exact confirmation: JA, ICH AKZEPTIERE
set /p QIKVRT_CONFIRM=Type exact confirmation now: 
if not "%QIKVRT_CONFIRM%"=="JA, ICH AKZEPTIERE" (
  echo BLOCK acceptance declined or not exact
  echo Exit code: 1
  pause
  exit /b 1
)

echo.
echo Optional GitHub origin input.
echo If this extracted ZIP is not already inside a Git repository, V45.11 can initialize .git locally.
echo To push/release, it still needs a GitHub remote. Enter one now if origin is not already configured.
echo Accepted formats: https://github.com/OWNER/REPO.git or OWNER/REPO
echo Leave blank to block cleanly at origin gate if no origin exists.
set /p QIKVRT_GITHUB_REMOTE_URL=GitHub origin URL or OWNER/REPO: 

if not defined QIKVRT_GIT_USER_NAME set "QIKVRT_GIT_USER_NAME=Ingolf Lohmann"
if not defined QIKVRT_GIT_USER_EMAIL set "QIKVRT_GIT_USER_EMAIL=ingolf.lohmann@web.de"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%QIKVRT_ROOT%\tools\qikvrt_acceptance_gate_windows.ps1" ^
  -AcceptedBy "Ingolf Lohmann" ^
  -Scope "QIKVRT V45.11 real GitHub merge/commit/push/release with git bootstrap, origin-safe remote evidence" ^
  -OutFile "%QIKVRT_ROOT%\state\owner_acceptance_record.json" ^
  -Confirmation "%QIKVRT_CONFIRM%"
set RC=%ERRORLEVEL%
if not "%RC%"=="0" (
  echo Exit code: %RC%
  pause
  exit /b %RC%
)

set "QIKVRT_ENABLE_REAL_GITHUB_EFFECTS=YES"

echo PASS interactive acceptance persisted before real GitHub effect attempt
echo PASS QIKVRT_ENABLE_REAL_GITHUB_EFFECTS set by wrapper after acceptance

echo.
echo Starting real GitHub automation. Missing git/gh/login/remote/release rights will BLOCK without a false PASS.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%QIKVRT_ROOT%\tools\qikvrt_github_automated_merge_commit_push_release_windows.ps1" ^
  -Repo "%QIKVRT_ROOT%" ^
  -TargetBranch "main" ^
  -SourceBranch "" ^
  -Tag "v45.11" ^
  -Title "QIKVRT V45.11" ^
  -AcceptanceJson "%QIKVRT_ROOT%\state\owner_acceptance_record.json" ^
  -EvidenceJson "%QIKVRT_ROOT%\audit\github_remote_effect_evidence.v45.11.json" ^
  -Asset "%QIKVRT_ROOT%\dist\QIKVRT_V45_11.zip" ^
  -CommitMessage "QIKVRT V45.11 short-path git bootstrap origin-safe real GitHub release repository" ^
  -RemoteUrl "%QIKVRT_GITHUB_REMOTE_URL%" ^
  -InitializeGitIfMissing ^
  -GitUserName "%QIKVRT_GIT_USER_NAME%" ^
  -GitUserEmail "%QIKVRT_GIT_USER_EMAIL%" ^
  -RealRemoteEffects
set RC=%ERRORLEVEL%
echo Exit code: %RC%
pause
exit /b %RC%
