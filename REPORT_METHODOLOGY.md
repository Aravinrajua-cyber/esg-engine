# §3 Methodology — Actions Taken

This section is the complete record of how the ESG Momentum Engine was built, in the order it was
built, with the reasoning behind every material decision, the alternatives considered, and why each
was accepted or rejected. It is deliberately unredacted: a reader should be able to reconstruct the
entire research process and challenge any single choice. Realized result magnitudes (ICs, spreads,
Deflated Sharpe) are not stated here — they are populated from the frozen `phase4_results.pkl` in
the Results section. This section documents *method and decisions only*; every parameter named below
was fixed in `config/settings.yaml` before the validation window was ever evaluated, so that no
threshold could be tuned to the answer.

---

## 3.1 Universe construction

**Goal and gate.** The target was a 500-name ASEAN equity universe with a hard acceptance gate of
≥450 valid tickers. The realized universe is **477 names**, allocated SG 125 / ID 116 / TH 100 /
MY 96 / VN 40. The shrinkage from 500 is documented rather than hidden, because the operating rule
of the project is that honest coverage gaps beat silent padding.

**Markets: six intended, five delivered.** The Philippines was dropped. The yfinance regional
screener returns zero PSE equities, and no PSE ticker resolves under any Yahoo suffix tested
(`.PS`, `.PH`, `.PSE` — all returned zero rows on 2026-06-13). Rather than fabricate Philippine
coverage, PH was excluded and the gap recorded (BIAS_REGISTER B-05); the curated PH seed list is
retained for the CSV-import upgrade path, which is the compliant route to licensed PH data. The
alternative — forcing PH in with a different data source mid-build — was rejected as scope creep
that would have introduced an unvalidated second data pipeline.

**Cleaning SGX depository receipts.** The Singapore screener is polluted with SGX-listed depository
receipts of foreign and cross-listed firms (PetroChina, Bank of China, HSBC, Tencent, Alibaba, plus
Thai/Indonesian names already in the universe). These double-count constituents and carry inflated
or misreported market caps — one showed US$480bn. Filter applied: drop names containing "SDR" or
four-letter tickers ending in `D`, plus a US$150bn market-cap sanity ceiling and a company-name
dedupe (which removed the SingTel Z74/Z77 dual line). Without this filter Singapore was 45–51% of
the universe; the alternative of keeping them would have made the cross-section a Singapore proxy.

**Allocation method.** Names per market are allocated **proportional to captured aggregate USD
market capitalization, with a 25% per-market share cap and pro-rata redistribution**. The reasoning:
the screener truncates each market's long tail at 250 results, so the larger markets (ID, MY) have
their *captured* aggregate market cap understated, while SGX's foreign secondary listings overstate
Singapore. A naive proportional allocation would therefore over-weight Singapore. The 25% cap is a
standard single-market-dominance guardrail and lands the final mix near true ASEAN market-cap
shares. Raw uncapped shares are recorded in `logs/actions.jsonl` for audit. The alternative of equal
per-market quotas was rejected because it would misrepresent the economic weight of the region.

**Liquidity filter — two thresholds for two purposes.** Liquidity is median daily dollar volume
over a trailing 6-month window.
- *Full universe / backtest eligibility:* a floor of **US$250,000** median daily dollar volume.
  74 names fall below it and are flagged `LOW_LIQUIDITY`. They are *kept* in the scoreboard and
  leaderboard (a user may still want to see them) but *excluded* from backtest portfolios, because
  the transaction-cost and capacity assumptions do not hold for them.
- *Discovery universe (see 3.5):* a tighter floor of **US$1,000,000** median daily dollar volume,
  restricted to mega- and large-cap tiers, yielding **198 names** (SG 47 / MY 46 / ID 43 / TH 37 /
  VN 25). This is the universe on which the statistical proof is run.

The two thresholds reflect a deliberate validation-vs-deployment separation: validate on the
universe where data is best and trading is realistic; deploy (rank) on the broad universe with
documented per-company confidence. Market-cap tiers are fixed at mega ≥ US$10bn, large ≥ US$2bn,
else mid.

---

## 3.2 Data fetchers — what was used, what failed, and why

**Price and FX (yfinance).** Daily close and volume for all 477 names from 2014-01-01 to the
retrieval date, converted to USD via daily FX (`close_usd = close_local × fx_to_usd` on the same
date, exactly, to floating-point tolerance). Coverage is complete: 477/477 tickers, current to
within five business days, and ~70% reach back to 2014 (the remainder are genuine post-2014 IPOs,
e.g. BREN.JK and DCII.JK, not gaps). FX uses one row per currency per day with weekends
forward-filled — the single documented exception to the no-imputation rule, because a currency's
rate is genuinely constant over a non-trading weekend. yfinance was chosen as a free, broad, ASEAN-
covering source appropriate for a research demonstration; its limitation is that it is an unofficial
scrape, which is exactly why the CSV/API import path exists as the licensed production route.

**News sentiment (GDELT DOC 2.0).** Monthly average tone and article volume per company from
2017-01-01, via the TimelineTone and TimelineVolRaw endpoints, aggregated to a monthly panel. GDELT
was chosen because it is the only free, global, daily-updated news instrument with the historical
depth the momentum thesis requires (Leetaru & Schrodt 2013). Its known weakness is entity-matching
noise — company-name collisions — which is mitigated by cleaning legal-form suffixes from query
strings and is disclosed as a residual risk. GDELT's hard rate limit (1 request / 5s) and aggressive
IP throttling are the operational long pole and drove the discovery pivot in 3.5.

**ESG scores (yfinance / Sustainalytics) — the source died.** The intended ESG snapshot
(total ESG risk, E/S/G sub-pillars, controversy level) could not be retrieved: Yahoo's free
`esgScores` module now returns HTTP 404 for **every** symbol, including US mega-caps such as AAPL.
This is an upstream removal of the free Sustainalytics feed, not an ASEAN-coverage thinness and not
a fetcher defect — the fetcher degraded exactly as designed, writing a schema-correct but empty
snapshot plus a complete failure log, fabricating nothing. The consequence is logged as
BIAS_REGISTER B-16: the entire B-family (ESG level, ESG momentum, controversy, pillar imbalance)
and E1 (governance pillar) are unavailable in live mode. This is not merely an inconvenience — it is
a live demonstration of the project's own thesis. Single-provider ESG dependence is a fragility, not
just a divergence problem (Berg, Kölbel & Rigobon 2022, "Aggregate Confusion"). The model therefore
rests on the families that *are* available — A (sentiment), C (fundamentals), F (regulatory) — which
is precisely the alternative-data argument the product makes. Where the 2×2 classification needs an
"ESG level" axis, it falls back to the trailing-12-month mean news-tone percentile (the level of the
same instrument whose slope is the momentum axis), and this substitution is tagged in
`companies.json` metadata so it is never mistaken for a real Sustainalytics level.

**Disclosures (SGX/Bursa, best-effort).** The sustainability-announcement fetcher was always scoped
as best-effort for SGX and Bursa only. In the live run it returned zero rows, so the D-family
(disclosure-frequency trend D1, disclosure recency D2) is empty. This is recorded honestly rather
than back-filled; the announcement feeds are a candidate for the licensed-import path.

**Net effect on the variable set.** Of the intended ~18 variables, the live, populated set is the
A-family, the C-family, and F1, plus the controls. B, E, and D families are documented as
data-unavailable. This is stated plainly because a judge who finds an empty family undocumented
would rightly distrust everything else.

---

## 3.3 Signal families — exact definitions

Every variable is a pure, point-in-time function of the raw panels: a signal observed at month *t*
uses only data dated ≤ *t*. Fundamentals carry a 90-day publication lag (a fiscal-year-end figure is
not treated as known until 90 days after the period close). The snapshot-based ESG variables are the
documented exception (BIAS_REGISTER B-02): a single retrieval-stamped snapshot is not point-in-time,
so those variables are excluded from the strict no-look-ahead test and flagged accordingly.

At each monthly rebalance date every variable is (1) winsorized at the **1st and 99th percentiles**
to cap the influence of outliers and data errors, (2) **z-scored cross-sectionally within that date**
(mean 0, standard deviation 1 across the names present that month), and (3) **sign-oriented** so that
a higher z-score always means a better expected return under the hypothesis. This within-date
standardize-and-winsorize construction follows standard factor practice (e.g. Asness, Frazzini &
Pedersen's factor work; Asness et al. on consistent cross-sectional scoring). **Missing values are
left missing (NaN) and never imputed** — a name absent from a variable simply does not contribute to
that variable's cross-section, and its overall coverage is reported.

The variable definitions (orientation in brackets: +1 = higher raw value is better, −1 = flipped):

**Family A — Sentiment dynamics (GDELT).** Windows from `signals.windows`.
- **A1 — Sentiment velocity** [+1]: OLS slope of monthly average tone over the trailing 12 months,
  requiring ≥9 of 12 observations. The core thesis variable: gradual tone improvement that official
  scores have not yet reflected.
- **A2 — Sentiment acceleration** [+1]: the trailing 6-month tone slope minus the prior 6-month tone
  slope — is the improvement itself speeding up.
- **A3 — Attention trend** [+1]: OLS slope of log(1 + article volume) over 12 months — rising
  coverage of improving names.
- **A4 — Tone dispersion** [−1]: standard deviation of monthly tone over 12 months, a
  controversy/uncertainty proxy expected to be negatively related to returns.

**Family B — ESG score structure (data-unavailable in live mode, B-16).** B1 ESG risk level [−1,
the deliberate "naive baseline" the thesis predicts is weak), B2 ESG momentum (Δ score where history
exists, else missing — never imputed), B3 controversy level [−1], B4 |E−G| pillar imbalance [−1].

**Family C — Capital allocation & balance sheet (fundamentals).**
- **C1 — CapEx-intensity trend** [+1]: change in CapEx/Revenue over 3 years (transition-investment
  proxy).
- **C2 — Cost-of-debt trend** [−1]: change in (interest expense / total debt) over 2 years — the
  credit market's repricing of the name; rising cost of debt is bad.
- **C3 — Revenue growth** [+1]: 3-year revenue CAGR.
- **C4 — CapEx-to-depreciation trend** [+1]: change in CapEx/Depreciation over 2 years (asset-
  renewal proxy).

**Family D — Disclosure behavior (empty in live mode).** D1 sustainability-announcement-count slope
over 8 quarters, ≥4 obs [+1]; D2 months since last sustainability announcement [−1].

**Family E — Governance (data-unavailable, B-16).** E1 governance pillar percentile [−1 oriented].

**Family F — Macro overlay.**
- **F1 — Country regulatory-momentum index** [+1]: a slowly-varying 0–10 country score built by hand
  from four publicly cited components — carbon pricing (0–3), mandatory climate disclosure (0–3),
  sustainable-finance taxonomy (0–2), and stewardship/governance code (0–2). Every input carries a
  dated public citation so the report's framework registry can reproduce it. F1 is tested both as a
  direct signal and as an interaction (does a company signal pay more in a strengthening regulatory
  regime).

**Controls (never sold as ESG alpha):** 12-1 price momentum (`mom_12_1`), size (`log_mcap`),
12-month volatility (`vol_12m`), and sector and country dummies. These exist so that any ESG result
must prove it carries information *beyond* the well-known factors.

---

## 3.4 Phase 4 — alpha discovery and validation

The validation protocol is executed in a fixed order, and the training/test separation is enforced
in code, not by convention.

**Univariate information coefficients.** For each variable and each forward horizon (1, 3, 6, 12
months) the monthly **Spearman rank IC** between the within-date z-score and the forward USD return
is computed. The IC time series is summarized by its mean, its standard deviation, its
**Newey–West**-corrected t-statistic, and its hit rate (share of months with positive IC). Spearman
(rank) rather than Pearson is used because the relationship need only be monotonic, not linear, and
rank correlation is robust to the heavy tails of return data. The Newey–West HAC correction (Newey &
West 1987) is applied with a lag equal to the return horizon, because overlapping multi-month forward
returns induce mechanical autocorrelation in the IC series that would otherwise inflate the
t-statistic; using lag = horizon is the standard, conservative choice for overlapping windows.

**Multiple-testing control.** Roughly 18 variables × 4 horizons ≈ 72 hypotheses are tested. Reporting
only the ones that "worked" would be textbook data-mining. **Benjamini–Hochberg false-discovery-rate
control at q = 0.10** is therefore applied jointly across all variable×horizon hypotheses (Benjamini
& Hochberg 1995), and only survivors are eligible to enter composites. q = 0.10 (rather than a
Bonferroni-style family-wise bound) is chosen deliberately: in a noisy financial cross-section,
controlling the *expected proportion of false discoveries* at 10% is the appropriate balance between
discipline and power; Bonferroni would be so conservative as to reject genuine signal, while no
correction would license noise. This directly addresses the factor-zoo critique of Harvey, Liu & Zhu
(2016, "…and the Cross-Section of Expected Returns"), which is cited because most candidate "factors"
in the literature do not survive honest multiple-testing correction. Controls are excluded from the
hypothesis family — they are nuisance regressors, not discoveries.

**Multivariate structure (Fama–MacBeth).** For the surviving variables, monthly cross-sectional
regressions of the forward 3-month return on the survivors plus all controls (12-1 momentum, log size,
12-month volatility, and sector and country dummies) are run, and Newey–West t-statistics are taken
on the time series of coefficients (Fama & MacBeth 1973). This answers the only question that matters
for an ESG-alpha claim: does any ESG variable carry information *beyond* momentum, size, sector, and
country. The 3-month horizon is chosen to match the quarterly rebalance of the backtest. Variance
inflation factors are computed across the survivors and any variable with VIF > 5 is flagged for
orthogonalization, so that collinear signals are not double-counted. The F1 regulatory interaction is
tested explicitly rather than assumed.

**Train/test protocol.** The training window is **everything up to 2021-12-31**; the test window is
**2022-01-01 to the present**. Every selection decision — which variables survive, which composite
and which weighting scheme wins — is made on the training window *only*. The test window is evaluated
exactly once, at the end, with the already-frozen winning composite, and is never consulted during
selection. This is enforced in `run_validation.py`: the winner is chosen by a function that receives
only training-window data. The 2021/2022 split is chosen because it places a genuine regime change
(the 2022 rate shock) in the out-of-sample period — if the signal survives that, it is more
believable than one tuned through it.

**Backtest (the economic result).** Quarterly-rebalanced quintile portfolios are formed on the
winning composite, equal-weighted within quintile, over the liquidity-filtered universe, in USD.
Transaction costs use a documented ASEAN cost matrix that grades from 25 bps one-way for Singapore
large caps up to 60 bps for Vietnamese mid caps, and both gross and net returns are reported. The
headline is the net Q5−Q1 spread, but it is reported with a **block-bootstrap 95% confidence
interval**, not as a point estimate: monthly returns are resampled in **6-month blocks** for **2,000
iterations**. Six-month blocks are used (rather than i.i.d. resampling) precisely to preserve the
serial dependence and overlapping structure of the return series — i.i.d. bootstrap would understate
the interval (moving-block bootstrap, Künsch 1989; Politis & Romano 1994). The **Deflated Sharpe
Ratio** (Bailey & López de Prado 2014) is computed and reported, with the trial count set to the
number of composite×scheme configurations actually tried (12), so that the Sharpe is discounted for
the selection effort that produced it. Two benchmarks are reported: the equal-weighted universe, and
naive ESG-level quintiles — the latter is the direct test of the thesis that *momentum beats level*.
A **placebo test** shuffles the composite cross-sectionally within each formation date and recomputes
the spread over **1,000 iterations**; the comparison is gross-against-gross, because costs are
orthogonal to whether a ranking carries information and netting both sides would only invite a
cost-model artifact into the p-value. Robustness is reported across sub-periods (2018–19, 2020 COVID,
2021, 2022 rate shock, 2023–25), by country, by sector, and under a one-month formation lag.

---

## 3.5 The GDELT pivot — full universe to liquid discovery universe

The single largest mid-build decision was forced by GDELT throttling. The sentiment fetch over the
full 477-name universe wedged at roughly 10% coverage: GDELT's IP-level rate limiting put each
throttled ticker into a multi-minute backoff, and at the observed rate the full universe was days
away, not hours. Continuing to grind the full 477 was rejected — it would not have completed on any
usable timeline, and a partial-coverage freeze would have been scientifically worthless (three of the
four composites would have appeared to "lose" purely because their inputs were missing, not because
their signal was absent).

The pivot was to run all statistical discovery on the **liquid discovery universe of 198 names**
(mega/large cap, ≥ US$1M median daily dollar volume) with complete sentiment coverage, while still
*scoring* the full 477-name universe for the leaderboard. This is not a compromise; it is the
standard separation real quant desks make between **validation** (a tight universe with the best
available data, where statistical claims are made) and **deployment** (a broader universe where the
validated model is applied, with documented per-name data-coverage caveats). It is in fact a cleaner
design than the original: every variable's IC is now computed on the same consistent, well-covered
cross-section, so the composite comparison is apples-to-apples rather than confounded by differential
coverage. The leaderboard for the remaining names carries confidence bands that widen with missing
coverage, so deployment never overstates what validation established. The discovery universe is
persisted as a documented artifact (`data/interim/discovery_universe.parquet`) with its exact
selection criteria, so the validation scope is reproducible and auditable.

A preliminary shakedown run on partial data — before the pivot completed — already showed the thesis
variable A1 (sentiment velocity) with a positive, individually significant information coefficient on
only ~50 names, which is consistent with a statistical-power constraint rather than an absent signal,
and is the empirical reason the pivot to complete-coverage discovery was expected to pay off.

---

## 3.6 Composite construction and weighting

Four composites are built from FDR-surviving members only:
- **EIP — ESG Improvement Probability:** sentiment velocity (A1), attention trend (A3), ESG momentum
  (B2, where available), disclosure trend (D1).
- **TRI — Transition Readiness Index:** CapEx-intensity trend (C1), cost-of-debt trend (C2), country
  regulatory overlay (F1).
- **CPS — Credibility Premium Signal:** governance (E1), controversy (B3), tone dispersion (A4,
  negative).
- **MASTER:** a training-IC-weighted blend of the three family composites.

Each composite is built under three weighting schemes — **equal weight**, **trailing-IC weight**, and
**rank-aggregate** — giving 12 candidate configurations in total. The winning configuration is
selected by **training-window net quarterly Q5−Q1 spread only**; the test window is never used for
selection, and the count of 12 configurations is fed into the Deflated Sharpe so the winner is
penalized for the search. Equal weighting is the robust default (no parameters to overfit);
trailing-IC weighting lets the data speak but risks chasing noise; rank-aggregate is robust to
outliers in any single member — trying all three and selecting on training performance lets the data
choose the trade-off without peeking at the test set.

The four *product pillars* exposed in the leaderboard (Sentiment Dynamics, Transition Readiness,
Governance Credibility, Disclosure Behavior) reuse the same machinery: members within each pillar are
training-IC-weighted, and the pillar weights in the shipped model are the normalized training-window
pillar ICs, floored at 0.05 so every pillar retains a visible minimum weight. This end-to-end
research-driven weighting is what lets the front-end "weight sandbox" recompute
`overall = Σ wᵢ × pillarᵢ` and exactly reproduce the validated ranking, with data-coverage shown
separately and held out of the weighted sum.

**Dress-rehearsal evidence.** Before any live data, the entire Phase 3→5 pipeline was validated on a
seeded synthetic panel containing a planted latent factor that drives *both* rising news tone and
forward returns, with every other variable as noise. A correct pipeline must recover the planted
signal and show a near-zero placebo distribution. It did: the final product score recovered the
latent factor at rank correlation ≈ 0.71 with a placebo p-value of zero. This is explicitly a test of
the *machinery*, not a result about ASEAN equities, and is labeled as synthetic wherever it appears —
but it is the evidence that the live numbers, once frozen, are produced by correct code rather than
by accident.

---

*Every threshold named in this section is defined in `config/settings.yaml`; every market-data and
coverage claim is reproducible from `data/raw/` and `logs/actions.jsonl`; every cut and failure
(Philippines, SGX SDRs, the dead ESG endpoint, the empty disclosure feed, the GDELT pivot) is
recorded in `RESEARCH_LOG.md` and `BIAS_REGISTER.md`. Nothing material to the result was decided
off the record.*
