@echo off
setlocal EnableExtensions
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\git_invocation_selftest.ps1"
exit /b %ERRORLEVEL%
