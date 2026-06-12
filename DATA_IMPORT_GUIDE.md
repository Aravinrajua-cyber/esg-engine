# Data Import Guide

This guide defines provider-neutral CSV templates for future real-data mode. It does not introduce proprietary ESG-provider fields.

## Files

- `data/templates/company_master_template.csv`
- `data/templates/esg_history_template.csv`
- `data/templates/financial_history_template.csv`
- `data/templates/price_history_template.csv`

## Company Identifier Rules

- `company_id` is the stable primary key across all CSV files.
- Use uppercase ASCII letters, numbers, dots, dashes, or underscores only.
- `company_id` must be unique in `company_master_template.csv`.
- History files may contain repeated `company_id` values across dates, but each `(company_id, date)` pair should be unique.
- Do not use company names as identifiers.

## Date Formats

Use ISO dates only:

```text
YYYY-MM-DD
```

Quarterly rows should use a quarter-end date, for example `2026-03-31`.

## Country Codes

Use ISO-style two-letter market codes for the ASEAN scope:

- `SG` Singapore
- `ID` Indonesia
- `MY` Malaysia
- `TH` Thailand
- `PH` Philippines
- `VN` Vietnam

Unsupported country codes must be rejected before real-data mode.

## Sector Values

Recommended provider-neutral sectors:

- `Financials`
- `Industrials`
- `Technology`
- `Consumer`
- `Utilities`
- `Materials`
- `Real Estate`
- `Energy`
- `Healthcare`
- `Telecommunications`

Unknown sector values should be reviewed and mapped before import.

## Missing Values

Allowed missing-value tokens:

- empty field
- `NA`
- `N/A`
- `null`

Missing values must remain missing. Do not fill, impute, or fabricate values during import unless a later governed pipeline step explicitly documents the transformation.

## Score Ranges

Provider-neutral score columns should use:

- `0` to `100` when higher is better.
- Blank/null if unavailable.

Rows with negative scores, scores above 100, or non-numeric score strings must be rejected.

## Numeric Units

- Market capitalization: USD.
- ADV: USD median daily trading value.
- Revenue: local currency unless a `_usd` suffix is present.
- Capex: local currency unless a `_usd` suffix is present.
- Debt: local currency unless a `_usd` suffix is present.
- Price: local currency in `close_local`; USD in `close_usd`.
- Volume: shares or units traded.
- Confidence values: `0` to `100`, with lower bound less than or equal to upper bound.

## Required And Optional Fields

### Company Master

Required:

- `company_id`
- `ticker`
- `name`
- `country`
- `exchange`
- `sector`
- `currency`

Optional:

- `mcap_tier`
- `market_cap_usd`
- `free_float_pct`
- `adv_usd`
- `source`

### ESG History

Required:

- `company_id`
- `as_of_date`

At least one of these provider-neutral score columns should be present:

- `esg_total_score`
- `environment_score`
- `social_score`
- `governance_score`

Optional:

- `controversy_level`
- `confidence_low`
- `confidence_high`
- `source`

### Financial History

Required:

- `company_id`
- `fiscal_date`
- `period`

Optional:

- `revenue_local`
- `capex_local`
- `total_debt_local`
- `interest_expense_local`
- `operating_cash_flow_local`
- `depreciation_local`
- `source`

Allowed `period` values:

- `annual`
- `quarter`

### Price History

Required:

- `company_id`
- `date`
- `close_local`

Optional:

- `volume`
- `close_usd`
- `currency`
- `source`

## Duplicate Handling

- Reject duplicate `company_id` values in the company master.
- Reject duplicate `(company_id, as_of_date)` rows in ESG history.
- Reject duplicate `(company_id, fiscal_date, period)` rows in financial history.
- Reject duplicate `(company_id, date)` rows in price history.
- Do not silently keep the first or last duplicate.

## Formula Injection Protection

Reject cells that begin with:

- `=`
- `+`
- `-`
- `@`

This prevents spreadsheet formula injection when CSV files are opened in Excel or imported into downstream tools.

## Authorised API Mapping

Authorised API data should map into the CSV schema before pipeline import:

- API issuer identifier -> `company_id`
- API ticker -> `ticker`
- API issuer name -> `name`
- API market/country -> `country`
- API ESG score -> provider-neutral score columns
- API financial statement fields -> financial history columns
- API adjusted close and volume -> price history columns

Do not pass proprietary field names directly into model code. Keep a provider-specific mapping layer outside the stable CSV contract.

## Required Data-Quality Checks Before Real-Data Mode

1. Validate required fields.
2. Validate unique identifiers and duplicate history keys.
3. Validate ISO date formats.
4. Validate numeric types and score bounds.
5. Validate country codes and sector mapping.
6. Validate confidence intervals.
7. Validate missing-value tokens.
8. Reject formula-injection cells.
9. Reject malformed CSV quoting.
10. Reject unreasonably large text fields.
11. Confirm source licensing and retrieval timestamps.
12. Write import failures to an auditable log.

