from __future__ import annotations

import pandas as pd


RAW_SCHEMAS = {
    "universe": ["ticker", "name", "country", "exchange", "sector", "mcap_tier", "currency", "market_cap_usd", "free_float_pct", "adv_usd", "liquidity_flag", "in_backtest", "source"],
    "prices_daily": ["date", "ticker", "close_local", "volume", "close_usd"],
    "fx_daily": ["date", "currency", "fx_to_usd"],
    "esg_snapshot": ["ticker", "retrieval_date", "esg_total_risk", "esg_e", "esg_s", "esg_g", "controversy_level"],
    "fundamentals": ["ticker", "fiscal_date", "period", "revenue", "capex", "total_debt", "interest_expense", "operating_cash_flow", "depreciation"],
    "disclosures_quarterly": ["ticker", "quarter", "sustainability_announcement_count", "last_announcement_date"],
}


def test_fixture_raw_schema_columns(sample_universe):
    assert list(sample_universe.columns) == RAW_SCHEMAS["universe"]


def test_schema_column_order_examples():
    examples = {
        "prices_daily": pd.DataFrame(columns=RAW_SCHEMAS["prices_daily"]),
        "fx_daily": pd.DataFrame(columns=RAW_SCHEMAS["fx_daily"]),
        "esg_snapshot": pd.DataFrame(columns=RAW_SCHEMAS["esg_snapshot"]),
        "fundamentals": pd.DataFrame(columns=RAW_SCHEMAS["fundamentals"]),
        "disclosures_quarterly": pd.DataFrame(columns=RAW_SCHEMAS["disclosures_quarterly"]),
    }
    for name, frame in examples.items():
        assert list(frame.columns) == RAW_SCHEMAS[name]


def test_companies_json_top_level_keys(sample_companies_json):
    # required frozen-contract keys must be present; the live feed adds an additive "meta" block.
    assert {
        "schema_version",
        "generated_at",
        "data_mode",
        "as_of_date",
        "universe_size",
        "model",
        "pillars",
        "flags",
        "companies",
    }.issubset(set(sample_companies_json))
    assert sample_companies_json["schema_version"] == 1
    assert sample_companies_json["data_mode"] in {"live", "synthetic"}
