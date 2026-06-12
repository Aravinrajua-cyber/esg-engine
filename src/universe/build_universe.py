"""Phase 1 — universe construction (top ~500 ASEAN).

Strategy (per RESEARCH_LOG 2026-06-12):
  - SG/ID/MY/TH: yfinance region screener (the only ASEAN markets it serves), filtered to
    real equities (drops DLCs / structured warrants / Thai depositary receipts).
  - PH/VN: curated seeds (screener returns nothing), validated live.
  - Allocate 500 slots proportionally to each market's aggregate USD market cap.
  - Validate every ticker by a real price download; compute 6m median daily $ volume (ADV);
    flag liquidity < $250k as out-of-backtest (kept in universe + scoreboard).
  - Non-resolving names are logged and dropped — never fabricated.

Run:  python -m src.universe.build_universe
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
import yfinance as yf
from yfinance import EquityQuery

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.util.log import log_action  # noqa: E402
from src.universe.seeds import SEED_MARKETS  # noqa: E402

SETTINGS = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text())
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

REGION_MARKETS = {  # yfinance region code -> (country, suffix, currency)
    "sg": ("Singapore", ".SI", "SGD"),
    "id": ("Indonesia", ".JK", "IDR"),
    "my": ("Malaysia", ".KL", "MYR"),
    "th": ("Thailand", ".BK", "THB"),
}
FX_TICKERS = {
    "SGD": "SGDUSD=X", "IDR": "IDRUSD=X", "MYR": "MYRUSD=X",
    "THB": "THBUSD=X", "PHP": "PHPUSD=X", "VND": "VNDUSD=X",
}
JUNK_NAME_TOKENS = ("DLC", "STRUCTURED", "LEVERAGE", "CALL WARRANT", "PUT WARRANT",
                    "DAILY LEVERAGE", " ETF", "ETF ", "FUND")


def fx_snapshot() -> dict[str, float]:
    """Latest FX (local->USD) per currency; USD=1.0. Per-ticker fetch with retry (the batch
    download intermittently hits the yfinance sqlite cache lock)."""
    out = {"USD": 1.0}
    for cur, tk in FX_TICKERS.items():
        val = np.nan
        for attempt in range(4):
            try:
                h = yf.Ticker(tk).history(period="1mo")["Close"].dropna()
                if len(h):
                    val = float(h.iloc[-1])
                    break
            except Exception:
                pass
            time.sleep(1.5 * (attempt + 1))
        out[cur] = val
    return out


def screen_region(reg: str, max_size: int = 250) -> list[dict]:
    q = EquityQuery("and", [
        EquityQuery("eq", ["region", reg]),
        EquityQuery("gt", ["intradaymarketcap", 200_000_000]),
    ])
    try:
        r = yf.screen(q, size=max_size, sortField="intradaymarketcap", sortAsc=False)
        return [x for x in r.get("quotes", []) if x.get("quoteType") == "EQUITY"]
    except Exception as e:
        log_action("phase1", "screen_region_failed", {"region": reg}, {"err": str(e)}, "error")
        return []


def is_junk(symbol: str, name: str, country: str) -> bool:
    nm = (name or "").upper()
    if any(tok in nm for tok in JUNK_NAME_TOKENS):
        return True
    bare = symbol.split(".")[0]
    if country == "Thailand":  # depositary receipts carry digits or -R/-F suffixes
        if any(c.isdigit() for c in bare) or bare.endswith(("-R", "-F")):
            return True
    if country == "Singapore":
        # SGX Depository Receipts (SDRs) of foreign/cross-listed firms — double-counted and
        # mcap-inflating. They carry "SDR" in the name or a 4-letter ticker ending in 'D'
        # (HPCD, HBND, TDED, IBKD, HSHD, HTCD, ...). Real SGX codes use digits or other endings.
        if "SDR" in nm or re.fullmatch(r"[A-Z]{3}D", bare):
            return True
    return False


def gather_candidates() -> pd.DataFrame:
    rows = []
    # Screener markets
    for reg, (country, suffix, currency) in REGION_MARKETS.items():
        quotes = screen_region(reg)
        for x in quotes:
            sym = x.get("symbol", "")
            name = x.get("longName") or x.get("shortName") or sym
            if not sym.endswith(suffix) or is_junk(sym, name, country):
                continue
            rows.append({
                "ticker": sym, "name": name, "country": country, "currency": currency,
                "sector": x.get("sector"), "market_cap_local": x.get("marketCap"),
                "source": "screener",
            })
        log_action("phase1", "screened", {"region": reg}, {"kept": len(quotes)})
        time.sleep(1.0)
    # Seed markets (PH, VN)
    for country, (suffix, codes) in SEED_MARKETS.items():
        currency = "PHP" if country == "Philippines" else "VND"
        for code in codes:
            rows.append({
                "ticker": code + suffix, "name": code, "country": country,
                "currency": currency, "sector": None, "market_cap_local": None,
                "source": "seed",
            })
    return pd.DataFrame(rows).drop_duplicates("ticker").reset_index(drop=True)


def validate_and_enrich(df: pd.DataFrame, fx: dict[str, float]) -> pd.DataFrame:
    """Batch-download 6m history; keep tickers that resolve; compute ADV (USD) and fill mcap."""
    tickers = df["ticker"].tolist()
    px = yf.download(tickers, period="6mo", progress=False, auto_adjust=True,
                     group_by="ticker", threads=True)
    keep, advs, mcaps = [], {}, {}
    for t in tickers:
        try:
            sub = px[t] if isinstance(px.columns, pd.MultiIndex) else px
            close = sub["Close"].dropna()
            vol = sub["Volume"].reindex(close.index)
            if len(close) < 60:
                continue
            cur = df.loc[df.ticker == t, "currency"].iloc[0]
            fxr = fx.get(cur, np.nan)
            dollar_vol = (close * vol * fxr).dropna()
            advs[t] = float(dollar_vol.median()) if len(dollar_vol) else np.nan
            keep.append(t)
            # fill missing market cap (seeds) from fast_info shares*price
            ml = df.loc[df.ticker == t, "market_cap_local"].iloc[0]
            if ml is None or (isinstance(ml, float) and np.isnan(ml)):
                try:
                    fi = yf.Ticker(t).fast_info
                    sh = getattr(fi, "shares", None)
                    if sh:
                        mcaps[t] = float(sh) * float(close.iloc[-1])
                except Exception:
                    pass
        except Exception:
            continue
    df = df[df.ticker.isin(keep)].copy()
    df["adv_usd"] = df.ticker.map(advs)
    df["market_cap_local"] = [mcaps.get(t, df.loc[df.ticker == t, "market_cap_local"].iloc[0])
                              for t in df.ticker]
    df["market_cap_usd"] = df.apply(
        lambda r: (r.market_cap_local or np.nan) * fx.get(r.currency, np.nan), axis=1)
    # Sanity ceiling: no ASEAN listed company exceeds ~USD 150B. Larger "market caps" are
    # mislabelled structured products / DLCs (e.g. HSBC daily-leverage certs on SES) that slipped
    # past the name filter — drop them so they neither distort allocation nor get GDELT-fetched.
    before = len(df)
    df = df[~(df.market_cap_usd > 1.5e11)].copy()
    # Dedupe dual-listed lines sharing a company name (e.g. SingTel Z74/Z77), keep largest mcap.
    df = df.sort_values("market_cap_usd", ascending=False).drop_duplicates("name", keep="first")
    log_action("phase1", "mcap_ceiling_filter", {"ceiling_usd": 1.5e11},
               {"dropped": before - len(df)})
    dropped = len(tickers) - len(keep)
    log_action("phase1", "validated", {"candidates": len(tickers)},
               {"resolved": len(keep), "dropped": dropped})
    return df


def allocate(df: pd.DataFrame, target: int, max_share: float = 0.25) -> pd.DataFrame:
    """Allocate `target` slots proportionally to each market's aggregate USD market cap, with a
    per-market share cap (default 25%) and pro-rata redistribution of the excess.

    Rationale (documented in RESEARCH_LOG): the yfinance screener caps results at 250/market, which
    truncates the long tail of the larger markets (ID, MY) and biases their captured aggregate
    downward; SGX additionally hosts foreign secondary listings. The cap prevents any single market
    from dominating and lands the country mix close to true ASEAN market-cap shares."""
    agg = df.groupby("country")["market_cap_usd"].sum()
    w = (agg / agg.sum()).astype(float)
    for _ in range(10):                       # iteratively cap + redistribute
        over = w[w > max_share]
        if over.empty:
            break
        excess = float((over - max_share).sum())
        w[over.index] = max_share
        under = w[w < max_share]
        if under.sum() == 0:
            break
        w[under.index] += excess * (under / under.sum())
    quota = (w * target).round().astype(int).to_dict()
    chosen = []
    for country, n in quota.items():
        sub = df[df.country == country].sort_values("market_cap_usd", ascending=False)
        chosen.append(sub.head(n))
    out = pd.concat(chosen).reset_index(drop=True)
    log_action("phase1", "allocated", {"target": target, "max_share": max_share},
               {"raw_share": (agg / agg.sum()).round(3).to_dict(),
                "capped_quota": quota, "selected": len(out)})
    return out


def finalize(df: pd.DataFrame) -> pd.DataFrame:
    tiers = SETTINGS["universe"]["mcap_tiers"]
    min_adv = SETTINGS["universe"]["liquidity_min_median_daily_dollar_volume_usd"]
    df["exchange"] = df["country"].map(
        {"Singapore": "SGX", "Indonesia": "IDX", "Malaysia": "Bursa",
         "Thailand": "SET", "Philippines": "PSE", "Vietnam": "HOSE_HNX"})
    df["mcap_tier"] = np.where(df.market_cap_usd >= tiers["mega_usd"], "mega",
                       np.where(df.market_cap_usd >= tiers["large_usd"], "large", "mid"))
    df["liquidity_flag"] = df.adv_usd < min_adv      # True = low liquidity
    df["in_backtest"] = ~df.liquidity_flag.fillna(True)
    df["free_float_pct"] = np.nan
    cols = ["ticker", "name", "country", "exchange", "sector", "mcap_tier", "currency",
            "market_cap_usd", "free_float_pct", "adv_usd", "liquidity_flag",
            "in_backtest", "source"]
    return df[cols].sort_values("market_cap_usd", ascending=False).reset_index(drop=True)


def main():
    print("Phase 1 — universe construction")
    fx = fx_snapshot()
    print("  FX:", {k: round(v, 6) for k, v in fx.items()})
    cand = gather_candidates()
    print(f"  candidates: {len(cand)} ({cand.country.value_counts().to_dict()})")
    cand = validate_and_enrich(cand, fx)
    print(f"  resolved:   {len(cand)}")
    uni = allocate(cand, SETTINGS["universe"]["target_size"])
    uni = finalize(uni)
    out = RAW / "universe.parquet"
    uni.to_parquet(out, index=False)
    print(f"  WROTE {out}: {len(uni)} names")
    print(uni.country.value_counts().to_dict())
    print(f"  low-liquidity (excluded from backtest): {int(uni.liquidity_flag.sum())}")
    print(f"  acceptance gate >=450: {'PASS' if len(uni) >= 450 else 'SHORTFALL — document'}")
    log_action("phase1", "universe_built", {},
               {"n": len(uni), "by_country": uni.country.value_counts().to_dict(),
                "low_liq": int(uni.liquidity_flag.sum())})


if __name__ == "__main__":
    main()
