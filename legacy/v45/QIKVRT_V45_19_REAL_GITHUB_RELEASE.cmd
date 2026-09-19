@echo off
setlocal EnableExtensions
set "QIKVRT_ROOT=%~dp0"
if "%QIKVRT_ROOT:~-1%"=="\" set "QIKVRT_ROOT=%QIKVRT_ROOT:~0,-1%"
echo QIKVRT V45.19 real GitHub document persistence release wrapper
if not exist "%QIKVRT_ROOT%\tools\qikvrt_v45_19_document_persistence_release_windows.ps1" (
  echo BLOCK wrapper target missing. Extract the ZIP fully before running.
  exit /b 1
)
set /p QIKVRT_ORIGIN=GitHub origin URL or OWNER/REPO [default Goldkelch/qik-vrt]: 
powershell -NoProfile -ExecutionPolicy Bypass -File "%QIKVRT_ROOT%\tools\qikvrt_v45_19_document_persistence_release_windows.ps1" -Root "%QIKVRT_ROOT%" -OriginInput "%QIKVRT_ORIGIN%"
echo Exit code: %ERRORLEVEL%
pause
exit /b %ERRORLEVEL%
