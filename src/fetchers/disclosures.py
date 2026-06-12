"""Best-effort disclosure announcement fetcher.

SGX/Bursa announcement scraping is intentionally optional for the first cut.
This module returns a schema-correct parquet and a failure note if the exchange
endpoints are not integrated yet.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import yaml

from src.util.log import log_action

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_PATH = RAW_DIR / "disclosures_quarterly.parquet"
FAIL_PATH = RAW_DIR / "disclosures_failures.csv"
SOURCE = "disclosures"
SCHEMA = ["ticker", "quarter", "sustainability_announcement_count", "last_announcement_date"]
ENDPOINTS = {
    "SGX": "https://www.sgx.com/securities/company-announcements",
    "Bursa": "https://www.bursamalaysia.com/market_information/announcements/company_announcement",
}


def _load_settings() -> dict[str, Any]:
    with open(PROJECT_ROOT / "config" / "settings.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _fresh(path: Path, hours: int = 24) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < hours * 3600


def fetch(
    universe_df: pd.DataFrame | None = None,
    settings: dict[str, Any] | None = None,
    force: bool = False,
) -> pd.DataFrame:
    """Write an empty schema-correct disclosure parquet with an explicit blocker note."""

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not force and _fresh(OUT_PATH):
        return pd.read_parquet(OUT_PATH)

    settings = settings or _load_settings()
    if universe_df is None:
        universe_df = pd.read_parquet(RAW_DIR / "universe.parquet")

    scoped = universe_df[universe_df["ticker"].astype(str).str.endswith((".SI", ".KL"), na=False)]
    log_action("phase2", "fetch_disclosures_start", inputs={"eligible_tickers": len(scoped)}, outputs={"path": str(OUT_PATH)})
    failures: list[dict[str, str]] = []
    for label, endpoint in ENDPOINTS.items():
        try:
            response = requests.get(endpoint, timeout=8, headers={"User-Agent": "esg-momentum-engine/0.1"})
            failures.append(
                {
                    "ticker": label,
                    "source": SOURCE,
                    "error": f"endpoint status {response.status_code}; parser deferred, wrote empty schema-correct parquet",
                }
            )
        except Exception as exc:  # pragma: no cover - network dependent
            failures.append({"ticker": label, "source": SOURCE, "error": f"endpoint unavailable: {exc}"})

    out = pd.DataFrame(columns=SCHEMA)
    out.to_parquet(OUT_PATH, index=False)
    pd.DataFrame(failures, columns=["ticker", "source", "error"]).to_csv(FAIL_PATH, index=False)
    log_action(
        "phase2",
        "fetch_disclosures_end",
        outputs={"path": str(OUT_PATH), "rows": 0, "eligible_tickers": len(scoped), "failures": len(failures)},
    )
    return out


if __name__ == "__main__":
    df = fetch()
    print(f"disclosures_quarterly rows={len(df)}")
