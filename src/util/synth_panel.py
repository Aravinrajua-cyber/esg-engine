"""Seeded synthetic RAW panels for developing & unit-testing the scientific core.

This is a TEST fixture (Claude-owned), distinct from Codex's `src/fetchers/synthetic.py`
(which emits the site's companies.json). It writes schema-correct raw parquets into a target dir
with a *planted* signal: a latent per-company improvement factor theta drives BOTH a rising news
tone (so sentiment-velocity A1 ~ theta) AND a forward-return drift (so theta predicts returns).
Other variables are mostly noise. A correct pipeline must therefore recover A1 / the sentiment
composite as significant, show a positive net Q5-Q1 spread, and a placebo distribution near zero.

Run:  python -m src.util.synth_panel            # writes to data/_synth/
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

COUNTRIES = ["Singapore", "Indonesia", "Malaysia", "Thailand", "Vietnam"]
EXCH = {"Singapore": "SGX", "Indonesia": "IDX", "Malaysia": "Bursa",
        "Thailand": "SET", "Vietnam": "HOSE_HNX"}
SECTORS = ["Banking", "Industrials", "Consumer", "Energy", "Telecom", "Utilities", "REIT"]


def generate(out_dir: Path | str = ROOT / "data" / "_synth", n: int = 80, seed: int = 42) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)

    tickers = [f"SYN{i:03d}.SY" for i in range(n)]
    theta = rng.normal(0, 1, n)                       # latent ESG-improvement factor (the signal)
    country = rng.choice(COUNTRIES, n)
    sector = rng.choice(SECTORS, n)

    # ---- universe ----
    mcap = np.exp(rng.normal(22, 1.0, n))             # ~US$1-50bn
    uni = pd.DataFrame({
        "ticker": tickers, "name": [f"Synthetic Co {i}" for i in range(n)],
        "country": country, "exchange": [EXCH[c] for c in country], "sector": sector,
        "mcap_tier": np.where(mcap > 1e10, "mega", np.where(mcap > 2e9, "large", "mid")),
        "currency": "USD", "market_cap_usd": mcap, "free_float_pct": np.nan,
        "adv_usd": rng.uniform(5e5, 5e7, n), "liquidity_flag": False,
        "in_backtest": True, "source": "synthetic",
    })
    uni.to_parquet(out / "universe.parquet", index=False)

    # ---- daily prices with theta-driven drift + shared market + idiosyncratic noise ----
    days = pd.bdate_range("2016-06-01", "2026-06-12")          # extra history for 12m momentum
    nd = len(days)
    mkt = rng.normal(0.0004 / 1, 0.009, nd)                    # shared daily market return
    drift = 0.02 * theta / 21.0                                # monthly 0.02*theta spread over ~21d
    price_rows = []
    for j, tk in enumerate(tickers):
        idio = rng.normal(0, 0.013, nd)                        # noise -> momentum is a noisy theta proxy
        ret = drift[j] + mkt + idio
        close = 100 * np.cumprod(1 + ret)
        vol = rng.lognormal(13, 0.6, nd)
        price_rows.append(pd.DataFrame({"date": days, "ticker": tk,
                                        "close_local": close, "volume": vol, "close_usd": close}))
    prices = pd.concat(price_rows, ignore_index=True)
    prices.to_parquet(out / "prices_daily.parquet", index=False)

    fx = pd.DataFrame({"date": days, "currency": "USD", "fx_to_usd": 1.0})
    fx.to_parquet(out / "fx_daily.parquet", index=False)

    # ---- monthly sentiment: tone trends up with theta (=> 12m slope ~ theta) ----
    months = pd.date_range("2016-06-01", "2026-06-01", freq="MS")
    s_rows = []
    for j, tk in enumerate(tickers):
        idx = np.arange(len(months))
        tone = 0.04 * theta[j] * idx + rng.normal(0, 0.8, len(months))
        base_vol = np.exp(rng.normal(3.0, 0.5)) * (1 + 0.15 * theta[j])   # attention ~ theta (A3)
        article_vol = rng.poisson(np.maximum(base_vol * (1 + 0.02 * idx * max(theta[j], 0)), 1))
        s_rows.append(pd.DataFrame({"ticker": tk, "month": months, "avg_tone": tone,
                                    "article_volume": article_vol.astype(float),
                                    "obs_days": rng.integers(18, 31, len(months))}))
    pd.concat(s_rows, ignore_index=True).to_parquet(out / "sentiment_monthly.parquet", index=False)

    # ---- ESG snapshot: level largely independent of theta (the thesis: level is weak) ----
    esg = pd.DataFrame({
        "ticker": tickers, "retrieval_date": "2026-06-12",
        "esg_total_risk": rng.uniform(10, 40, n),
        "esg_e": rng.uniform(0, 15, n), "esg_s": rng.uniform(0, 15, n),
        "esg_g": rng.uniform(0, 15, n),
        "controversy_level": rng.integers(0, 5, n).astype(float),
    })
    # leave ~30% ESG missing (realistic ASEAN coverage)
    miss = rng.choice(n, int(0.3 * n), replace=False)
    esg.loc[miss, ["esg_total_risk", "esg_e", "esg_s", "esg_g", "controversy_level"]] = np.nan
    esg.to_parquet(out / "esg_snapshot.parquet", index=False)

    # ---- fundamentals: annual, capex/revenue mildly trends with theta (C1) ----
    f_rows = []
    for j, tk in enumerate(tickers):
        for y, yr in enumerate(range(2015, 2026)):
            rev = np.exp(rng.normal(20, 0.4)) * (1.05 ** y)
            capex_int = 0.08 + 0.01 * theta[j] * y + rng.normal(0, 0.01)
            f_rows.append({"ticker": tk, "fiscal_date": f"{yr}-12-31", "period": "annual",
                           "revenue": rev, "capex": max(capex_int, 0.01) * rev,
                           "total_debt": rev * rng.uniform(0.2, 0.8),
                           "interest_expense": rev * rng.uniform(0.005, 0.03),
                           "operating_cash_flow": rev * rng.uniform(0.05, 0.2),
                           "depreciation": rev * rng.uniform(0.02, 0.06)})
    pd.DataFrame(f_rows).to_parquet(out / "fundamentals.parquet", index=False)

    # ---- disclosures: quarterly counts, mild theta trend (D1) for SG/MY only ----
    q = pd.period_range("2017Q1", "2026Q1", freq="Q")
    d_rows = []
    for j, tk in enumerate(tickers):
        if country[j] not in ("Singapore", "Malaysia"):
            continue
        for k, per in enumerate(q):
            cnt = int(rng.poisson(max(0.05, 1 + 0.1 * theta[j] * k / 4)))
            d_rows.append({"ticker": tk, "quarter": per.to_timestamp().date().isoformat(),
                           "sustainability_announcement_count": cnt,
                           "last_announcement_date": per.to_timestamp().date().isoformat()})
    pd.DataFrame(d_rows).to_parquet(out / "disclosures_quarterly.parquet", index=False)

    # carry the latent factor for diagnostics (not consumed by the pipeline)
    pd.DataFrame({"ticker": tickers, "theta": theta}).to_parquet(out / "_truth_theta.parquet", index=False)
    print(f"synthetic panels written to {out} ({n} companies, {len(months)} months)")
    return out


if __name__ == "__main__":
    generate()
