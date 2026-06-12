"""Deterministic synthetic site-data generator for frontend development."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.util.log import log_action

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SITE_DATA_DIR = PROJECT_ROOT / "outputs" / "site_data"

PILLAR_KEYS = [
    "sentiment_dynamics",
    "transition_readiness",
    "governance_credibility",
    "disclosure_behavior",
]
WEIGHTS = {
    "sentiment_dynamics": 0.35,
    "transition_readiness": 0.25,
    "governance_credibility": 0.25,
    "disclosure_behavior": 0.15,
}
GRADES = [(90, "A+"), (80, "A"), (65, "B"), (50, "C"), (0, "D")]
CLASSIFICATIONS = ["hidden_winner", "future_leader", "overrated_leader", "value_trap"]
FLAG_DEFS = [
    {"key": "LOW_COVERAGE", "label": "Low coverage", "tooltip": "Fewer source observations than the model prefers."},
    {"key": "CONTROVERSY_RISING", "label": "Controversy rising", "tooltip": "Recent controversy proxy is moving against the company."},
    {"key": "LOW_LIQUIDITY", "label": "Low liquidity", "tooltip": "Trading liquidity may be below institutional thresholds."},
    {"key": "HIGH_VOL", "label": "High volatility", "tooltip": "Recent return volatility is elevated."},
    {"key": "STALE_DATA", "label": "Stale data", "tooltip": "Some source fields have not refreshed recently."},
]
DEMO_SECTORS = [
    "Financials",
    "Industrials",
    "Technology",
    "Consumer",
    "Utilities",
    "Materials",
    "Real Estate",
    "Energy",
]


def _load_settings() -> dict[str, Any]:
    with open(PROJECT_ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _grade(score: float) -> str:
    for threshold, grade in GRADES:
        if score >= threshold:
            return grade
    return "D"


def _classification(level: float, momentum: float) -> str:
    if level >= 50 and momentum >= 50:
        return "future_leader"
    if level < 50 <= momentum:
        return "hidden_winner"
    if level >= 50 > momentum:
        return "overrated_leader"
    return "value_trap"


def _timeseries(rng: np.random.Generator, score: float) -> dict[str, list[float | str]]:
    dates = pd.date_range(end=date.today(), periods=18, freq="ME").date.astype(str).tolist()
    price = 100 * np.cumprod(1 + rng.normal(0.012, 0.055, len(dates)))
    tone = np.clip(rng.normal(0.5, 1.4, len(dates)).cumsum() / 6, -5, 5)
    scores = np.clip(score + rng.normal(0, 3, len(dates)).cumsum() / 3, 0, 100)
    return {
        "dates": dates,
        "price_usd": [round(float(v), 2) for v in price],
        "sentiment_tone": [round(float(v), 2) for v in tone],
        "score": [round(float(v), 1) for v in scores],
    }


def _clean(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    if pd.isna(value):
        return fallback
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return fallback
    return text


def _company_source_rows(universe_df: pd.DataFrame, target_size: int) -> list[dict[str, Any]]:
    rows = universe_df.to_dict("records")
    if len(rows) >= target_size:
        return rows[:target_size]
    countries = sorted({_clean(row.get("country"), "Singapore") for row in rows}) or ["Singapore", "Malaysia", "Thailand", "Indonesia", "Vietnam"]
    exchanges = sorted({_clean(row.get("exchange"), "Demo Exchange") for row in rows}) or ["Demo Exchange"]
    currencies = sorted({_clean(row.get("currency"), "USD") for row in rows}) or ["USD"]
    tiers = ["mega", "large", "mid"]
    for idx in range(len(rows), target_size):
        country = countries[idx % len(countries)]
        rows.append(
            {
                "ticker": f"SYN{idx + 1:03d}",
                "name": f"Synthetic Demo Company {idx + 1}",
                "country": country,
                "exchange": exchanges[idx % len(exchanges)],
                "sector": DEMO_SECTORS[idx % len(DEMO_SECTORS)],
                "mcap_tier": tiers[idx % len(tiers)],
                "currency": currencies[idx % len(currencies)],
                "liquidity_flag": False,
            }
        )
    return rows


def _stub_backtest() -> dict[str, Any]:
    dates = pd.date_range("2018-01-31", periods=72, freq="ME").date.astype(str).tolist()
    x = np.linspace(0, 1, len(dates))
    return {
        "dates": dates,
        "q5": [round(float(100 * (1 + 0.72 * v + 0.04 * np.sin(i / 4))), 2) for i, v in enumerate(x)],
        "q1": [round(float(100 * (1 + 0.22 * v + 0.05 * np.cos(i / 5))), 2) for i, v in enumerate(x)],
        "benchmark": [round(float(100 * (1 + 0.38 * v)), 2) for v in x],
        "naive_esg_q5": [round(float(100 * (1 + 0.31 * v + 0.03 * np.sin(i / 3))), 2) for i, v in enumerate(x)],
        "net": True,
        "train_end_index": 47,
    }


def _stub_ic_table() -> list[dict[str, Any]]:
    return [
        {"variable": "A1", "label": "Sentiment velocity", "ic_3m": 0.041, "t_nw": 2.1, "fdr_survived": True},
        {"variable": "B2", "label": "Transition investment", "ic_3m": 0.033, "t_nw": 1.8, "fdr_survived": True},
        {"variable": "C3", "label": "Governance credibility", "ic_3m": 0.025, "t_nw": 1.4, "fdr_survived": False},
    ]


def fetch(
    universe_df: pd.DataFrame | None = None,
    settings: dict[str, Any] | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Generate deterministic synthetic JSON artifacts and return company rows."""

    del force
    settings = settings or _load_settings()
    if universe_df is None:
        universe_df = pd.read_parquet(RAW_DIR / "universe.parquet")
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log_action("phase2", "generate_synthetic_start", inputs={"universe_rows": len(universe_df)})

    rng = np.random.default_rng(settings.get("run", {}).get("random_seed", 42))
    target_size = 500
    source_rows = _company_source_rows(universe_df, target_size)
    companies = []
    for idx, row in enumerate(source_rows):
        sector = _clean(row.get("sector"), DEMO_SECTORS[idx % len(DEMO_SECTORS)])
        pillars = {key: float(np.clip(rng.normal(66, 17), 0, 100)) for key in PILLAR_KEYS}
        coverage = float(np.clip(rng.normal(76, 16), 20, 100))
        raw_score = sum(WEIGHTS[key] * pillars[key] for key in PILLAR_KEYS)
        score = float(np.clip(raw_score + rng.normal(0, 3), 0, 100))
        band = float(rng.uniform(4, 13))
        level = float(np.clip(rng.normal(score, 18), 0, 100))
        momentum = float(np.clip(rng.normal(score, 20), 0, 100))
        flags = []
        if coverage < 50:
            flags.append("LOW_COVERAGE")
        if bool(row.get("liquidity_flag")):
            flags.append("LOW_LIQUIDITY")
        if rng.random() < 0.08:
            flags.append("CONTROVERSY_RISING")
        if rng.random() < 0.08:
            flags.append("HIGH_VOL")
        if rng.random() < 0.05:
            flags.append("STALE_DATA")
        grade = _grade(score)
        company = {
            "ticker": str(row.get("ticker")),
            "name": _clean(row.get("name"), f"Synthetic Demo Company {idx + 1}"),
            "country": _clean(row.get("country"), "Singapore"),
            "exchange": _clean(row.get("exchange"), "Demo Exchange"),
            "sector": sector,
            "mcap_tier": _clean(row.get("mcap_tier"), "mid"),
            "currency": _clean(row.get("currency"), "USD"),
            "rank": 0,
            "overall_score": round(score, 1),
            "grade": grade,
            "confidence_low": round(max(0, score - band), 1),
            "confidence_high": round(min(100, score + band), 1),
            "coverage_pct": round(coverage, 1),
            "classification": _classification(level, momentum),
            "esg_level_pctile": round(level, 1),
            "esg_momentum_pctile": round(momentum, 1),
            "pillar_scores": {
                **{key: round(pillars[key], 1) for key in PILLAR_KEYS},
                "data_coverage": round(coverage, 1),
            },
            "flags": flags,
            "explanation": f"Synthetic demo score {score:.0f} ({grade}) based on placeholder pillar patterns for frontend testing.",
            "timeseries": None,
        }
        companies.append(company)

    companies.sort(key=lambda item: item["overall_score"], reverse=True)
    for rank, company in enumerate(companies, 1):
        company["rank"] = rank
        if rank <= 40:
            company["timeseries"] = _timeseries(rng, company["overall_score"])

    payload = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_mode": "synthetic",
        "as_of_date": date.today().isoformat(),
        "universe_size": len(companies),
        "model": {
            "winning_composite": "synthetic_demo_composite",
            "validated_weights": WEIGHTS,
            "train_end": settings.get("dates", {}).get("train_end", "2021-12-31"),
            "headline": {
                "net_q5q1_spread_annual_pct": 8.7,
                "deflated_sharpe": 0.82,
                "test_ic": 0.038,
                "sharpe_net": 1.14,
            },
        },
        "pillars": [
            {"key": "sentiment_dynamics", "label": "Sentiment dynamics", "description": "Synthetic news momentum proxy."},
            {"key": "transition_readiness", "label": "Transition readiness", "description": "Synthetic transition investment proxy."},
            {"key": "governance_credibility", "label": "Governance credibility", "description": "Synthetic governance signal proxy."},
            {"key": "disclosure_behavior", "label": "Disclosure behavior", "description": "Synthetic disclosure consistency proxy."},
            {"key": "data_coverage", "label": "Data coverage", "description": "Share of expected synthetic inputs present."},
        ],
        "flags": FLAG_DEFS,
        "companies": companies,
    }
    (SITE_DATA_DIR / "companies.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (SITE_DATA_DIR / "backtest.json").write_text(json.dumps(_stub_backtest(), indent=2), encoding="utf-8")
    (SITE_DATA_DIR / "ic_table.json").write_text(json.dumps(_stub_ic_table(), indent=2), encoding="utf-8")
    placebo = {
        "realized_spread": 8.7,
        "hist_bins": [round(float(v), 2) for v in np.linspace(-6, 6, 25)],
        "hist_counts": [int(v) for v in np.maximum(1, 80 * np.exp(-np.linspace(-2, 2, 25) ** 2) + rng.normal(0, 2, 25))],
    }
    (SITE_DATA_DIR / "placebo.json").write_text(json.dumps(placebo, indent=2), encoding="utf-8")
    (SITE_DATA_DIR / "by_country.json").write_text(
        json.dumps([{"key": key, "spread_net": round(float(rng.normal(4, 3)), 2)} for key in sorted({c["country"] for c in companies})], indent=2),
        encoding="utf-8",
    )
    (SITE_DATA_DIR / "by_sector.json").write_text(
        json.dumps([{"key": key, "spread_net": round(float(rng.normal(3, 4)), 2)} for key in sorted({c["sector"] for c in companies})[:12]], indent=2),
        encoding="utf-8",
    )
    log_action("phase2", "generate_synthetic_end", outputs={"companies": len(companies), "path": str(SITE_DATA_DIR / "companies.json")})
    return pd.DataFrame(companies)


if __name__ == "__main__":
    df = fetch()
    print(f"synthetic companies={len(df)} output={SITE_DATA_DIR / 'companies.json'}")
