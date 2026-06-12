"""Phase 4.6 — quintile backtest with ASEAN cost matrix, bootstrap CI, DSR, placebo, robustness.

Quarterly-rebalanced quintile portfolios on a composite z (date x ticker), equal weight within
quintile, liquidity-filtered universe (in_backtest & not liquidity-flagged), USD returns via the
fwd_3m panel. Costs: one-way bps by country x mcap_tier (settings: backtest.costs_one_way_bps)
charged on traded weight per leg. All annualization assumes 4 non-overlapping quarterly periods.

Owned by Claude (the science).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats as sps

EULER_MASCHERONI = 0.5772156649
MIN_GROUP_NAMES = 25          # min eligible names for within-group (country/sector) quintiles
MIN_QUINTILE_NAMES = 4        # min names per quintile bucket at a formation date


# ------------------------------------------------------------------ portfolio mechanics
def formation_dates(z_wide: pd.DataFrame, fwd3_wide: pd.DataFrame, hold_months: int) -> list:
    """Every hold_months-th rebalance date with both signal and forward return (non-overlapping)."""
    dates = sorted(z_wide.index.intersection(fwd3_wide.index))
    return dates[::hold_months]


def _cost_bps(universe: pd.DataFrame, cost_matrix: dict) -> pd.Series:
    cmap = {"Singapore": "SG", "Indonesia": "ID", "Malaysia": "MY",
            "Thailand": "TH", "Philippines": "PH", "Vietnam": "VN"}
    def one(row):
        cc = cmap.get(row["country"], row["country"])
        tier = row["mcap_tier"] if row["mcap_tier"] in ("mega", "large", "mid") else "mid"
        return float(cost_matrix.get(cc, {}).get(tier, max(
            v for m in cost_matrix.values() for v in m.values())))
    return pd.Series(universe.apply(one, axis=1).values, index=universe["ticker"].values)


def quintile_backtest(z_wide: pd.DataFrame, fwd3_wide: pd.DataFrame, universe: pd.DataFrame,
                      settings: dict, eligible: pd.Index | None = None,
                      dates: list | None = None) -> dict:
    """Run the quintile machine. Returns period-level series (gross & net) + holdings history."""
    bt = settings["backtest"]
    nq = bt["quintiles"]
    if eligible is None:
        eligible = pd.Index(universe.loc[universe["in_backtest"] & ~universe["liquidity_flag"],
                                         "ticker"].unique())
    bps = _cost_bps(universe, bt["costs_one_way_bps"])
    if dates is None:
        dates = formation_dates(z_wide, fwd3_wide, bt["hold_months"])
    rec = {"date": [], "q5": [], "q1": [], "bench": [], "q5_cost": [], "q1_cost": [],
           "turnover": [], "quintile_means": []}
    prev = {"q5": set(), "q1": set()}
    for t in dates:
        if t not in z_wide.index or t not in fwd3_wide.index:
            continue
        z = z_wide.loc[t].reindex(eligible)
        f = fwd3_wide.loc[t].reindex(eligible)
        m = z.notna() & f.notna()
        if m.sum() < nq * MIN_QUINTILE_NAMES:
            continue
        z, f = z[m], f[m]
        try:
            q = pd.qcut(z.rank(method="first"), nq, labels=False) + 1
        except ValueError:
            continue
        qmeans = [float(f[q == k].mean()) for k in range(1, nq + 1)]
        legs, costs, turnovers = {}, {}, {}
        for leg, k in (("q5", nq), ("q1", 1)):
            names = set(z.index[q == k])
            n_new = len(names)
            entered = names - prev[leg]               # first period: entered == names (full entry)
            exited = prev[leg] - names
            # cost = sum of traded weights x per-name one-way bps (equal weights within leg)
            cost = sum(bps.get(nm, bps.mean()) for nm in entered) / max(n_new, 1) / 1e4
            if prev[leg]:
                cost += sum(bps.get(nm, bps.mean()) for nm in exited) / len(prev[leg]) / 1e4
            legs[leg] = float(f[q == k].mean())
            costs[leg] = cost
            turnovers[leg] = len(entered) / max(n_new, 1)
            prev[leg] = names
        rec["date"].append(pd.Timestamp(t))
        rec["q5"].append(legs["q5"]); rec["q1"].append(legs["q1"])
        rec["bench"].append(float(f.mean()))
        rec["q5_cost"].append(costs["q5"]); rec["q1_cost"].append(costs["q1"])
        rec["quintile_means"].append(qmeans)
        rec["turnover"].append(turnovers["q5"])       # one-way replaced fraction, long leg
    df = pd.DataFrame({k: v for k, v in rec.items() if k != "quintile_means"})
    df["spread_gross"] = df["q5"] - df["q1"]
    df["spread_net"] = df["spread_gross"] - df["q5_cost"] - df["q1_cost"]
    df["q5_net"] = df["q5"] - df["q5_cost"]
    return {"periods": df, "quintile_means": rec["quintile_means"]}


# ------------------------------------------------------------------ metrics
def annualize(period_returns: pd.Series, periods_per_year: int = 4) -> dict:
    r = period_returns.dropna()
    if len(r) < 4:
        return {k: None for k in ("ann_return", "ann_vol", "sharpe", "sortino",
                                  "max_dd", "calmar", "n_periods")}
    ann_ret = float(r.mean() * periods_per_year)
    ann_vol = float(r.std(ddof=1) * np.sqrt(periods_per_year))
    downside = r[r < 0]
    dvol = float(downside.std(ddof=1) * np.sqrt(periods_per_year)) if len(downside) > 1 else np.nan
    nav = (1 + r).cumprod()
    dd = float((nav / nav.cummax() - 1).min())
    return {"ann_return": ann_ret, "ann_vol": ann_vol,
            "sharpe": ann_ret / ann_vol if ann_vol > 0 else None,
            "sortino": ann_ret / dvol if dvol and dvol > 0 else None,
            "max_dd": dd, "calmar": ann_ret / abs(dd) if dd < 0 else None,
            "n_periods": int(len(r))}


def block_bootstrap_ci(period_returns: pd.Series, block_periods: int, iterations: int,
                       ci: float, periods_per_year: int = 4, seed: int = 42) -> tuple[float, float]:
    """CI on the ANNUALIZED mean via circular block bootstrap of the period series."""
    r = period_returns.dropna().to_numpy()
    n = len(r)
    if n < block_periods * 2:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    nblocks = int(np.ceil(n / block_periods))
    means = np.empty(iterations)
    for i in range(iterations):
        starts = rng.integers(0, n, nblocks)
        idx = (starts[:, None] + np.arange(block_periods)[None, :]).ravel() % n
        means[i] = r[idx[:n]].mean() * periods_per_year
    lo, hi = np.percentile(means, [(1 - ci) / 2 * 100, (1 + ci) / 2 * 100])
    return float(lo), float(hi)


def deflated_sharpe(period_returns: pd.Series, trial_sharpes: list[float],
                    periods_per_year: int = 4) -> float | None:
    """Bailey & Lopez de Prado (2014). Inputs: the winner's period return series and the
    per-period Sharpe ratios of ALL configs trialed (selection universe). Returns DSR in [0,1]."""
    r = period_returns.dropna().to_numpy()
    T = len(r)
    if T < 8 or len(trial_sharpes) < 2:
        return None
    sr = r.mean() / r.std(ddof=1)                       # per-period Sharpe of the winner
    g3 = float(sps.skew(r))
    g4 = float(sps.kurtosis(r, fisher=False))
    trials = np.array([s for s in trial_sharpes if np.isfinite(s)])
    var_sr = trials.var(ddof=1)
    n = len(trials)
    if var_sr <= 0 or n < 2:
        return None
    z1 = sps.norm.ppf(1 - 1 / n)
    z2 = sps.norm.ppf(1 - 1 / (n * np.e))
    sr0 = np.sqrt(var_sr) * ((1 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2)
    denom = np.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2, 1e-12))
    return float(sps.norm.cdf((sr - sr0) * np.sqrt(T - 1) / denom))


# ------------------------------------------------------------------ placebo + robustness
def placebo_test(z_wide: pd.DataFrame, fwd3_wide: pd.DataFrame, universe: pd.DataFrame,
                 settings: dict, realized_gross_spread: float, iterations: int,
                 seed: int = 42, bins: int = 30) -> dict:
    """Shuffle the composite cross-sectionally within each formation date and recompute the
    annualized GROSS Q5-Q1 spread. Gross-vs-gross is the clean information-content comparison
    (costs are orthogonal to whether the ranking carries signal; documented in RESEARCH_LOG).
    p = share of placebo spreads >= the realized gross spread (one-sided)."""
    bt = settings["backtest"]
    nq = bt["quintiles"]
    eligible = pd.Index(universe.loc[universe["in_backtest"] & ~universe["liquidity_flag"],
                                     "ticker"].unique())
    rng = np.random.default_rng(seed)
    # pre-extract the valid forward-return vector per formation date (names with signal + return)
    per_date = []
    for t in formation_dates(z_wide, fwd3_wide, bt["hold_months"]):
        z = z_wide.loc[t].reindex(eligible)
        f = fwd3_wide.loc[t].reindex(eligible)
        vals = f[z.notna() & f.notna()].to_numpy(float)
        if len(vals) >= nq * MIN_QUINTILE_NAMES:
            per_date.append(vals)
    if not per_date:
        return {"realized_spread": realized_gross_spread, "placebo_mean": None, "placebo_p": None,
                "hist_bins": [], "hist_counts": []}
    spreads = np.empty(iterations)
    for i in range(iterations):
        acc = 0.0
        for vals in per_date:
            k = len(vals) // nq
            perm = rng.permutation(vals)
            acc += perm[-k:].mean() - perm[:k].mean()    # random Q5 minus random Q1
        spreads[i] = acc / len(per_date) * 4             # annualized
    counts, edges = np.histogram(spreads, bins=bins)
    p = float((spreads >= realized_gross_spread).mean())
    return {"realized_spread": realized_gross_spread, "placebo_mean": float(spreads.mean()),
            "placebo_p": p, "hist_bins": [float(x) for x in edges],
            "hist_counts": [int(c) for c in counts]}


def group_spreads(z_wide: pd.DataFrame, fwd3_wide: pd.DataFrame, universe: pd.DataFrame,
                  settings: dict, group_col: str) -> list[dict]:
    """Net Q5-Q1 annualized spread within each country / sector (skipped below MIN_GROUP_NAMES)."""
    out = []
    for key, sub in universe.groupby(group_col):
        elig = pd.Index(sub.loc[sub["in_backtest"] & ~sub["liquidity_flag"], "ticker"].unique())
        if len(elig) < MIN_GROUP_NAMES:
            continue
        res = quintile_backtest(z_wide, fwd3_wide, universe, settings, eligible=elig)
        s = res["periods"]["spread_net"]
        if len(s) >= 4:
            out.append({"key": str(key), "spread_net": float(s.mean() * 4)})
    return out


def subperiod_spreads(periods: pd.DataFrame, spans: dict[str, tuple[str, str]]) -> list[dict]:
    out = []
    for label, (a, b) in spans.items():
        m = (periods["date"] >= pd.Timestamp(a)) & (periods["date"] <= pd.Timestamp(b))
        s = periods.loc[m, "spread_net"]
        out.append({"period": label,
                    "spread_net": float(s.mean() * 4) if len(s) >= 2 else None,
                    "n_quarters": int(len(s))})
    return out


def formation_lag_spread(z_wide: pd.DataFrame, fwd3_wide: pd.DataFrame, universe: pd.DataFrame,
                         settings: dict, lag_months: int) -> float | None:
    """Skip lag_months between signal observation and portfolio formation (staleness check)."""
    rebal = sorted(z_wide.index)
    if len(rebal) <= lag_months or lag_months < 1:
        return None
    # signal observed at rebal[i] is not acted on until rebal[i + lag] (stale-signal stress)
    lagged = z_wide.loc[rebal[:-lag_months]].copy()
    lagged.index = pd.Index(rebal[lag_months:])
    res = quintile_backtest(lagged, fwd3_wide, universe, settings)
    s = res["periods"]["spread_net"]
    return float(s.mean() * 4) if len(s) >= 4 else None
