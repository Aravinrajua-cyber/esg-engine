"""Phase 4 orchestrator — runs the full alpha-discovery + validation protocol and serializes
data/processed/validation_results.json (frozen schema, SCHEMAS.md) plus composite_panel.parquet
for the Phase 5 scoring layer.

Protocol (strict order, training window <= dates.train_end; test window touched ONCE at the end):
  1. univariate Spearman ICs (NW t, hit rate) on the training window
  2. Benjamini-Hochberg FDR (q = validation.fdr_q) across all variable x horizon hypotheses
  3. composites from FDR survivors: EIP / TRI / CPS / MASTER x {equal, trailing_ic, rank_agg};
     winner chosen on TRAINING-window net quarterly Q5-Q1 spread ONLY
  4. Fama-MacBeth + VIF + F1 interaction (training window)
  5. walk-forward weight stability (24m/6m) inside the training window
  6. full quarterly cost-matrix backtest of the frozen winner (train+test, marked split),
     block-bootstrap CI, Deflated Sharpe (N = all configs trialed), gross placebo
  7. robustness: sub-periods, by-country, by-sector, formation-lag sensitivity

Run:  python -m src.validation.run_validation --raw data/_synth --panel data/_synth --out data/_synth
      python -m src.validation.run_validation                       # real data (defaults)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.util.log import log_action                                   # noqa: E402
from src.validation.ic import univariate_table, apply_bh_fdr, ic_series  # noqa: E402
from src.validation import backtest as bt                             # noqa: E402
from src.validation.fama_macbeth import fama_macbeth, vif_table, f1_interaction, CONTROLS  # noqa: E402
from src.composite.composites import (build_all_configs, combine, train_ic_weights,  # noqa: E402
                                      walk_forward, FAMILIES, PILLARS)

SETTINGS = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text())

SUBPERIODS = {
    "2018-19": ("2018-01-01", "2019-12-31"),
    "2020 covid": ("2020-01-01", "2020-12-31"),
    "2021": ("2021-01-01", "2021-12-31"),
    "2022 rate shock": ("2022-01-01", "2022-12-31"),
    "2023-25": ("2023-01-01", "2025-12-31"),
}
PILLAR_WEIGHT_FLOOR = 0.05   # every product pillar keeps a visible minimum weight (documented)


def _wide(panel: pd.DataFrame, var: str) -> pd.DataFrame:
    sub = panel[panel["variable"] == var]
    return sub.pivot_table(index="date", columns="ticker", values="z_value", aggfunc="last")


def _fwd_wide(fwd: pd.DataFrame, h: int) -> pd.DataFrame:
    return fwd.pivot_table(index="date", columns="ticker", values=f"fwd_{h}m", aggfunc="last")


def _train_test_split(idx: pd.Index, train_end: pd.Timestamp):
    return idx[idx <= train_end], idx[idx > train_end]


def _spread_stats(z: pd.DataFrame, fwd3: pd.DataFrame, universe: pd.DataFrame,
                  dates_subset: pd.Index | None) -> pd.DataFrame:
    zz = z.loc[z.index.isin(dates_subset)] if dates_subset is not None else z
    return bt.quintile_backtest(zz, fwd3, universe, SETTINGS)["periods"]


def run(raw_dir: Path, panel_dir: Path, out_dir: Path, discovery_path: Path | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    universe = pd.read_parquet(raw_dir / "universe.parquet")
    panel = pd.read_parquet(panel_dir / "signal_panel.parquet")
    fwd = pd.read_parquet(panel_dir / "returns_forward.parquet")
    panel["date"] = pd.to_datetime(panel["date"])
    fwd["date"] = pd.to_datetime(fwd["date"])

    # Discovery scope: all statistical work (IC/FDR/FM/composite/backtest/DSR/placebo) runs on the
    # liquid universe with complete sentiment coverage; the composite is later scored on all 477.
    discovery_scope = None
    if discovery_path is not None:
        disc = pd.read_parquet(discovery_path)
        keep = set(disc["ticker"])
        universe = universe[universe["ticker"].isin(keep)].copy()
        panel = panel[panel["ticker"].isin(keep)].copy()
        fwd = fwd[fwd["ticker"].isin(keep)].copy()
        discovery_scope = {"path": str(discovery_path), "n_names": len(keep),
                           "by_country": disc["country"].value_counts().to_dict()}
        print(f"DISCOVERY scope: {len(keep)} liquid names ({discovery_scope['by_country']})")

    v = SETTINGS["validation"]
    train_end = pd.Timestamp(SETTINGS["dates"]["train_end"])
    fwd3 = _fwd_wide(fwd, v["fm_horizon_months"])

    # ---- 4.1 + 4.2: univariate ICs (train) + FDR ------------------------------------------
    uni_tbl = univariate_table(panel, fwd, v["horizons_months"], train_end=str(train_end.date()))
    uni_tbl = apply_bh_fdr(uni_tbl, v["fdr_q"], exclude_vars=set(CONTROLS))
    survivors = sorted(uni_tbl.loc[uni_tbl["fdr_survived"], "variable"].unique())
    print(f"FDR survivors (q={v['fdr_q']}): {survivors}")

    # ---- 4.4: composites, winner on TRAIN net spread only ---------------------------------
    configs, comp_decisions = build_all_configs(panel, fwd3, set(survivors), train_end)
    if not configs:
        raise RuntimeError("no composite has surviving members — cannot proceed")
    comp_rows, trial_sharpes, train_net = [], [], {}
    for name, z in configs.items():
        tr_dates, te_dates = _train_test_split(z.index, train_end)
        tr = _spread_stats(z, fwd3, universe, tr_dates)
        te = _spread_stats(z, fwd3, universe, te_dates)
        s_tr_ic = ic_series(z.loc[z.index.isin(tr_dates)], fwd3)
        s_te_ic = ic_series(z.loc[z.index.isin(te_dates)], fwd3)
        net = tr["spread_net"]
        train_net[name] = float(net.mean() * 4) if len(net) >= 4 else -np.inf
        if len(net) >= 4 and net.std(ddof=1) > 0:
            trial_sharpes.append(float(net.mean() / net.std(ddof=1)))
        comp_rows.append({
            "name": name,
            "train_ic": float(s_tr_ic.mean()) if len(s_tr_ic) else None,
            "test_ic": float(s_te_ic.mean()) if len(s_te_ic) else None,
            "train_spread": train_net[name] if np.isfinite(train_net[name]) else None,
            "test_spread": float(te["spread_net"].mean() * 4) if len(te) >= 4 else None,
        })
    winner_name = max(train_net, key=train_net.get)
    winner_z = configs[winner_name]
    print(f"winner (train net spread only): {winner_name}  "
          f"({train_net[winner_name]:+.2%} ann.)  out of {len(configs)} configs")

    # ---- 4.3: Fama-MacBeth + VIF + F1 interaction (train) ---------------------------------
    fm_vars = [s for s in survivors if s not in CONTROLS]
    fm_tbl = fama_macbeth(panel, fwd, universe, fm_vars, v["fm_horizon_months"],
                          str(train_end.date()))
    vif_tbl = vif_table(panel, fm_vars, str(train_end.date())) if len(fm_vars) >= 2 else \
        pd.DataFrame({"variable": fm_vars, "vif": [np.nan] * len(fm_vars)})
    high_vif = vif_tbl.loc[vif_tbl["vif"] > v["vif_threshold"], "variable"].tolist()
    f1_int = f1_interaction(panel, fwd, universe, winner_z, v["fm_horizon_months"],
                            str(train_end.date()))

    # ---- 4.5: walk-forward stability (train window) ---------------------------------------
    wf_members = comp_decisions["members_after_fdr"].get(winner_name.split("_")[0]) or \
        [m for ms in comp_decisions["members_after_fdr"].values() for m in ms]
    wf = walk_forward(panel, fwd3, wf_members, train_end,
                      v["walk_forward"]["train_months"], v["walk_forward"]["validate_months"]) \
        if wf_members else []

    # ---- 4.6: full backtest of the frozen winner ------------------------------------------
    full = bt.quintile_backtest(winner_z, fwd3, universe, SETTINGS)
    per = full["periods"]
    m_net = bt.annualize(per["spread_net"])
    m_gross = bt.annualize(per["spread_gross"])
    ci_lo, ci_hi = bt.block_bootstrap_ci(
        per["spread_net"], block_periods=max(SETTINGS["validation"]["bootstrap"]["block_months"] //
                                             SETTINGS["backtest"]["hold_months"], 1),
        iterations=SETTINGS["validation"]["bootstrap"]["iterations"],
        ci=SETTINGS["validation"]["bootstrap"]["ci"], seed=SETTINGS["run"]["random_seed"])
    dsr = bt.deflated_sharpe(per["spread_net"], trial_sharpes)
    placebo = bt.placebo_test(winner_z, fwd3, universe, SETTINGS,
                              realized_gross_spread=float(per["spread_gross"].mean() * 4),
                              iterations=v["placebo_iterations"],
                              seed=SETTINGS["run"]["random_seed"])

    # naive ESG-level benchmark (B1 quintiles) — the thesis comparison
    naive = None
    b1 = _wide(panel, "B1")
    if not b1.empty:
        naive = bt.quintile_backtest(b1, fwd3, universe, SETTINGS)["periods"]

    # ---- robustness ------------------------------------------------------------------------
    by_country = bt.group_spreads(winner_z, fwd3, universe, SETTINGS, "country")
    by_sector = bt.group_spreads(winner_z, fwd3, universe, SETTINGS, "sector")
    subp = bt.subperiod_spreads(per, SUBPERIODS)
    lag_spread = bt.formation_lag_spread(winner_z, fwd3, universe, SETTINGS,
                                         v["formation_lag_sensitivity_months"])

    # ---- product weights: pillar composites + train-IC weights (floored, normalized) -------
    # members inside each pillar are train-IC-weighted too (research-driven end-to-end), so the
    # sandbox identity overall = sum(w_i x pillar_i) reproduces a validated-quality ranking
    pillar_panels = {}
    for pn, mem in PILLARS.items():
        mw = train_ic_weights(panel, fwd3, mem, train_end)
        z = combine(panel, mem, weights=mw)
        if not z.empty:
            pillar_panels[pn] = z
    raw_w = {}
    for pn, z in pillar_panels.items():
        s = ic_series(z.loc[z.index <= train_end], fwd3.loc[fwd3.index <= train_end])
        raw_w[pn] = max(float(s.mean()) if len(s) >= 6 else 0.0, PILLAR_WEIGHT_FLOOR)
    for pn in PILLARS:                                   # every product pillar gets a weight
        raw_w.setdefault(pn, PILLAR_WEIGHT_FLOOR)
    tot = sum(raw_w.values())
    validated_weights = {pn: round(w / tot, 4) for pn, w in raw_w.items()}

    # ---- serialize: frozen schema + additive extras ----------------------------------------
    te_ic = next((r["test_ic"] for r in comp_rows if r["name"] == winner_name), None)
    results = {
        "ic": [{"variable": r.variable, "horizon": int(r.horizon),
                "ic_mean": _f(r.ic_mean), "ic_std": _f(r.ic_std), "t_nw": _f(r.t_nw),
                "hit_rate": _f(r.hit_rate), "fdr_survived": bool(r.fdr_survived)}
               for r in uni_tbl.itertuples()],
        "fama_macbeth": [{"variable": r.variable, "coef": _f(r.coef), "t_nw": _f(r.t_nw),
                          "p": _f(r.p)} for r in fm_tbl.itertuples()],
        "composites": comp_rows,
        "backtest": {
            "winning_composite": winner_name,
            "gross": _f(m_gross["ann_return"]), "net": _f(m_net["ann_return"]),
            "sharpe": _f(m_net["sharpe"]), "sortino": _f(m_net["sortino"]),
            "max_dd": _f(m_net["max_dd"]), "calmar": _f(m_net["calmar"]),
            "q5_q1_spread_net": _f(m_net["ann_return"]),
            "spread_ci_low": _f(ci_lo), "spread_ci_high": _f(ci_hi),
            "turnover": _f(per["turnover"].mean() * 4) if len(per) else None,  # annual, one-way
            "deflated_sharpe": _f(dsr),
        },
        "placebo": placebo,
        # ---- additive extras (report + site; not in the frozen minimum) ----
        "meta": {
            "train_end": str(train_end.date()), "n_configs_trialed": len(configs),
            "fdr_q": v["fdr_q"], "survivors": survivors,
            "winner_members": wf_members, "selection_metric": "train net quarterly Q5-Q1 spread",
            "placebo_basis": "gross-vs-gross (information content; costs orthogonal)",
            "high_vif": high_vif, "discovery_scope": discovery_scope,
            "n_names_in_scope": int(universe["ticker"].nunique()),
        },
        "vif": [{"variable": r.variable, "vif": _f(r.vif)} for r in vif_tbl.itertuples()],
        "f1_interaction": f1_int,
        "walk_forward": wf,
        "by_country": by_country, "by_sector": by_sector,
        "sub_periods": subp,
        "formation_lag_net_spread": _f(lag_spread),
        "validated_weights": validated_weights,
        "master_family_weights": comp_decisions.get("master_family_weights", {}),
        "series": {
            "dates": [d.strftime("%Y-%m-%d") for d in per["date"]],
            "q5_net": [_f(x) for x in (per["q5"] - per["q5_cost"])],
            "q1_net": [_f(x) for x in (per["q1"] - per["q1_cost"])],
            "benchmark": [_f(x) for x in per["bench"]],
            "naive_esg_q5_net": [_f(x) for x in (naive["q5"] - naive["q5_cost"])] if naive is not None else [],
            "naive_dates": [d.strftime("%Y-%m-%d") for d in naive["date"]] if naive is not None else [],
            "quintile_gross_means": [list(map(_f, q)) for q in full["quintile_means"]],
        },
    }
    (out_dir / "validation_results.json").write_text(json.dumps(results, indent=1))

    # full results object (richer than JSON: keeps the raw frames + the frozen winner z-panel).
    # Top-level aliases ic_results / fama_macbeth_coefficients / backtest_metrics are the contract
    # the Codex report builder (build_report._phase4_tables) reads to populate the Phase 4 tables.
    import pickle
    payload = {
        "results": results,
        "frozen_winner": {"name": winner_name, "members": wf_members,
                          "z_panel": winner_z, "validated_weights": validated_weights},
        "tables": {"univariate_ic": uni_tbl, "fama_macbeth": fm_tbl, "vif": vif_tbl,
                   "backtest_periods": per, "composite_summary": pd.DataFrame(comp_rows)},
        "config_train_net_spread": train_net,
        "ic_results": uni_tbl,
        "fama_macbeth_coefficients": fm_tbl,
        "backtest_metrics": results["backtest"],
    }
    with open(out_dir / "phase4_results.pkl", "wb") as fh:
        pickle.dump(payload, fh)

    # composite + pillar panel for Phase 5 scoring
    long = winner_z.stack().rename("winner_z").reset_index()
    long.columns = ["date", "ticker", "winner_z"]
    eip = configs.get("EIP_trailing_ic", configs.get("EIP_equal"))
    if eip is not None:
        e = eip.stack().rename("momentum_z").reset_index()
        e.columns = ["date", "ticker", "momentum_z"]
        long = long.merge(e, on=["date", "ticker"], how="outer")
    for pn, z in pillar_panels.items():
        p = z.stack().rename(pn).reset_index()
        p.columns = ["date", "ticker", pn]
        long = long.merge(p, on=["date", "ticker"], how="outer")
    long.to_parquet(out_dir / "composite_panel.parquet", index=False)

    log_action("phase4", "validation_done",
               {"panel_dir": str(panel_dir)},
               {"winner": winner_name, "survivors": survivors,
                "net_spread": results["backtest"]["q5_q1_spread_net"],
                "dsr": results["backtest"]["deflated_sharpe"],
                "placebo_p": placebo.get("placebo_p")})
    print(json.dumps(results["backtest"], indent=2))
    print(f"placebo: p={placebo.get('placebo_p')}  mean={placebo.get('placebo_mean')}")
    return results


def _f(x) -> float | None:
    try:
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return None
        return round(float(x), 6)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw", help="dir with universe.parquet")
    ap.add_argument("--panel", default="data/processed", help="dir with signal_panel + returns_forward")
    ap.add_argument("--out", default="data/processed")
    ap.add_argument("--discovery", default=None,
                    help="path to discovery_universe.parquet; restricts ALL Phase 4 statistics to "
                         "that liquid subset (composite later scored on the full universe)")
    args = ap.parse_args()
    _abs = lambda p: Path(p) if Path(p).is_absolute() else ROOT / p
    run(_abs(args.raw), _abs(args.panel), _abs(args.out),
        discovery_path=_abs(args.discovery) if args.discovery else None)
