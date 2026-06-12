# CODEX WORK ORDERS — 2026-06-13

Maintained by Claude (orchestrator). Paste one work order at a time into Codex, top to bottom.
Each order is self-contained: it includes every schema, path, and constraint Codex needs.
WO-1 is the critical path (Claude's signal work is blocked on its outputs). WO-2/WO-3/WO-4 can
run in any order after or parallel to WO-1. WO-5 is gated on npm being unblocked.

---
---

## WORK ORDER 1 (P0 — critical path): Execute and harden the four live market-data fetchers

### Objective
Run the four live data fetchers (`fx`, `prices`, `esg`, `fundamentals`) end-to-end against the
477-ticker universe in `C:\Hackathon\esg-engine\data\raw\universe.parquet`, fixing any
straightforward runtime errors, so that the four contract parquet files described below exist on
disk and conform to their schemas exactly.

### Environment
- Repo root: `C:\Hackathon\esg-engine` (Windows; no git commits — leave changes in the working tree).
- Python: `.\.venv\Scripts\python.exe` (run all commands from the repo root).
- Test baseline today: `.\.venv\Scripts\python.exe -m pytest -q` → **32 passed, 3 skipped**. It must not regress.
- Network access to Yahoo Finance (via `yfinance`, already installed in the venv) is required.

### Files to modify (bug fixes only — the implementations already exist)
- `src/fetchers/fx.py`
- `src/fetchers/prices.py`
- `src/fetchers/esg.py`
- `src/fetchers/fundamentals.py`

### Files created by running them (run in this order — prices needs FX for USD conversion)
```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.fetchers.fx
.\.venv\Scripts\python.exe -m src.fetchers.prices
.\.venv\Scripts\python.exe -m src.fetchers.esg
.\.venv\Scripts\python.exe -m src.fetchers.fundamentals
```
Outputs: `data/raw/fx_daily.parquet`, `data/raw/prices_daily.parquet`,
`data/raw/esg_snapshot.parquet`, `data/raw/fundamentals.parquet`, plus a
`data/raw/<name>_failures.csv` per fetcher enumerating every ticker that failed and why.

### Interface contract (frozen — do not change)
Each module exposes:
```python
def fetch(universe_df: pd.DataFrame, settings: dict) -> pd.DataFrame
```
It writes its parquet to `data/raw/`, returns the DataFrame, skips work when the output file is
fresh (<24h), retries with exponential backoff + jitter (max 5 tries — do not shorten backoff),
and logs via `src.util.log.log_action` (import-only; do not edit `src/util/`).

### Output schemas (frozen — exact columns, no additions, no renames; dates ISO YYYY-MM-DD)
**fx_daily.parquet** — one row per currency per day, weekends forward-filled (forward-fill is
permitted for FX only and must be stated in the module docstring):
`date, currency, fx_to_usd`

**prices_daily.parquet** — long format, 2014-01-01 → today, daily; `close_usd = close_local × fx_to_usd` on the same date; do NOT forward-fill or impute missing prices:
`date, ticker, close_local, volume, close_usd`

**esg_snapshot.parquet** — one row per ticker, single retrieval-stamped snapshot (NOT a history):
`ticker, retrieval_date, esg_total_risk, esg_e, esg_s, esg_g, controversy_level` (controversy 0–5, nullable)

**fundamentals.parquet** — long format:
`ticker, fiscal_date, period, revenue, capex, total_debt, interest_expense, operating_cash_flow, depreciation`
with `period ∈ {annual, quarter}`.

### Constraints
- **No fabricated data.** Missing = NaN/null, never imputed (FX weekend forward-fill is the sole exception). If a ticker returns nothing, it goes in the failures CSV — never synthesize a row.
- **No hardcoded parameters.** Date ranges, FX ticker map, and market suffixes come from `config/settings.yaml` (`dates.prices_start: 2014-01-01`; `universe.markets.<MKT>.fx_ticker`, e.g. `SGDUSD=X`). PH is intentionally absent from the universe — do not re-add it.
- Expect low ESG coverage in ASEAN from Yahoo. Report the real coverage number; do not pad it.
- Keep batched downloads (~50 tickers/chunk) and respect retry/backoff as coded; fixes should target real errors (yfinance API quirks, dtype issues, empty frames), not redesign.
- Code style: match the existing modules — type hints, descriptive names, module-level constants, no new dependencies.

### Acceptance criteria (Claude will check all of these on review)
1. All four parquets exist with exactly the schema columns and sensible dtypes (dates as datetime, numerics as float).
2. No duplicate keys: `(date,currency)` in fx; `(date,ticker)` in prices; `ticker` in esg; `(ticker,fiscal_date,period)` in fundamentals.
3. Prices span from ≤2014-01-31 to within 5 business days of today for ≥90% of non-`LOW_LIQUIDITY` universe tickers (universe column `liquidity_flag`).
4. Spot-check holds: `close_usd ≈ close_local × fx_to_usd` (relative error < 1e-6) on sampled rows.
5. Every absent ticker appears in the matching `_failures.csv` with a reason string.
6. `pytest -q` still reports ≥32 passed, 0 failed.
7. A new section `## WO-1 results — 2026-06-13` appended to `CODEX_RESULTS.md` containing: exact commands run, per-market coverage table (rows = SG/ID/MY/TH/VN, cols = % tickers covered per artifact), row counts per parquet, and unresolved blockers.

### Must NOT touch (Claude-owned)
`config/settings.yaml`, `SCHEMAS.md`, `COORDINATION.md`, `RESEARCH_LOG.md`, `BIAS_REGISTER.md`,
`AGENTS.md`, `src/signals/**`, `src/composite/**`, `src/validation/**`, `src/scoring/**`,
`src/universe/**`, `src/util/**` (import-only), and **`src/fetchers/gdelt.py` and
`data/raw/gdelt_cache/**` — a long-running GDELT fetch may be in progress; do not read-modify,
delete, or restart anything GDELT-related.** `data/raw/universe.parquet` is read-only input.

---
---

## WORK ORDER 2 (P1): Runtime JSON validation + live/synthetic mode handling in the frontend

### Objective
Add dependency-free runtime validation of every `/site_data/*.json` payload in the React frontend
at `C:\Hackathon\esg-engine\site`, so malformed data renders a readable error panel instead of a
crash, and the synthetic-data banner is driven by the `data_mode` field rather than assumed.

### Environment
- Repo root: `C:\Hackathon\esg-engine`. Frontend source: `site/src/` (Vite + React + TypeScript).
- **npm install is blocked in this environment** (`EACCES` to registry.npmjs.org — see
  `FRONTEND_BUILD_BLOCKER.md`). Therefore: add **zero** new packages (no zod/ajv — hand-roll the
  validators), and do not edit `site/package.json`. If `npm.cmd install` happens to work in your
  session, run `npm.cmd run build` and report the result; otherwise verify statically.
- Python test baseline: `.\.venv\Scripts\python.exe -m pytest -q` → **32 passed, 3 skipped**; must not regress (`tests/test_frontend_static_contract.py` greps the source for required strings — keep them).

### Files
- Create: `site/src/validate.ts`
- Modify: `site/src/data.ts`, `site/src/types.ts`, `site/src/App.tsx`
- Do not modify: `site/package.json`, `site/tsconfig.json`, `site/vite.config.ts`, `outputs/site_data/*.json`

### Required function signatures (in `site/src/validate.ts`)
```ts
export type ValidationResult<T> =
  | { ok: true; data: T }
  | { ok: false; errors: string[] };   // each error names the JSON path, e.g. "companies[3].grade"

export function validateCompaniesPayload(raw: unknown): ValidationResult<CompaniesPayload>;
export function validateBacktestPayload(raw: unknown): ValidationResult<BacktestPayload>;
export function validateIcTablePayload(raw: unknown): ValidationResult<IcRow[]>;
export function validatePlaceboPayload(raw: unknown): ValidationResult<PlaceboPayload>;
export function validateGroupSpreadPayload(raw: unknown): ValidationResult<GroupSpreadRow[]>; // by_country / by_sector
```
Cap reported errors at 10 per file. Types live in `site/src/types.ts` (extend the existing ones; do not duplicate).

### Payload schemas to validate against (frozen contract, schema_version 1)
**companies.json** (primary feed):
```
{ schema_version:1, generated_at, data_mode:"live"|"synthetic", as_of_date, universe_size,
  model: { winning_composite, validated_weights:{sentiment_dynamics,transition_readiness,
           governance_credibility,disclosure_behavior}, train_end,
           headline:{ net_q5q1_spread_annual_pct, deflated_sharpe, test_ic, sharpe_net } },
  pillars: [{key,label,description}],
  flags:   [{key,label,tooltip}],
  companies: [{
     ticker,name,country,exchange,sector,mcap_tier,currency,
     rank, overall_score(0-100), grade("A+"|"A"|"B"|"C"|"D"),
     confidence_low, confidence_high, coverage_pct,
     classification:"hidden_winner"|"future_leader"|"overrated_leader"|"value_trap",
     esg_level_pctile(0-100), esg_momentum_pctile(0-100),
     pillar_scores: { sentiment_dynamics, transition_readiness,
                      governance_credibility, disclosure_behavior, data_coverage },  // each 0-100
     flags: ["LOW_COVERAGE"|"CONTROVERSY_RISING"|"LOW_LIQUIDITY"|"HIGH_VOL"|"STALE_DATA"],
     explanation: string,
     timeseries: null | { dates:[], price_usd:[], sentiment_tone:[], score:[] }
  }] }
```
**backtest.json**: `{dates:[], q5:[], q1:[], benchmark:[], naive_esg_q5:[], net:bool, train_end_index:int}` (arrays equal length)
**ic_table.json**: `[{variable, label, ic_3m, t_nw, fdr_survived}]`
**placebo.json**: `{realized_spread, hist_bins:[], hist_counts:[]}` (bins = counts+1 or equal — accept either, but lengths must be consistent with how `Plot.tsx` consumes them)
**by_country.json / by_sector.json**: `[{key, spread_net}]`

Validation must reject: missing required keys, wrong primitive types, NaN/non-finite numbers,
scores outside 0–100, grades/classifications/flags outside their enums, `schema_version !== 1`,
and timeseries arrays of unequal length.

### Behavior rules
1. Banner with the exact string `SYNTHETIC DEMONSTRATION DATA` is shown **iff** `data_mode === "synthetic"`. When `data_mode === "live"`, show instead a tag reading `LIVE DATA · as of {as_of_date}`. Never show the live tag for synthetic data.
2. The exact disclaimer string `Research demonstration - not investment advice.` remains always visible regardless of mode.
3. On validation failure: render a visible error panel naming the file and the first errors; never a blank screen, never partially-rendered garbage data.
4. Weight sandbox (existing feature): client recompute is `overall = Σ weight_i × pillar_scores[i]` over the four model pillars only — `data_coverage` is display-only and must stay out of the weighted sum; reset restores `model.validated_weights`.

### Constraints
- TypeScript strict; no `any` escaping the validator boundary (`unknown` in, typed out).
- No new dependencies; no changes to build config.
- Keep code style consistent with the existing `site/src` files.

### Acceptance criteria
1. `pytest -q` ≥32 passed, 0 failed (banner/disclaimer strings still found in source).
2. Reading `outputs/site_data/companies.json` (and the four small files) through the validators succeeds — confirm by reasoning through the actual file contents, and state in your results whether each current file passes.
3. Each rejection class listed above is demonstrably handled (show the validator branch per class in your results notes).
4. If npm worked: `npm.cmd run build` exit 0. If blocked: say so explicitly — do not claim the build passes.
5. Section `## WO-2 results — 2026-06-13` appended to `CODEX_RESULTS.md`: files changed, validation coverage summary, build status, blockers.

### Must NOT touch (Claude-owned)
`config/settings.yaml`, `SCHEMAS.md`, `COORDINATION.md`, `RESEARCH_LOG.md`, `BIAS_REGISTER.md`,
`AGENTS.md`, anything under `src/` except nothing (this WO is frontend-only),
`outputs/site_data/*.json` (read-only inputs), `data/**`.

---
---

## WORK ORDER 3 (P1): Live-mode plumbing for figures and report

### Objective
Make `src/viz/style.py` and `src/report/build_report.py` consume real pipeline artifacts
(`data/processed/validation_results.json` and live-mode `outputs/site_data/*.json`) when they
exist, with every figure and report header carrying a data-mode label driven by the data itself,
falling back to today's synthetic inputs unchanged when they don't.

### Environment
- Repo root: `C:\Hackathon\esg-engine`; Python: `.\.venv\Scripts\python.exe`; no git commits.
- Test baseline: `pytest -q` → **32 passed, 3 skipped**; must not regress.
- Regeneration commands that must keep working on current (synthetic) inputs:
```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.viz.style
.\.venv\Scripts\python.exe -m src.report.build_report
```

### Files
- Modify: `src/viz/style.py`, `src/report/build_report.py`
- Create: `tests/fixtures/live_mode/validation_results.json` (tiny, obviously-fake numbers),
  `tests/test_viz_report_modes.py`

### Input schema for `data/processed/validation_results.json` (frozen; produced later by Claude)
```
{ ic: [{variable, horizon, ic_mean, ic_std, t_nw, hit_rate, fdr_survived(bool)}],
  fama_macbeth: [{variable, coef, t_nw, p}],
  composites: [{name, train_ic, test_ic, train_spread, test_spread}],
  backtest: {winning_composite, gross, net, sharpe, sortino, max_dd, calmar,
             q5_q1_spread_net, spread_ci_low, spread_ci_high, turnover, deflated_sharpe},
  placebo: {realized_spread, placebo_mean, placebo_p, hist_bins[], hist_counts[]} }
```
Mode detection: `outputs/site_data/companies.json` has `data_mode: "live" | "synthetic"`; treat a
missing `data/processed/validation_results.json` as synthetic mode regardless.

### Required refactor shape
Give both modules an explicit entry point that takes paths instead of relying only on module-level
constants, defaulting to current behavior, e.g.:
```python
def build_figures(site_data_dir: Path = SITE_DATA_DIR,
                  validation_path: Path = VALIDATION_PATH,
                  out_dir: Path = FIGURES_DIR) -> list[Path]: ...

def build_report(site_data_dir: Path = SITE_DATA_DIR,
                 validation_path: Path = VALIDATION_PATH,
                 out_path: Path = REPORT_PATH) -> Path: ...
```
`__main__` behavior unchanged.

### Constraints
- **Analytical content of figures must not change** — this is labeling + data-source plumbing only.
- Mode label text: synthetic → `SYNTHETIC DEMONSTRATION` (keep existing wording where already present); live → `Live data · retrieved {date}` where the date comes from the data, never from `datetime.now()` at render time.
- **Never write live-labeled artifacts from fixture data**: the live-mode test must direct all outputs to pytest `tmp_path`; nothing under `outputs/` may be produced with a live label by tests. Do not modify the real files in `outputs/` in live mode at all during this WO.
- Report prose placeholders (citations, retrieval dates, Claude-supplied paragraphs) stay intact — plumbing only, Claude owns the words.
- No hardcoded numbers: any figure that currently reads synthetic stats must read them from the JSON inputs in both modes.
- No new dependencies.

### Acceptance criteria
1. Both regeneration commands above run clean on current synthetic inputs and outputs are still labeled synthetic.
2. `tests/test_viz_report_modes.py` proves: (a) synthetic mode → synthetic label, (b) fixture live mode → live label with fixture date, both writing only to `tmp_path`.
3. `pytest -q` ≥ baseline +2, 0 failed.
4. Section `## WO-3 results — 2026-06-13` appended to `CODEX_RESULTS.md`: files changed, commands run, before/after labeling behavior, blockers.

### Must NOT touch (Claude-owned)
`config/settings.yaml`, `SCHEMAS.md`, `COORDINATION.md`, `RESEARCH_LOG.md`, `BIAS_REGISTER.md`,
`AGENTS.md`, `src/signals/**`, `src/composite/**`, `src/validation/**`, `src/scoring/**`,
`src/universe/**`, `src/util/**` (import-only), `src/fetchers/**`, `site/**`,
`outputs/site_data/*.json` (read-only).

---
---

## WORK ORDER 4 (P2): Fixture-based contract tests for the raw data artifacts

### Objective
Add pytest coverage that enforces the frozen schemas of the four raw parquet artifacts
(`fx_daily`, `prices_daily`, `esg_snapshot`, `fundamentals`) using tiny checked-in fixtures, and
that skips cleanly (not fails) when a real artifact is absent from `data/raw/`.

### Environment
- Repo root: `C:\Hackathon\esg-engine`; Python: `.\.venv\Scripts\python.exe`; no git commits.
- Test baseline: `pytest -q` → **32 passed, 3 skipped** (may be higher if WO-1/WO-3 landed); 0 failures required. **No network access in tests.** Added runtime ≤5 seconds.

### Files
- Create: `tests/test_raw_contracts.py`, `tests/fixtures/raw/` containing valid + deliberately
  corrupted parquet/builder fixtures (≤20 rows each; obviously fake tickers like `TESTA.SI`,
  `TESTB.JK` — never real-looking data).

### Contracts to enforce (frozen — from SCHEMAS.md, schema_version 1)
- `fx_daily.parquet`: columns exactly `date, currency, fx_to_usd`; key `(date,currency)` unique; `fx_to_usd > 0`; dates contiguous daily including weekends (forward-filled).
- `prices_daily.parquet`: columns exactly `date, ticker, close_local, volume, close_usd`; key `(date,ticker)` unique; `close_usd ≈ close_local × fx_to_usd` for the matching `(date,currency)` row (relative tol 1e-6); no negative prices/volumes; NaN allowed (missing is never imputed) but a NaN `close_local` must imply NaN `close_usd`.
- `esg_snapshot.parquet`: columns exactly `ticker, retrieval_date, esg_total_risk, esg_e, esg_s, esg_g, controversy_level`; `ticker` unique; single `retrieval_date` value across all rows; `controversy_level` null or integer 0–5.
- `fundamentals.parquet`: columns exactly `ticker, fiscal_date, period, revenue, capex, total_debt, interest_expense, operating_cash_flow, depreciation`; `period ∈ {annual, quarter}`; key `(ticker, fiscal_date, period)` unique.

### Test structure required
- One parametrized contract-check function reused for fixtures and real artifacts.
- Real-artifact tests: `pytest.mark.skipif(not path.exists(), reason="artifact not yet fetched")` per artifact — skip, never fail, when missing.
- Negative tests: for each artifact at least three corrupted variants (missing column, duplicate key, enum/range violation) asserting the contract check raises/fails with a message naming the offending column or key.

### Constraints
- No network, no yfinance imports in tests, no fixtures large enough to look like real data.
- Build corrupted fixtures in-test from the valid fixture via pandas mutation where possible (fewer binary files in git).
- Match existing test style in `tests/` (plain pytest, no new dependencies).

### Acceptance criteria
1. With `data/raw/` in its current state, `pytest -q` shows the new real-artifact checks skipping for absent files and passing for present ones (e.g. `disclosures` is out of scope; `universe.parquet` is not part of this WO).
2. All negative tests pass (i.e., corruption is caught with a named-column/key message).
3. Full suite: 0 failures; added runtime ≤5s.
4. Section `## WO-4 results — 2026-06-13` appended to `CODEX_RESULTS.md`: test count added, skip/pass breakdown, blockers.

### Must NOT touch (Claude-owned)
Everything outside `tests/**` and `CODEX_RESULTS.md`. In particular: `data/**` (read-only),
`config/settings.yaml`, `SCHEMAS.md`, all `src/**`, all prose docs.

---
---

## WORK ORDER 5 (P3 — gated on npm): Frontend build verification, browser QA, leaderboard figure polish

### PRECONDITION — check first, stop if unmet
```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install
```
If this fails with `EACCES`/`EPERM` (see `FRONTEND_BUILD_BLOCKER.md` for the known sandbox
blocker), **stop immediately**, append a one-paragraph status to `CODEX_RESULTS.md` saying the
precondition failed, and do nothing else. The user will run the install in a normal terminal first.
If the default npm cache is locked, retry once with `npm.cmd install --cache .npm-cache`.

### Objective
Verify the frontend actually builds and passes browser QA (fixing straightforward build/runtime
errors only), and fix the top-20 leaderboard figure where long company names wrap and create
uneven row heights.

### Environment
- Repo root: `C:\Hackathon\esg-engine`; frontend: `site/` (Vite + React + TS); Python: `.\.venv\Scripts\python.exe`.
- Test baseline: `pytest -q` 0 failures; must not regress.
- QA checklist to execute: `MANUAL_QA_CHECKLIST.md` (in repo root).

### Files
- Modify (fixes only): `site/src/**`, `src/viz/style.py` (top-20 leaderboard figure block only)
- Update: `MANUAL_QA_CHECKLIST.md` (mark items pass/fail), `CODEX_RESULTS.md`
- Do not add dependencies beyond what `site/package.json` already declares.

### Tasks
1. `npm.cmd run build` — fix straightforward TS/build errors until it exits 0 and creates `site/dist/`.
2. `npm.cmd run dev` — in a real browser verify: persistent `SYNTHETIC DEMONSTRATION DATA` banner; hero section; virtualized leaderboard scrolls smoothly with ~500 rows; row click and Enter-key both open the company detail view; weight-sandbox sliders re-rank and Reset restores validated weights; layouts at 1280px / 768px / 375px widths; keyboard-only navigation; `prefers-reduced-motion` respected; zero console errors.
3. Leaderboard figure: in `src/viz/style.py`, make the top-20 leaderboard render with uniform row heights — truncate names with an ellipsis at a fixed character budget and/or widen the name column; regenerate via `.\.venv\Scripts\python.exe -m src.viz.style` and visually confirm `outputs/figures/top20_leaderboard.png`.

### Constraints
- Fix-only scope: no redesigns, no new features, no new dependencies.
- **Never claim the build or any QA item passes unless you actually ran it and it passed** — record exact commands and outcomes.
- Synthetic banner and the disclaimer string `Research demonstration - not investment advice.` must remain visible after any fix (Python tests grep for them).
- Figure changes must not alter which companies appear or their ordering/scores.

### Acceptance criteria
1. `npm.cmd run build` exit 0; `site/dist/` exists.
2. Every checklist item in `MANUAL_QA_CHECKLIST.md` marked pass or fail with a note; failures you can fix within scope are fixed and re-verified.
3. Regenerated `top20_leaderboard.png` has uniform row heights and no wrapped names.
4. `pytest -q` 0 failures.
5. Section `## WO-5 results — 2026-06-13` in `CODEX_RESULTS.md`: build status, browser/viewport matrix results, console-error status, figure before/after note, blockers.

### Must NOT touch (Claude-owned)
`config/settings.yaml`, `SCHEMAS.md`, `COORDINATION.md`, `RESEARCH_LOG.md`, `BIAS_REGISTER.md`,
`AGENTS.md`, `src/signals/**`, `src/composite/**`, `src/validation/**`, `src/scoring/**`,
`src/universe/**`, `src/fetchers/**`, `src/util/**`, `src/report/**`, `outputs/site_data/*.json`,
`data/**`, all prose docs (`README.md`, `DEMO_SCRIPT.md`, report text).

---
---

## Retained by Claude (do not delegate, regardless of what any WO says)
- `src/fetchers/gdelt.py` + the running GDELT sentiment fetch → `sentiment_monthly.parquet`
- All science: `src/signals/`, `src/composite/`, `src/validation/`, `src/scoring/`, and generation of the real `companies.json` / `backtest.json` / `ic_table.json` / `placebo.json` / `validation_results.json`
- Frozen contracts: `config/settings.yaml`, `SCHEMAS.md`
- All prose: report text, `README.md`, `DEMO_SCRIPT.md`, pitch/QA/judging copy, `RESEARCH_LOG.md`, `BIAS_REGISTER.md`
