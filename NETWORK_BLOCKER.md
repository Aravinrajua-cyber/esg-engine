# Network Blocker

## Summary

Live Yahoo Finance verification is incomplete in this Codex session because Yahoo Finance requests returned empty or unavailable responses. The application logic should not be judged defective from these empty responses alone.

## Commands Attempted

From the original repository before the mirror was created:

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.fetchers.fx
.\.venv\Scripts\python.exe -m src.fetchers.prices
```

Small smoke checks also attempted `yfinance.download` for:

- `SGDUSD=X`
- `D05.SI`

## Observed Error Excerpts

Yahoo requests returned messages such as:

```text
$SGDUSD=X: possibly delisted; no price data found
Failed to connect to query1.finance.yahoo.com port 443
```

During `src.fetchers.fx`, the affected FX tickers were:

- `IDRUSD=X`
- `MYRUSD=X`
- `SGDUSD=X`
- `THBUSD=X`
- `VNDUSD=X`

During `src.fetchers.prices`, large ticker chunks across the 477-name universe returned empty "possibly delisted/no price data" responses.

## Why Live Verification Remains Incomplete

The WO-1 acceptance criteria require current live Yahoo downloads and persisted raw parquet/CSV outputs. This session had unreliable or blocked Yahoo connectivity, so coverage percentages, live row counts, and live spot checks cannot be validated honestly here.

## How To Rerun Locally

In a normal terminal with working outbound HTTPS and write access to the original repo:

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.fetchers.fx
.\.venv\Scripts\python.exe -m src.fetchers.prices
.\.venv\Scripts\python.exe -m src.fetchers.esg
.\.venv\Scripts\python.exe -m src.fetchers.fundamentals
.\.venv\Scripts\python.exe -m pytest -q
```

Do not treat empty Yahoo responses for hundreds of tickers in this sandbox as issuer delisting evidence.
