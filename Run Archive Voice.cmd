@echo off
setlocal

set "APP_DIR=%~dp0"
set "PYTHON=%APP_DIR%.venv\Scripts\python.exe"

cd /d "%APP_DIR%"

if not exist "%PYTHON%" (
  echo Archive Voice could not find its local Python environment.
  echo.
  echo Expected:
  echo %PYTHON%
  echo.
  echo Open Command Prompt once and run:
  echo cd /d "%APP_DIR%"
  echo py -m venv .venv
  echo .venv\Scripts\python.exe -m pip install -e .
  echo.
  echo Then double-click this file again.
  echo.
  pause
  exit /b 1
)

echo Starting Archive Voice...
"%PYTHON%" -m archive_voice
