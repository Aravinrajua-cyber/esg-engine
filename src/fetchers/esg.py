"""Yahoo Finance sustainability snapshot fetcher."""

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
OUT_PATH = RAW_DIR / "esg_snapshot.parquet"
FAIL_PATH = RAW_DIR / "esg_failures.csv"
SOURCE = "esg"
SCHEMA = ["ticker", "retrieval_date", "esg_total_risk", "esg_e", "esg_s", "esg_g", "controversy_level"]


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


def _lookup(sustainability: pd.DataFrame | None, *names: str) -> float:
    if sustainability is None or sustainability.empty:
        return float("nan")
    series = sustainability.iloc[:, 0] if isinstance(sustainability, pd.DataFrame) else sustainability
    normalized = {str(idx).strip().lower().replace(" ", ""): val for idx, val in series.items()}
    for name in names:
        val = normalized.get(name.lower().replace(" ", ""))
        if val is not None:
            return pd.to_numeric(val, errors="coerce")
    return float("nan")


def fetch(
    universe_df: pd.DataFrame | None = None,
    settings: dict[str, Any] | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Fetch Sustainalytics risk snapshot from Yahoo Finance where available."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and _fresh(OUT_PATH):
        return pd.read_parquet(OUT_PATH)

    settings = settings or _load_settings()
    if universe_df is None:
        universe_df = pd.read_parquet(RAW_DIR / "universe.parquet")

    log_action("phase2", "fetch_esg_start", inputs={"tickers": len(universe_df)}, outputs={"path": str(OUT_PATH)})
    import yfinance as yf

    retrieval_date = date.today().isoformat()
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for ticker in universe_df["ticker"].dropna().astype(str):
        sustainability = _retry(lambda t=ticker: yf.Ticker(t).sustainability, ticker, failures)
        if sustainability is None or getattr(sustainability, "empty", True):
            failures.append({"ticker": ticker, "source": SOURCE, "error": "missing sustainability snapshot"})
            sustainability = None
        rows.append(
            {
                "ticker": ticker,
                "retrieval_date": retrieval_date,
                "esg_total_risk": _lookup(sustainability, "totalEsg", "total ESG risk score"),
                "esg_e": _lookup(sustainability, "environmentScore", "environment risk score"),
                "esg_s": _lookup(sustainability, "socialScore", "social risk score"),
                "esg_g": _lookup(sustainability, "governanceScore", "governance risk score"),
                "controversy_level": _lookup(sustainability, "highestControversy", "controversy level"),
            }
        )

    out = pd.DataFrame(rows, columns=SCHEMA)
    out.to_parquet(OUT_PATH, index=False)
    pd.DataFrame(failures, columns=["ticker", "source", "error"]).to_csv(FAIL_PATH, index=False)
    log_action(
        "phase2",
        "fetch_esg_end",
        outputs={"path": str(OUT_PATH), "rows": len(out), "resolved_tickers": int(out["esg_total_risk"].notna().sum()), "failures": len(failures)},
    )
    return out


if __name__ == "__main__":
    df = fetch()
    print(f"esg_snapshot rows={len(df)} resolved={int(df['esg_total_risk'].notna().sum()) if not df.empty else 0}")
