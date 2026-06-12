# SPEC 03 — Viz suite, docx report skeleton, test scaffolds (Codex)

Read `AGENTS.md`, `COORDINATION.md`, `SCHEMAS.md` first.
**You own only:** `src/viz/`, `src/report/`, `tests/`. You read data contracts from SCHEMAS.md and
the JSON/parquet artifacts; you do NOT compute statistics (Claude owns `validation/`) and you do NOT
write report prose (Claude supplies it). Build against `validation_results.json` /
`outputs/site_data/*.json`; if missing, use a small schema-correct fixture and note it.

## A. src/viz/ — figure functions
- `style.py`: shared Plotly+Matplotlib theme — font Inter, single accent `#3B3BFF`, 14pt min axis
  labels, title + one-line annotated takeaway baked onto each figure, consistent margins. No default
  Plotly look.
- One function per figure, signature `make_<name>(data, outdir) -> (png_path, html_path)`; each
  writes a 300-DPI PNG (for docx) AND an interactive HTML (for site). Figures (per master prompt):
  treemap, coverage heatmap, per-variable IC bar (+NW significance + FDR survival line), IC-decay
  curves, **the money chart** (cum Q5/Q1/benchmark/naive-ESG, train/test boundary, net),
  walk-forward weight ribbon, placebo histogram + realized line, 2×2 matrix scatter, equity curve +
  drawdown subplot, by-country & by-sector spread bars, composite correlation heatmap, score
  histogram with grade bands, top-20 leaderboard table figure, per-company overlay (price+sentiment+
  score). Take all inputs from the contracts — never hardcode numbers.
- `__main__` smoke-renders every figure from fixtures into `outputs/figures/`.

## B. src/report/ — docx builder skeleton
- `build_report.py` using python-docx: title page, auto ToC field, page numbers, numbered headings,
  styled tables, captioned figures. Section scaffold for all 10 report sections (Exec Summary →
  References) with `### TODO: Claude prose` placeholders and figure-insertion + table-from-JSON
  helpers (`add_figure(path, caption)`, `add_table_from_records(records, headers)`).
- Pull every table from `validation_results.json` so numbers trace to the pipeline. Output
  `outputs/report/ESG_Momentum_Engine_Report.docx`. Must open clean in Word with a populating ToC.
- Do not write final prose — leave clearly-marked placeholders Claude will fill.

## C. tests/ — pytest scaffolds
- `conftest.py` with fixtures loading small sample panels.
- Schema tests: assert every artifact in SCHEMAS.md has exactly its columns/keys and dtypes.
- Stubs (mark `@pytest.mark.skip(reason="Claude fills assertion")`) for the signal-math tests Claude
  owns: (a) no signal at date T uses post-T data, (b) z-scoring within-date, (c) winsorization
  bounds hold. Create the test files + descriptive names; Claude writes the assertions.
- A `companies.json` validator test (required fields, score ranges 0–100, grade in allowed set).

## Acceptance
`pytest -q` runs (schema tests pass on fixtures, signal stubs skip); `python -m src.viz.style` +
viz smoke render PNG+HTML for every figure; docx builds and opens in Word.

Report back: list of figures rendered, the docx path, and `pytest` summary line.
Do NOT edit SCHEMAS.md / settings.yaml / validation/ — flag blockers for Claude.
