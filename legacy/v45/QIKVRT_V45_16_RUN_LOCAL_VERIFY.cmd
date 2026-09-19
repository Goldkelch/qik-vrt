@echo off
setlocal EnableExtensions
set "QIKVRT_ROOT=%~dp0"
if "%QIKVRT_ROOT:~-1%"=="\" set "QIKVRT_ROOT=%QIKVRT_ROOT:~0,-1%"
echo QIKVRT V45.16 local verify wrapper - package selftest safe
if not exist "%QIKVRT_ROOT%\tools\qikvrt_v45_16_local_verify_windows.ps1" (
  echo BLOCK wrapper target missing. Fully extract the ZIP before running.
  echo Missing: %QIKVRT_ROOT%\tools\qikvrt_v45_16_local_verify_windows.ps1
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%QIKVRT_ROOT%\tools\qikvrt_v45_16_local_verify_windows.ps1" -Root "%QIKVRT_ROOT%"
set "RC=%ERRORLEVEL%"
echo Exit code: %RC%
pause
exit /b %RC%
