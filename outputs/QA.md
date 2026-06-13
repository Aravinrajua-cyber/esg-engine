# QA — 25 judge questions, pre-written answers

> `‹FROZEN: …›` values come from `phase4_results.pkl` after the freeze. Keep answers to 2–4 sentences
> when delivered aloud; the extra context is for your own confidence.

## Methodology & statistics

**1. Why momentum, not level?**
Because the level is contested and the change is informative. We tested both: in monthly
Fama–MacBeth cross-sectional regressions of forward 3-month returns, controlling for momentum, size,
volatility, sector, and country, the ESG-*momentum* signals carry information **beyond** those
factors while the naive ESG *level* (B1) does not. The money chart shows the level-quintile line flat
against our momentum line. Level is a 0.54-correlation coin-flip (Berg et al. 2022); momentum is
observable.

**2. How do you know this isn't overfitting / data mining?**
Four guardrails. We applied **Benjamini–Hochberg FDR at q=0.10** across ~72 variable×horizon
hypotheses, so only honest survivors enter composites (Harvey, Liu & Zhu 2016). We selected the
winning composite on the **training window only** (≤2021-12-31) and touched 2022+ **exactly once**.
We report the **Deflated Sharpe Ratio**, which discounts for the 12 configurations we tried. And we
ran a 1,000-iteration placebo. If we were curve-fitting, the placebo and the DSR would expose it.

**3. What is the Deflated Sharpe Ratio and why should I trust it over a raw Sharpe?**
It's the probability that the observed Sharpe is real after accounting for how many strategies you
tried, the length of the track record, and the non-normality of returns (Bailey & López de Prado
2014). A raw Sharpe from 12 trials is inflated by selection; the DSR removes that inflation. Ours is
**‹FROZEN: deflated_sharpe›**.

**4. Why Newey–West standard errors?**
Because our forward returns overlap — a 3-month return observed monthly is autocorrelated by
construction — and ordinary standard errors would understate the noise and inflate the t-stats. The
Newey–West HAC correction with lag equal to the horizon is the standard, conservative fix.

**5. Why Benjamini–Hochberg specifically, and why q=0.10?**
BH controls the *expected proportion of false discoveries*, which is the right target when you're
screening many candidate signals. q=0.10 means we tolerate ~10% false positives among our
"discoveries" — disciplined without being so strict it rejects genuine signal. Bonferroni would kill
real effects in a noisy cross-section; no correction would license noise.

**6. Why 500 names, not a focused 30?**
Statistical power. The noise in a cross-sectional information coefficient scales like 1/√N, so moving
from 30 names to ~500 cuts the standard error by roughly **four times** (√(500/30) ≈ 4.1). Thirty
names can't distinguish signal from luck; breadth is what lets us make a multiple-testing-corrected
claim at all. We then *validate* on the 198 most liquid names — still ~2.5× the standard-error
advantage over 30, with clean, complete data.

**7. Why validate on 198 names but score 477?**
This is the standard validation-vs-deployment split. We make statistical claims only where the data
is complete and the names are genuinely tradeable (198 liquid names, full sentiment coverage), then
apply the frozen model to the full 477 for the leaderboard, with confidence bands that widen as
per-company coverage drops. Deployment never overstates what validation established.

**8. What's your out-of-sample test, and did you peek?**
Training is everything up to 2021-12-31; the test window is 2022-01-01 onward. Selection — which
variables survive, which composite and weighting scheme win — happens on training only, enforced in
code. The test window was evaluated once, at the end, with the already-frozen composite. The 2022
rate shock sits in that out-of-sample period deliberately.

## Data

**9. Your free ESG source died mid-build. Isn't that fatal?**
It's the opposite — it's our thesis made literal. Yahoo removed the free Sustainalytics endpoint
(it now 404s for every symbol, including Apple), so the official-score families are unavailable and
the model runs on **alternative data**: news-sentiment momentum, capital-allocation fundamentals, and
a regulatory overlay. Single-provider ESG dependence is a fragility (Berg et al. 2022) — we just
lived it. The CSV/API import path restores official ESG history the moment a licensed feed is plugged
in.

**10. Isn't GDELT news tone just noise?**
If it were pure noise it wouldn't survive FDR correction — and sentiment velocity (A1) is our core
surviving variable. We reduce entity-matching noise by stripping legal-form suffixes from company
queries, we require ≥9 of 12 monthly observations for a slope, and we winsorize before z-scoring.
Tone is noisy per-article; the 12-month *slope* across many articles is a stable signal.

**11. The disclosure family (D) is empty — why include it at all?**
The SGX/Bursa announcement feed returned zero rows in this run, so D1/D2 are unavailable and we say
so. It's specified and ready: when an exchange-announcement feed is supplied via the import layer, the
disclosure-trend variables activate without code changes. We'd rather ship a documented empty family
than a fabricated one.

**12. How do you handle missing data?**
Missing is missing — never imputed. A name absent from a variable simply doesn't enter that
variable's cross-section, its coverage is reported on its card, and its score confidence band widens.
The one exception is weekend FX forward-fill, which is documented, because a currency rate is
genuinely constant over a non-trading weekend.

**13. FX risk across five currencies?**
All returns are converted to USD at same-day FX before any comparison, so the cross-section is in one
numeraire. Residual FX exposure is a named market risk in the register; a USD-funded investor bears
it and we don't net it away silently.

**14. Scope 3 emissions gaps?**
Acknowledged and registered. Most ASEAN disclosure omits Scope 3, so any emissions-linked variable
systematically understates supply-chain exposure. Our live signal set doesn't lean on emissions
levels — it leans on sentiment and capital-allocation *trends* — which sidesteps the worst of the
Scope 3 gap, but we flag it rather than claim coverage we don't have.

## Product

**15. Is the score a black box?**
No. The overall score is a transparent weighted sum of four 0–100 pillar percentiles; the weights are
the research-validated weights and are exposed in a live sandbox; and every company gets a
deterministic, rule-based sentence naming its top two positive drivers and its main negative one. You
can re-derive any score by hand.

**16. What exactly is a "Hidden Winner"?**
The 2×2 splits ESG level against ESG momentum at the cross-sectional medians. A Hidden Winner is
**low level, high momentum** — unremarkable on a static scorecard but improving fast. That's the
category the level-focused market is slowest to reprice, and it's the product's hero quadrant.

**17. Can a company game these signals (greenwashing)?**
Disclosure-volume signals are the most gameable, which is why we cross-check: a firm can inflate
press releases, but it's much harder to simultaneously fake a rising news-tone *slope across
independent outlets* and a multi-year shift in capital expenditure. The fundamental and sentiment
families act as mutual checks.

**18. Is this investment advice?**
No, and we say so persistently — a fixed "research demonstration, not investment advice" disclaimer is
on the site and in the report, and the UI avoids action words like buy/sell/outperform. It's a
research screen.

## Risk & robustness

**19. Survivorship bias?**
Present by construction — today's constituents are yesterday's survivors — and registered (B-01,
citing Elton–Gruber–Blake). Direction: it overstates the absolute return of *all* quintiles, but the
Q5−Q1 *spread* is partially insulated because both legs are drawn from the same survivor set. We
report it as a modest upward bias on the spread, not a silent omission.

**20. Can you short in Indonesia (or Vietnam, Philippines)?**
Largely no — shorting is infeasible or impractical across much of ASEAN, so a long-short Q5−Q1
portfolio is partly theoretical. That's why our **implementable** headline is **long-only top-quintile
(Q5) versus the equal-weight benchmark**, reported net of costs alongside the spread. We don't claim a
short book we couldn't run.

**21. What about capacity and turnover — can this hold real AUM?**
The backtest universe is liquidity-filtered (≥US$250k median daily dollar volume; the validation
universe ≥US$1M), rebalanced only quarterly to limit turnover, and costed per market and cap tier.
Capacity is bounded by the liquid sleeve and is discussed explicitly; this is a research-desk screen,
not an uncapped strategy.

**22. How is this different from existing ESG-momentum work?**
ESG momentum has precedent (e.g. Nagy, Kassam & Lee 2016). What's new here is the combination:
**ASEAN** (where thin coverage means larger underreaction), an **alternative-data** construction that
survives a provider blackout, and a level of statistical hygiene — FDR, Deflated Sharpe, a placebo
test, a once-touched test window — that most submissions won't have.

## Business / CGS

**23. What does CGS's data actually unlock?**
Point-in-time ESG history. Today our ESG-momentum variable (B2) is proxied from alternative data
because no free point-in-time ESG history exists. With a licensed CGS/Sustainalytics-grade feed in the
import layer, B2 becomes a **true measured ESG-score change across the entire panel**, the official-
score families (B1, B3, B4, E1) come back online, and the same validation re-runs unchanged. It's the
single highest-leverage upgrade.

**24. How reproducible is this for your team?**
Every parameter is frozen in one config file with a fixed random seed; the whole submission —
report, deck, site — rebuilds with a single command (`python tools/submit/assemble_submission.py`);
and the pipeline is covered by a test suite including schema-contract and validation tests. Your
quants can re-run and audit it, not just take our word.

**25. What would you do with more time?**
In order: licensed point-in-time ESG history (the big unlock), supervised composite weighting,
expansion beyond 500 names, and intraday/higher-frequency sentiment. Each is additive to the existing
frozen contracts — none requires re-architecting what you saw today.
