@echo off
setlocal

set SCRIPT_PATH=%~dp0powerbi\setup_surprise_pbip.ps1

if not exist "%SCRIPT_PATH%" (
  echo Script not found: %SCRIPT_PATH%
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_PATH%"
