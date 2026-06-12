# ESG Momentum Engine

Research prototype for screening ASEAN companies by ESG momentum, data coverage, confidence, and risk flags.

Current repository state is a synthetic demonstration build. The generated 500-company feed, figures, and Word report are for local verification and hackathon demonstration only. They are not live company data and are not investment advice.

## Quick Start On Windows

```bat
cd /d C:\Hackathon\esg-engine
scripts\verify_local.bat
```

If verification passes, start the site:

```bat
scripts\start_site.bat
```

## Manual Commands

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.report.build_report
```

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install
npm.cmd run build
npm.cmd run dev
```

If npm package fetching is blocked, read `FRONTEND_BUILD_BLOCKER.md`.

## Key Artifacts

- `outputs/site_data/companies.json` - primary synthetic frontend feed.
- `outputs/figures/` - rendered PNG and HTML figure artifacts.
- `outputs/report/ESG_Momentum_Engine_Final_Report.docx` - final synthetic-demo report.
- `LOCAL_RUN_GUIDE.md` - detailed local setup and verification commands.
- `MANUAL_QA_CHECKLIST.md` - browser and Word QA checklist.
- `DEMO_SCRIPT.md` - 3-minute judge-facing demo flow.
- `DATA_IMPORT_GUIDE.md` - provider-neutral CSV import contract for future real-data mode.

## Important Limits

- Synthetic outputs are illustrative only.
- The frontend build requires npm access to `registry.npmjs.org`.
- Browser QA must be completed locally after `npm.cmd run dev` succeeds.
- Word report visual QA should be completed in Word or LibreOffice before submission/export.

