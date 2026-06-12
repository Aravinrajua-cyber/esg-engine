from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"

FX_COLUMNS = ["date", "currency", "fx_to_usd"]
PRICE_COLUMNS = ["date", "ticker", "close_local", "volume", "close_usd"]
ESG_COLUMNS = ["ticker", "retrieval_date", "esg_total_risk", "esg_e", "esg_s", "esg_g", "controversy_level"]
FUNDAMENTALS_COLUMNS = [
    "ticker",
    "fiscal_date",
    "period",
    "revenue",
    "capex",
    "total_debt",
    "interest_expense",
    "operating_cash_flow",
    "depreciation",
]


def check_raw_contract(
    artifact: str,
    frame: pd.DataFrame,
    *,
    fx_frame: pd.DataFrame | None = None,
    ticker_currency: dict[str, str] | None = None,
) -> None:
    if artifact == "fx":
        assert list(frame.columns) == FX_COLUMNS, "fx columns"
        assert not frame.duplicated(["date", "currency"]).any(), "fx key duplicate"
        assert (pd.to_numeric(frame["fx_to_usd"], errors="coerce") > 0).all(), "fx_to_usd"
        dates = pd.to_datetime(frame["date"])
        for currency, group in frame.assign(_date=dates).groupby("currency"):
            observed = group["_date"].sort_values().reset_index(drop=True)
            expected = pd.Series(pd.date_range(observed.min(), observed.max(), freq="D"))
            assert observed.equals(expected), f"fx date continuity {currency}"
        return

    if artifact == "prices":
        assert list(frame.columns) == PRICE_COLUMNS, "prices columns"
        assert not frame.duplicated(["date", "ticker"]).any(), "prices key duplicate"
        for column in ["close_local", "volume", "close_usd"]:
            non_null = pd.to_numeric(frame[column], errors="coerce").dropna()
            assert (non_null >= 0).all(), column
        assert frame.loc[frame["close_local"].isna(), "close_usd"].isna().all(), "close_usd NaN"
        assert fx_frame is not None, "fx_frame required"
        assert ticker_currency is not None, "ticker_currency required"
        priced = frame.assign(currency=frame["ticker"].map(ticker_currency)).merge(
            fx_frame,
            on=["date", "currency"],
            how="left",
        )
        comparable = priced.dropna(subset=["close_local", "close_usd", "fx_to_usd"])
        expected = comparable["close_local"] * comparable["fx_to_usd"]
        assert ((comparable["close_usd"] - expected).abs() <= expected.abs().clip(lower=1.0) * 1e-6).all(), "close_usd"
        return

    if artifact == "esg":
        assert list(frame.columns) == ESG_COLUMNS, "esg columns"
        assert not frame.duplicated(["ticker"]).any(), "ticker key duplicate"
        assert frame["retrieval_date"].nunique(dropna=False) == 1, "retrieval_date"
        controversy = pd.to_numeric(frame["controversy_level"], errors="coerce")
        valid = frame["controversy_level"].isna() | ((controversy % 1 == 0) & controversy.between(0, 5))
        assert valid.all(), "controversy_level"
        return

    if artifact == "fundamentals":
        assert list(frame.columns) == FUNDAMENTALS_COLUMNS, "fundamentals columns"
        assert frame["period"].isin({"annual", "quarter"}).all(), "period"
        assert not frame.duplicated(["ticker", "fiscal_date", "period"]).any(), "fundamentals key duplicate"
        return

    raise AssertionError(f"unknown artifact {artifact}")


def _valid_fixtures() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, dict[str, str]]:
    fx = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-01", "2026-01-02", "2026-01-03"],
            "currency": ["SGD", "SGD", "SGD", "MYR", "MYR", "MYR"],
            "fx_to_usd": [0.75, 0.75, 0.76, 0.21, 0.21, 0.22],
        }
    )
    prices = pd.DataFrame(
        {
            "date": ["2026-01-02", "2026-01-02", "2026-01-03"],
            "ticker": ["TESTA.SI", "TESTB.KL", "TESTA.SI"],
            "close_local": [4.0, 10.0, None],
            "volume": [1000.0, 2000.0, 0.0],
            "close_usd": [3.0, 2.1, None],
        }
    )
    esg = pd.DataFrame(
        {
            "ticker": ["TESTA.SI", "TESTB.KL"],
            "retrieval_date": ["2026-01-03", "2026-01-03"],
            "esg_total_risk": [20.0, None],
            "esg_e": [5.0, None],
            "esg_s": [7.0, None],
            "esg_g": [8.0, None],
            "controversy_level": [1.0, None],
        }
    )
    fundamentals = pd.DataFrame(
        {
            "ticker": ["TESTA.SI", "TESTA.SI"],
            "fiscal_date": ["2025-12-31", "2026-03-31"],
            "period": ["annual", "quarter"],
            "revenue": [100.0, 25.0],
            "capex": [10.0, 2.0],
            "total_debt": [40.0, 42.0],
            "interest_expense": [3.0, 1.0],
            "operating_cash_flow": [12.0, 4.0],
            "depreciation": [5.0, 1.0],
        }
    )
    return fx, prices, esg, fundamentals, {"TESTA.SI": "SGD", "TESTB.KL": "MYR"}


@pytest.mark.parametrize("artifact", ["fx", "prices", "esg", "fundamentals"])
def test_valid_fixture_contracts(artifact: str):
    fx, prices, esg, fundamentals, ticker_currency = _valid_fixtures()
    frames = {"fx": fx, "prices": prices, "esg": esg, "fundamentals": fundamentals}
    check_raw_contract(artifact, frames[artifact], fx_frame=fx, ticker_currency=ticker_currency)


@pytest.mark.parametrize(
    ("artifact", "mutate", "message"),
    [
        ("fx", lambda df: df.drop(columns=["fx_to_usd"]), "fx columns"),
        ("fx", lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True), "fx key duplicate"),
        ("fx", lambda df: df.assign(fx_to_usd=[-1.0] + df["fx_to_usd"].tolist()[1:]), "fx_to_usd"),
        ("prices", lambda df: df.drop(columns=["close_usd"]), "prices columns"),
        ("prices", lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True), "prices key duplicate"),
        ("prices", lambda df: df.assign(volume=[-1.0, 1.0, 1.0]), "volume"),
        ("esg", lambda df: df.drop(columns=["controversy_level"]), "esg columns"),
        ("esg", lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True), "ticker key duplicate"),
        ("esg", lambda df: df.assign(controversy_level=[6.0, None]), "controversy_level"),
        ("fundamentals", lambda df: df.drop(columns=["period"]), "fundamentals columns"),
        ("fundamentals", lambda df: pd.concat([df, df.iloc[[0]]], ignore_index=True), "fundamentals key duplicate"),
        ("fundamentals", lambda df: df.assign(period=["annual", "monthly"]), "period"),
    ],
)
def test_corrupted_fixture_contracts_fail(artifact: str, mutate, message: str):
    fx, prices, esg, fundamentals, ticker_currency = _valid_fixtures()
    frames = {"fx": fx, "prices": prices, "esg": esg, "fundamentals": fundamentals}
    with pytest.raises(AssertionError, match=message):
        check_raw_contract(artifact, mutate(frames[artifact]), fx_frame=fx, ticker_currency=ticker_currency)


@pytest.mark.parametrize(
    ("artifact", "path"),
    [
        ("fx", RAW_DIR / "fx_daily.parquet"),
        ("prices", RAW_DIR / "prices_daily.parquet"),
        ("esg", RAW_DIR / "esg_snapshot.parquet"),
        ("fundamentals", RAW_DIR / "fundamentals.parquet"),
    ],
)
def test_real_raw_artifact_contracts_skip_when_absent(artifact: str, path: Path):
    if not path.exists():
        pytest.skip(f"{artifact} artifact not yet fetched")
    frame = pd.read_parquet(path)
    kwargs = {}
    if artifact == "prices":
        fx_path = RAW_DIR / "fx_daily.parquet"
        universe_path = RAW_DIR / "universe.parquet"
        if not fx_path.exists() or not universe_path.exists():
            pytest.skip("prices contract requires fetched FX and universe artifacts")
        universe = pd.read_parquet(universe_path)
        kwargs["fx_frame"] = pd.read_parquet(fx_path)
        kwargs["ticker_currency"] = dict(zip(universe["ticker"], universe["currency"], strict=False))
    check_raw_contract(artifact, frame, **kwargs)
