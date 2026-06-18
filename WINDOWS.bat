REM SPDX-License-Identifier: Apache-2.0
REM Copyright (c) 2026 Ingolf Lohmann.
REM Author/Rights holder: Ingolf Lohmann.
@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
if not exist "%ROOT%\LOGS" mkdir "%ROOT%\LOGS"
echo [QALL] Windows-Start / Windows start > "%ROOT%\LOGS\LAST_RUN.txt"

where powershell.exe >nul 2>nul
if errorlevel 1 (
  echo [BLOCK] powershell.exe nicht gefunden / powershell.exe not found.>> "%ROOT%\LOGS\LAST_RUN.txt"
  exit /b 20
)

if not exist "%ROOT%\_payload\_internal\RUN.ps1" (
  echo [BLOCK] _payload\_internal\RUN.ps1 fehlt / _payload\_internal\RUN.ps1 missing.>> "%ROOT%\LOGS\LAST_RUN.txt"
  exit /b 21
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\_payload\_internal\RUN.ps1" -DeliveryRoot "%ROOT%"
set "RC=%ERRORLEVEL%"
echo EXITCODE=%RC%>> "%ROOT%\LOGS\LAST_RUN.txt"
exit /b %RC%
