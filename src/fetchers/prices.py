"""Daily price fetcher for universe tickers."""

from __future__ import annotations

import random
import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.fetchers import fx
from src.util.log import log_action

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_PATH = RAW_DIR / "prices_daily.parquet"
FAIL_PATH = RAW_DIR / "prices_failures.csv"
SOURCE = "prices"


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


def _chunks(values: list[str], size: int = 50):
    for i in range(0, len(values), size):
        yield values[i : i + size]


def _extract_ticker_frame(raw: pd.DataFrame, ticker: str, multiple: bool) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=["date", "ticker", "close_local", "volume"])
    if multiple:
        if not isinstance(raw.columns, pd.MultiIndex) or ticker not in raw.columns.get_level_values(0):
            return pd.DataFrame(columns=["date", "ticker", "close_local", "volume"])
        part = raw[ticker].copy()
    else:
        part = raw.copy()
    close_col = "Close" if "Close" in part.columns else "Adj Close"
    if close_col not in part.columns:
        return pd.DataFrame(columns=["date", "ticker", "close_local", "volume"])
    out = pd.DataFrame(
        {
            "date": pd.to_datetime(part.index).date.astype(str),
            "ticker": ticker,
            "close_local": pd.to_numeric(part[close_col], errors="coerce"),
            "volume": pd.to_numeric(part.get("Volume"), errors="coerce"),
        }
    )
    return out.dropna(subset=["close_local"], how="all")


def fetch(
    universe_df: pd.DataFrame | None = None,
    settings: dict[str, Any] | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Fetch adjusted daily close and volume, converted to USD with ``fx_daily``."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and _fresh(OUT_PATH):
        return pd.read_parquet(OUT_PATH)

    settings = settings or _load_settings()
    if universe_df is None:
        universe_df = pd.read_parquet(RAW_DIR / "universe.parquet")

    log_action("phase2", "fetch_prices_start", inputs={"tickers": len(universe_df)}, outputs={"path": str(OUT_PATH)})
    import yfinance as yf

    start = settings.get("dates", {}).get("prices_start", "2014-01-01")
    end = settings.get("dates", {}).get("end") or date.today().isoformat()
    tickers = universe_df["ticker"].dropna().astype(str).tolist()
    failures: list[dict[str, str]] = []
    frames: list[pd.DataFrame] = []

    for chunk in _chunks(tickers, 50):
        label = ",".join(chunk[:3]) + ("..." if len(chunk) > 3 else "")

        def _download():
            return yf.download(
                tickers=chunk,
                start=start,
                end=(pd.Timestamp(end) + pd.Timedelta(days=1)).date().isoformat(),
                auto_adjust=True,
                group_by="ticker",
                threads=True,
                progress=False,
            )

        raw = _retry(_download, label, failures)
        if raw is None or raw.empty:
            for ticker in chunk:
                failures.append({"ticker": ticker, "source": SOURCE, "error": "no rows returned"})
            continue
        multiple = len(chunk) > 1
        for ticker in chunk:
            part = _extract_ticker_frame(raw, ticker, multiple)
            if part.empty:
                failures.append({"ticker": ticker, "source": SOURCE, "error": "missing close series"})
            else:
                frames.append(part)

    prices = (
        pd.concat(frames, ignore_index=True)
        if frames
        else pd.DataFrame(columns=["date", "ticker", "close_local", "volume"])
    )
    currency_map = universe_df[["ticker", "currency"]].drop_duplicates()
    prices = prices.merge(currency_map, on="ticker", how="left")
    fx_df = fx.fetch(universe_df, settings, force=force)
    prices = prices.merge(fx_df, on=["date", "currency"], how="left")
    prices["close_usd"] = prices["close_local"] * prices["fx_to_usd"]
    out = prices[["date", "ticker", "close_local", "volume", "close_usd"]].sort_values(["ticker", "date"])
    out.to_parquet(OUT_PATH, index=False)
    pd.DataFrame(failures, columns=["ticker", "source", "error"]).to_csv(FAIL_PATH, index=False)
    log_action(
        "phase2",
        "fetch_prices_end",
        outputs={"path": str(OUT_PATH), "rows": len(out), "resolved_tickers": out["ticker"].nunique(), "failures": len(failures)},
    )
    return out


if __name__ == "__main__":
    df = fetch()
    print(f"prices_daily rows={len(df)} tickers={df['ticker'].nunique() if not df.empty else 0}")
