"""Phase 4.1/4.2 — univariate IC screening with Newey-West t-stats and Benjamini-Hochberg FDR.

For each variable x horizon: monthly Spearman rank IC of the within-date z-score against forward
USD returns; the IC time series is summarized by mean, std, NW-corrected t-stat (lag = horizon,
overlapping returns), hit rate. BH-FDR at q (settings: validation.fdr_q) is applied across ALL
variable-x-horizon hypotheses jointly — the factor-zoo discipline (Harvey, Liu & Zhu 2016).

All discovery statistics are computed on the TRAINING window only (dates <= dates.train_end).

Owned by Claude (the science). Pure functions; no I/O besides the caller's.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps


def newey_west_tstat(x: np.ndarray, lag: int) -> float:
    """t-stat of mean(x) with Newey-West (Bartlett kernel) HAC standard error."""
    x = np.asarray(x, dtype=float)
    x = x[~np.isnan(x)]
    n = len(x)
    if n < 3:
        return np.nan
    e = x - x.mean()
    gamma0 = float(e @ e) / n
    var = gamma0
    for l in range(1, min(lag, n - 1) + 1):
        cov = float(e[l:] @ e[:-l]) / n
        var += 2.0 * (1.0 - l / (lag + 1.0)) * cov
    if var <= 0:
        return np.nan
    se = np.sqrt(var / n)
    return float(x.mean() / se)


def nw_pvalue(t: float) -> float:
    """Two-sided p-value from a NW t-stat (normal approximation)."""
    if np.isnan(t):
        return np.nan
    return float(2.0 * (1.0 - sps.norm.cdf(abs(t))))


def ic_series(z_wide: pd.DataFrame, fwd_wide: pd.DataFrame, min_names: int = 10) -> pd.Series:
    """Per-date Spearman IC between two date x ticker frames (aligned)."""
    out = {}
    common_dates = z_wide.index.intersection(fwd_wide.index)
    for t in common_dates:
        a, b = z_wide.loc[t], fwd_wide.loc[t]
        m = a.notna() & b.notna()
        if m.sum() < min_names or a[m].nunique() < 2 or b[m].nunique() < 2:
            continue
        rho = sps.spearmanr(a[m], b[m]).statistic
        if not np.isnan(rho):
            out[t] = rho
    return pd.Series(out, dtype=float).sort_index()


def _pivot(panel: pd.DataFrame, variable: str) -> pd.DataFrame:
    sub = panel[panel["variable"] == variable]
    return sub.pivot_table(index="date", columns="ticker", values="z_value", aggfunc="last")


def univariate_table(panel: pd.DataFrame, fwd: pd.DataFrame, horizons: list[int],
                     train_end: str | None = None) -> pd.DataFrame:
    """IC summary rows: variable, horizon, ic_mean, ic_std, t_nw, hit_rate, p."""
    fwd = fwd.copy()
    fwd["date"] = pd.to_datetime(fwd["date"])
    panel = panel.copy()
    panel["date"] = pd.to_datetime(panel["date"])
    if train_end:
        cut = pd.Timestamp(train_end)
        panel = panel[panel["date"] <= cut]
        fwd = fwd[fwd["date"] <= cut]
    rows = []
    for var in sorted(panel["variable"].unique()):
        z = _pivot(panel, var)
        for h in horizons:
            col = f"fwd_{h}m"
            if col not in fwd.columns:
                continue
            f = fwd.pivot_table(index="date", columns="ticker", values=col, aggfunc="last")
            s = ic_series(z, f)
            if len(s) < 6:
                rows.append({"variable": var, "horizon": h, "ic_mean": np.nan, "ic_std": np.nan,
                             "t_nw": np.nan, "hit_rate": np.nan, "p": np.nan, "n_dates": len(s)})
                continue
            t = newey_west_tstat(s.to_numpy(), lag=h)
            rows.append({"variable": var, "horizon": h,
                         "ic_mean": float(s.mean()), "ic_std": float(s.std(ddof=1)),
                         "t_nw": t, "hit_rate": float((s > 0).mean()),
                         "p": nw_pvalue(t), "n_dates": len(s)})
    return pd.DataFrame(rows)


def apply_bh_fdr(table: pd.DataFrame, q: float, exclude_vars: set[str] | None = None) -> pd.DataFrame:
    """Benjamini-Hochberg across all testable rows jointly. Controls are excluded from the
    hypothesis family (they are not sold as ESG alpha) but kept in the table for reference."""
    exclude_vars = exclude_vars or set()
    t = table.copy()
    t["fdr_survived"] = False
    mask = t["p"].notna() & ~t["variable"].isin(exclude_vars)
    p = t.loc[mask, "p"].to_numpy()
    if len(p) == 0:
        return t
    order = np.argsort(p)
    m = len(p)
    thresh_rank = 0
    for rank, idx in enumerate(order, start=1):
        if p[idx] <= q * rank / m:
            thresh_rank = rank
    if thresh_rank > 0:
        cutoff = p[order[thresh_rank - 1]]
        t.loc[mask, "fdr_survived"] = t.loc[mask, "p"] <= cutoff
    return t
