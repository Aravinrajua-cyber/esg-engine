from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PROJECT_ROOT / "data" / "templates"
INVALID_DIR = PROJECT_ROOT / "data" / "examples" / "invalid"

ALLOWED_COUNTRIES = {"SG", "ID", "MY", "TH", "PH", "VN"}
ALLOWED_PERIODS = {"annual", "quarter"}
MISSING = {"", "NA", "N/A", "null"}
FORMULA_PREFIXES = ("=", "+", "-", "@")
MAX_TEXT_LEN = 256

REQUIRED = {
    "company": {"company_id", "ticker", "name", "country", "exchange", "sector", "currency"},
    "esg": {"company_id", "as_of_date"},
    "financial": {"company_id", "fiscal_date", "period"},
    "price": {"company_id", "date", "close_local"},
}

ESG_SCORE_COLUMNS = {"esg_total_score", "environment_score", "social_score", "governance_score"}
NUMERIC_COLUMNS = {
    "market_cap_usd",
    "free_float_pct",
    "adv_usd",
    "esg_total_score",
    "environment_score",
    "social_score",
    "governance_score",
    "controversy_level",
    "confidence_low",
    "confidence_high",
    "revenue_local",
    "capex_local",
    "total_debt_local",
    "interest_expense_local",
    "operating_cash_flow_local",
    "depreciation_local",
    "close_local",
    "volume",
    "close_usd",
}
NON_NEGATIVE_COLUMNS = {
    "market_cap_usd",
    "adv_usd",
    "revenue_local",
    "total_debt_local",
    "close_local",
    "volume",
    "close_usd",
}


class CsvValidationError(ValueError):
    pass


def _kind(fieldnames: list[str]) -> str:
    fields = set(fieldnames)
    if "as_of_date" in fields:
        return "esg"
    if "fiscal_date" in fields:
        return "financial"
    if "date" in fields and "close_local" in fields:
        return "price"
    return "company"


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle, strict=True)
            rows = list(reader)
    except csv.Error as exc:
        raise CsvValidationError(f"malformed csv: {exc}") from exc
    if not reader.fieldnames:
        raise CsvValidationError("missing header")
    if any(None in row for row in rows):
        raise CsvValidationError("malformed csv: row has extra fields")
    return reader.fieldnames, rows


def _date(value: str, field: str) -> None:
    if value in MISSING:
        raise CsvValidationError(f"missing date {field}")
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise CsvValidationError(f"invalid date {field}") from exc


def _number(value: str, field: str) -> float | None:
    if value in MISSING:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise CsvValidationError(f"non-numeric {field}") from exc


def _validate(path: Path) -> None:
    fieldnames, rows = _read_csv(path)
    kind = _kind(fieldnames)
    missing_fields = REQUIRED[kind] - set(fieldnames)
    if missing_fields:
        raise CsvValidationError(f"missing required field: {sorted(missing_fields)[0]}")
    if not rows:
        raise CsvValidationError("empty file")

    keys_seen: set[tuple[str, ...]] = set()
    for row in rows:
        for field, value in row.items():
            value = value or ""
            if len(value) > MAX_TEXT_LEN:
                raise CsvValidationError(f"excessively large text field: {field}")
            if value and value[0] in FORMULA_PREFIXES:
                raise CsvValidationError(f"formula injection: {field}")

        company_id = row.get("company_id", "")
        if not company_id:
            raise CsvValidationError("missing company_id")

        country = row.get("country")
        if country is not None and country not in MISSING and country not in ALLOWED_COUNTRIES:
            raise CsvValidationError(f"unsupported country code: {country}")

        if kind == "company":
            key = (company_id,)
        elif kind == "esg":
            _date(row["as_of_date"], "as_of_date")
            key = (company_id, row["as_of_date"])
        elif kind == "financial":
            _date(row["fiscal_date"], "fiscal_date")
            if row["period"] not in ALLOWED_PERIODS:
                raise CsvValidationError("unsupported period")
            key = (company_id, row["fiscal_date"], row["period"])
        else:
            _date(row["date"], "date")
            key = (company_id, row["date"])

        if key in keys_seen:
            raise CsvValidationError("duplicate company identifier or history key")
        keys_seen.add(key)

        for field in NUMERIC_COLUMNS & set(fieldnames):
            value = _number(row.get(field, ""), field)
            if field in ESG_SCORE_COLUMNS and value is not None and not 0 <= value <= 100:
                raise CsvValidationError(f"score outside allowed range: {field}")
            if field in {"confidence_low", "confidence_high"} and value is not None and not 0 <= value <= 100:
                raise CsvValidationError(f"confidence outside allowed range: {field}")
            if field == "controversy_level" and value is not None and (value % 1 != 0 or not 0 <= value <= 5):
                raise CsvValidationError(f"controversy outside allowed range: {field}")
            if field in NON_NEGATIVE_COLUMNS and value is not None and value < 0:
                raise CsvValidationError(f"negative numeric field: {field}")

        if {"confidence_low", "confidence_high"}.issubset(fieldnames):
            low = _number(row.get("confidence_low", ""), "confidence_low")
            high = _number(row.get("confidence_high", ""), "confidence_high")
            if low is not None and high is not None and low > high:
                raise CsvValidationError("impossible confidence interval")


@pytest.mark.parametrize(
    "template",
    [
        "company_master_template.csv",
        "esg_history_template.csv",
        "financial_history_template.csv",
        "price_history_template.csv",
    ],
)
def test_csv_templates_are_valid(template: str):
    _validate(TEMPLATE_DIR / template)


@pytest.mark.parametrize(
    ("fixture", "message"),
    [
        ("missing_required_field.csv", "missing required field"),
        ("duplicate_company_identifier.csv", "duplicate"),
        ("invalid_date.csv", "invalid date"),
        ("non_numeric_score.csv", "non-numeric"),
        ("score_outside_allowed_range.csv", "score outside allowed range"),
        ("impossible_confidence_interval.csv", "impossible confidence interval"),
        ("malformed_csv_quoting.csv", "malformed csv"),
        ("formula_injection_cell.csv", "formula injection"),
        ("excessively_large_text_field.csv", "excessively large text field"),
        ("unsupported_country_code.csv", "unsupported country code"),
        ("invalid_numeric_field.csv", "non-numeric"),
        ("controversy_out_of_range.csv", "controversy outside allowed range"),
        ("unsupported_period.csv", "unsupported period"),
        ("negative_price_or_volume.csv", "negative numeric field"),
    ],
)
def test_invalid_csv_examples_are_rejected(fixture: str, message: str):
    with pytest.raises(CsvValidationError, match=message):
        _validate(INVALID_DIR / fixture)
