"""Phase 4.3 — Fama-MacBeth cross-sectional regressions, VIF screen, F1 interaction test.

Monthly cross-sections of forward 3m USD returns on FDR-surviving variables + controls
(mom_12_1, log_mcap, vol_12m, sector & country dummies); Newey-West t-stats (lag = horizon)
on the time series of coefficients. Answers: do ESG variables carry information BEYOND
momentum / size / sector / country?

Training window only. Owned by Claude (the science).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.validation.ic import newey_west_tstat, nw_pvalue

CONTROLS = ["mom_12_1", "log_mcap", "vol_12m"]


def _cross_section(panel: pd.DataFrame, variables: list[str], date) -> pd.DataFrame:
    sub = panel[(panel["date"] == date) & (panel["variable"].isin(variables))]
    return sub.pivot_table(index="ticker", columns="variable", values="z_value", aggfunc="last")


def fama_macbeth(panel: pd.DataFrame, fwd: pd.DataFrame, universe: pd.DataFrame,
                 variables: list[str], horizon: int, train_end: str,
                 min_names: int = 30) -> pd.DataFrame:
    """Rows: variable, coef, t_nw, p, n_dates (controls included, dummies absorbed not reported)."""
    cut = pd.Timestamp(train_end)
    fwd = fwd.copy()
    fwd["date"] = pd.to_datetime(fwd["date"])
    panel = panel.copy()
    panel["date"] = pd.to_datetime(panel["date"])
    col = f"fwd_{horizon}m"
    meta = universe.set_index("ticker")[["sector", "country"]]
    regs = [v for v in variables if v not in CONTROLS] + CONTROLS
    coefs: dict[str, list[float]] = {v: [] for v in regs}
    dates_used = 0
    for t in sorted(panel["date"].unique()):
        if t > cut:
            continue
        X = _cross_section(panel, regs, t)
        if X.empty:
            continue
        y = fwd[fwd["date"] == t].set_index("ticker")[col]
        df = X.join(y, how="inner").join(meta, how="left").dropna(subset=[col])
        # demand full availability of regressors per name (no silent imputation)
        df = df.dropna(subset=[v for v in regs if v in df.columns])
        present = [v for v in regs if v in df.columns]
        if len(df) < max(min_names, 5 * (len(present) + 2)):
            continue
        dummies = pd.get_dummies(df[["sector", "country"]], drop_first=True, dtype=float)
        Xm = np.column_stack([np.ones(len(df)), df[present].to_numpy(float), dummies.to_numpy(float)])
        try:
            beta, *_ = np.linalg.lstsq(Xm, df[col].to_numpy(float), rcond=None)
        except np.linalg.LinAlgError:
            continue
        for j, v in enumerate(present, start=1):
            coefs[v].append(float(beta[j]))
        dates_used += 1
    rows = []
    for v in regs:
        c = np.array(coefs[v], dtype=float)
        if len(c) < 6:
            rows.append({"variable": v, "coef": np.nan, "t_nw": np.nan, "p": np.nan, "n_dates": len(c)})
            continue
        t_nw = newey_west_tstat(c, lag=horizon)
        rows.append({"variable": v, "coef": float(c.mean()), "t_nw": t_nw,
                     "p": nw_pvalue(t_nw), "n_dates": len(c)})
    return pd.DataFrame(rows)


def vif_table(panel: pd.DataFrame, variables: list[str], train_end: str) -> pd.DataFrame:
    """VIF on the pooled training-window z-matrix (z is already within-date standardized)."""
    cut = pd.Timestamp(train_end)
    p = panel.copy()
    p["date"] = pd.to_datetime(p["date"])
    p = p[(p["date"] <= cut) & (p["variable"].isin(variables))]
    wide = p.pivot_table(index=["date", "ticker"], columns="variable", values="z_value").dropna()
    if len(wide) < 50 or wide.shape[1] < 2:
        return pd.DataFrame({"variable": variables, "vif": np.nan})
    corr = wide.corr().to_numpy()
    try:
        inv = np.linalg.inv(corr)
        vifs = np.diag(inv)
    except np.linalg.LinAlgError:
        vifs = [np.nan] * len(wide.columns)
    return pd.DataFrame({"variable": wide.columns, "vif": [float(v) for v in vifs]})


def f1_interaction(panel: pd.DataFrame, fwd: pd.DataFrame, universe: pd.DataFrame,
                   composite_wide: pd.DataFrame, horizon: int, train_end: str) -> dict:
    """FM test of composite x F1 (country regulatory momentum): is the signal stronger in
    high-regulatory-momentum regimes? Reports the interaction coefficient + NW t."""
    cut = pd.Timestamp(train_end)
    fwd = fwd.copy()
    fwd["date"] = pd.to_datetime(fwd["date"])
    col = f"fwd_{horizon}m"
    f1 = panel[panel["variable"] == "F1"].pivot_table(index="date", columns="ticker",
                                                      values="z_value", aggfunc="last")
    coefs = []
    for t in composite_wide.index:
        ts = pd.Timestamp(t)
        if ts > cut or t not in f1.index:
            continue
        y = fwd[fwd["date"] == ts].set_index("ticker")[col]
        df = pd.DataFrame({"comp": composite_wide.loc[t], "f1": f1.loc[t]}).join(y, how="inner").dropna()
        if len(df) < 30:
            continue
        df["inter"] = df["comp"] * df["f1"]
        Xm = np.column_stack([np.ones(len(df)), df[["comp", "f1", "inter"]].to_numpy(float)])
        try:
            beta, *_ = np.linalg.lstsq(Xm, df[col].to_numpy(float), rcond=None)
        except np.linalg.LinAlgError:
            continue
        coefs.append(float(beta[3]))
    c = np.array(coefs, dtype=float)
    if len(c) < 6:
        return {"coef": None, "t_nw": None, "p": None, "n_dates": len(c)}
    t_nw = newey_west_tstat(c, lag=horizon)
    return {"coef": float(c.mean()), "t_nw": float(t_nw), "p": nw_pvalue(t_nw), "n_dates": len(c)}
