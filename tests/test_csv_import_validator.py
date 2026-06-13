from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.csv_import.validate import validate_csv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = PROJECT_ROOT / "src" / "csv_import" / "templates"


@pytest.mark.parametrize(
    ("family", "template"),
    [
        ("prices", "prices_template.csv"),
        ("esg", "esg_template.csv"),
        ("fundamentals", "fundamentals_template.csv"),
    ],
)
def test_csv_import_templates_validate(family: str, template: str):
    report = validate_csv(TEMPLATE_DIR / template, family)
    assert report.passed, report.render()
    assert report.rows_checked == 1


def test_cli_outputs_pass_for_template():
    result = subprocess.run(
        [
            sys.executable,
            "src/csv_import/validate.py",
            "--csv",
            str(TEMPLATE_DIR / "prices_template.csv"),
            "--family",
            "prices",
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.startswith("PASS prices")


@pytest.mark.parametrize(
    ("family", "contents", "expected"),
    [
        (
            "prices",
            "date,ticker,close_local,volume,close_usd\n2026-03-31,DEMO1.SI,-1,100,1\n",
            "close_local must be >= 0",
        ),
        (
            "prices",
            "date,ticker,close_local,volume,close_usd\n2026-04-02,DEMO1.SI,4,100,3\n2026-04-01,DEMO1.SI,4,100,3\n",
            "date is not monotonic",
        ),
        (
            "esg",
            "ticker,retrieval_date,esg_total_risk,esg_e,esg_s,esg_g,controversy_level\nDEMO1.SI,2026-03-31,24,7,9,8,6\n",
            "controversy_level must be between 0 and 5",
        ),
        (
            "fundamentals",
            "ticker,fiscal_date,period,revenue,capex,total_debt,interest_expense,operating_cash_flow,depreciation\nDEMO1.SI,2025-12-31,monthly,100,10,40,3,12,5\n",
            "period must be annual or quarter",
        ),
        (
            "sentiment",
            "ticker,month,article_volume,avg_tone,obs_days\nDEMO1.SI,2026-03-15,12,1.5,8\n",
            "month must be the first day of month",
        ),
        (
            "sentiment",
            "ticker,month,article_volume,avg_tone,obs_days\nDEMO1.SI,2026-03-01,12,101,8\n",
            "avg_tone must be between -100 and 100",
        ),
        (
            "prices",
            "date,ticker,close_local,volume,close_usd\n2026-03-31,DEMO1.SI,=1+1,100,3\n",
            "formula-like cell is not allowed",
        ),
    ],
)
def test_broken_csvs_are_rejected(tmp_path: Path, family: str, contents: str, expected: str):
    path = tmp_path / f"broken_{family}.csv"
    path.write_text(contents, encoding="utf-8")

    report = validate_csv(path, family)

    assert not report.passed
    assert expected in report.render()
