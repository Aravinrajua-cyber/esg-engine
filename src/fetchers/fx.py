"""Daily FX fetcher for local currency to USD conversion rates."""

from __future__ import annotations

import random
import time
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from src.util.log import log_action

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_PATH = RAW_DIR / "fx_daily.parquet"
FAIL_PATH = RAW_DIR / "fx_failures.csv"
SOURCE = "fx"


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


def _failure_frame(rows: list[dict[str, str]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["ticker", "source", "error"])


def fetch(
    universe_df: pd.DataFrame | None = None,
    settings: dict[str, Any] | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Fetch daily FX rates and write ``data/raw/fx_daily.parquet``.

    Weekend and market-holiday gaps are forward-filled onto a calendar-day index.
    """

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and _fresh(OUT_PATH):
        return pd.read_parquet(OUT_PATH)

    settings = settings or _load_settings()
    if universe_df is None:
        universe_df = pd.read_parquet(RAW_DIR / "universe.parquet")

    log_action("phase2", "fetch_fx_start", outputs={"path": str(OUT_PATH)})
    import yfinance as yf

    start = settings.get("dates", {}).get("prices_start", "2014-01-01")
    end = settings.get("dates", {}).get("end") or date.today().isoformat()
    currencies = sorted(c for c in universe_df["currency"].dropna().unique() if c != "USD")
    market_cfg = settings.get("universe", {}).get("markets", {})
    currency_to_ticker = {
        cfg.get("currency"): cfg.get("fx_ticker")
        for cfg in market_cfg.values()
        if cfg.get("currency") and cfg.get("fx_ticker")
    }

    failures: list[dict[str, str]] = []
    frames: list[pd.DataFrame] = []
    calendar = pd.date_range(start=start, end=end, freq="D")
    for currency in currencies:
        fx_ticker = currency_to_ticker.get(currency) or f"{currency}USD=X"

        def _download():
            return yf.download(
                fx_ticker,
                start=start,
                end=(pd.Timestamp(end) + pd.Timedelta(days=1)).date().isoformat(),
                auto_adjust=True,
                progress=False,
                threads=False,
            )

        raw = _retry(_download, fx_ticker, failures)
        if raw is None or raw.empty:
            failures.append({"ticker": fx_ticker, "source": SOURCE, "error": "no rows returned"})
            continue

        close = raw["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        series = close.reindex(calendar).ffill()
        frame = pd.DataFrame(
            {
                "date": calendar.date.astype(str),
                "currency": currency,
                "fx_to_usd": pd.to_numeric(series, errors="coerce").to_numpy(),
            }
        )
        frames.append(frame)

    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date", "currency", "fx_to_usd"])
    out = out[["date", "currency", "fx_to_usd"]]
    out.to_parquet(OUT_PATH, index=False)
    _failure_frame(failures).to_csv(FAIL_PATH, index=False)
    log_action(
        "phase2",
        "fetch_fx_end",
        outputs={"path": str(OUT_PATH), "rows": len(out), "failures": len(failures)},
    )
    return out


if __name__ == "__main__":
    df = fetch()
    print(f"fx_daily rows={len(df)} currencies={df['currency'].nunique() if not df.empty else 0}")
