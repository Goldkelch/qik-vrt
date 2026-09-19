@echo off
setlocal EnableExtensions
set "QIKVRT_ROOT=%~dp0"
if "%QIKVRT_ROOT:~-1%"=="\" set "QIKVRT_ROOT=%QIKVRT_ROOT:~0,-1%"
cd /d "%QIKVRT_ROOT%"
echo QIKVRT V45.12 optional Python verify wrapper
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%QIKVRT_ROOT%\tools\qikvrt_windows_python_resolver.ps1" -Root "%QIKVRT_ROOT%"
set RC=%ERRORLEVEL%
echo Exit code: %RC%
pause
exit /b %RC%
