# SPEC 01 — Data fetchers + synthetic demo (Codex)

Read `AGENTS.md`, `COORDINATION.md`, `SCHEMAS.md`, `config/settings.yaml` first.
**You own only:** `src/fetchers/prices.py`, `fx.py`, `esg.py`, `fundamentals.py`,
`disclosures.py`, `synthetic.py`. Do not touch `gdelt.py`, `universe/`, `signals/`, or any
Claude-owned path. `data/raw/universe.parquet` already exists (461 names, 5 markets) — read it.

## Shared rules for every fetcher
- Signature: `fetch(universe_df: pd.DataFrame, settings: dict) -> pd.DataFrame` and also write the
  parquet named in SCHEMAS.md to `data/raw/`.
- **Disk cache:** if the target parquet exists and is <24h old, load & return it (no re-download).
  Support `force=False` kwarg to bypass.
- **Retry:** exponential backoff + jitter (base 2s, max 5 tries) around every network call.
- **Failure log:** collect `{ticker, source, error}` rows; write `data/raw/<source>_failures.csv`.
- Use `from src.util.log import log_action` for start/end (`phase="phase2"`).
- Read settings via `yaml.safe_load(open("config/settings.yaml"))`. Read currency/suffix per ticker
  from the universe parquet (`currency` column) — do not hardcode FX.
- **No fabrication.** Missing field → NaN. Never invent values.

## Modules
1. **fx.py** → `fx_daily.parquet` (`date,currency,fx_to_usd`). yfinance crosses `<CUR>USD=X` for
   SGD,IDR,MYR,THB,VND (PHP unused). Daily 2014-01-01→today; forward-fill non-trading days (note it).
2. **prices.py** → `prices_daily.parquet` (`date,ticker,close_local,volume,close_usd`).
   yfinance daily auto-adjusted close+volume per universe ticker; join fx_daily to make close_usd.
   Batch `yf.download` in chunks of ~50 tickers, `group_by="ticker"`, `threads=True`.
3. **esg.py** → `esg_snapshot.parquet` (one row/ticker, see SCHEMAS). `yf.Ticker(t).sustainability`
   (Sustainalytics). Stamp `retrieval_date=today`. Most ASEAN names will be missing → that's fine,
   record NaN. This is a snapshot, NOT a history.
4. **fundamentals.py** → `fundamentals.parquet` (long; annual+quarter). From
   `yf.Ticker(t).financials/.quarterly_financials/.balance_sheet/.cashflow`: revenue, capex,
   total_debt, interest_expense, operating_cash_flow, depreciation. Field names vary by ticker —
   map defensively, NaN when absent.
5. **disclosures.py** → `disclosures_quarterly.parquet`. **Best-effort, SG (.SI) + MY (.KL) only.**
   Try SGX announcements; count sustainability-tagged announcements/quarter + last date. If not
   scrapeable within ~1h of effort, write an empty schema-correct parquet + a note in the failure
   log and STOP — do not burn the build on this (it is the first optional cut).
6. **synthetic.py** → deterministic seeded (seed 42) generator that writes
   `outputs/site_data/companies.json` (+ stub `backtest.json`, `ic_table.json`, `placebo.json`)
   **exactly matching SCHEMAS.md**, with `data_mode:"synthetic"`. ~500 plausible rows so the
   frontend can build before live data. Numbers must be obviously synthetic-plausible, never
   presented as findings. This is the file the frontend team builds against.

## Acceptance
- All fetchers run end-to-end; second run hits cache (no re-download).
- Failure CSVs written. prices covers ≥440 names × ≥8y where data exists.
- `synthetic.py` output validates against SCHEMAS.md (every required field present, correct types).
- Add a quick `if __name__=="__main__"` smoke run to each module.

Report back: a summary of coverage per source (how many tickers resolved) + the failure counts.
Do NOT edit settings.yaml or SCHEMAS.md — if something there blocks you, flag it for Claude.
