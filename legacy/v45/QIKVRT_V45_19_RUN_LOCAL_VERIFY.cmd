@echo off
setlocal EnableExtensions
set "QIKVRT_ROOT=%~dp0"
if "%QIKVRT_ROOT:~-1%"=="\" set "QIKVRT_ROOT=%QIKVRT_ROOT:~0,-1%"
echo QIKVRT V45.19 local verify wrapper
if not exist "%QIKVRT_ROOT%\tools\qikvrt_v45_19_local_verify_windows.ps1" (
  echo BLOCK wrapper target missing. Extract the ZIP fully before running.
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%QIKVRT_ROOT%\tools\qikvrt_v45_19_local_verify_windows.ps1" -Root "%QIKVRT_ROOT%"
echo Exit code: %ERRORLEVEL%
pause
exit /b %ERRORLEVEL%
