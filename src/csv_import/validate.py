from __future__ import annotations

import argparse
import csv
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable


MISSING = {"", "NA", "N/A", "null", "None"}
FORMULA_PREFIXES = ("=", "+", "-", "@")
TICKER_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,24}$")
VALID_FAMILIES = {"prices", "esg", "fundamentals", "sentiment"}


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    parser: Callable[[str, int, str], object]
    required: bool = True


@dataclass(frozen=True)
class FamilySpec:
    columns: tuple[ColumnSpec, ...]
    key_columns: tuple[str, ...]
    date_column: str
    monotonic_group: tuple[str, ...] = ("ticker",)


@dataclass
class ValidationIssue:
    level: str
    line: int
    column: str
    message: str

    def render(self) -> str:
        location = f"line {self.line}" if self.line else "file"
        column = f", column {self.column}" if self.column else ""
        return f"{self.level}: {location}{column}: {self.message}"


@dataclass
class ValidationReport:
    family: str
    path: Path
    rows_checked: int = 0
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors

    def add_error(self, line: int, column: str, message: str) -> None:
        self.errors.append(ValidationIssue("ERROR", line, column, message))

    def add_warning(self, line: int, column: str, message: str) -> None:
        self.warnings.append(ValidationIssue("WARNING", line, column, message))

    def render(self) -> str:
        if self.passed:
            lines = [f"PASS {self.family}: {self.rows_checked} row(s) checked"]
        else:
            lines = [f"FAIL {self.family}: {len(self.errors)} error(s), {len(self.warnings)} warning(s)"]
        lines.extend(issue.render() for issue in self.errors)
        lines.extend(issue.render() for issue in self.warnings)
        return "\n".join(lines)


def _missing(value: str) -> bool:
    return value.strip() in MISSING


def _reject_formula(value: str, line: int, column: str, *, allow_numeric_minus: bool = False) -> None:
    stripped = value.lstrip()
    if allow_numeric_minus and stripped.startswith("-"):
        try:
            float(stripped)
            return
        except ValueError:
            pass
    if stripped and stripped[0] in FORMULA_PREFIXES:
        raise ValueError(f"formula-like cell is not allowed in {column}")


def parse_text(value: str, line: int, column: str) -> str | None:
    _reject_formula(value, line, column)
    value = value.strip()
    if _missing(value):
        return None
    return value


def parse_ticker(value: str, line: int, column: str) -> str:
    parsed = parse_text(value, line, column)
    if not parsed:
        raise ValueError(f"{column} is required")
    if not TICKER_RE.match(parsed):
        raise ValueError(f"{column} must be uppercase ticker-like text")
    return parsed


def parse_date(value: str, line: int, column: str) -> datetime:
    parsed = parse_text(value, line, column)
    if not parsed:
        raise ValueError(f"{column} is required")
    try:
        return datetime.strptime(parsed, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{column} must be ISO YYYY-MM-DD") from exc


def parse_month_start(value: str, line: int, column: str) -> datetime:
    parsed = parse_date(value, line, column)
    if parsed.day != 1:
        raise ValueError(f"{column} must be the first day of month, YYYY-MM-01")
    return parsed


def parse_float(value: str, line: int, column: str) -> float | None:
    _reject_formula(value, line, column, allow_numeric_minus=True)
    if _missing(value):
        return None
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"{column} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{column} must be finite")
    return parsed


def parse_non_negative_float(value: str, line: int, column: str) -> float | None:
    parsed = parse_float(value, line, column)
    if parsed is not None and parsed < 0:
        raise ValueError(f"{column} must be >= 0")
    return parsed


def parse_int_range(low: int, high: int) -> Callable[[str, int, str], int | None]:
    def _parse(value: str, line: int, column: str) -> int | None:
        parsed = parse_float(value, line, column)
        if parsed is None:
            return None
        if parsed % 1 != 0:
            raise ValueError(f"{column} must be an integer")
        integer = int(parsed)
        if not low <= integer <= high:
            raise ValueError(f"{column} must be between {low} and {high}")
        return integer

    return _parse


def parse_float_range(low: float, high: float) -> Callable[[str, int, str], float | None]:
    def _parse(value: str, line: int, column: str) -> float | None:
        parsed = parse_float(value, line, column)
        if parsed is None:
            return None
        if not low <= parsed <= high:
            raise ValueError(f"{column} must be between {low:g} and {high:g}")
        return parsed

    return _parse


def parse_period(value: str, line: int, column: str) -> str:
    parsed = parse_text(value, line, column)
    if parsed not in {"annual", "quarter"}:
        raise ValueError("period must be annual or quarter")
    return parsed


FAMILY_SPECS: dict[str, FamilySpec] = {
    "prices": FamilySpec(
        columns=(
            ColumnSpec("date", parse_date),
            ColumnSpec("ticker", parse_ticker),
            ColumnSpec("close_local", parse_non_negative_float),
            ColumnSpec("volume", parse_non_negative_float),
            ColumnSpec("close_usd", parse_non_negative_float),
        ),
        key_columns=("date", "ticker"),
        date_column="date",
    ),
    "esg": FamilySpec(
        columns=(
            ColumnSpec("ticker", parse_ticker),
            ColumnSpec("retrieval_date", parse_date),
            ColumnSpec("esg_total_risk", parse_float_range(0, 100), required=False),
            ColumnSpec("esg_e", parse_float_range(0, 100), required=False),
            ColumnSpec("esg_s", parse_float_range(0, 100), required=False),
            ColumnSpec("esg_g", parse_float_range(0, 100), required=False),
            ColumnSpec("controversy_level", parse_int_range(0, 5), required=False),
        ),
        key_columns=("ticker",),
        date_column="retrieval_date",
    ),
    "fundamentals": FamilySpec(
        columns=(
            ColumnSpec("ticker", parse_ticker),
            ColumnSpec("fiscal_date", parse_date),
            ColumnSpec("period", parse_period),
            ColumnSpec("revenue", parse_float),
            ColumnSpec("capex", parse_float),
            ColumnSpec("total_debt", parse_float),
            ColumnSpec("interest_expense", parse_float),
            ColumnSpec("operating_cash_flow", parse_float),
            ColumnSpec("depreciation", parse_float),
        ),
        key_columns=("ticker", "fiscal_date", "period"),
        date_column="fiscal_date",
        monotonic_group=("ticker", "period"),
    ),
    "sentiment": FamilySpec(
        columns=(
            ColumnSpec("ticker", parse_ticker),
            ColumnSpec("month", parse_month_start),
            ColumnSpec("article_volume", parse_int_range(0, 1_000_000)),
            ColumnSpec("avg_tone", parse_float_range(-100, 100)),
            ColumnSpec("obs_days", parse_int_range(0, 31)),
        ),
        key_columns=("ticker", "month"),
        date_column="month",
    ),
}


def _data_lines(path: Path) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for line_number, raw in enumerate(handle, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            lines.append((line_number, raw))
    return lines


def _read_rows(path: Path, report: ValidationReport) -> tuple[list[str], list[tuple[int, dict[str, str]]]]:
    lines = _data_lines(path)
    if not lines:
        report.add_error(0, "", "CSV contains no header row")
        return [], []
    text = "".join(line for _, line in lines)
    try:
        reader = csv.DictReader(text.splitlines(), strict=True)
        raw_rows = list(reader)
    except csv.Error as exc:
        report.add_error(0, "", f"malformed CSV: {exc}")
        return [], []
    if not reader.fieldnames:
        report.add_error(0, "", "CSV contains no header row")
        return [], []
    if any(None in row for row in raw_rows):
        report.add_error(0, "", "malformed CSV: row has extra fields")
    line_numbers = [line_no for line_no, _ in lines[1:]]
    return reader.fieldnames, list(zip(line_numbers, raw_rows, strict=False))


def validate_csv(path: Path | str, family: str) -> ValidationReport:
    csv_path = Path(path)
    if family not in FAMILY_SPECS:
        raise ValueError(f"family must be one of {sorted(VALID_FAMILIES)}")
    report = ValidationReport(family=family, path=csv_path)
    if not csv_path.exists():
        report.add_error(0, "", f"CSV file does not exist: {csv_path}")
        return report

    spec = FAMILY_SPECS[family]
    expected_columns = [column.name for column in spec.columns]
    fieldnames, rows = _read_rows(csv_path, report)
    if not fieldnames:
        return report
    if fieldnames != expected_columns:
        report.add_error(
            0,
            "",
            f"columns must exactly match {expected_columns}; found {fieldnames}",
        )
        return report
    if not rows:
        report.add_error(0, "", "CSV contains no data rows")
        return report

    parsed_rows: list[tuple[int, dict[str, object]]] = []
    seen_keys: dict[tuple[object, ...], int] = {}
    for line_number, row in rows:
        parsed: dict[str, object] = {}
        for column in spec.columns:
            raw_value = row.get(column.name, "")
            if column.required and _missing(raw_value):
                report.add_error(line_number, column.name, f"{column.name} is required")
                continue
            try:
                parsed[column.name] = column.parser(raw_value, line_number, column.name)
            except ValueError as exc:
                report.add_error(line_number, column.name, str(exc))
        if report.errors and any(issue.line == line_number for issue in report.errors):
            continue
        key = tuple(parsed[column] for column in spec.key_columns)
        if key in seen_keys:
            report.add_error(line_number, ",".join(spec.key_columns), f"duplicate key first seen on line {seen_keys[key]}")
        else:
            seen_keys[key] = line_number
        parsed_rows.append((line_number, parsed))

    report.rows_checked = len(parsed_rows)
    _validate_family_rules(spec, parsed_rows, report)
    return report


def _validate_family_rules(spec: FamilySpec, rows: list[tuple[int, dict[str, object]]], report: ValidationReport) -> None:
    groups: dict[tuple[object, ...], list[tuple[int, datetime]]] = {}
    for line_number, row in rows:
        key = tuple(row[column] for column in spec.monotonic_group)
        date_value = row.get(spec.date_column)
        if isinstance(date_value, datetime):
            groups.setdefault(key, []).append((line_number, date_value))

    for key, values in groups.items():
        previous_line = 0
        previous_date: datetime | None = None
        for line_number, current_date in values:
            if previous_date is not None and current_date < previous_date:
                report.add_error(
                    line_number,
                    spec.date_column,
                    f"date is not monotonic for {key}; previous line {previous_line} has {previous_date.date()}",
                )
            previous_line = line_number
            previous_date = current_date

    if report.family == "esg":
        retrieval_dates = {row["retrieval_date"] for _, row in rows}
        if len(retrieval_dates) > 1:
            report.add_warning(0, "retrieval_date", "esg_snapshot is normally a single retrieval-stamped snapshot")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ESG Engine CSV imports against frozen schemas.")
    parser.add_argument("--csv", required=True, type=Path, help="Path to user-supplied CSV")
    parser.add_argument("--family", required=True, choices=sorted(VALID_FAMILIES), help="Data family to validate")
    args = parser.parse_args(argv)

    report = validate_csv(args.csv, args.family)
    print(report.render())
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
