@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "REPO_DIR=%~dp0.."
for %%I in ("%REPO_DIR%") do set "REPO_DIR=%%~fI"

echo ============================================================
echo ESG Momentum Engine local verification
echo Repo: %REPO_DIR%
echo ============================================================

cd /d "%REPO_DIR%"
if errorlevel 1 (
  echo [FAIL] Could not change into repository directory.
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo.
echo [1/10] Checking Python...
"%PYTHON%" --version
if errorlevel 1 (
  echo [FAIL] Python is not available. Install Python or restore .venv.
  exit /b 1
)

echo.
echo [2/10] Checking Node...
node --version
if errorlevel 1 (
  echo [FAIL] Node is not available. Install Node.js before building the frontend.
  exit /b 1
)

echo.
echo [3/10] Checking npm...
call npm.cmd --version
if errorlevel 1 (
  echo [FAIL] npm.cmd is not available. Reinstall Node.js or repair PATH.
  exit /b 1
)

echo.
echo [4/10] Running Python test suite...
"%PYTHON%" -m pytest -q
if errorlevel 1 (
  echo [FAIL] Python tests failed.
  exit /b 1
)

echo.
echo [5/10] Rebuilding Word report...
"%PYTHON%" -m src.report.build_report
if errorlevel 1 (
  echo [FAIL] Report rebuild failed.
  exit /b 1
)

echo.
echo [6/10] Checking companies.json exists...
if not exist "outputs\site_data\companies.json" (
  echo [FAIL] outputs\site_data\companies.json is missing.
  exit /b 1
)
echo [OK] Found outputs\site_data\companies.json

echo.
echo [7/10] Checking synthetic company count...
"%PYTHON%" -c "import json,sys; p=r'outputs\site_data\companies.json'; data=json.load(open(p,encoding='utf-8')); n=len(data.get('companies',[])); mode=data.get('data_mode'); print(f'companies={n} data_mode={mode}'); sys.exit(0 if n==500 and mode=='synthetic' else 1)"
if errorlevel 1 (
  echo [FAIL] Expected exactly 500 synthetic company records.
  exit /b 1
)

echo.
echo [8/10] Checking expected PNG figures...
"%PYTHON%" -c "from pathlib import Path; import sys; expected=['treemap','coverage_heatmap','ic_bar','ic_decay_curves','money_chart','walk_forward_weight_ribbon','placebo_histogram','matrix_scatter','equity_drawdown','by_country_sector_spreads','composite_correlation_heatmap','score_histogram','top20_leaderboard','company_overlay']; base=Path(r'outputs/figures'); missing=[f'{name}.png' for name in expected if not (base/f'{name}.png').exists()]; print('expected_png_count=14 missing=' + (','.join(missing) if missing else 'none')); sys.exit(1 if missing else 0)"
if errorlevel 1 (
  echo [FAIL] One or more expected PNG figures are missing.
  exit /b 1
)

echo.
echo [9/10] Installing frontend dependencies...
cd /d "%REPO_DIR%\site"
if errorlevel 1 (
  echo [FAIL] Could not enter site directory.
  exit /b 1
)
call npm.cmd install
if errorlevel 1 (
  echo [FAIL] npm install failed. See LOCAL_RUN_GUIDE.md if registry access is blocked.
  exit /b 1
)

echo.
echo [10/10] Building frontend...
call npm.cmd run build
if errorlevel 1 (
  echo [FAIL] Frontend build failed.
  exit /b 1
)

echo.
echo ============================================================
echo [SUCCESS] Local verification passed.
echo To start the development server manually:
echo   cd /d %REPO_DIR%
echo   scripts\start_site.bat
echo Or:
echo   cd /d %REPO_DIR%\site
echo   npm.cmd run dev
echo ============================================================
exit /b 0
