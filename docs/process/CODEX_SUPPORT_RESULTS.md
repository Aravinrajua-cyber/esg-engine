# Codex Support Results

## Branch

```text
codex-support-pass
```

## Files Created

- `README.md`
- `LOCAL_RUN_GUIDE.md`
- `MANUAL_QA_CHECKLIST.md`
- `DEMO_SCRIPT.md`
- `DATA_IMPORT_GUIDE.md`
- `SECURITY_REVIEW.md`
- `REPO_HYGIENE_REVIEW.md`
- `CODEX_SUPPORT_RESULTS.md`
- `scripts/verify_local.bat`
- `scripts/start_site.bat`
- `data/templates/company_master_template.csv`
- `data/templates/esg_history_template.csv`
- `data/templates/financial_history_template.csv`
- `data/templates/price_history_template.csv`
- `data/examples/invalid/missing_required_field.csv`
- `data/examples/invalid/duplicate_company_identifier.csv`
- `data/examples/invalid/invalid_date.csv`
- `data/examples/invalid/non_numeric_score.csv`
- `data/examples/invalid/score_outside_allowed_range.csv`
- `data/examples/invalid/impossible_confidence_interval.csv`
- `data/examples/invalid/malformed_csv_quoting.csv`
- `data/examples/invalid/formula_injection_cell.csv`
- `data/examples/invalid/excessively_large_text_field.csv`
- `data/examples/invalid/unsupported_country_code.csv`
- `tests/test_csv_import_fixtures.py`

## Files Modified

- `.gitignore`

## Commands Run

```bat
git checkout -b codex-support-pass
```

Result: branch created and checked out.

```bat
.\.venv\Scripts\python.exe -m pytest -q
```

Intermediate result after adding CSV tests:

```text
1 failed, 29 passed, 3 skipped
```

The failure was expected fixture cleanup: `formula_injection_cell.csv` was malformed due to unescaped quotes, so it tested malformed CSV instead of formula injection. The fixture was corrected.

Final result:

```text
30 passed, 3 skipped
```

Repository hygiene commands run:

```bat
Get-ChildItem -Force -Recurse -File | Where-Object { $_.Name -match '^\.env($|\.)|\.npmrc$|id_rsa|id_dsa|credentials|secret|token|key' }
rg -n --hidden --glob '!/.git/**' --glob '!site/.npm-cache/**' --glob '!.venv/**' --glob '!**/__pycache__/**' "(api[_-]?key|secret|token|password|BEGIN RSA|PRIVATE KEY|AWS_ACCESS_KEY|AIza|sk-[A-Za-z0-9])" .
Get-ChildItem -Force -Recurse -Directory | Where-Object { $_.Name -in @('node_modules','__pycache__','.pytest_cache','.npm-cache','.venv','.vscode') }
Get-ChildItem -Force -Recurse -File | Where-Object { $_.Length -gt 5MB }
```

Result: no project secret files or obvious API keys found. Generated/cached artifacts identified and `.gitignore` updated.

## Tests Passed

```text
30 passed
```

New coverage added:

- CSV templates validate successfully.
- Invalid CSV examples are rejected for:
  - missing required field;
  - duplicate company identifier;
  - invalid date;
  - non-numeric score;
  - score outside allowed range;
  - impossible confidence interval;
  - malformed CSV quoting;
  - formula-injection cell;
  - excessively large text field;
  - unsupported country code.

## Tests Skipped

```text
3 skipped
```

These are existing signal-math stubs marked for Claude-owned assertions.

## Failures

- Frontend build was not rerun in this support pass because npm dependency fetching is already documented as blocked in `FRONTEND_BUILD_BLOCKER.md`.
- `scripts/verify_local.bat` was created but not executed end-to-end in this environment because its required `npm.cmd install` step is expected to fail or hang under the current npm registry-access limitation.

## Issues Found In Prohibited Files

Do not patch these in this branch.

1. `site/src/App.tsx:294`
   - Finding: the company detail panel displays risk flags and data coverage, but not a numeric risk score.
   - Impact: the `MANUAL_QA_CHECKLIST.md` item "Risk score is visible" will fail unless the frontend intentionally adds a derived risk score or the checklist requirement is changed.
   - Recommended fix: add a clearly labelled derived risk score near the risk flags, using the same clipped formula documented in the report: `min(100, 100 - coverage_pct + weighted flags)`.

2. `site/src/App.tsx:291`
   - Finding: score components are presented as the current model pillars: sentiment dynamics, transition readiness, governance credibility, and disclosure behaviour. They are not labelled as E, S, G, and non-ESG buckets.
   - Impact: the demo request asks for E, S, G, non-ESG, risk, and confidence components. The implementation may need a mapping layer or copy update if judges expect those exact terms.
   - Recommended fix: add explanatory labels or a mapping note without changing the underlying score contract.

## Unresolved Blockers

- npm package installation remains blocked in this environment. Use a normal terminal with registry access to run frontend install/build.
- Browser-based QA has not occurred in this environment.
- Word report visual QA has not occurred in this support pass. It should be opened in Word, the TOC should be updated, and a PDF export should be inspected.
- No production CSV import layer exists yet. The new tests define expected validation behaviour using a test-local validator and fixtures; they do not integrate with pipeline code.

## Exact Local Commands To Run Next

One-command verification:

```bat
cd /d C:\Hackathon\esg-engine
scripts\verify_local.bat
```

If npm install fails due cache locking, try:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install --cache .npm-cache
npm.cmd run build
npm.cmd run dev
```

Python-only verification:

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.report.build_report
```

Start site after dependencies are installed:

```bat
cd /d C:\Hackathon\esg-engine
scripts\start_site.bat
```

## Files Claude Code Should Review Before Merging

- `scripts/verify_local.bat`
- `scripts/start_site.bat`
- `MANUAL_QA_CHECKLIST.md`
- `DEMO_SCRIPT.md`
- `DATA_IMPORT_GUIDE.md`
- `SECURITY_REVIEW.md`
- `REPO_HYGIENE_REVIEW.md`
- `tests/test_csv_import_fixtures.py`
- `data/templates/*.csv`
- `data/examples/invalid/*.csv`
- `.gitignore`

