"""Yahoo Finance fundamentals fetcher."""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.util.log import log_action

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_PATH = RAW_DIR / "fundamentals.parquet"
FAIL_PATH = RAW_DIR / "fundamentals_failures.csv"
SOURCE = "fundamentals"
SCHEMA = [
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

FIELD_ALIASES = {
    "revenue": ["Total Revenue", "Operating Revenue", "Revenue"],
    "capex": ["Capital Expenditure", "Capital Expenditures", "Purchase Of PPE", "Capital Expenditure Reported"],
    "total_debt": ["Total Debt", "Long Term Debt And Capital Lease Obligation", "Long Term Debt", "Short Long Term Debt Total"],
    "interest_expense": ["Interest Expense", "Interest Expense Non Operating", "Interest Paid Supplemental Data"],
    "operating_cash_flow": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    "depreciation": ["Depreciation", "Depreciation And Amortization", "Reconciled Depreciation"],
}


def _load_settings() -> dict[str, Any]:
    with open(PROJECT_ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fresh(path: Path, hours: int = 24) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < hours * 3600


def _retry(callable_, ticker: str, failures: list[dict[str, str]], max_tries: int = 5):
    last_error: Exception | None = None
    for attempt in range(max_tries):
        try:
            return callable_()
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            if attempt < max_tries - 1:
                time.sleep(min(2 * (2**attempt), 30) + random.uniform(0, 1))
    failures.append({"ticker": ticker, "source": SOURCE, "error": str(last_error)})
    return None


def _value(frame: pd.DataFrame, fiscal_date, aliases: list[str]) -> float:
    if frame is None or frame.empty:
        return float("nan")
    lookup = {str(idx).strip().lower(): idx for idx in frame.index}
    for alias in aliases:
        idx = lookup.get(alias.lower())
        if idx is not None and fiscal_date in frame.columns:
            return pd.to_numeric(frame.at[idx, fiscal_date], errors="coerce")
    return float("nan")


def _period_rows(ticker: str, period: str, financials: pd.DataFrame, balance: pd.DataFrame, cashflow: pd.DataFrame):
    columns = set()
    for frame in (financials, balance, cashflow):
        if frame is not None and not frame.empty:
            columns.update(frame.columns)
    rows = []
    for fiscal_date in sorted(columns):
        rows.append(
            {
                "ticker": ticker,
                "fiscal_date": pd.Timestamp(fiscal_date).date().isoformat(),
                "period": period,
                "revenue": _value(financials, fiscal_date, FIELD_ALIASES["revenue"]),
                "capex": _value(cashflow, fiscal_date, FIELD_ALIASES["capex"]),
                "total_debt": _value(balance, fiscal_date, FIELD_ALIASES["total_debt"]),
                "interest_expense": _value(financials, fiscal_date, FIELD_ALIASES["interest_expense"]),
                "operating_cash_flow": _value(cashflow, fiscal_date, FIELD_ALIASES["operating_cash_flow"]),
                "depreciation": _value(cashflow, fiscal_date, FIELD_ALIASES["depreciation"]),
            }
        )
    return rows


def fetch(
    universe_df: pd.DataFrame | None = None,
    settings: dict[str, Any] | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Fetch annual and quarterly fundamentals in long format."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and _fresh(OUT_PATH):
        return pd.read_parquet(OUT_PATH)

    settings = settings or _load_settings()
    if universe_df is None:
        universe_df = pd.read_parquet(RAW_DIR / "universe.parquet")

    log_action("phase2", "fetch_fundamentals_start", inputs={"tickers": len(universe_df)}, outputs={"path": str(OUT_PATH)})
    import yfinance as yf

    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for ticker in universe_df["ticker"].dropna().astype(str):
        ticker_obj = _retry(lambda t=ticker: yf.Ticker(t), ticker, failures)
        if ticker_obj is None:
            continue
        annual = _retry(
            lambda obj=ticker_obj: (obj.financials, obj.balance_sheet, obj.cashflow),
            ticker,
            failures,
        )
        quarterly = _retry(
            lambda obj=ticker_obj: (obj.quarterly_financials, obj.quarterly_balance_sheet, obj.quarterly_cashflow),
            ticker,
            failures,
        )
        ticker_rows = []
        if annual is not None:
            ticker_rows.extend(_period_rows(ticker, "annual", *annual))
        if quarterly is not None:
            ticker_rows.extend(_period_rows(ticker, "quarter", *quarterly))
        if not ticker_rows:
            failures.append({"ticker": ticker, "source": SOURCE, "error": "no fundamentals returned"})
        rows.extend(ticker_rows)

    out = pd.DataFrame(rows, columns=SCHEMA)
    out.to_parquet(OUT_PATH, index=False)
    pd.DataFrame(failures, columns=["ticker", "source", "error"]).to_csv(FAIL_PATH, index=False)
    log_action(
        "phase2",
        "fetch_fundamentals_end",
        outputs={"path": str(OUT_PATH), "rows": len(out), "resolved_tickers": out["ticker"].nunique() if not out.empty else 0, "failures": len(failures)},
    )
    return out


if __name__ == "__main__":
    df = fetch()
    print(f"fundamentals rows={len(df)} tickers={df['ticker'].nunique() if not df.empty else 0}")
