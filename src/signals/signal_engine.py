"""Phase 3 — signal engine. Pure functions of the raw panels -> signal_panel + forward returns.

Every variable is computed point-in-time (a signal at month t uses only data dated <= t; fundamentals
carry a 90-day publication lag). Snapshot-based ESG variables (B*, E1) are the documented exception
(BIAS_REGISTER B-02) and are excluded from the strict no-lookahead test. Within each rebalance date
every variable is winsorized 1/99, z-scored cross-sectionally, and sign-oriented so higher = better
expected return under the hypothesis.

API:  compute_signals(raw_dir, out_dir) -> writes signal_panel.parquet + returns_forward.parquet
Run:  python -m src.signals.signal_engine --raw data/_synth --out data/_synth   (synthetic test)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.util.log import log_action  # noqa: E402

# Sign orientation: +1 keep, -1 flip so that higher z = better expected return.
ORIENT = {
    "A1": +1, "A2": +1, "A3": +1, "A4": -1,
    "B1": -1, "B2": +1, "B3": -1, "B4": -1,
    "C1": +1, "C2": -1, "C3": +1, "C4": +1,
    "D1": +1, "D2": -1,
    "E1": -1, "F1": +1,
    "mom_12_1": +1, "log_mcap": +1, "vol_12m": +1,   # controls (orientation nominal)
}
SNAPSHOT_VARS = {"B1", "B2", "B3", "B4", "E1"}        # not point-in-time (snapshot) — see B-02


def _slope(a: np.ndarray, min_obs: int = 9) -> float:
    x = np.arange(len(a), dtype=float)
    m = ~np.isnan(a)
    if m.sum() < min_obs:
        return np.nan
    return float(np.polyfit(x[m], a[m], 1)[0])


def _roll_slope(wide: pd.DataFrame, window: int, min_obs: int) -> pd.DataFrame:
    return wide.rolling(window, min_periods=min_obs).apply(lambda a: _slope(a, min_obs), raw=True)


def _to_ts(period_index) -> pd.DatetimeIndex:
    return period_index.to_timestamp(how="start")


# ---------------------------------------------------------------- prices / returns / controls
def _monthly_close(prices: pd.DataFrame) -> pd.DataFrame:
    wide = prices.pivot_table(index="date", columns="ticker", values="close_usd", aggfunc="last")
    wide.index = pd.to_datetime(wide.index)
    m = wide.resample("ME").last()
    m.index = m.index.to_period("M")
    return m


def price_signals(prices: pd.DataFrame, universe: pd.DataFrame):
    mclose = _monthly_close(prices)
    mret = mclose.pct_change()
    mom = mclose.shift(1) / mclose.shift(13) - 1.0           # 12-1 momentum
    vol = mret.rolling(12, min_periods=9).std()
    fwd = {h: mclose.shift(-h) / mclose - 1.0 for h in (1, 3, 6, 12)}
    size = pd.Series(np.log(universe.set_index("ticker")["market_cap_usd"]), name="log_mcap")
    return mclose, mret, mom, vol, fwd, size


# ---------------------------------------------------------------- sentiment (A family)
def sentiment_signals(sent: pd.DataFrame) -> dict[str, pd.DataFrame]:
    sent = sent.copy()
    sent["month"] = pd.to_datetime(sent["month"]).dt.to_period("M")
    tone = sent.pivot_table(index="month", columns="ticker", values="avg_tone", aggfunc="mean")
    vol = sent.pivot_table(index="month", columns="ticker", values="article_volume", aggfunc="sum")
    logvol = np.log1p(vol)
    s12 = _roll_slope(tone, 12, 9)
    s6 = _roll_slope(tone, 6, 5)
    return {
        "A1": s12,
        "A2": s6 - s6.shift(6),
        "A3": _roll_slope(logvol, 12, 9),
        "A4": tone.rolling(12, min_periods=9).std(),
    }


# ---------------------------------------------------------------- ESG snapshot (B, E)
def esg_signals(esg: pd.DataFrame) -> pd.DataFrame:
    e = esg.set_index("ticker")
    out = pd.DataFrame(index=e.index)
    out["B1"] = e["esg_total_risk"]
    out["B2"] = np.nan                                       # momentum: no history -> missing
    out["B3"] = e["controversy_level"]
    out["B4"] = (e["esg_e"] - e["esg_g"]).abs()
    out["E1"] = e["esg_g"]
    return out


# ---------------------------------------------------------------- fundamentals (C family)
def fundamentals_signals(fund: pd.DataFrame) -> pd.DataFrame:
    f = fund[fund["period"] == "annual"].copy()
    f["fiscal_date"] = pd.to_datetime(f["fiscal_date"])
    f = f.sort_values(["ticker", "fiscal_date"])
    f["capex_int"] = f["capex"] / f["revenue"]
    f["cod"] = f["interest_expense"] / f["total_debt"]
    f["capex_dep"] = f["capex"] / f["depreciation"]
    g = f.groupby("ticker", group_keys=False)
    f["C1"] = f["capex_int"] - g["capex_int"].shift(3)
    f["C2"] = f["cod"] - g["cod"].shift(2)
    f["C3"] = (f["revenue"] / g["revenue"].shift(3)) ** (1 / 3) - 1
    f["C4"] = f["capex_dep"] - g["capex_dep"].shift(2)
    f["available_date"] = f["fiscal_date"] + pd.Timedelta(days=90)   # publication lag
    return f[["ticker", "available_date", "C1", "C2", "C3", "C4"]]


# ---------------------------------------------------------------- disclosures (D family)
def disclosure_signals(disc: pd.DataFrame, rebal_ts: pd.DatetimeIndex) -> pd.DataFrame:
    if disc is None or len(disc) == 0:
        return pd.DataFrame(columns=["date", "ticker", "D1", "D2"])
    d = disc.copy()
    d["quarter"] = pd.to_datetime(d["quarter"])
    d["last"] = pd.to_datetime(d["last_announcement_date"])
    rows = []
    for tk, sub in d.groupby("ticker"):
        sub = sub.sort_values("quarter")
        for t in rebal_ts:
            hist = sub[sub["quarter"] <= t]
            if hist.empty:
                continue
            last8 = hist.tail(8)["sustainability_announcement_count"].to_numpy(dtype=float)
            d1 = _slope(last8, min_obs=4) if len(last8) >= 4 else np.nan
            last_date = hist["last"].max()
            d2 = (t - last_date).days / 30.0 if pd.notna(last_date) else np.nan
            rows.append({"date": t, "ticker": tk, "D1": d1, "D2": d2})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- assembly
def _melt(wide: pd.DataFrame, var: str) -> pd.DataFrame:
    df = wide.copy()
    df.index = _to_ts(df.index) if isinstance(df.index, pd.PeriodIndex) else df.index
    out = df.reset_index(names="date").melt(id_vars="date", var_name="ticker", value_name="raw_value")
    out["variable"] = var
    return out.dropna(subset=["raw_value"])


def compute_signals(raw_dir: str | Path, out_dir: str | Path) -> pd.DataFrame:
    raw, out = Path(raw_dir), Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    universe = pd.read_parquet(raw / "universe.parquet")
    prices = pd.read_parquet(raw / "prices_daily.parquet")
    sent = pd.read_parquet(raw / "sentiment_monthly.parquet")
    esg = pd.read_parquet(raw / "esg_snapshot.parquet")
    fund = pd.read_parquet(raw / "fundamentals.parquet")
    disc = pd.read_parquet(raw / "disclosures_quarterly.parquet") if (raw / "disclosures_quarterly.parquet").exists() else None
    creg = pd.read_parquet(ROOT / "data" / "interim" / "country_regulatory.parquet")

    mclose, mret, mom, vol, fwd, size = price_signals(prices, universe)
    # rebalance dates: months with >=12m history and at least a 1m forward return
    rebal = mclose.index[(mclose.notna().sum(axis=1) > 0)]
    rebal = rebal[12:-1]                                     # drop warmup + last (no fwd)
    rebal_ts = _to_ts(rebal)

    frames = []
    # A family
    for var, wide in sentiment_signals(sent).items():
        frames.append(_melt(wide.loc[wide.index.isin(rebal)], var))
    # price controls
    frames.append(_melt(mom.loc[mom.index.isin(rebal)], "mom_12_1"))
    frames.append(_melt(vol.loc[vol.index.isin(rebal)], "vol_12m"))
    # size (static) broadcast to all rebalance dates
    size_long = pd.DataFrame([(t, tk, v) for tk, v in size.items() for t in rebal_ts],
                             columns=["date", "ticker", "raw_value"])
    size_long["variable"] = "log_mcap"
    frames.append(size_long.dropna(subset=["raw_value"]))
    # B/E snapshot (constant across dates)
    esgs = esg_signals(esg)
    for var in ["B1", "B2", "B3", "B4", "E1"]:
        s = esgs[var].dropna()
        if s.notna().any():
            long = pd.DataFrame([(t, tk, s[tk]) for tk in s.index for t in rebal_ts],
                                columns=["date", "ticker", "raw_value"])
            long["variable"] = var
            frames.append(long.dropna(subset=["raw_value"]))
    # C family — point-in-time via merge_asof on availability date
    csig = fundamentals_signals(fund)
    for var in ["C1", "C2", "C3", "C4"]:
        rows = []
        for tk, sub in csig.groupby("ticker"):
            sub = sub.dropna(subset=[var]).sort_values("available_date")
            if sub.empty:
                continue
            asof = pd.merge_asof(pd.DataFrame({"date": rebal_ts}), sub[["available_date", var]],
                                 left_on="date", right_on="available_date", direction="backward")
            asof["ticker"] = tk
            rows.append(asof[["date", "ticker", var]].rename(columns={var: "raw_value"}))
        if rows:
            cc = pd.concat(rows, ignore_index=True).dropna(subset=["raw_value"])
            cc["variable"] = var
            frames.append(cc)
    # D family
    dsig = disclosure_signals(disc, rebal_ts)
    for var in ["D1", "D2"]:
        if var in dsig.columns:
            dd = dsig[["date", "ticker", var]].rename(columns={var: "raw_value"}).dropna(subset=["raw_value"])
            dd["variable"] = var
            frames.append(dd)
    # F1 country regulatory (broadcast by country)
    cmap = creg.set_index("country")["reg_momentum_index"].to_dict()
    f1 = universe[["ticker", "country"]].copy()
    f1["raw_value"] = f1["country"].map(cmap)
    f1 = pd.DataFrame([(t, r.ticker, r.raw_value) for r in f1.itertuples() for t in rebal_ts],
                      columns=["date", "ticker", "raw_value"])
    f1["variable"] = "F1"
    frames.append(f1.dropna(subset=["raw_value"]))

    panel = pd.concat(frames, ignore_index=True)
    panel = _winsorize_zscore(panel)
    panel = panel[["date", "ticker", "variable", "raw_value", "z_value"]].sort_values(
        ["date", "variable", "ticker"]).reset_index(drop=True)
    panel.to_parquet(out / "signal_panel.parquet", index=False)

    # forward returns
    fwd_long = []
    for h, wide in fwd.items():
        w = wide.loc[wide.index.isin(rebal)]
        m = _melt(w, f"fwd_{h}m").rename(columns={"raw_value": f"fwd_{h}m"}).drop(columns="variable")
        fwd_long.append(m.set_index(["date", "ticker"]))
    fwd_df = pd.concat(fwd_long, axis=1).reset_index()
    fwd_df.to_parquet(out / "returns_forward.parquet", index=False)

    log_action("phase3", "signals_computed", {"raw_dir": str(raw)},
               {"panel_rows": len(panel), "variables": sorted(panel["variable"].unique()),
                "dates": panel["date"].nunique(), "tickers": panel["ticker"].nunique()})
    print(f"signal_panel: {len(panel)} rows, {panel['variable'].nunique()} variables, "
          f"{panel['date'].nunique()} dates, {panel['ticker'].nunique()} tickers")
    return panel


def _winsorize_zscore(panel: pd.DataFrame) -> pd.DataFrame:
    panel = panel.copy()
    x = panel["raw_value"].astype(float)
    g = panel.assign(_x=x).groupby(["date", "variable"])["_x"]
    xw = x.clip(g.transform(lambda s: s.quantile(0.01)), g.transform(lambda s: s.quantile(0.99)))
    gw = panel.assign(_xw=xw).groupby(["date", "variable"])["_xw"]
    sd = gw.transform(lambda s: s.std(ddof=0))
    z = ((xw - gw.transform("mean")) / sd.where(sd > 0)).fillna(0.0)
    panel["z_value"] = z * panel["variable"].map(ORIENT).fillna(1).astype(float)
    return panel


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--out", default="data/processed")
    args = ap.parse_args()
    compute_signals(args.raw, args.out)
