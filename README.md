# ESG Momentum Engine

A research prototype testing whether ESG momentum signals predict equity returns across ASEAN markets — built for PolyFinTech100 2026. The headline finding is negative: after rigorous statistical correction, out-of-sample predictive power is approximately zero. This repository documents why that's the honest answer, and how to reach it without fooling yourself.

## The Question

ESG scores are marketed as alpha. Most backtests supporting that claim fail basic multiple-testing discipline: dozens of signal variants tried, the best one reported, no correction applied. This project asks the question properly: **does ESG momentum carry statistically defensible predictive information for ASEAN equity returns, after controlling for data snooping?**

## Universe & Data

- **477 ASEAN-listed companies** across Singapore, Malaysia, Indonesia, Thailand, and Vietnam (the Philippines was intended but dropped — no PSE ticker resolves on the free data provider; documented in `BIAS_REGISTER.md`)
- **198-name liquid discovery universe** for all statistical validation (Singapore 47, Malaysia 46, Indonesia 43, Thailand 37, Vietnam 25) — mega/large-cap names with ≥US$1M median daily dollar volume and complete sentiment coverage. Discovery and deployment are deliberately separated: statistical claims are made only on the tight, fully covered universe; the full 477 are scored for the leaderboard with confidence bands that widen with missing coverage
- Signal families tested:
  - **A — Sentiment dynamics**: GDELT news-tone momentum and shock features
  - **C — Fundamentals**: coverage-adjusted fundamental momentum
  - **F — Regulatory overlay**: jurisdiction-level ESG regulation intensity
- Families B and D (provider ESG scores) were dropped mid-project when the upstream ESG endpoint was discontinued — documented in `BIAS_REGISTER.md` as a live example of provider risk in ESG data pipelines

## Methodology

Every signal passes through the same gauntlet, in order:

1. **Information Coefficients with Newey-West errors** — rank IC of signal vs. forward returns, HAC-corrected for autocorrelation in overlapping windows
2. **Benjamini-Hochberg FDR control** — all signal variants tested are counted; nothing gets reported without surviving false-discovery correction across the full search space
3. **Fama-MacBeth cross-sectional regressions** — per-period cross-sections, time-series of coefficients, testing whether the signal survives alongside known factors
4. **Deflated Sharpe Ratio** (Bailey & López de Prado) — backtest Sharpe adjusted for the number of trials, skewness, and kurtosis
5. **Placebo test, 1,000 iterations** — signal labels randomly permuted; the real signal must beat the null distribution, not just zero

## The Result

Out-of-sample ICs across surviving signal families are statistically indistinguishable from zero. The in-sample results that looked promising did not survive FDR correction and placebo testing.

This is the finding, not a failure of the project. The infrastructure demonstrates what it takes to *reject* a seductive hypothesis: most published ESG-alpha claims would not survive this pipeline. The negative result is more informative than a fragile positive one.

Full statistical audit: [`REPORT_METHODOLOGY.md`](REPORT_METHODOLOGY.md) (~3,200 words). Chronological research decisions: [`RESEARCH_LOG.md`](RESEARCH_LOG.md). Known biases and mitigations: [`BIAS_REGISTER.md`](BIAS_REGISTER.md).

## Architecture

The pipeline is a linear data flow — fetch → signal → composite → validate → score → report — with every stage driven by a central config and logged to an append-only action log.

```
src/
├── universe/     Universe construction: seed lists per market, liquidity
│                 tiering, and the 198-name discovery-universe filter
├── fetchers/     Data acquisition: prices, fundamentals, FX, GDELT news
│                 tone, disclosures, and the (since-discontinued) ESG
│                 provider endpoint
├── signals/      Signal engine: sentiment-momentum and shock features,
│                 fundamental momentum, jurisdiction regulatory overlay
├── composite/    Composite construction: combines signal families into
│                 candidate composites under multiple weighting schemes
├── validation/   The statistical gauntlet: Newey-West ICs (ic.py),
│                 Fama-MacBeth regressions (fama_macbeth.py), quintile
│                 backtest with ASEAN cost matrix and Deflated Sharpe
│                 (backtest.py), orchestrated by run_validation.py
├── scoring/      Deployment scoring: full-universe leaderboard with
│                 coverage-aware confidence bands
├── csv_import/   Provider-neutral CSV import contract with schema
│                 validation — the licensed-data upgrade path
├── report/       Word report builder (build_report.py)
├── viz/          Figure generation and shared plot styling
└── util/         Logging and the synthetic validation panel
```

Supporting directories:

- `config/` — central configuration; every threshold used by the pipeline is defined here, not inline
- `site/` — frontend for browsing the leaderboard (`outputs/site_data/companies.json` is its feed)
- `tests/` — pytest suite, including pipeline validation against a seeded synthetic panel (the planted factor is recovered at rank correlation ≈ 0.71 with placebo p = 0 before any live data is trusted)
- `scripts/` — Windows entry points: `verify_local.bat`, `start_site.bat`
- `specs/`, `tools/` — design specs and one-off tooling (deck builder, submission assembler)

## Running Locally

```bat
cd /d C:\Hackathon\esg-engine
scripts\verify_local.bat
```

If verification passes, start the site:

```bat
scripts\start_site.bat
```

Manual equivalents and troubleshooting: `LOCAL_RUN_GUIDE.md`. If npm package fetching is blocked, see `FRONTEND_BUILD_BLOCKER.md`.

## Repository Guide

- `REPORT_METHODOLOGY.md` — full statistical methodology and audit trail
- `RESEARCH_LOG.md` — chronological research decisions
- `BIAS_REGISTER.md` — known biases, cuts, and mitigations
- `DATA_IMPORT_GUIDE.md` — CSV import contract for licensed real-data mode
- `DEMO_SCRIPT.md` — 3-minute judge-facing demo flow
- `MANUAL_QA_CHECKLIST.md` — browser and Word report QA

## Disclaimer

This is a research prototype built for a hackathon. Outputs are not investment advice. Synthetic demonstration artifacts (where present) are illustrative only and are labeled as such.
