# SCHEMAS.md — frozen data contracts (schema_version 1)

Single source of truth for every pipeline artifact. **Do not invent or rename columns.**
All dates ISO `YYYY-MM-DD`. All monetary comparisons in USD unless suffixed `_local`.
Missing = NaN/null (never imputed).

---

## data/raw + interim (parquet)

### universe.parquet  (Claude)
`ticker, name, country, exchange, sector, mcap_tier{mega|large|mid}, currency,
market_cap_usd, free_float_pct(nullable), adv_usd(median daily $ vol, 6m), liquidity_flag(bool),
in_backtest(bool), source{seed|screener}`

### prices_daily.parquet  (Codex: prices.py)
Long format: `date, ticker, close_local, volume, close_usd`
(close_usd = close_local × FX on date). 2014-01-01 → today, daily.

### fx_daily.parquet  (Codex: fx.py)
`date, currency, fx_to_usd`  (one row per currency per day; forward-fill weekends documented).

### esg_snapshot.parquet  (Codex: esg.py)
One row per ticker (single retrieval-stamped snapshot, NOT a history):
`ticker, retrieval_date, esg_total_risk, esg_e, esg_s, esg_g, controversy_level(0-5 nullable)`

### fundamentals.parquet  (Codex: fundamentals.py)
Long: `ticker, fiscal_date, period{annual|quarter}, revenue, capex, total_debt,
interest_expense, operating_cash_flow, depreciation`

### sentiment_monthly.parquet  (Claude: gdelt.py)
`ticker, month(YYYY-MM-01), article_volume, avg_tone, obs_days`

### disclosures_quarterly.parquet  (Codex: disclosures.py — best-effort, SGX/Bursa only)
`ticker, quarter(YYYY-Qn date), sustainability_announcement_count, last_announcement_date`

---

## data/processed (parquet)

### signal_panel.parquet  (Claude: signals/)
Long: `date(rebalance, month-end), ticker, variable, raw_value, z_value`
variable ∈ {A1,A2,A3,A4,B1,B2,B3,B4,C1,C2,C3,C4,D1,D2,E1,E2,F1, plus controls
mom_12_1, log_mcap, vol_12m}. z_value winsorized 1/99, z-scored within date, higher=better.

### returns_forward.parquet  (Claude)
`date, ticker, fwd_1m, fwd_3m, fwd_6m, fwd_12m` (USD; `_local` variants too).

### validation_results.json  (Claude) — drives report tables & some site charts
```
{ ic: [{variable, horizon, ic_mean, ic_std, t_nw, hit_rate, fdr_survived(bool)}],
  fama_macbeth: [{variable, coef, t_nw, p}],
  composites: [{name, train_ic, test_ic, train_spread, test_spread}],
  backtest: {winning_composite, gross, net, sharpe, sortino, max_dd, calmar,
             q5_q1_spread_net, spread_ci_low, spread_ci_high, turnover, deflated_sharpe},
  placebo: {realized_spread, placebo_mean, placebo_p, hist_bins[], hist_counts[]} }
```

---

## outputs/site_data/*.json (schema_version 1) — frontend contract

### companies.json  (Claude real / Codex synthetic) — PRIMARY frontend feed
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
     esg_level_pctile(0-100), esg_momentum_pctile(0-100),     // 2x2 axes
     pillar_scores: { sentiment_dynamics, transition_readiness,
                      governance_credibility, disclosure_behavior, data_coverage },  // each 0-100
     flags: ["LOW_COVERAGE"|"CONTROVERSY_RISING"|"LOW_LIQUIDITY"|"HIGH_VOL"|"STALE_DATA"],
     explanation: "Scored 81 (A): ...",            // one deterministic sentence
     timeseries: null | { dates:[], price_usd:[], sentiment_tone:[], score:[] }  // top names only
  }] }
```
**Weight sandbox:** frontend recomputes `overall = Σ weight_i × pillar_scores[i]` client-side
(data_coverage pillar is display-only, not in the weighted sum) and re-ranks. Reset = validated_weights.

### backtest.json (Claude): `{dates:[], q5:[], q1:[], benchmark:[], naive_esg_q5:[], net:bool, train_end_index:int}`
### ic_table.json (Claude): `[{variable, label, ic_3m, t_nw, fdr_survived}]`
### placebo.json (Claude): `{realized_spread, hist_bins:[], hist_counts:[]}`
### by_country.json / by_sector.json (Claude): `[{key, spread_net}]`

Codex's `synthetic.py` must emit companies.json (+ stub backtest/ic/placebo) matching the above
exactly, deterministic (seed 42), with `data_mode:"synthetic"` so the UI shows the watermark.
