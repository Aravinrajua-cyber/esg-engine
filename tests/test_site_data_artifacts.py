from __future__ import annotations

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITE_DATA = PROJECT_ROOT / "outputs" / "site_data"


def _load(name: str):
    path = SITE_DATA / name
    if not path.exists():
        pytest.skip(f"{name} has not been generated yet")
    return json.loads(path.read_text(encoding="utf-8"))


def test_generated_backtest_stub_shape():
    backtest = _load("backtest.json")
    assert set(backtest) == {"dates", "q5", "q1", "benchmark", "naive_esg_q5", "net", "train_end_index"}
    lengths = {len(backtest[key]) for key in ["dates", "q5", "q1", "benchmark", "naive_esg_q5"]}
    assert len(lengths) == 1
    assert 0 <= backtest["train_end_index"] < len(backtest["dates"])
    assert isinstance(backtest["net"], bool)


def test_generated_ic_and_placebo_stub_shape():
    ic_rows = _load("ic_table.json")
    assert ic_rows
    for row in ic_rows:
        assert set(row) == {"variable", "label", "ic_3m", "t_nw", "fdr_survived"}
        assert isinstance(row["fdr_survived"], bool)

    placebo = _load("placebo.json")
    assert set(placebo) == {"realized_spread", "hist_bins", "hist_counts"}
    assert len(placebo["hist_bins"]) == len(placebo["hist_counts"])


def test_generated_country_and_sector_aggregates_are_non_empty():
    for name in ["by_country.json", "by_sector.json"]:
        rows = _load(name)
        assert rows
        for row in rows:
            assert set(row) == {"key", "spread_net"}
            assert row["key"]
