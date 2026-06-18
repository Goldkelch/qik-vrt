REM QALL_SCRIPT_TERMINATION_GUARD_BEGIN
set QALL_SCRIPT_NAME=%~nx0
if not exist LOGS mkdir LOGS
REM QALL_SCRIPT_TERMINATION_GUARD_END

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


REM QALL_SCRIPT_TERMINATION_GUARD_FINAL_BEGIN
set QALL_RC=%ERRORLEVEL%
if "%QALL_RC%"=="0" (
  echo SCRIPT_TERMINATION=PASS
  echo SCRIPT_EXIT_CODE=0
  echo {"id":"QIKVRT_SCRIPT_TERMINATION_RECORD","script":"%QALL_SCRIPT_NAME%","status":"PASS","exit_code":0,"errors":[],"license_notice":{"spdx_license_identifier":"Apache-2.0","copyright":"Copyright (c) 2026 Ingolf Lohmann.","author_rights_holder":"Ingolf Lohmann","future_outputs_require_header_or_manifest_coverage":true,"streams_and_information_objects_require_manifest_coverage":true}} > LOGS\%QALL_SCRIPT_NAME%.termination.json
) else (
  echo SCRIPT_TERMINATION=ERROR
  echo SCRIPT_EXIT_CODE=%QALL_RC%
  echo {"id":"QIKVRT_SCRIPT_TERMINATION_RECORD","script":"%QALL_SCRIPT_NAME%","status":"ERROR","exit_code":%QALL_RC%,"errors":[{"operation":"batch","type":"BatchError","message":"batch command failed"}],"license_notice":{"spdx_license_identifier":"Apache-2.0","copyright":"Copyright (c) 2026 Ingolf Lohmann.","author_rights_holder":"Ingolf Lohmann","future_outputs_require_header_or_manifest_coverage":true,"streams_and_information_objects_require_manifest_coverage":true}} > LOGS\%QALL_SCRIPT_NAME%.termination.json
)
exit /b %QALL_RC%
REM QALL_SCRIPT_TERMINATION_GUARD_FINAL_END
