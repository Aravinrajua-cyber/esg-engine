"""Phase 4.4/4.5 — composite construction, weighting schemes, walk-forward stability.

Composites (master prompt 4.4), built from FDR-surviving members only:
  EIP — ESG Improvement Probability : A1 sentiment velocity, A3 attention trend,
                                      B2 ESG momentum (where it exists), D1 disclosure trend
  TRI — Transition Readiness Index  : C1 capex-intensity trend, C2 cost-of-debt trend, F1 country overlay
  CPS — Credibility Premium Signal  : E1 governance, B3 controversy, A4 tone dispersion
  MASTER                            : train-IC-weighted blend of EIP + TRI + CPS

Weighting schemes per composite: equal | trailing-IC | rank-aggregate. Selection of the winning
(composite, scheme) config uses TRAINING-window annualized gross Q5-Q1 spread ONLY; the test
window is never consulted here. Total configs trialed (feeds the Deflated Sharpe) = len(FAMILIES
incl. MASTER) x len(SCHEMES).

Pillar composites (product layer, Phase 5) reuse the same machinery over full families
(display granularity, not selection): see PILLARS.

Owned by Claude (the science).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.validation.ic import ic_series

FAMILIES: dict[str, list[str]] = {
    "EIP": ["A1", "A3", "B2", "D1"],
    "TRI": ["C1", "C2", "F1"],
    "CPS": ["E1", "B3", "A4"],
}
SCHEMES = ["equal", "trailing_ic", "rank_agg"]

PILLARS: dict[str, list[str]] = {
    "sentiment_dynamics": ["A1", "A2", "A3", "A4"],
    "transition_readiness": ["C1", "C2", "C3", "C4", "F1"],
    "governance_credibility": ["E1", "B3", "B4"],
    "disclosure_behavior": ["D1", "D2"],
}


def _z_wide(panel: pd.DataFrame, variable: str) -> pd.DataFrame:
    sub = panel[panel["variable"] == variable]
    return sub.pivot_table(index="date", columns="ticker", values="z_value", aggfunc="last")


def _rezscore(wide: pd.DataFrame) -> pd.DataFrame:
    mu = wide.mean(axis=1)
    sd = wide.std(axis=1, ddof=0).replace(0, np.nan)
    return wide.sub(mu, axis=0).div(sd, axis=0)


def combine(panel: pd.DataFrame, members: list[str],
            weights: dict[str, float] | None = None,
            scheme: str = "equal", min_members: int = 1) -> pd.DataFrame:
    """date x ticker composite z. Missing members are skipped per name (weights renormalized over
    what is available); names with < min_members observed members are NaN. Re-z-scored within date."""
    wides = {v: _z_wide(panel, v) for v in members}
    wides = {v: w for v, w in wides.items() if not w.empty}
    if not wides:
        return pd.DataFrame()
    if scheme == "rank_agg":
        wides = {v: w.rank(axis=1, pct=True) for v, w in wides.items()}
    idx = sorted(set().union(*[w.index for w in wides.values()]))
    cols = sorted(set().union(*[w.columns for w in wides.values()]))
    num = pd.DataFrame(0.0, index=idx, columns=cols)
    den = pd.DataFrame(0.0, index=idx, columns=cols)
    cnt = pd.DataFrame(0, index=idx, columns=cols)
    for v, w in wides.items():
        wt = (weights or {}).get(v, 1.0)
        if wt <= 0:
            continue
        a = w.reindex(index=idx, columns=cols)
        m = a.notna()
        num += (a.fillna(0.0)) * wt
        den += m.astype(float) * wt
        cnt += m.astype(int)
    out = num / den.replace(0, np.nan)
    out = out.where(cnt >= min_members)
    return _rezscore(out)


def train_ic_weights(panel: pd.DataFrame, fwd3_wide: pd.DataFrame, members: list[str],
                     train_end: pd.Timestamp, floor: float = 0.0) -> dict[str, float]:
    """Member weights proportional to training-window mean 3m IC, floored at `floor`.
    Falls back to equal weights if everything floors out."""
    w = {}
    for v in members:
        z = _z_wide(panel, v)
        z = z.loc[z.index <= train_end]
        s = ic_series(z, fwd3_wide.loc[fwd3_wide.index <= train_end])
        w[v] = max(float(s.mean()) if len(s) >= 6 else 0.0, floor)
    tot = sum(w.values())
    if tot <= 0:
        return {v: 1.0 / len(members) for v in members}
    return {v: x / tot for v, x in w.items()}


def build_composite(panel: pd.DataFrame, fwd3_wide: pd.DataFrame, members: list[str],
                    scheme: str, train_end: pd.Timestamp) -> pd.DataFrame:
    if scheme == "equal":
        return combine(panel, members, scheme="equal")
    if scheme == "rank_agg":
        return combine(panel, members, scheme="rank_agg")
    if scheme == "trailing_ic":
        w = train_ic_weights(panel, fwd3_wide, members, train_end)
        return combine(panel, members, weights=w)
    raise ValueError(f"unknown scheme {scheme}")


def build_all_configs(panel: pd.DataFrame, fwd3_wide: pd.DataFrame, survivors: set[str],
                      train_end: pd.Timestamp) -> tuple[dict[str, pd.DataFrame], dict]:
    """Every (family, scheme) config from FDR-surviving members + MASTER blends.
    Returns ({config_name: date x ticker z}, decisions metadata)."""
    eff = {name: [v for v in mem if v in survivors] for name, mem in FAMILIES.items()}
    decisions = {"members_after_fdr": eff, "n_configs": 0}
    configs: dict[str, pd.DataFrame] = {}
    for name, members in eff.items():
        if not members:
            continue
        for scheme in SCHEMES:
            configs[f"{name}_{scheme}"] = build_composite(panel, fwd3_wide, members, scheme, train_end)
    # MASTER: train-IC-weighted blend of the three family composites (equal-scheme versions)
    fam_avail = [n for n in FAMILIES if f"{n}_equal" in configs]
    if len(fam_avail) >= 2:
        fam_ics = {}
        for n in fam_avail:
            z = configs[f"{n}_equal"]
            s = ic_series(z.loc[z.index <= train_end], fwd3_wide.loc[fwd3_wide.index <= train_end])
            fam_ics[n] = max(float(s.mean()) if len(s) >= 6 else 0.0, 0.0)
        tot = sum(fam_ics.values()) or 1.0
        fam_w = {n: v / tot for n, v in fam_ics.items()}
        decisions["master_family_weights"] = fam_w
        for scheme in SCHEMES:
            parts = {n: configs[f"{n}_{scheme}"] for n in fam_avail}
            idx = sorted(set().union(*[p.index for p in parts.values()]))
            cols = sorted(set().union(*[p.columns for p in parts.values()]))
            num = pd.DataFrame(0.0, index=idx, columns=cols)
            den = pd.DataFrame(0.0, index=idx, columns=cols)
            for n, p in parts.items():
                a = p.reindex(index=idx, columns=cols)
                num += a.fillna(0.0) * fam_w[n]
                den += a.notna().astype(float) * fam_w[n]
            configs[f"MASTER_{scheme}"] = _rezscore(num / den.replace(0, np.nan))
    decisions["n_configs"] = len(configs)
    return configs, decisions


def walk_forward(panel: pd.DataFrame, fwd3_wide: pd.DataFrame, members: list[str],
                 train_end: pd.Timestamp, train_months: int, validate_months: int) -> list[dict]:
    """Rolling 24m/6m windows inside the training period: member IC weights per window +
    next-window validation IC of the weighted composite. Shows weight stability (ribbon figure)."""
    dates = sorted(d for d in fwd3_wide.index.unique() if d <= train_end)
    out = []
    i = 0
    while i + train_months + validate_months <= len(dates):
        tr = dates[i:i + train_months]
        va = dates[i + train_months:i + train_months + validate_months]
        sub_end = tr[-1]
        sub_panel = panel[panel["date"].isin(tr)]
        w = train_ic_weights(sub_panel, fwd3_wide.loc[fwd3_wide.index.isin(tr)], members,
                             pd.Timestamp(sub_end))
        comp = combine(panel, members, weights=w)
        comp_va = comp.loc[comp.index.isin(va)]
        s = ic_series(comp_va, fwd3_wide.loc[fwd3_wide.index.isin(va)])
        out.append({"window_end": pd.Timestamp(sub_end).strftime("%Y-%m-%d"),
                    "weights": {k: round(v, 4) for k, v in w.items()},
                    "validate_ic": float(s.mean()) if len(s) else np.nan,
                    "validate_dates": len(s)})
        i += validate_months
    return out
