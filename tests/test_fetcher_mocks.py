from __future__ import annotations

import sys
import types

import pandas as pd
import pytest

from src.fetchers import esg, fundamentals, fx, prices


def test_price_extracts_single_download_frame_successfully():
    raw = pd.DataFrame(
        {"Close": [4.2, 4.3], "Volume": [1000, 1200]},
        index=pd.to_datetime(["2026-01-02", "2026-01-03"]),
    )
    out = prices._extract_ticker_frame(raw, "TESTA.SI", multiple=False)
    assert out.to_dict("records") == [
        {"date": "2026-01-02", "ticker": "TESTA.SI", "close_local": 4.2, "volume": 1000},
        {"date": "2026-01-03", "ticker": "TESTA.SI", "close_local": 4.3, "volume": 1200},
    ]


def test_malformed_price_response_returns_empty_frame():
    raw = pd.DataFrame({"Open": [4.2]}, index=pd.to_datetime(["2026-01-02"]))
    out = prices._extract_ticker_frame(raw, "TESTA.SI", multiple=False)
    assert out.empty


def test_retry_records_timeout_without_network_sleep(monkeypatch):
    failures: list[dict[str, str]] = []
    monkeypatch.setattr(fx.time, "sleep", lambda _: None)

    def raises_timeout():
        raise TimeoutError("local timeout fixture")

    assert fx._retry(raises_timeout, "TESTA.SI", failures, max_tries=2) is None
    assert failures == [{"ticker": "TESTA.SI", "source": "fx", "error": "local timeout fixture"}]


def test_prices_fetch_empty_upstream_records_each_ticker(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "OUT_PATH", tmp_path / "prices_daily.parquet")
    monkeypatch.setattr(prices, "FAIL_PATH", tmp_path / "prices_failures.csv")
    monkeypatch.setattr(prices.fx, "fetch", lambda *_args, **_kwargs: pd.DataFrame(columns=["date", "currency", "fx_to_usd"]))
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(download=lambda **_kwargs: pd.DataFrame()))

    universe = pd.DataFrame({"ticker": ["TESTA.SI", "TESTB.KL"], "currency": ["SGD", "MYR"]})
    out = prices.fetch(universe, {"dates": {"prices_start": "2026-01-01", "end": "2026-01-05"}}, force=True)

    assert out.empty
    failures = pd.read_csv(tmp_path / "prices_failures.csv")
    assert failures["ticker"].tolist() == ["TESTA.SI", "TESTB.KL"]
    assert (failures["error"] == "no rows returned").all()


def test_prices_fetch_partial_coverage_and_missing_fx_series(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "OUT_PATH", tmp_path / "prices_daily.parquet")
    monkeypatch.setattr(prices, "FAIL_PATH", tmp_path / "prices_failures.csv")
    raw = pd.DataFrame(
        {
            ("TESTA.SI", "Close"): [4.0],
            ("TESTA.SI", "Volume"): [1000],
        },
        index=pd.to_datetime(["2026-01-02"]),
    )
    raw.columns = pd.MultiIndex.from_tuples(raw.columns)

    def fake_fx_fetch(*_args, **_kwargs):
        return pd.DataFrame({"date": ["2026-01-03"], "currency": ["SGD"], "fx_to_usd": [0.75]})

    monkeypatch.setattr(prices.fx, "fetch", fake_fx_fetch)
    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(download=lambda **_kwargs: raw))

    universe = pd.DataFrame({"ticker": ["TESTA.SI", "TESTB.KL"], "currency": ["SGD", "SGD"]})
    out = prices.fetch(universe, {"dates": {"prices_start": "2026-01-01", "end": "2026-01-05"}}, force=True)

    assert out["ticker"].tolist() == ["TESTA.SI"]
    assert pd.isna(out.loc[0, "close_usd"])
    failures = pd.read_csv(tmp_path / "prices_failures.csv")
    assert failures.to_dict("records") == [{"ticker": "TESTB.KL", "source": "prices", "error": "missing close series"}]


def test_prices_fetch_surfaces_permission_error_while_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(prices, "OUT_PATH", tmp_path / "prices_daily.parquet")
    monkeypatch.setattr(prices, "FAIL_PATH", tmp_path / "prices_failures.csv")
    monkeypatch.setattr(
        prices.fx,
        "fetch",
        lambda *_args, **_kwargs: pd.DataFrame({"date": ["2026-01-02"], "currency": ["SGD"], "fx_to_usd": [0.75]}),
    )
    monkeypatch.setitem(
        sys.modules,
        "yfinance",
        types.SimpleNamespace(
            download=lambda **_kwargs: pd.DataFrame(
                {"Close": [4.0], "Volume": [1000]},
                index=pd.to_datetime(["2026-01-02"]),
            )
        ),
    )
    monkeypatch.setattr(pd.DataFrame, "to_parquet", lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("denied fixture")))
    universe = pd.DataFrame({"ticker": ["TESTA.SI"], "currency": ["SGD"]})

    with pytest.raises(PermissionError, match="denied fixture"):
        prices.fetch(universe, {"dates": {"prices_start": "2026-01-01", "end": "2026-01-05"}}, force=True)


def test_fundamentals_period_rows_parse_local_statement_frames():
    fiscal_date = pd.Timestamp("2025-12-31")
    financials = pd.DataFrame({fiscal_date: [100.0, 3.0]}, index=["Total Revenue", "Interest Expense"])
    balance = pd.DataFrame({fiscal_date: [40.0]}, index=["Total Debt"])
    cashflow = pd.DataFrame({fiscal_date: [10.0, 12.0, 5.0]}, index=["Capital Expenditure", "Operating Cash Flow", "Depreciation"])

    rows = fundamentals._period_rows("TESTA.SI", "annual", financials, balance, cashflow)

    assert rows == [
        {
            "ticker": "TESTA.SI",
            "fiscal_date": "2025-12-31",
            "period": "annual",
            "revenue": 100.0,
            "capex": 10.0,
            "total_debt": 40.0,
            "interest_expense": 3.0,
            "operating_cash_flow": 12.0,
            "depreciation": 5.0,
        }
    ]


def test_esg_lookup_handles_missing_and_malformed_snapshots():
    assert pd.isna(esg._lookup(None, "totalEsg"))
    malformed = pd.DataFrame({"Value": ["not_numeric"]}, index=["totalEsg"])
    assert pd.isna(esg._lookup(malformed, "totalEsg"))
