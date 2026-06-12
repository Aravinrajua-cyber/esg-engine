"""Phase 5 — scoring system + explanation engine -> the site_data JSON contract.

Translates Phase 4 research artifacts into the product feed:
  companies.json   (primary; schema_version 1, SCHEMAS.md)
  backtest.json, ic_table.json, placebo.json, by_country.json, by_sector.json

Inputs: universe.parquet, signal_panel.parquet, composite_panel.parquet,
validation_results.json, prices_daily.parquet, sentiment_monthly.parquet.

Everything is deterministic and rule-based (no LLM calls). Names with zero scoreable pillars are
excluded and counted honestly (meta in companies.json). Missing inputs degrade to nulls/flags —
never imputed, never fabricated.

Run:  python -m src.scoring.score                                  # live (data/raw + data/processed)
      python -m src.scoring.score --raw data/_synth --panel data/_synth \
             --out data/_synth/site_data --mode synthetic          # pipeline test, quarantined
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.util.log import log_action  # noqa: E402

SETTINGS = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text())

PILLAR_KEYS = ["sentiment_dynamics", "transition_readiness",
               "governance_credibility", "disclosure_behavior"]

PILLAR_META = [
    {"key": "sentiment_dynamics", "label": "Sentiment Dynamics",
     "description": "Direction and acceleration of news tone and media attention (GDELT)."},
    {"key": "transition_readiness", "label": "Transition Readiness",
     "description": "Capital-allocation and credit-market evidence of transition investment."},
    {"key": "governance_credibility", "label": "Governance Credibility",
     "description": "Governance quality, controversy exposure and pillar balance."},
    {"key": "disclosure_behavior", "label": "Disclosure Behavior",
     "description": "Frequency and recency of sustainability disclosures (SGX/Bursa)."},
    {"key": "data_coverage", "label": "Data Coverage",
     "description": "Share of candidate variables observed for this company (display only — "
                    "not part of the weighted score)."},
]

FLAG_META = [
    {"key": "LOW_COVERAGE", "label": "Low coverage",
     "tooltip": f"Fewer than {SETTINGS['scoring']['flags']['low_coverage_pct']}% of candidate "
                "variables observed; score confidence interval widens accordingly."},
    {"key": "CONTROVERSY_RISING", "label": "Controversy",
     "tooltip": "Elevated Sustainalytics controversy level (>= 3 of 5) at the latest snapshot."},
    {"key": "LOW_LIQUIDITY", "label": "Low liquidity",
     "tooltip": "Median daily dollar volume below the backtest liquidity floor; scored but "
                "excluded from backtest portfolios."},
    {"key": "HIGH_VOL", "label": "High volatility",
     "tooltip": "Trailing 12m return volatility in the top decile of the universe."},
    {"key": "STALE_DATA", "label": "Stale data",
     "tooltip": f"No sentiment observation within the last "
                f"{SETTINGS['scoring']['flags']['stale_data_days']} days."},
]

LABELS = {
    "A1": "Sentiment velocity (12m tone slope)", "A2": "Sentiment acceleration",
    "A3": "Attention trend (log volume slope)", "A4": "Tone dispersion",
    "B1": "ESG risk level (naive baseline)", "B2": "ESG score momentum",
    "B3": "Controversy level", "B4": "E-G pillar imbalance",
    "C1": "CapEx intensity trend", "C2": "Cost-of-debt trend",
    "C3": "Revenue growth (3y CAGR)", "C4": "CapEx/depreciation trend",
    "D1": "Disclosure frequency trend", "D2": "Disclosure recency",
    "E1": "Governance pillar", "F1": "Country regulatory momentum",
    "mom_12_1": "Price momentum 12-1 (control)", "log_mcap": "Size (control)",
    "vol_12m": "Volatility 12m (control)",
}

# explanation grammar: variable -> (phrase when z is favorable, phrase when z is unfavorable)
PHRASES = {
    "A1": ("news sentiment has been improving steadily", "news sentiment has been deteriorating"),
    "A2": ("sentiment improvement is accelerating", "sentiment momentum is fading"),
    "A3": ("media attention is building", "media attention is fading"),
    "A4": ("news tone has been consistent", "news tone has been unusually volatile"),
    "B1": ("headline ESG risk is low", "headline ESG risk is high"),
    "B2": ("official ESG scores are improving", "official ESG scores are slipping"),
    "B3": ("the controversy record is clean", "an elevated controversy level weighs on the profile"),
    "B4": ("E and G pillars are balanced", "governance lags the environmental pillar"),
    "C1": ("capital spending is shifting toward renewal", "transition capex is fading"),
    "C2": ("borrowing costs are trending down", "borrowing costs are trending up"),
    "C3": ("revenue growth is strong", "revenue growth is weak"),
    "C4": ("asset-renewal investment is rising", "asset renewal is lagging depreciation"),
    "D1": ("sustainability disclosure is becoming more frequent", "sustainability disclosure is thinning out"),
    "D2": ("sustainability reporting is current", "the last sustainability disclosure is stale"),
    "E1": ("governance quality is strong", "governance quality is weak"),
    "F1": ("it operates in a strengthening regulatory regime", "its home market's ESG regulation lags"),
}
CONTROLS = {"mom_12_1", "log_mcap", "vol_12m"}
CANDIDATE_VARS = [v for v in LABELS if v not in CONTROLS]


def _pct(s: pd.Series) -> pd.Series:
    return s.rank(pct=True) * 100.0


def _grade(score: float) -> str:
    gb = SETTINGS["scoring"]["grade_bands"]
    if score >= gb["A_plus"]:
        return "A+"
    if score >= gb["A"]:
        return "A"
    if score >= gb["B"]:
        return "B"
    if score >= gb["C"]:
        return "C"
    return "D"


def _classify(mom_pct: float, lvl_pct: float, mom_med: float, lvl_med: float) -> str:
    hi_mom, hi_lvl = mom_pct >= mom_med, lvl_pct >= lvl_med
    if hi_mom and not hi_lvl:
        return "hidden_winner"
    if hi_mom and hi_lvl:
        return "future_leader"
    if not hi_mom and hi_lvl:
        return "overrated_leader"
    return "value_trap"


def _explain(score: int, grade: str, zrow: pd.Series) -> str:
    avail = zrow.dropna()
    avail = avail[avail.index.isin(PHRASES.keys())]
    if avail.empty:
        return f"Scored {score} ({grade}): insufficient variable coverage for attribution."
    pos = avail[avail > 0].sort_values(ascending=False)
    neg = avail[avail < 0].sort_values()
    bits = [PHRASES[v][0] for v in pos.index[:2]]
    head = " and ".join(bits) if bits else "signals are mixed"
    if len(neg):
        return f"Scored {score} ({grade}): {head}, partially offset because {PHRASES[neg.index[0]][1]}."
    return f"Scored {score} ({grade}): {head}, with no material negative signal."


def _nav(returns: list) -> list:
    out, acc = [], 1.0
    for r in returns:
        acc *= 1.0 + (r or 0.0)
        out.append(round(acc, 6))
    return out


def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(x) for x in o]
    if isinstance(o, (np.floating, float)):
        return None if not np.isfinite(o) else round(float(o), 6)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def build_site_data(raw_dir: Path, panel_dir: Path, out_dir: Path, data_mode: str = "live") -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    sc = SETTINGS["scoring"]
    universe = pd.read_parquet(raw_dir / "universe.parquet")
    panel = pd.read_parquet(panel_dir / "signal_panel.parquet")
    comp = pd.read_parquet(panel_dir / "composite_panel.parquet")
    val = json.loads((panel_dir / "validation_results.json").read_text())
    panel["date"] = pd.to_datetime(panel["date"])
    comp["date"] = pd.to_datetime(comp["date"])

    as_of = comp["date"].max()
    # product scores use the mean z over the trailing smooth_months rebalances (noise reduction;
    # settings: scoring.smooth_months). Validation/backtest never smooth — this is display-side.
    smooth_dates = sorted(comp["date"].unique())[-max(int(sc.get("smooth_months", 1)), 1):]
    latest = comp[comp["date"].isin(smooth_dates)].groupby("ticker").mean(numeric_only=True)
    zlatest = panel[panel["date"].isin(smooth_dates)].pivot_table(
        index="ticker", columns="variable", values="z_value", aggfunc="mean")
    rawlatest = panel[panel["date"] == as_of].pivot_table(
        index="ticker", columns="variable", values="raw_value", aggfunc="last")

    weights = val["validated_weights"]
    # pillar percentiles (0-100) within the as-of cross-section
    pillar_pct = pd.DataFrame({p: _pct(latest[p]) for p in PILLAR_KEYS if p in latest})
    vars_present = [v for v in CANDIDATE_VARS if v in zlatest.columns]
    coverage = zlatest[vars_present].notna().sum(axis=1) / len(CANDIDATE_VARS) * 100.0

    # overall = weighted mean over AVAILABLE pillars (weights renormalized; coverage shows gaps)
    w = pd.Series({p: weights.get(p, 0.0) for p in pillar_pct.columns})
    avail = pillar_pct.notna()
    overall = (pillar_pct.fillna(0.0) * w).sum(axis=1) / (avail * w).sum(axis=1)
    overall = overall.dropna()

    mom_pct = _pct(latest["momentum_z"]) if "momentum_z" in latest else _pct(latest["winner_z"])
    lvl_pct = _pct(zlatest["B1"]) if "B1" in zlatest.columns else pd.Series(dtype=float)
    mom_med = float(mom_pct.median()) if len(mom_pct) else 50.0
    lvl_med = float(lvl_pct.median()) if len(lvl_pct) else 50.0

    hv_cut = rawlatest["vol_12m"].quantile(0.9) if "vol_12m" in rawlatest.columns else np.inf
    sent_path = raw_dir / "sentiment_monthly.parquet"
    last_sent = {}
    if sent_path.exists():
        s = pd.read_parquet(sent_path)
        if len(s):
            s["month"] = pd.to_datetime(s["month"])
            last_sent = s.groupby("ticker")["month"].max().to_dict()

    uni = universe.set_index("ticker")
    ranked = overall.sort_values(ascending=False)
    conf = sc["confidence"]
    top_n = sc["timeseries_top_n"]

    # timeseries inputs for the top names
    score_hist = comp.pivot_table(index="date", columns="ticker", values="winner_z")
    score_hist = score_hist.rank(axis=1, pct=True) * 100.0
    prices_path = raw_dir / "prices_daily.parquet"
    monthly_px = pd.DataFrame()
    if prices_path.exists():
        px = pd.read_parquet(prices_path)
        top_tickers = set(ranked.index[:top_n])
        px = px[px["ticker"].isin(top_tickers)]
        px["date"] = pd.to_datetime(px["date"])
        monthly_px = px.pivot_table(index="date", columns="ticker", values="close_usd",
                                    aggfunc="last").resample("ME").last()
    tone_m = pd.DataFrame()
    if sent_path.exists():
        s = pd.read_parquet(sent_path)
        if len(s):
            s["month"] = pd.to_datetime(s["month"])
            tone_m = s.pivot_table(index="month", columns="ticker", values="avg_tone")

    companies = []
    for rank, (tk, sc_val) in enumerate(ranked.items(), start=1):
        if tk not in uni.index:
            continue
        u = uni.loc[tk]
        score = float(sc_val)
        cov = float(coverage.get(tk, 0.0))
        prow = pillar_pct.loc[tk] if tk in pillar_pct.index else pd.Series(dtype=float)
        disp = float(prow.std()) if prow.notna().sum() >= 2 else 0.0
        hw = conf["base"] + conf["coverage_coeff"] * (1 - cov / 100.0) + conf["dispersion_coeff"] * disp
        zrow = zlatest.loc[tk] if tk in zlatest.index else pd.Series(dtype=float)
        rrow = rawlatest.loc[tk] if tk in rawlatest.index else pd.Series(dtype=float)

        flags = []
        if cov < sc["flags"]["low_coverage_pct"]:
            flags.append("LOW_COVERAGE")
        if float(rrow.get("B3", np.nan)) >= 3:
            flags.append("CONTROVERSY_RISING")
        if bool(u["liquidity_flag"]):
            flags.append("LOW_LIQUIDITY")
        if float(rrow.get("vol_12m", np.nan)) >= hv_cut:
            flags.append("HIGH_VOL")
        ls = last_sent.get(tk)
        if ls is None or (as_of - ls).days > sc["flags"]["stale_data_days"]:
            flags.append("STALE_DATA")

        mp = float(mom_pct.get(tk, np.nan))
        lp = float(lvl_pct.get(tk, np.nan)) if len(lvl_pct) else np.nan
        mp_eff = mp if np.isfinite(mp) else 50.0
        lp_eff = lp if np.isfinite(lp) else 50.0   # missing level -> median (flagged via coverage)

        ts = None
        if rank <= top_n:
            dates = [d.strftime("%Y-%m-%d") for d in score_hist.index]
            px_m = monthly_px.reindex(score_hist.index, method="ffill")[tk] \
                if tk in monthly_px.columns else pd.Series(np.nan, index=score_hist.index)
            tn_m = tone_m.reindex(score_hist.index)[tk] \
                if tk in tone_m.columns else pd.Series(np.nan, index=score_hist.index)
            ts = {"dates": dates,
                  "price_usd": [_noneify(x) for x in px_m],
                  "sentiment_tone": [_noneify(x) for x in tn_m],
                  "score": [_noneify(x) for x in score_hist[tk]] if tk in score_hist.columns else []}

        grade = _grade(score)
        companies.append({
            "ticker": tk, "name": u["name"], "country": u["country"], "exchange": u["exchange"],
            "sector": u["sector"], "mcap_tier": u["mcap_tier"], "currency": u["currency"],
            "rank": rank, "overall_score": round(score, 1), "grade": grade,
            "confidence_low": round(max(score - hw, 0.0), 1),
            "confidence_high": round(min(score + hw, 100.0), 1),
            "coverage_pct": round(cov, 1),
            "classification": _classify(mp_eff, lp_eff, mom_med, lvl_med),
            "esg_level_pctile": round(lp_eff, 1), "esg_momentum_pctile": round(mp_eff, 1),
            "pillar_scores": {**{p: _noneify(prow.get(p, np.nan), nd=1) for p in PILLAR_KEYS},
                              "data_coverage": round(cov, 1)},
            "flags": flags,
            "explanation": _explain(int(round(score)), grade, zrow),
            "timeseries": ts,
        })

    bt = val["backtest"]
    model = {
        "winning_composite": bt["winning_composite"],
        "validated_weights": {p: weights.get(p, 0.0) for p in PILLAR_KEYS},
        "train_end": val["meta"]["train_end"],
        "headline": {
            "net_q5q1_spread_annual_pct": _noneify((bt["q5_q1_spread_net"] or 0) * 100, nd=2),
            "deflated_sharpe": bt["deflated_sharpe"],
            "test_ic": next((r["test_ic"] for r in val["composites"]
                             if r["name"] == bt["winning_composite"]), None),
            "sharpe_net": bt["sharpe"],
        },
    }
    companies_json = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_mode": data_mode,
        "as_of_date": as_of.strftime("%Y-%m-%d"),
        "universe_size": len(companies),
        "model": model,
        "pillars": PILLAR_META,
        "flags": FLAG_META,
        "companies": companies,
        "meta": {"universe_rows": int(len(universe)),
                 "unscored_names": int(len(universe) - len(companies))},
    }
    _write(out_dir / "companies.json", companies_json)

    # ---- the four small files --------------------------------------------------------------
    series = val.get("series", {})
    dates = series.get("dates", [])
    train_end = pd.Timestamp(val["meta"]["train_end"])
    tei = max((i for i, d in enumerate(dates) if pd.Timestamp(d) <= train_end), default=0)
    naive_nav = []
    if series.get("naive_esg_q5_net"):
        aligned = {d: r for d, r in zip(series["naive_dates"], series["naive_esg_q5_net"])}
        naive_nav = _nav([aligned.get(d) for d in dates])
    _write(out_dir / "backtest.json", {
        "dates": dates, "q5": _nav(series.get("q5_net", [])), "q1": _nav(series.get("q1_net", [])),
        "benchmark": _nav(series.get("benchmark", [])), "naive_esg_q5": naive_nav,
        "net": True, "train_end_index": tei,
    })
    _write(out_dir / "ic_table.json", [
        {"variable": r["variable"], "label": LABELS.get(r["variable"], r["variable"]),
         "ic_3m": r["ic_mean"], "t_nw": r["t_nw"], "fdr_survived": r["fdr_survived"]}
        for r in val["ic"] if r["horizon"] == 3])
    _write(out_dir / "placebo.json", {
        "realized_spread": val["placebo"]["realized_spread"],
        "hist_bins": val["placebo"]["hist_bins"], "hist_counts": val["placebo"]["hist_counts"]})
    _write(out_dir / "by_country.json", val.get("by_country", []))
    _write(out_dir / "by_sector.json", val.get("by_sector", []))

    log_action("phase5", "site_data_built", {"mode": data_mode, "out": str(out_dir)},
               {"companies": len(companies), "as_of": companies_json["as_of_date"]})
    print(f"site_data ({data_mode}) -> {out_dir}: {len(companies)} companies, "
          f"as_of {companies_json['as_of_date']}, winner {model['winning_composite']}")
    return companies_json


def _noneify(x, nd: int = 4):
    try:
        xf = float(x)
        return round(xf, nd) if np.isfinite(xf) else None
    except (TypeError, ValueError):
        return None


def _write(path: Path, obj) -> None:
    path.write_text(json.dumps(_clean(obj), indent=1, allow_nan=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default="data/raw")
    ap.add_argument("--panel", default="data/processed")
    ap.add_argument("--out", default="outputs/site_data")
    ap.add_argument("--mode", default="live", choices=["live", "synthetic"])
    args = ap.parse_args()
    build_site_data(ROOT / args.raw if not Path(args.raw).is_absolute() else Path(args.raw),
                    ROOT / args.panel if not Path(args.panel).is_absolute() else Path(args.panel),
                    ROOT / args.out if not Path(args.out).is_absolute() else Path(args.out),
                    data_mode=args.mode)
