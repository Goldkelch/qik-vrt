@echo off
setlocal EnableExtensions
set "QIKVRT_ROOT=%~dp0"
if "%QIKVRT_ROOT:~-1%"=="\" set "QIKVRT_ROOT=%QIKVRT_ROOT:~0,-1%"
cd /d "%QIKVRT_ROOT%"
echo QIKVRT V45.11 local verify wrapper - Windows 9009, trailing-backslash, and short-path safe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%QIKVRT_ROOT%\tools\qikvrt_local_verify_windows.ps1" -Root "%QIKVRT_ROOT%"
set RC=%ERRORLEVEL%
echo Exit code: %RC%
pause
exit /b %RC%
