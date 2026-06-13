# CSV Import Validator

Validate provider-neutral CSV files before converting them into pipeline parquet artifacts.

## Usage

```bat
python src/csv_import/validate.py --csv path/to/data.csv --family prices
```

The command prints `PASS` when the file conforms. On failure it prints a detailed error log with line numbers and exits non-zero.

## Families

- `prices`: `date,ticker,close_local,volume,close_usd`
- `esg`: `ticker,retrieval_date,esg_total_risk,esg_e,esg_s,esg_g,controversy_level`
- `fundamentals`: `ticker,fiscal_date,period,revenue,capex,total_debt,interest_expense,operating_cash_flow,depreciation`
- `sentiment`: `ticker,month,article_volume,avg_tone,obs_days`

## Templates

- `templates/prices_template.csv`
- `templates/esg_template.csv`
- `templates/fundamentals_template.csv`

Each template includes a leading `#` comment that documents the columns and valid ranges. The validator ignores blank lines and leading `#` comment lines before parsing.

## Validation Rules

- Columns must exactly match the selected family schema and order.
- Dates must be ISO `YYYY-MM-DD`; sentiment `month` must be `YYYY-MM-01`.
- Tickers must be uppercase ticker-like strings.
- Numeric fields must be finite.
- Price and volume fields must be non-negative.
- ESG risk fields must be `0..100` when present.
- `controversy_level` must be integer `0..5` when present.
- `period` must be `annual` or `quarter`.
- Key columns must be unique.
- Dates must be monotonic within each ticker, or within ticker/period for fundamentals.
- Formula-like cells beginning with `=`, `+`, `-`, or `@` are rejected.
