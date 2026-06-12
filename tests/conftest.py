from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def sample_universe() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": "DEMO.SI",
                "name": "Demo Ltd",
                "country": "SG",
                "exchange": "SGX",
                "sector": "Industrials",
                "mcap_tier": "large",
                "currency": "SGD",
                "market_cap_usd": 1_000_000_000.0,
                "free_float_pct": None,
                "adv_usd": 500_000.0,
                "liquidity_flag": False,
                "in_backtest": True,
                "source": "seed",
            }
        ]
    )


@pytest.fixture()
def sample_companies_json() -> dict:
    path = PROJECT_ROOT / "outputs" / "site_data" / "companies.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema_version": 1,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "data_mode": "synthetic",
        "as_of_date": "2026-01-01",
        "universe_size": 1,
        "model": {
            "winning_composite": "fixture",
            "validated_weights": {
                "sentiment_dynamics": 0.35,
                "transition_readiness": 0.25,
                "governance_credibility": 0.25,
                "disclosure_behavior": 0.15,
            },
            "train_end": "2021-12-31",
            "headline": {"net_q5q1_spread_annual_pct": 0, "deflated_sharpe": 0, "test_ic": 0, "sharpe_net": 0},
        },
        "pillars": [],
        "flags": [],
        "companies": [
            {
                "ticker": "DEMO.SI",
                "name": "Demo Ltd",
                "country": "SG",
                "exchange": "SGX",
                "sector": "Industrials",
                "mcap_tier": "large",
                "currency": "SGD",
                "rank": 1,
                "overall_score": 75,
                "grade": "B",
                "confidence_low": 70,
                "confidence_high": 80,
                "coverage_pct": 90,
                "classification": "future_leader",
                "esg_level_pctile": 60,
                "esg_momentum_pctile": 65,
                "pillar_scores": {
                    "sentiment_dynamics": 75,
                    "transition_readiness": 75,
                    "governance_credibility": 75,
                    "disclosure_behavior": 75,
                    "data_coverage": 90,
                },
                "flags": [],
                "explanation": "Fixture.",
                "timeseries": None,
            }
        ],
    }
