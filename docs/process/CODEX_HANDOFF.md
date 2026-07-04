# Codex Independent Review Handoff

## Context

This repository contains the ESG Momentum Engine prototype. The current build has generated synthetic site-data artifacts, rendered figure PNG/HTML files, a final Word report, and Python tests. The frontend package installation is blocked in the current execution environment; see `FRONTEND_BUILD_BLOCKER.md`.

Codex should act as an independent reviewer, not a redesign agent. Minimize merge conflicts by working in a separate Git branch or worktree and by making small, scoped review/test changes only.

## Required Branch Or Worktree

Create a separate branch or worktree before editing:

```bat
cd /d C:\Hackathon\esg-engine
git switch -c codex-independent-review
```

If the main worktree is dirty or shared, use a worktree instead:

```bat
cd /d C:\Hackathon
git -C esg-engine worktree add ..\esg-engine-codex-review -b codex-independent-review
```

## Primary Review Tasks

1. Static frontend code review while npm installation is blocked.
2. Backend and scoring-pipeline test audit.
3. CSV-import validation edge-case tests, if any CSV import path exists or is added.
4. Accessibility review of the frontend source.
5. Security review of API inputs, local file handling, and any future upload paths.
6. Review of graph readability and report clarity.
7. Check for fabricated, overstated, or unsupported claims.
8. Check that synthetic data is labelled clearly everywhere.

## Permitted Files

Codex may read all repository files.

Codex may edit only:

- `tests/**`
- `site/src/**`
- `site/package.json`
- `site/tsconfig.json`
- `site/vite.config.ts`
- `src/report/**`
- `src/viz/**`
- `FRONTEND_BUILD_BLOCKER.md`
- `CODEX_RESULTS.md`

Codex may create additional test fixtures under:

- `tests/fixtures/**`

## Prohibited Files

Do not edit:

- `config/settings.yaml`
- `SCHEMAS.md`
- `RESEARCH_LOG.md`
- `BIAS_REGISTER.md`
- `COORDINATION.md`
- `AGENTS.md`
- `src/signals/**`
- `src/composite/**`
- `src/validation/**`
- `src/scoring/**`
- `src/universe/**`
- `src/fetchers/gdelt.py`
- generated data under `data/raw/**`, `data/interim/**`, `data/processed/**`, unless the task is explicitly to regenerate outputs

Do not delete source files. Do not use destructive cleanup commands. Do not convert synthetic outputs into live-looking outputs.

## Acceptance Criteria

Codex review is complete only when:

- `CODEX_RESULTS.md` exists and summarizes findings, tests run, and unresolved blockers.
- All findings include file paths and line references where possible.
- Any code/test changes are small and scoped to permitted files.
- Synthetic-demo labels remain visible in report and frontend source.
- No claim is made that frontend build passes unless `npm.cmd run build` actually passes.
- Any CSV-import recommendation includes tests for malformed rows, missing columns, bad encodings, formula injection strings, out-of-range values, duplicate keys, oversized files, and empty files.
- Accessibility review covers keyboard navigation, semantic headings, focus states, reduced motion, color contrast, table/card readability, and chart alternatives.
- Security review covers untrusted JSON/CSV input, path traversal, file upload constraints, dependency risk, and client-side rendering assumptions.

## Expected Test Commands

Python tests:

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m pytest -q
```

Frontend dependency diagnosis:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install
npm.cmd run build
```

If npm remains blocked, use the documented local-cache diagnostic:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install --cache .npm-cache --prefer-offline --verbose --fetch-retries=0 --fetch-timeout=30000
npm.cmd ping --cache .npm-cache --fetch-retries=0 --fetch-timeout=30000 --verbose
```

Report regeneration:

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.report.build_report
```

Figure regeneration:

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.viz.style
```

## Required Output File

Create:

```text
C:\Hackathon\esg-engine\CODEX_RESULTS.md
```

`CODEX_RESULTS.md` must include:

- branch or worktree used;
- exact commands run and results;
- frontend build status;
- browser visual-check status;
- report clarity/readability findings;
- accessibility findings;
- security findings;
- unsupported-claims findings;
- synthetic-labeling findings;
- recommended next actions ranked by priority.

