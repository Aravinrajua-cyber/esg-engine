@echo off
setlocal EnableExtensions

set "REPO_DIR=%~dp0.."
for %%I in ("%REPO_DIR%") do set "REPO_DIR=%%~fI"

cd /d "%REPO_DIR%\site"
if errorlevel 1 (
  echo [FAIL] Could not change into %REPO_DIR%\site
  exit /b 1
)

echo Starting ESG Momentum Engine frontend dev server...
echo Press Ctrl+C to stop.
npm.cmd run dev
exit /b %ERRORLEVEL%
