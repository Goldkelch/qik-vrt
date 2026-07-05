@echo off
setlocal EnableExtensions
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\powershell_parse_check.ps1"
exit /b %ERRORLEVEL%
