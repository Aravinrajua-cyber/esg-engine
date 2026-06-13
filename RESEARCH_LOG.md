# RESEARCH LOG — ESG Momentum Engine 2.0

Running prose log of every research decision, the alternatives considered, and the rationale.
This document becomes the methodology section of the final report and proves intellectual ownership.
Machine-readable action log: `logs/actions.jsonl`.

---

## 2026-06-12 (evening SGT) — Project start, scope, and environment

**Context.** PolyFinTech100 API Hackathon 2026, ESG Intelligence category (CGS International).
Thesis under test: official ESG scores are lagging/noisy/inconsistent; the *rate of change* of a
company's ESG trajectory — detectable early via alternative data (news sentiment dynamics,
disclosure behavior, capital allocation shifts, governance deltas) — predicts future equity
returns in ASEAN before official scores update.

**Hard constraint decided today: ~2–3 day build window.** Applying the master plan's cut order
up front, as conscious scope decisions (not silent omissions):

1. **Wayback Machine ESG score-history reconstruction: SKIPPED** (first item in the cut order).
   Consequence: time-series ESG momentum (variable B2) is missing for nearly all names and the
   ESG-momentum leg of the thesis is carried by the alternative-data signals (sentiment velocity,
   disclosure trend, capital-allocation trend). This proxy structure is itself part of the thesis
   (alt data leads official scores) and is stated plainly in the report. B2 is computed only if a
   score history happens to be reconstructible cheaply; it is never imputed.
2. **Family D disclosure signals: best-effort.** SGX announcements are attempted; if
   not scrapeable within bounded effort, documented and skipped. Bursa second priority.
3. **Per-company detail figures: top names only** (leaderboard covers the full universe).
4. **Never cut (the moat):** Phase 4 rigor — Newey–West ICs, BH-FDR multiple-testing control,
   Fama–MacBeth with controls, train/test split frozen at 2021-12-31, walk-forward, placebo
   shuffle, block-bootstrap CIs, Deflated Sharpe Ratio, transaction-cost matrix.

**Deliverables locked:** research report (.docx), static site, PITCH.md, QA.md, DEMO.md,
JUDGING.md, README, **plus a slide deck (.pptx)** requested by the team today.

**Environment.** Windows 11, Python 3.14.3 (fresh venv; deps pinned in requirements.txt),
Node v24/npm 11 for the site build, git repo initialized at `esg-engine/`. Implementation-heavy
modules are delegated to Codex (CLI 0.135.0) against written specs; every diff is reviewed by the
lead agent before acceptance. Review standard: no fabricated data, no hardcoded results, explicit
error handling, missing values stay missing.

**Prior art in-house.** A v1.0 prototype (20 hardcoded large caps, Streamlit dashboard, simple
lead-lag analysis) exists at `../ESG_Momentum_Engine`. Decision: build 2.0 clean rather than
evolve v1.0 — the architecture differs fundamentally (universe screening, point-in-time signal
panel, validation engine, static React site). v1.0 is kept untouched as reference.

**Data modes decided (three, per plan):** LIVE (primary; all reported statistics), SYNTHETIC DEMO
(seeded, schema-identical, watermarked, never in the report), CSV IMPORT (strict templates +
validation — the documented upgrade path to licensed point-in-time data, e.g. Bloomberg/Refinitiv
or CGS internal data).

---

## 2026-06-12 — Phase 1 design: universe construction

**Objective:** defensible top ~500 ASEAN universe across SGX, IDX, Bursa, SET, PSE, HOSE/HNX.

**Allocation methodology decision.** The 500 slots are allocated proportionally to each market's
aggregate market capitalization, computed live from the screened candidate pool (free-float
weighting where Yahoo exposes float shares; otherwise full market cap — documented per market).
Expected rough split per plan: SG ~90, ID ~110, MY ~90, TH ~110, PH ~50, VN ~50 — to be verified
against live data, not assumed. Final allocation table goes in the report.

**Candidate sourcing decision.** Two-layer approach:
- *Seed layer:* curated constituent lists per market (STI + SG mid caps; IDX80/Kompas100;
  FBM KLCI + FBM Mid 70; SET100; PSEi + mid caps; VN100 proxies). Curated from public index
  membership knowledge; every ticker is validated live against yfinance before inclusion —
  non-resolving names are logged, never silently dropped.
- *Screen layer:* Yahoo Finance equity screener by region (where supported) sorted by market cap
  to fill remaining slots and catch large names missing from seeds.
Markets Yahoo cannot reliably serve shrink honestly (documented count + names).

**Liquidity rule decision.** Median daily dollar volume (trailing 6 months) < US$250k → flagged
LOW_LIQUIDITY. Flagged names stay in the universe and the scoreboard but are excluded from
backtest portfolios: an untradeable signal is not alpha. Count reported.

**Survivorship acknowledgment.** The universe is selected as of 2026-06, so the backtest inherits
survivorship bias: names that delisted or shrank before today never enter the panel, and today's
constituents are, by construction, yesterday's relative winners. Effect direction: overstates
absolute returns of all quintiles; the Q5−Q1 *spread* is partially insulated (both legs drawn from
survivors) but is still likely modestly overstated. Logged in BIAS_REGISTER (B-01) with the
Elton–Gruber–Blake citation; stated in the report.

---

## 2026-06-13 — Phase 1 EXECUTED: universe built (`data/raw/universe.parquet`, 477 names)

Three live findings forced documented deviations from the initial plan:

1. **Philippines dropped (6 → 5 markets).** The yfinance region screener returns zero PH equities,
   and no PSE ticker resolves under any Yahoo suffix tested (`.PS`, `.PH`, `.PSE` — all 0 rows,
   2026-06-13). PH is therefore excluded from the live universe and documented as a coverage gap;
   the curated PH seed list is retained in `seeds.py` for the CSV-import upgrade path. Honest
   shrinkage, not silent dropping (operating rule #1). Logged BIAS_REGISTER B-05.
2. **SGX Depository Receipts (SDRs) filtered.** The SG screener is polluted with SGX-listed
   depository receipts of foreign/cross-listed firms (PetroChina, Bank of China, HSBC, Tencent,
   Alibaba, plus Thai/Indonesian names already in our universe — e.g. "i BBCA ID SDR 1to2"). These
   are double-counted and carry inflated/misreported market caps (one showed US$480B). Filter:
   drop names containing "SDR" or 4-letter tickers ending in `D` (HPCD, HBND, TDED, IBKD, HSHD…).
   Plus a USD 150B mcap sanity ceiling and a company-name dedupe (removed the SingTel Z74/Z77 dual
   line). Without this SG was 45–51% of the universe.
3. **Allocation method finalized.** Proportional to captured aggregate USD market cap, but with a
   **25% per-market share cap and pro-rata redistribution.** Reason: the screener caps results at
   250/market, truncating the long tail of the larger markets (ID, MY) so their *captured*
   aggregate understates true market cap, while SGX's foreign secondary listings overstate SG. The
   cap is a standard single-market-dominance guardrail and lands the mix near true ASEAN
   market-cap shares. Final: **SG 125, ID 116, TH 100, MY 96, VN 40 (= 477)**; raw uncapped shares
   are recorded in `logs/actions.jsonl` (`allocated` action). Acceptance gate (≥450) PASS.
   Liquidity: 74 names below US$250k median daily $ volume flagged LOW_LIQUIDITY (kept in universe
   + scoreboard, excluded from backtest portfolios). TH capped at 100 by the DR-filtered candidate
   pool; VN = 40 curated seeds (screener serves no VN).

**Next:** launch the GDELT sentiment fetch (the long pole) on this universe as a resumable
background process; Codex runs the other fetchers, the frontend (synthetic mode), and the
viz/report/test scaffolds against the frozen contracts in parallel.

---

## 2026-06-13 — Phases 3-5 science core BUILT and verified on the planted-signal synthetic panel

GDELT fetch (the long pole) launched as a resumable background run over the 477-name universe
(~14s/name under the 7s request spacing; per-ticker cache makes interruption free). While it runs,
the full scientific core was written and validated against `data/_synth` (latent factor theta
drives news tone AND forward returns; everything else is noise — a correct pipeline must find it).

**New modules** — `src/validation/ic.py` (Spearman ICs, Newey-West t, BH-FDR),
`src/composite/composites.py` (EIP/TRI/CPS/MASTER x {equal, trailing-IC, rank-aggregate},
walk-forward), `src/validation/fama_macbeth.py` (FM + VIF + F1 interaction),
`src/validation/backtest.py` (quarterly quintiles, ASEAN cost matrix, block bootstrap, DSR,
placebo, robustness), `src/validation/run_validation.py` (orchestrator -> frozen
validation_results.json), `src/scoring/score.py` (Phase 5 product layer -> site_data JSONs).

**Methodological decisions (fixed before any real-data run):**
1. **Winner selection metric:** training-window NET quarterly Q5-Q1 spread only. Test window is
   evaluated once, for the table; never for selection.
2. **DSR trial accounting:** N = 12 configs (4 composites x 3 weighting schemes); Var(SR) taken
   across the 12 training-window per-period Sharpes (Bailey & Lopez de Prado 2014).
3. **Placebo basis is gross-vs-gross.** Costs are orthogonal to whether a ranking carries
   information; netting both sides would only shift both distributions by the same drag and
   invite a cost-model artifact into the p-value.
4. **Pillar composites IC-weight their members** (training window). First build equal-weighted
   members inside each pillar; the synthetic test caught it: corr(product score, theta) was only
   0.165 because noise members (A2, A4) diluted the planted ones, while the validated composite
   itself sat at 0.67. After member IC-weighting + display smoothing: **0.705**. Lesson logged:
   the product layer must inherit the research weights end-to-end, not re-aggregate naively.
5. **Display smoothing:** product scores average pillar z over the trailing 3 rebalances
   (`scoring.smooth_months`). Display-side only — validation and backtest never smooth.
   Uses only t and earlier data: no lookahead.
6. **Confidence interval:** half-width = base + coverage_coeff x (1 - coverage) +
   dispersion_coeff x std(pillar scores) (`scoring.confidence`, settings.yaml). Additive
   settings keys documented here per the B-14 parameter-freeze rule.
7. pandas 3 removed grouping columns from `groupby.apply`; winsorize/z-score rewritten with
   vectorized transforms (same math, contract tests unchanged).

**Synthetic recovery results** (80 names, 108 rebalances, seed 42): FDR survivors
{A1, A3, B3, C1, C3, C4, D1, E1} — planted A1/A3/C1/D1 all recovered; B3/C3/E1 are chance
survivors, consistent with what q=0.10 FDR permits in a single draw (the register's honesty
point, not a defect). Winner: TRI_equal. Net Q5-Q1 +43.1% ann. (the planted effect is
deliberately enormous), bootstrap CI [+38.4%, +48.0%], DSR 0.978, placebo p = 0.000 with placebo
mean +0.1%. Q5 spread has no down quarter on synth, so Sortino/Calmar are undefined (null) —
expected there, will be populated on real data. Suite: 32 passed.

**Next:** GDELT completes -> real signal run blocked only on Codex WO-1 (prices/fx/esg/
fundamentals). Then: real validation -> real site_data -> report prose with real numbers.

## 2026-06-13 — Live fetcher verification: prices/fx/fundamentals GOOD; Yahoo ESG endpoint DEAD

Live runs (Codex's sandbox had no Yahoo route, so verified by Claude): `fx_daily` 22,735 rows x 5
currencies, 2014-01-01 -> today, spot rates sane. `prices_daily` 1,249,605 rows, 477/477 tickers,
100% current within 7 days, 403/403 backtest-eligible names covered, close_usd = close_local x fx
exact; 70.4% of names reach back to 2014-01 (the rest are post-2014 IPOs, e.g. BREN.JK 2023 — not
gaps). `fundamentals` 5,099 rows, 477/477 tickers, median 5 annual periods, revenue 72.9%
populated — C-family computable for most of the universe. Codex's raw-contract tests (merged from
the mirror pass) activate against the real artifacts and pass.

`esg_snapshot`: 0/477 populated. Differential diagnosis: AAPL returns the same quoteSummary 404 —
Yahoo has removed the free Sustainalytics module entirely (upstream death, not a fetcher bug; the
fetcher degraded exactly per contract: empty schema-correct snapshot + 477-row failure log, no
fabrication). Consequences and fallback logged as BIAS_REGISTER B-16; the 2x2 level axis now
proxies from trailing-12m mean tone when B1 is absent (scoring layer, tagged in meta). The naive
ESG-level backtest benchmark is reported as unavailable in live mode.

## 2026-06-13 — PIVOT: discovery on the liquid universe (GDELT throttle forced the split)

Real-data shakedown (full pipeline on 477 names, partial sentiment) confirmed the Phase 3->4 code
runs clean on live data and surfaced the live coverage map: C-family (fundamentals) 300-460 names
and F1 (country) 477 are real/final; A-family stuck at ~10% (GDELT IP-throttled to 48/477, days
from completing); B-family + E1 dead (Yahoo ESG, B-16); D-family empty (disclosures fetcher
returned 0 rows). On that partial data NOTHING survived BH-FDR and the orchestrator correctly
halted rather than fabricate a composite — but A1 (sentiment velocity) already showed IC +0.085,
t_NW 2.16, p 0.030, 62% hit at 3m on just ~52 names, i.e. a power problem, not a dead thesis.

Decision (validation vs deployment split, standard quant practice): run all statistical discovery
(Phases 3-4: univariate IC, FDR, Fama-MacBeth, composite discovery, backtest, DSR, placebo) on the
**liquid discovery universe** = mcap_tier in {mega,large} AND adv_usd >= USD 1M median daily volume
= **198 names** (SG 47, MY 46, ID 43, TH 37, VN 25), persisted to
data/interim/discovery_universe.parquet. This is the backtest-tradeable scope anyway, so FDR/DSR
on it is clean, not a compromise. The frozen composite is then SCORED on the full 477 for the
leaderboard, with confidence bands widening by per-company data coverage. Report framing must state
this discovery/deployment split explicitly.

Implementation: gdelt.py --universe <path> (fetch a specific scope, shared resumable cache);
run_validation.py --discovery <path> (restrict ALL Phase 4 stats to that subset; composite still
scored on full universe downstream); phase4_results.pkl now written alongside validation_results.json.
GDELT discovery fetch launched on the 198 liquid names (39 already cached, 159 remaining; full-477
fetch stopped — cache preserved). Phase 3->4 + freeze runs the moment sentiment lands.
