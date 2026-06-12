# Local Run Guide

This guide assumes Windows and repository path:

```text
C:\Hackathon\esg-engine
```

## One-Command Verification

```bat
cd /d C:\Hackathon\esg-engine
scripts\verify_local.bat
```

The script checks Python, Node, pytest, report generation, synthetic company count, figure inventory, npm install, and frontend build.

## Python Verification Only

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m pytest -q
```

Expected current result:

```text
16 passed, 3 skipped
```

## Rebuild Report

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.report.build_report
```

Expected output:

```text
C:\Hackathon\esg-engine\outputs\report\ESG_Momentum_Engine_Final_Report.docx
```

## Frontend Verification

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install
npm.cmd run build
npm.cmd run dev
```

If the default npm cache is locked, try:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install --cache .npm-cache
```

If package fetches fail with `EACCES`, the current environment likely blocks outbound registry access. See `FRONTEND_BUILD_BLOCKER.md`.

## Manual Browser Targets

Vite normally prints the localhost URL after:

```bat
npm.cmd run dev
```

Open the printed URL, usually:

```text
http://127.0.0.1:5173/
```

Run the checks in `MANUAL_QA_CHECKLIST.md`.

