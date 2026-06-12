# BIAS REGISTER — ESG Momentum Engine 2.0

Every known bias in the research design: severity, direction, mitigation, residual risk.
This register is maintained continuously and becomes the risk section of the report.

| ID | Bias | Severity | Direction of distortion | Mitigation | Residual risk |
|----|------|----------|------------------------|------------|---------------|
| B-01 | **Survivorship bias** — universe selected as of 2026-06; delisted/shrunken names absent from the historical panel | High | Inflates absolute returns of all portfolios; Q5−Q1 spread partially insulated (both legs are survivors) but likely modestly overstated | Acknowledged, directionally quantified in report (Elton, Gruber & Blake 1996 show survivorship materially inflates measured performance); spread interpreted with this caveat; no claim of unbiased absolute returns | Cannot be removed without point-in-time constituent data (named as the licensed-data upgrade) |
| B-02 | **Look-ahead via Sustainalytics snapshot** — yfinance ESG scores are a single current snapshot, not point-in-time history | High | Using today's score at historical dates would leak future information | Snapshot used ONLY for (a) cross-sectional level percentile (B1, the deliberate "naive baseline") and (b) latest-date scoreboard context; never as a historical time series. ESG *momentum* is carried by alt-data signals computed point-in-time | Level variable (B1) backtest is labeled approximate; conclusions rest on point-in-time variables |
| B-03 | **Multiple-testing / factor-zoo risk** — ~18 variables × 4 horizons ≈ 72 hypotheses | High | Some "significant" ICs expected by chance alone | Benjamini–Hochberg FDR control at q=0.10 on IC t-stats (Harvey, Liu & Zhu 2016); Deflated Sharpe Ratio (Bailey & López de Prado 2014) accounting for number of composite configurations trialed; placebo shuffle test | Residual selection effects acknowledged; test-window touched once |
| B-04 | **Backtest overfitting** — composite weighting choices could be tuned to the full sample | High | Overstates out-of-sample performance | Strict train (≤2021-12-31) / test (2022-01→) split; weights frozen from training window only; walk-forward validation inside training window; test window touched once at the end | Single test window is short (~4.5y); stated |
| B-05 | **Universe selection bias** — index seeds + screener favor large, covered, liquid names | Medium | Results generalize to the investable large/mid-cap segment only | Allocation methodology documented; coverage matrix published; claims scoped to "top ~500 ASEAN" | Accepted by design (matches the use case) |
| B-06 | **GDELT entity-matching noise** — name collisions (e.g., generic company names matching unrelated articles) | Medium | Attenuates true sentiment signal (noise → bias toward zero) or injects spurious tone for collision-prone names | Query design: exact company phrase + country qualifier; English + sourcecountry filters; per-name article-volume sanity checks; collision-prone names flagged in coverage matrix | Some noise inevitable; biases against finding signal (conservative) |
| B-07 | **Short sample / regime dependence** — effective sample 2017–2026 dominated by COVID and the 2022 rate shock | Medium | Signal may be regime-specific | Sub-period robustness (2018–19, 2020, 2021, 2022, 2023–25); by-country and by-sector splits | Cannot extend history; stated |
| B-08 | **FX conversion artifacts** — 6 currencies vs USD | Medium | Country-level FX trends could masquerade as cross-sectional alpha | All returns computed in USD AND local currency; country dummies in Fama–MacBeth; by-country spreads reported | Residual FX co-movement noted |
| B-09 | **yfinance data quality / ToS fragility** — unofficial Yahoo scrape, fields can be stale or missing | Medium | Random gaps; occasional bad prints | Winsorization 1/99; missing stays missing (no imputation); coverage matrix with per-company coverage_pct; confidence bands scale with coverage; CSV import mode is the compliant production path (stated) | Accepted for research demonstration |
| B-10 | **Liquidity / implementability** — several ASEAN markets restrict shorting; small names untradeable | Medium | Q5−Q1 spread partly theoretical | <US$250k median daily dollar volume excluded from backtest portfolios; transaction-cost matrix (25–60bps one-way) applied; long-only Q5 vs benchmark reported as the implementable claim | Capacity comment in report |
| B-11 | **Greenwashing / gameability of disclosure signals** — communications volume ≠ substance | Medium | Disclosure-behavior variables can be inflated by PR activity | Cross-checked against sentiment dynamics and fundamental (CapEx, cost-of-debt) signals in composites; flagged in risk section | Partially mitigated only |
| B-12 | **Scope 3 emissions gaps** — most ASEAN disclosure omits Scope 3 | Low (no emissions-level variable used) | Any emissions-linked inference understates supply-chain exposure | No emissions-quantity variable in the signal set (documented as future work with licensed data) | N/A in current design |
| B-13 | **ESG-rating provider divergence** — single-provider (Sustainalytics) dependency | Medium | Level baseline (B1) reflects one provider's methodology (Berg, Kölbel & Rigobon 2022: pairwise rating correlations ~0.38–0.71) | B1 used only as the naive baseline the thesis argues against; alt-data signals are provider-independent | Stated |
| B-14 | **Data-snooping in design choices** — windows (12m slopes, 3m holds) chosen from literature/convention before seeing results | Medium | Subtle overfitting via "conventional" parameters | Parameters fixed in settings.yaml before validation runs; formation-lag sensitivity test; no per-variable window tuning | Stated |
| B-15 | **User misinterpretation risk** — scores mistaken for investment advice | Medium | n/a (legal/communication risk) | Persistent "research demonstration — not investment advice" disclaimer on site and report | Standard |

Updates are appended with date stamps as new biases are identified during the build.

## B-16 — Single-provider ESG dependency materialized as total loss (2026-06-13)
Yahoo's free quoteSummary `esgScores` module now returns HTTP 404 for every symbol tested,
including US mega-caps (AAPL) — the free Sustainalytics feed is dead, not ASEAN-thin. Live
`esg_snapshot.parquet` is schema-correct but 0/477 populated; all B-family variables and E1 are
missing in live mode. Effect: the validated composite can only draw on alt-data families
(A sentiment, C fundamentals, D disclosures, F regulatory) — which is the thesis, stated more
strongly: official-score dependence is now demonstrably a fragility, not just a divergence risk
(Berg, Kölbel & Rigobon 2022). Mitigations: (1) the 2x2 level axis falls back to the trailing-12m
mean-tone percentile (level of the same instrument whose slope is the momentum axis), tagged in
companies.json meta.esg_level_axis_source; (2) the CSV import path is the licensed upgrade route
for real point-in-time ESG history; (3) report and site state the gap plainly. Severity: M
(level baseline lost; momentum thesis unaffected). Residual: naive-level benchmark (B1 quintiles)
cannot be run on live data — reported as unavailable rather than proxied in the backtest.
