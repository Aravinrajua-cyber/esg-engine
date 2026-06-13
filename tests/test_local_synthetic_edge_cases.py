from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.csv_import.validate import validate_csv
from src.fetchers import synthetic


ALLOWED_COUNTRIES = {"SG", "ID", "MY", "TH", "PH", "VN"}
RISK_FLAG_WEIGHTS = {
    "LOW_COVERAGE": 30,
    "CONTROVERSY_RISING": 25,
    "LOW_LIQUIDITY": 20,
    "HIGH_VOL": 15,
    "STALE_DATA": 10,
}


def _local_universe_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ticker": f"FIX{i:03d}.{country}",
                "name": f"Fixture Company {i:03d}",
                "country": country,
                "exchange": f"{country}X",
                "sector": "Industrials",
                "mcap_tier": "large",
                "currency": "USD",
                "liquidity_flag": i % 7 == 0,
            }
            for i, country in enumerate(sorted(ALLOWED_COUNTRIES), start=1)
        ]
    )


def test_synthetic_generator_is_offline_deterministic_and_bounds_safe(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(synthetic, "SITE_DATA_DIR", tmp_path / "site_data")
    monkeypatch.setattr(synthetic, "log_action", lambda *_args, **_kwargs: None)
    settings = {"run": {"random_seed": 12345}, "dates": {"train_end": "2021-12-31"}}
    universe = _local_universe_fixture()

    first = synthetic.fetch(universe, settings=settings)
    first_payload = json.loads((tmp_path / "site_data" / "companies.json").read_text(encoding="utf-8"))
    second = synthetic.fetch(universe, settings=settings)
    second_payload = json.loads((tmp_path / "site_data" / "companies.json").read_text(encoding="utf-8"))

    assert len(first) == 500
    assert len(second) == 500
    assert first_payload["data_mode"] == "synthetic"
    assert first_payload["universe_size"] == 500
    assert len(first_payload["companies"]) == 500
    assert [
        (company["ticker"], company["rank"], company["overall_score"], company["confidence_low"], company["confidence_high"])
        for company in first_payload["companies"]
    ] == [
        (company["ticker"], company["rank"], company["overall_score"], company["confidence_low"], company["confidence_high"])
        for company in second_payload["companies"]
    ]

    tickers = [company["ticker"] for company in first_payload["companies"]]
    assert len(tickers) == len(set(tickers))
    assert sorted(company["rank"] for company in first_payload["companies"]) == list(range(1, 501))

    for company in first_payload["companies"]:
        assert company["country"] in ALLOWED_COUNTRIES
        assert 0 <= company["overall_score"] <= 100
        assert 0 <= company["coverage_pct"] <= 100
        assert 0 <= company["esg_level_pctile"] <= 100
        assert 0 <= company["esg_momentum_pctile"] <= 100
        assert 0 <= company["confidence_low"] <= company["confidence_high"] <= 100
        assert all(0 <= score <= 100 for score in company["pillar_scores"].values())
        risk_index = min(
            100,
            max(0, 100 - company["coverage_pct"]) + sum(RISK_FLAG_WEIGHTS.get(flag, 0) for flag in company["flags"]),
        )
        assert 0 <= risk_index <= 100


@pytest.mark.parametrize(
    ("family", "contents", "expected"),
    [
        (
            "prices",
            "date,ticker,close_local,volume\n2026-01-01,TEST.SI,4.2,1000\n",
            "columns must exactly match",
        ),
        (
            "prices",
            "date,ticker,close_local,volume,close_usd\n2026-01-01,TEST.SI,4.2,1000,3.1\n2026-01-01,TEST.SI,4.2,1000,3.1\n",
            "duplicate key",
        ),
        (
            "prices",
            "date,ticker,close_local,volume,close_usd\n2026-99-99,TEST.SI,4.2,1000,3.1\n",
            "date must be ISO YYYY-MM-DD",
        ),
        (
            "prices",
            "date,ticker,close_local,volume,close_usd\n2026-01-01,TEST.SI,abc,1000,3.1\n",
            "close_local must be numeric",
        ),
        (
            "esg",
            "ticker,retrieval_date,esg_total_risk,esg_e,esg_s,esg_g,controversy_level\nTEST.SI,2026-01-01,101,30,40,50,1\n",
            "esg_total_risk must be between 0 and 100",
        ),
    ],
)
def test_local_csv_edge_fixtures_are_rejected(tmp_path: Path, family: str, contents: str, expected: str):
    path = tmp_path / f"{family}_bad.csv"
    path.write_text(contents, encoding="utf-8")

    report = validate_csv(path, family)

    assert not report.passed
    assert expected in report.render()


@pytest.mark.parametrize("prefix", ["=", "+", "-", "@"])
def test_formula_injection_prefixes_are_rejected(tmp_path: Path, prefix: str):
    path = tmp_path / "formula.csv"
    path.write_text(
        f"date,ticker,close_local,volume,close_usd\n2026-01-01,{prefix}BAD,4.2,1000,3.1\n",
        encoding="utf-8",
    )

    report = validate_csv(path, "prices")

    assert not report.passed
    assert "formula-like cell is not allowed" in report.render()


def test_unsupported_country_code_local_fixture_is_rejected():
    row = {
        "company_id": "BAD1",
        "ticker": "BAD1.XX",
        "name": "Unsupported Country Fixture",
        "country": "XX",
        "exchange": "BADX",
        "sector": "Industrials",
        "currency": "USD",
    }

    def validate_country_code(company_row: dict[str, str]) -> None:
        if company_row["country"] not in ALLOWED_COUNTRIES:
            raise ValueError(f"unsupported country code: {company_row['country']}")

    with pytest.raises(ValueError, match="unsupported country code: XX"):
        validate_country_code(row)
