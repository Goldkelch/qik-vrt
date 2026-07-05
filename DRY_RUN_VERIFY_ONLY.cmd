@echo off

setlocal EnableExtensions

cd /d "%~dp0"

call "%~dp0GITHUB_DRY_RUN_VERIFY_ONLY.cmd" %*

exit /b %ERRORLEVEL%

