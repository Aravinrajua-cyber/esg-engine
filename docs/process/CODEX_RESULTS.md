# Codex Independent Review Results

## Branch / Worktree

- Branch used: `codex-independent-review`
- Starting checkout was already on `codex-support-pass`; I switched to `codex-independent-review` after discovering that branch mismatch.
- Existing dirty files before my edits: `scripts/start_site.bat`, `scripts/verify_local.bat`. I left those changes intact.

## Changes Made

- `site/src/App.tsx:8` added explicit E/S/G/non-ESG component labels for the company detail pillar bars.
- `site/src/App.tsx:14` and `site/src/App.tsx:398` added a schema-safe derived risk index from coverage gaps plus weighted existing risk flags. This does not add `risk_index` to `companies.json`.
- `site/src/styles.css:35` added visible `:focus-visible` styles for links, buttons, form controls, and keyboard-focusable rows.
- `site/src/styles.css:217` and `site/src/styles.css:228` adjusted detail-panel sizing so longer component labels and risk-index text fit cleanly.
- `src/viz/style.py:24` changed figure titles/takeaways into a single title block to prevent overlap in exported PNGs.
- `tests/test_frontend_static_contract.py:21`, `tests/test_frontend_static_contract.py:35`, and `tests/test_frontend_static_contract.py:44` added static coverage for focus visibility, risk index display, and E/S/G/non-ESG labels.

## Commands Run

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m pytest -q
```

Result:

```text
32 passed, 3 skipped in 0.50s
```

After the final figure-theme and CSS/test changes:

```text
32 passed, 3 skipped in 0.47s
```

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd --version
```

Result:

```text
11.11.0
```

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install --cache .npm-cache --prefer-offline --verbose --fetch-retries=0 --fetch-timeout=30000
```

Result: failed. Registry fetches to `https://registry.npmjs.org/` failed with `EACCES`, including `@vitejs/plugin-react`, `vite`, `typescript`, `react`, `react-dom`, `plotly.js-dist-min`, and `lucide-react`.

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd run build
```

Result: failed because dependencies are not installed.

```text
'tsc' is not recognized as an internal or external command,
operable program or batch file.
```

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.viz.style
```

Result: passed. Rendered:

```text
treemap, coverage_heatmap, ic_bar, ic_decay_curves, money_chart,
walk_forward_weight_ribbon, placebo_histogram, matrix_scatter,
equity_drawdown, by_country_sector_spreads, composite_correlation_heatmap,
score_histogram, top20_leaderboard, company_overlay
```

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.report.build_report
```

Result:

```text
C:\Hackathon\esg-engine\outputs\report\ESG_Momentum_Engine_Final_Report.docx
```

```bat
cd /d C:\Hackathon\esg-engine
rg -n --hidden --glob '!/.git/**' --glob '!site/.npm-cache/**' --glob '!.venv/**' --glob '!**/__pycache__/**' "(api[_-]?key|secret|token|password|BEGIN RSA|PRIVATE KEY|AWS_ACCESS_KEY|AIza|sk-[A-Za-z0-9])" .
```

Result: no exposed credentials found. Hits were documentation, configuration words such as `tokens`, and review notes.

```bat
cd /d C:\Hackathon\esg-engine
Get-ChildItem -Force -Recurse -File | Where-Object { $_.FullName -notlike '*\.venv\*' -and $_.FullName -notlike '*\.git\*' -and $_.FullName -notlike '*\site\.npm-cache\*' -and $_.Name -match '^\.env($|\.)|\.npmrc$|id_rsa|id_dsa|credentials|secret|token|key' } | Select-Object FullName,Length
```

Result: no project secret files found.

```bat
cd /d C:\Hackathon\esg-engine
rg -n "dangerouslySetInnerHTML|eval\(|new Function|innerHTML|document\.write" site/src src tests
```

Result: no matches.

## Frontend Build Status

Blocked in this environment. `node_modules` is absent, `npm.cmd install` cannot fetch packages because registry requests fail with `EACCES`, and `npm.cmd run build` fails before TypeScript compilation because `tsc` is unavailable.

No claim should be made that the frontend build passes until this succeeds in a normal terminal:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install
npm.cmd run build
```

## Browser Visual-Check Status

Blocked. I could not run the Vite dev server because dependency installation is blocked, so browser-based QA of hero, leaderboard, detail view, responsive breakpoints, keyboard navigation, and Lighthouse remains open.

Static source checks did confirm:

- synthetic banner is present at `site/src/App.tsx:82`;
- not-investment-advice disclaimer is present at `site/src/App.tsx:104`;
- leaderboard rows are keyboard-focusable and open on Enter in source;
- reduced-motion CSS exists at `site/src/styles.css:265`;
- focus-visible styles now exist at `site/src/styles.css:35`.

## Report / Graph Readability

- Figure smoke rendering passed for all 14 expected figure families.
- I visually spot-checked `money_chart.png`, `top20_leaderboard.png`, and `matrix_scatter.png`.
- Finding fixed: exported figure titles and one-line takeaways overlapped in the PNGs. The shared figure theme now renders them as a single title block.
- Remaining observation: the top-20 table is readable but dense; long company names wrap and create uneven row heights. This is acceptable for a report snapshot, but a future polish pass could reduce font size or widen the company column.
- Report regeneration passed and produced `outputs/report/ESG_Momentum_Engine_Final_Report.docx`.

## Accessibility Findings

- Keyboard support: leaderboard rows have `tabIndex={0}` and Enter-key open behavior.
- Focus states: fixed in this pass with global `:focus-visible` styles.
- Reduced motion: supported by `@media (prefers-reduced-motion: reduce)`.
- Semantic structure: source uses sectioned page regions and headings; browser validation remains blocked.
- Color contrast: source palette appears conservative, but automated contrast/Lighthouse validation remains blocked until the frontend can run.
- Chart alternatives: `site/src/Plot.tsx` uses `role="img"` and `aria-label={title}` for Plotly containers. This is a minimal alternative; richer chart summaries would improve screen-reader utility.
- Table/card readability: static CSS includes desktop grid and mobile collapsed row rules; runtime verification is blocked.

## Security Findings

- Current frontend has no backend, no upload path, and fetches static JSON files from `/site_data/*`.
- Main client-side risk is trusting static JSON shape without runtime validation. If files can be user-controlled later, add schema validation before rendering.
- CSV-import risk is documented and test fixtures exist, but no production CSV import layer exists yet.
- Path traversal risk is low in the current static app, but future upload/import code must reject arbitrary paths and normalize filenames.
- Dependency risk remains unresolved because there is no installed dependency tree in this environment and no successful frontend build verification.
- Rendering assumptions: React escapes text by default in current code; no `dangerouslySetInnerHTML` was found during this pass.

## Unsupported-Claims Findings

- No live-data or investment recommendation claim was added in this pass.
- Synthetic labels remain visible in frontend source: `site/src/App.tsx:82` and `site/src/App.tsx:104`.
- Report generation text labels results as synthetic demonstration output and not investment advice.
- The footer still says citations and retrieval dates are placeholders for Claude prose. That is honest, but final demo copy should replace placeholders before judging if possible.

## Synthetic-Labeling Findings

- Persistent frontend banner: `SYNTHETIC DEMONSTRATION DATA`.
- Site-wide disclaimer: `Research demonstration - not investment advice.`
- Tests enforce both strings.
- Generated `companies.json` tests enforce `data_mode == "synthetic"` and 500 synthetic/demo records.

## Ranked Next Actions

1. Unblock npm in a normal terminal, then run `npm.cmd install`, `npm.cmd run build`, and browser QA against desktop/tablet/mobile.
2. Complete browser accessibility checks: focus order, color contrast, chart labels, reduced motion, and mobile leaderboard usability.
3. Review the final Word report in Word, update the TOC field, export PDF, and inspect page breaks/captions.
4. Replace placeholder frontend/footer/report prose with Claude-approved final copy while keeping synthetic/live distinctions explicit.
5. Add runtime JSON schema validation before rendering if `/site_data/*` can ever be supplied by a user or untrusted process.
6. Build a real CSV import path only if required, then connect the existing CSV edge-case fixtures to production validation.

## Mirror support pass - 2026-06-13

Codex created a writable mirror at `C:\Users\aravi\esg-engine-codex-mirror` because the original repository at `C:\Hackathon\esg-engine` was read-only to this session.

Commands run in the mirror:

```bat
robocopy C:\Hackathon\esg-engine C:\Users\aravi\esg-engine-codex-mirror /E /XD .venv node_modules .npm-cache __pycache__ .pytest_cache /XF *.pyc /TEE /LOG:C:\Users\aravi\esg-engine-codex-mirror\mirror_robocopy.log /NP /R:1 /W:1
git switch -c codex-mirror-support-pass
C:\Hackathon\esg-engine\.venv\Scripts\python.exe -m pytest -q
rg -n "dangerouslySetInnerHTML|eval\(|new Function|innerHTML|document\.write" site/src src tests
rg -n "buy|sell|hold|outperform|underperform|target price|guaranteed|guarantee|investment advice|SYNTHETIC DEMONSTRATION DATA|synthetic" site/src src/report DEMO_SCRIPT.md README.md LOCAL_RUN_GUIDE.md DATA_IMPORT_GUIDE.md
node --version
npm.cmd --version
```

Results:

- Mirror copy preserved `.git`.
- Python tests in the mirror: `60 passed, 7 skipped`.
- Dangerous-rendering source scan: no matches.
- Node/npm versions available: Node `v24.14.1`, npm `11.11.0`.
- `npm install`, frontend build, browser QA, and Word/PDF visual QA were not run in this network-independent pass.
- Live Yahoo fetchers were not rerun after the blocker was documented.

Files added or updated in this mirror pass are summarized in `CODEX_MIRROR_RESULTS.md`.
