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
60 passed, 7 skipped
```

The exact count may increase as Claude or Codex add more fixture-based tests. Treat any failure as blocking.

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

If package fetches fail with `EACCES` and registry/proxy settings look normal (`npm config get registry` returns `https://registry.npmjs.org/`, proxy settings are `null`), the environment is blocking outbound registry access — for example a sandboxed shell or restrictive antivirus. Re-run the install from a regular user terminal with network access. If `npm cache verify` fails with `EPERM` on the default cache, the project-local `--cache .npm-cache` workaround above bypasses it.

Do not run the live Yahoo fetchers as part of routine local verification unless outbound HTTPS and write access to `data/raw/` are both confirmed.

## Manual Browser Targets

Vite normally prints the localhost URL after:

```bat
npm.cmd run dev
```

Open the printed URL, usually:

```text
http://127.0.0.1:5173/
```

Run the checks in `docs/qa/MANUAL_QA_CHECKLIST.md`.
