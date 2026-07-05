@echo off
setlocal EnableExtensions
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\github_zenodo_release_publish.ps1" -AuthPreflightOnly %*
exit /b %ERRORLEVEL%
