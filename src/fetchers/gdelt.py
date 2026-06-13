"""Phase 2.3 — GDELT 2.0 news-sentiment fetcher (the long pole).

For each company: monthly average tone + article volume, gdelt_start -> today, from the GDELT
DOC 2.0 API (TimelineTone + TimelineVolRaw). Resumable via per-ticker cache files
(data/raw/gdelt_cache/<ticker>.parquet); a re-run skips completed tickers. Honors a request
interval and retries with exponential backoff + jitter. Aggregates to
data/raw/sentiment_monthly.parquet (schema in SCHEMAS.md).

Owned by Claude (do not let Codex edit). Run:
    python -m src.fetchers.gdelt                 # full universe, resumable
    python -m src.fetchers.gdelt --limit 3       # smoke test on first 3 names
    python -m src.fetchers.gdelt --interval 2.5  # override request spacing (seconds)
"""

from __future__ import annotations

import argparse
import random
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.util.log import log_action          # noqa: E402
from src.universe.seeds import VN_NAMES       # noqa: E402

SETTINGS = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text())
G = SETTINGS["gdelt"]
RAW = ROOT / "data" / "raw"
CACHE = RAW / "gdelt_cache"
CACHE.mkdir(parents=True, exist_ok=True)

# Legal-form / suffix tokens stripped to get a cleaner query phrase (higher article volume).
_SUFFIX = re.compile(
    r"\b(public company limited|pcl|limited|ltd|berhad|bhd|tbk|plc|"
    r"incorporated|inc|corporation|corp|company|co)\b\.?", re.IGNORECASE)
_PREFIX = re.compile(r"^pt\s+", re.IGNORECASE)   # Indonesian "PT " prefix


def clean_name(name: str, ticker: str, country: str) -> str:
    """Best query phrase for a company. VN codes are mapped to real names; legal suffixes stripped."""
    if country == "Vietnam":
        base = VN_NAMES.get(ticker.split(".")[0], name)
    else:
        base = name or ticker
    base = _PREFIX.sub("", base)
    base = _SUFFIX.sub("", base)
    base = re.sub(r"\s+", " ", base).strip(" ,.-")
    return base


_last_request_ts = 0.0   # module-level: enforce global min spacing across tone+vol calls


def _space(interval: float) -> None:
    """Sleep so consecutive GDELT requests are >= `interval` seconds apart (global)."""
    global _last_request_ts
    wait = interval - (time.time() - _last_request_ts)
    if wait > 0:
        time.sleep(wait)
    _last_request_ts = time.time()


def _request(query: str, mode: str, start: str, end: str, interval: float) -> tuple[list[dict], str]:
    """One GDELT timeline request -> (data, status). status in {ok, empty, throttled, fail}.
    Retries 429/transient with backoff; honors global min spacing."""
    params = {
        "query": f'"{query}"', "mode": mode, "format": "json",
        "startdatetime": start, "enddatetime": end, "timelinesmooth": "0",
    }
    throttled = False
    for attempt in range(G["max_retries"]):
        _space(interval)
        try:
            r = requests.get(G["base_url"], params=params, timeout=90)
            if r.status_code == 429 or "limit requests" in r.text[:80].lower():
                throttled = True
                time.sleep(G["backoff_base_seconds"] * (1.7 ** attempt) + random.uniform(0, 4))
                continue
            if r.status_code != 200 or not r.text.strip().startswith("{"):
                time.sleep(G["backoff_base_seconds"] + random.uniform(0, 2))
                continue
            tl = r.json().get("timeline", [])
            return (tl[0]["data"] if tl else [], "ok" if tl else "empty")
        except Exception:
            time.sleep(G["backoff_base_seconds"] * (1.4 ** attempt) + random.uniform(0, 2))
    return ([], "throttled" if throttled else "fail")


def fetch_company(query: str, start: str, end: str, interval: float) -> tuple[pd.DataFrame, bool]:
    """Monthly tone + volume for one company. Returns (df, throttled). df empty if no coverage."""
    empty = pd.DataFrame(columns=["month", "avg_tone", "article_volume", "obs_days"])
    tone, ts = _request(query, "TimelineTone", start, end, interval)
    vol, vs = _request(query, "TimelineVolRaw", start, end, interval)
    throttled = "throttled" in (ts, vs)
    if not tone and not vol:
        return empty, throttled

    def _series(points, col):
        if not points:
            return pd.Series(dtype=float, name=col)
        df = pd.DataFrame(points)
        df["date"] = pd.to_datetime(df["date"], errors="coerce", utc=True).dt.tz_localize(None)
        df = df.dropna(subset=["date"]).set_index("date")["value"].astype(float)
        df.name = col
        return df

    t = _series(tone, "avg_tone")
    v = _series(vol, "article_volume")
    if t.empty and v.empty:
        return pd.DataFrame(columns=["month", "avg_tone", "article_volume", "obs_days"])
    daily = pd.concat([t, v], axis=1)
    monthly = pd.DataFrame({
        "avg_tone": daily["avg_tone"].resample("MS").mean() if "avg_tone" in daily else np.nan,
        "article_volume": daily["article_volume"].resample("MS").sum() if "article_volume" in daily else np.nan,
        "obs_days": daily["avg_tone"].resample("MS").count() if "avg_tone" in daily else 0,
    })
    monthly = monthly[(monthly["article_volume"].fillna(0) > 0) | (monthly["obs_days"] > 0)]
    return monthly.reset_index(names="month"), throttled


def fetch_all_sentiment(limit: int | None = None, interval: float | None = None,
                        universe_path: Path | None = None) -> pd.DataFrame:
    interval = interval if interval is not None else G["request_interval_seconds"]
    uni = pd.read_parquet(universe_path or RAW / "universe.parquet")
    if limit:
        uni = uni.head(limit)
    start = SETTINGS["dates"]["gdelt_start"].replace("-", "") + "000000"
    end = pd.Timestamp.today().strftime("%Y%m%d") + "000000"
    if G.get("initial_cooldown_s", 0):
        print(f"  initial cooldown {G['initial_cooldown_s']}s ...", flush=True)
        time.sleep(G["initial_cooldown_s"])
    log_action("phase2", "gdelt_start", {"n": len(uni), "interval": interval},
               {"start": start, "end": end})

    cooldown = G.get("consecutive_throttle_cooldown_s", 180)
    failures, consec_throttle = [], 0
    try:
        for i, row in enumerate(uni.itertuples(index=False), 1):
            cache = CACHE / f"{row.ticker.replace('.', '_')}.parquet"
            if cache.exists():
                continue
            query = clean_name(row.name, row.ticker, row.country)
            try:
                df, throttled = fetch_company(query, start, end, interval)
                if throttled and len(df) == 0:           # circuit breaker: GDELT is throttling us
                    consec_throttle += 1
                    wait = cooldown * min(consec_throttle, 4)
                    print(f"  [{i}/{len(uni)}] {row.ticker:<10} THROTTLED — cooldown {wait}s then retry", flush=True)
                    time.sleep(wait)
                    df, throttled = fetch_company(query, start, end, interval)  # one retry
                if not throttled:
                    consec_throttle = 0
                df.insert(0, "ticker", row.ticker)
                df.to_parquet(cache, index=False)        # cache even if empty (re-fill pass can skip)
                status = "ok" if len(df) else "empty"
                print(f"  [{i}/{len(uni)}] {row.ticker:<10} '{query}' -> {len(df)} months ({status})", flush=True)
            except Exception as e:
                failures.append({"ticker": row.ticker, "query": query, "error": str(e)})
                print(f"  [{i}/{len(uni)}] {row.ticker:<10} FAILED: {str(e)[:70]}", flush=True)
    finally:
        agg = _aggregate()
        if failures:
            pd.DataFrame(failures).to_csv(RAW / "gdelt_failures.csv", index=False)
        log_action("phase2", "gdelt_done",
                   {"n": len(uni)},
                   {"rows": len(agg), "tickers_with_data": agg["ticker"].nunique() if len(agg) else 0,
                    "failures": len(failures)})
    return agg


def _aggregate() -> pd.DataFrame:
    """Concatenate all per-ticker caches into data/raw/sentiment_monthly.parquet."""
    frames = [pd.read_parquet(p) for p in sorted(CACHE.glob("*.parquet"))]
    frames = [f for f in frames if len(f)]
    if not frames:
        out = pd.DataFrame(columns=["ticker", "month", "article_volume", "avg_tone", "obs_days"])
    else:
        out = pd.concat(frames, ignore_index=True)
        out = out[["ticker", "month", "article_volume", "avg_tone", "obs_days"]]
    out.to_parquet(RAW / "sentiment_monthly.parquet", index=False)
    return out


def refill_empty() -> int:
    """Delete empty / zero-volume caches so the next run retries only those. Returns count removed."""
    removed = 0
    for p in CACHE.glob("*.parquet"):
        df = pd.read_parquet(p)
        if len(df) == 0 or df["article_volume"].fillna(0).sum() == 0:
            p.unlink()
            removed += 1
    print(f"refill: removed {removed} empty/zero-volume caches; re-run to fetch them.")
    return removed


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--interval", type=float, default=None)
    ap.add_argument("--universe", type=str, default=None,
                    help="path to a universe parquet to fetch (default: data/raw/universe.parquet); "
                         "use data/interim/discovery_universe.parquet for the liquid discovery scope")
    ap.add_argument("--refill", action="store_true",
                    help="delete empty/zero-volume caches then exit (re-run to fetch them)")
    args = ap.parse_args()
    if args.refill:
        refill_empty()
        raise SystemExit(0)
    upath = Path(args.universe) if args.universe else None
    print(f"GDELT sentiment fetch (universe={args.universe or 'full'}, limit={args.limit}, "
          f"interval={args.interval}) ...", flush=True)
    df = fetch_all_sentiment(limit=args.limit, interval=args.interval, universe_path=upath)
    print(f"\nDONE. sentiment_monthly.parquet: {len(df)} rows, "
          f"{df['ticker'].nunique() if len(df) else 0} tickers with data.")
