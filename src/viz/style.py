"""Shared figure theme and smoke-renderable visualization suite."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACCENT = "#3B3BFF"
BG = "#FAFAF8"
INK = "#0B0B0C"
GREEN = "#148A4A"
RED = "#C0372B"
FONT = "Inter, Arial, sans-serif"


def _plotly():
    import plotly.graph_objects as go
    import plotly.io as pio

    template = go.layout.Template(
        layout=go.Layout(
            font={"family": FONT, "size": 14, "color": INK},
            paper_bgcolor=BG,
            plot_bgcolor=BG,
            margin={"l": 72, "r": 32, "t": 84, "b": 64},
            colorway=[ACCENT, GREEN, RED, "#6B7280", "#111827", "#9CA3AF"],
            xaxis={"showgrid": False, "zeroline": False, "linecolor": "#D8D8D2"},
            yaxis={"gridcolor": "#E6E6E0", "zeroline": False, "linecolor": "#D8D8D2"},
        )
    )
    pio.templates["esg_engine"] = template
    pio.templates.default = "esg_engine"
    return go


def apply_theme(fig, title: str, takeaway: str):
    fig.update_layout(
        title={"text": f"{title}<br><sup>{takeaway}</sup>", "x": 0.02, "xanchor": "left"},
        template="esg_engine",
    )
    return fig


def _write(fig, outdir: Path, name: str) -> tuple[Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    html_path = outdir / f"{name}.html"
    png_path = outdir / f"{name}.png"
    fig.write_html(html_path, include_plotlyjs="cdn")
    try:
        fig.write_image(png_path, scale=3, width=1200, height=780)
    except Exception:
        _fallback_png(png_path, name)
    return png_path, html_path


def _fallback_png(path: Path, title: str) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.axis("off")
    ax.text(0.04, 0.56, title.replace("_", " ").title(), fontsize=18, color=INK)
    ax.text(0.04, 0.46, "Static export placeholder; interactive HTML contains the chart.", fontsize=9, color="#555555")
    fig.savefig(path, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def _records(data: dict[str, Any], key: str, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
    value = data.get(key)
    return value if isinstance(value, list) and value else fallback


def make_treemap(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    companies = _records(data, "companies", _fixture_companies())
    labels = [c["sector"] for c in companies[:60]]
    parents = ["Universe"] * len(labels)
    values = [max(1, c.get("coverage_pct", 1)) for c in companies[:60]]
    fig = go.Figure(go.Treemap(labels=labels, parents=parents, values=values, marker={"colorscale": [[0, "#D8D8FF"], [1, ACCENT]]}))
    return _write(apply_theme(fig, "Universe Coverage Treemap", "Sector footprint shown from available company records."), Path(outdir), "treemap")


def make_coverage_heatmap(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    companies = _records(data, "companies", _fixture_companies())
    countries = sorted({c["country"] for c in companies})
    sectors = sorted({c["sector"] for c in companies})[:8]
    z = [[np.mean([c["coverage_pct"] for c in companies if c["country"] == country and c["sector"] == sector] or [0]) for sector in sectors] for country in countries]
    fig = go.Figure(go.Heatmap(z=z, x=sectors, y=countries, colorscale=[[0, "#F1F1EE"], [1, ACCENT]], colorbar={"title": "Coverage"}))
    return _write(apply_theme(fig, "Coverage Heatmap", "Coverage varies by market and sector in the current artifact."), Path(outdir), "coverage_heatmap")


def make_ic_bar(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    rows = _records(data, "ic", data.get("ic_table", _fixture_ic()))
    x = [r.get("variable", r.get("label", "var")) for r in rows]
    y = [r.get("ic_mean", r.get("ic_3m", 0)) for r in rows]
    survived = [bool(r.get("fdr_survived", False)) for r in rows]
    fig = go.Figure(go.Bar(x=x, y=y, marker={"color": [ACCENT if s else "#A7A7A0" for s in survived]}))
    fig.add_hline(y=0, line_color="#777777")
    return _write(apply_theme(fig, "Per-Variable IC", "Bars use validated IC records; color marks FDR survival."), Path(outdir), "ic_bar")


def make_ic_decay_curves(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    rows = _records(data, "ic", _fixture_ic_multi())
    fig = go.Figure()
    for variable in sorted({r["variable"] for r in rows}):
        var_rows = [r for r in rows if r["variable"] == variable]
        fig.add_trace(go.Scatter(x=[r.get("horizon", "3m") for r in var_rows], y=[r.get("ic_mean", 0) for r in var_rows], mode="lines+markers", name=variable))
    return _write(apply_theme(fig, "IC Decay", "Signal strength is plotted by forecast horizon."), Path(outdir), "ic_decay_curves")


def make_money_chart(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    backtest = data.get("backtest", data if "dates" in data else _fixture_backtest())
    fig = go.Figure()
    for key, label in [("q5", "Q5"), ("q1", "Q1"), ("benchmark", "Benchmark"), ("naive_esg_q5", "Naive ESG Q5")]:
        fig.add_trace(go.Scatter(x=backtest["dates"], y=backtest[key], mode="lines", name=label))
    if "train_end_index" in backtest and backtest["dates"]:
        idx = min(backtest["train_end_index"], len(backtest["dates"]) - 1)
        fig.add_vline(x=backtest["dates"][idx], line_dash="dash", line_color="#666666")
    return _write(apply_theme(fig, "Money Chart", "Cumulative test curves come directly from the backtest artifact."), Path(outdir), "money_chart")


def make_walk_forward_weight_ribbon(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    weights = data.get("walk_forward_weights", _fixture_weights())
    dates = [r["date"] for r in weights]
    fig = go.Figure()
    for key in ["sentiment_dynamics", "transition_readiness", "governance_credibility", "disclosure_behavior"]:
        fig.add_trace(go.Scatter(x=dates, y=[r[key] for r in weights], stackgroup="one", name=key))
    return _write(apply_theme(fig, "Walk-Forward Weights", "The ribbon shows how model weights evolve across windows."), Path(outdir), "walk_forward_weight_ribbon")


def make_placebo_histogram(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    placebo = data.get("placebo", data if "hist_bins" in data else _fixture_placebo())
    fig = go.Figure(go.Bar(x=placebo["hist_bins"], y=placebo["hist_counts"], marker={"color": "#BFC0FF"}))
    fig.add_vline(x=placebo["realized_spread"], line_color=ACCENT, line_width=3)
    return _write(apply_theme(fig, "Placebo Test", "The realized spread is compared with placebo draws."), Path(outdir), "placebo_histogram")


def make_matrix_scatter(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    companies = _records(data, "companies", _fixture_companies())
    fig = go.Figure(go.Scatter(
        x=[c["esg_level_pctile"] for c in companies],
        y=[c["esg_momentum_pctile"] for c in companies],
        mode="markers",
        text=[c["name"] for c in companies],
        marker={"color": [c["overall_score"] for c in companies], "colorscale": [[0, "#D9D9FF"], [1, ACCENT]], "size": 8},
    ))
    fig.add_vline(x=50, line_color="#777777", line_dash="dot")
    fig.add_hline(y=50, line_color="#777777", line_dash="dot")
    return _write(apply_theme(fig, "2x2 ESG Matrix", "Companies are positioned by level and momentum percentiles."), Path(outdir), "matrix_scatter")


def make_equity_drawdown(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    backtest = data.get("backtest", _fixture_backtest())
    equity = np.array(backtest["q5"], dtype=float)
    drawdown = equity / np.maximum.accumulate(equity) - 1
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=backtest["dates"], y=equity, mode="lines", name="Equity"))
    fig.add_trace(go.Scatter(x=backtest["dates"], y=drawdown, mode="lines", name="Drawdown", yaxis="y2"))
    fig.update_layout(yaxis2={"overlaying": "y", "side": "right", "tickformat": ".0%"})
    return _write(apply_theme(fig, "Equity And Drawdown", "Return path and drawdown are shown together for risk context."), Path(outdir), "equity_drawdown")


def make_by_country_sector_spreads(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    countries = data.get("by_country", [{"key": "SG", "spread_net": 4.2}, {"key": "MY", "spread_net": 3.1}])
    sectors = data.get("by_sector", [{"key": "Financials", "spread_net": 2.2}, {"key": "Industrials", "spread_net": 5.0}])
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[r["key"] for r in countries], y=[r["spread_net"] for r in countries], name="Country"))
    fig.add_trace(go.Bar(x=[r["key"] for r in sectors], y=[r["spread_net"] for r in sectors], name="Sector"))
    return _write(apply_theme(fig, "Spread By Country And Sector", "Net spreads are grouped by geography and sector."), Path(outdir), "by_country_sector_spreads")


def make_composite_correlation_heatmap(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    labels = ["sentiment", "transition", "governance", "disclosure"]
    corr = np.array(data.get("composite_correlation", np.eye(4).tolist()))
    fig = go.Figure(go.Heatmap(z=corr, x=labels, y=labels, zmin=-1, zmax=1, colorscale=[[0, RED], [0.5, "#FFFFFF"], [1, ACCENT]]))
    return _write(apply_theme(fig, "Composite Correlation", "Correlation structure uses the supplied composite matrix."), Path(outdir), "composite_correlation_heatmap")


def make_score_histogram(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    companies = _records(data, "companies", _fixture_companies())
    fig = go.Figure(go.Histogram(x=[c["overall_score"] for c in companies], nbinsx=20, marker={"color": ACCENT}))
    for x in [50, 65, 80, 90]:
        fig.add_vline(x=x, line_dash="dot", line_color="#777777")
    return _write(apply_theme(fig, "Score Distribution", "Grade bands are marked on the current company score distribution."), Path(outdir), "score_histogram")


def make_top20_leaderboard(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    companies = sorted(_records(data, "companies", _fixture_companies()), key=lambda c: c["rank"])[:20]
    fig = go.Figure(go.Table(
        header={"values": ["Rank", "Company", "Country", "Score", "Grade"], "fill_color": "#E8E8FF", "align": "left"},
        cells={"values": [[c["rank"] for c in companies], [c["name"] for c in companies], [c["country"] for c in companies], [c["overall_score"] for c in companies], [c["grade"] for c in companies]], "align": "left"},
    ))
    return _write(apply_theme(fig, "Top 20 Leaderboard", "Top companies are read from the site-data contract."), Path(outdir), "top20_leaderboard")


def make_company_overlay(data: dict[str, Any], outdir: str | Path):
    go = _plotly()
    companies = _records(data, "companies", _fixture_companies())
    company = next((c for c in companies if c.get("timeseries")), companies[0])
    ts = company.get("timeseries") or _fixture_timeseries()
    fig = go.Figure()
    for key, label in [("price_usd", "Price USD"), ("sentiment_tone", "Sentiment"), ("score", "Score")]:
        fig.add_trace(go.Scatter(x=ts["dates"], y=ts[key], mode="lines", name=label))
    return _write(apply_theme(fig, "Company Overlay", f"{company['name']} price, sentiment, and score timeline."), Path(outdir), "company_overlay")


FIGURES: dict[str, Callable[[dict[str, Any], str | Path], tuple[Path, Path]]] = {
    "treemap": make_treemap,
    "coverage_heatmap": make_coverage_heatmap,
    "ic_bar": make_ic_bar,
    "ic_decay_curves": make_ic_decay_curves,
    "money_chart": make_money_chart,
    "walk_forward_weight_ribbon": make_walk_forward_weight_ribbon,
    "placebo_histogram": make_placebo_histogram,
    "matrix_scatter": make_matrix_scatter,
    "equity_drawdown": make_equity_drawdown,
    "by_country_sector_spreads": make_by_country_sector_spreads,
    "composite_correlation_heatmap": make_composite_correlation_heatmap,
    "score_histogram": make_score_histogram,
    "top20_leaderboard": make_top20_leaderboard,
    "company_overlay": make_company_overlay,
}


def load_smoke_data() -> dict[str, Any]:
    site_dir = PROJECT_ROOT / "outputs" / "site_data"
    data: dict[str, Any] = {"companies": _fixture_companies()}
    for name in ["companies", "backtest", "ic_table", "placebo", "by_country", "by_sector"]:
        path = site_dir / f"{name}.json"
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            if name == "companies":
                data.update(payload)
            else:
                data[name] = payload
    validation = PROJECT_ROOT / "data" / "processed" / "validation_results.json"
    if validation.exists():
        data.update(json.loads(validation.read_text(encoding="utf-8")))
    return data


def _fixture_companies() -> list[dict[str, Any]]:
    return [
        {
            "ticker": f"DEMO{i}.SI",
            "name": f"Synthetic Company {i}",
            "country": "SG" if i % 2 else "MY",
            "exchange": "SGX",
            "sector": ["Financials", "Industrials", "Technology", "Utilities"][i % 4],
            "rank": i,
            "overall_score": 92 - i,
            "grade": "A" if i < 10 else "B",
            "coverage_pct": 70 + i % 20,
            "esg_level_pctile": (i * 7) % 100,
            "esg_momentum_pctile": (i * 11) % 100,
            "timeseries": _fixture_timeseries() if i == 1 else None,
        }
        for i in range(1, 31)
    ]


def _fixture_timeseries() -> dict[str, list[Any]]:
    dates = [f"2024-{month:02d}-01" for month in range(1, 13)]
    return {"dates": dates, "price_usd": list(np.linspace(90, 122, 12)), "sentiment_tone": list(np.linspace(-1, 2, 12)), "score": list(np.linspace(62, 82, 12))}


def _fixture_ic() -> list[dict[str, Any]]:
    return [{"variable": f"A{i}", "ic_3m": 0.01 * i, "fdr_survived": i % 2 == 0} for i in range(1, 8)]


def _fixture_ic_multi() -> list[dict[str, Any]]:
    return [{"variable": var, "horizon": horizon, "ic_mean": value / 100} for var, values in {"A1": [4, 3, 2, 1], "B2": [3, 2, 2, 1]}.items() for horizon, value in zip(["1m", "3m", "6m", "12m"], values)]


def _fixture_backtest() -> dict[str, Any]:
    dates = [f"2020-{month:02d}-01" for month in range(1, 13)]
    return {
        "dates": dates,
        "q5": list(np.linspace(100, 140, 12)),
        "q1": list(np.linspace(100, 108, 12)),
        "benchmark": list(np.linspace(100, 121, 12)),
        "naive_esg_q5": list(np.linspace(100, 116, 12)),
        "net": True,
        "train_end_index": 7,
    }


def _fixture_placebo() -> dict[str, Any]:
    bins = list(np.linspace(-5, 5, 21))
    return {"realized_spread": 3.8, "hist_bins": bins, "hist_counts": [int(50 * np.exp(-(x / 2) ** 2)) + 1 for x in bins]}


def _fixture_weights() -> list[dict[str, Any]]:
    return [
        {"date": f"202{i}-12-31", "sentiment_dynamics": 0.30 + i * 0.01, "transition_readiness": 0.25, "governance_credibility": 0.25 - i * 0.005, "disclosure_behavior": 0.20 - i * 0.005}
        for i in range(6)
    ]


if __name__ == "__main__":
    rendered = []
    smoke_data = load_smoke_data()
    for name, maker in FIGURES.items():
        png, html = maker(smoke_data, PROJECT_ROOT / "outputs" / "figures")
        rendered.append(f"{name}: {png.name}, {html.name}")
    print("\n".join(rendered))
