@echo off
setlocal EnableExtensions
set "QIKVRT_ROOT=%~dp0"
if "%QIKVRT_ROOT:~-1%"=="\" set "QIKVRT_ROOT=%QIKVRT_ROOT:~0,-1%"
cd /d "%QIKVRT_ROOT%"
echo QIKVRT V45.11 build ZIP and hash wrapper - OutDir-created and short-path safe
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%QIKVRT_ROOT%\tools\qikvrt_build_zip_and_hash_windows.ps1" -Root "%QIKVRT_ROOT%" -OutDir "%QIKVRT_ROOT%\dist"
set RC=%ERRORLEVEL%
echo Exit code: %RC%
pause
exit /b %RC%
