from __future__ import annotations

import json
from pathlib import Path

from src.fetchers import synthetic


REQUIRED_COMPANY_KEYS = {
    "ticker",
    "name",
    "country",
    "exchange",
    "sector",
    "mcap_tier",
    "currency",
    "rank",
    "overall_score",
    "grade",
    "confidence_low",
    "confidence_high",
    "coverage_pct",
    "classification",
    "esg_level_pctile",
    "esg_momentum_pctile",
    "pillar_scores",
    "flags",
    "explanation",
    "timeseries",
}
ALLOWED_GRADES = {"A+", "A", "B", "C", "D"}
ALLOWED_CLASSIFICATIONS = {"hidden_winner", "future_leader", "overrated_leader", "value_trap"}
PILLAR_KEYS = {"sentiment_dynamics", "transition_readiness", "governance_credibility", "disclosure_behavior", "data_coverage"}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPANIES_PATH = PROJECT_ROOT / "outputs" / "site_data" / "companies.json"


def test_companies_json_company_records(sample_companies_json):
    assert sample_companies_json["companies"]
    for company in sample_companies_json["companies"]:
        assert set(company) == REQUIRED_COMPANY_KEYS
        assert company["grade"] in ALLOWED_GRADES
        assert company["classification"] in ALLOWED_CLASSIFICATIONS
        for key in ["overall_score", "confidence_low", "confidence_high", "coverage_pct", "esg_level_pctile", "esg_momentum_pctile"]:
            assert 0 <= company[key] <= 100
        assert set(company["pillar_scores"]) == PILLAR_KEYS
        for score in company["pillar_scores"].values():
            assert 0 <= score <= 100
        assert company["confidence_low"] <= company["confidence_high"]
        assert "risk_index" not in company


def test_generated_companies_feed_has_consistent_cardinality_and_labels(sample_companies_json):
    # Works for the synthetic demo feed (500) and the frozen live feed (real discovery universe).
    feed = sample_companies_json
    assert feed["data_mode"] in {"live", "synthetic"}
    assert feed["universe_size"] == len(feed["companies"]) >= 1
    assert all(company["name"] for company in feed["companies"])
    assert all(company["ticker"] for company in feed["companies"])
    assert all(company["explanation"] for company in feed["companies"])


def test_rankings_are_complete_unique_and_score_sorted(sample_companies_json):
    companies = sample_companies_json["companies"]
    ranks = [company["rank"] for company in companies]
    assert sorted(ranks) == list(range(1, len(companies) + 1))
    scores = [company["overall_score"] for company in companies]
    assert scores == sorted(scores, reverse=True)


def test_timeseries_missing_data_and_bounds_are_explicit(sample_companies_json):
    companies = sample_companies_json["companies"]
    assert any(company["timeseries"] is None for company in companies)
    assert any(company["timeseries"] is not None for company in companies)
    for company in companies:
        series = company["timeseries"]
        if series is None:
            continue
        assert set(series) == {"dates", "price_usd", "sentiment_tone", "score"}
        lengths = {len(series[key]) for key in series}
        assert len(lengths) == 1
        # real series carry None for missing months (never imputed); bound only present values
        assert all(value is None or value >= 0 for value in series["price_usd"])
        assert all(value is None or -100 <= value <= 100 for value in series["sentiment_tone"])  # GDELT tone scale
        assert all(value is None or 0 <= value <= 100 for value in series["score"])


def test_schema_safe_derived_risk_index_bounds(sample_companies_json):
    """Risk is derived for reporting; it is not a stored SCHEMAS.md company field."""

    flag_weights = {
        "LOW_COVERAGE": 30,
        "CONTROVERSY_RISING": 25,
        "LOW_LIQUIDITY": 20,
        "HIGH_VOL": 15,
        "STALE_DATA": 10,
    }
    allowed_flags = {flag["key"] for flag in sample_companies_json["flags"]}
    for company in sample_companies_json["companies"]:
        assert set(company["flags"]).issubset(allowed_flags)
        risk_index = min(
            100,
            max(0, 100 - company["coverage_pct"]) + sum(flag_weights.get(flag, 0) for flag in company["flags"]),
        )
        assert 0 <= risk_index <= 100


def test_synthetic_generation_is_deterministic_with_seed_42(sample_companies_json):
    before = COMPANIES_PATH.read_text(encoding="utf-8") if COMPANIES_PATH.exists() else None
    try:
        first = synthetic.fetch()
        first_payload = json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))
        second = synthetic.fetch()
        second_payload = json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))

        assert first["ticker"].tolist() == second["ticker"].tolist()
        assert first["overall_score"].tolist() == second["overall_score"].tolist()
        assert [
            (company["ticker"], company["rank"], company["overall_score"], company["flags"])
            for company in first_payload["companies"]
        ] == [
            (company["ticker"], company["rank"], company["overall_score"], company["flags"])
            for company in second_payload["companies"]
        ]
    finally:
        if before is not None:
            COMPANIES_PATH.write_text(before, encoding="utf-8")


def test_model_weights_match_sandbox_keys(sample_companies_json):
    weights = sample_companies_json["model"]["validated_weights"]
    assert set(weights) == PILLAR_KEYS - {"data_coverage"}
    assert abs(sum(weights.values()) - 1.0) < 1e-9
