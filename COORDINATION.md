# COORDINATION — live ownership board

Updated by Claude. Prevents the two agents editing the same files.

## File / directory ownership

| Path | Owner | Status |
|------|-------|--------|
| `config/settings.yaml` | Claude | FROZEN contract — Codex read-only |
| `SCHEMAS.md` | Claude | FROZEN contract — Codex read-only |
| `RESEARCH_LOG.md`, `BIAS_REGISTER.md` | Claude | Claude-only |
| `src/util/` | Claude | shared lib (Codex may import, not edit) |
| `src/universe/` | Claude | in progress |
| `src/fetchers/gdelt.py` | Claude | in progress (long-pole, launches first) |
| `src/fetchers/prices.py, esg.py, fundamentals.py, fx.py, disclosures.py` | **Codex** | spec: `specs/01_fetchers.md` |
| `src/fetchers/synthetic.py` | **Codex** | spec: `specs/01_fetchers.md` |
| `src/signals/`, `src/composite/`, `src/validation/`, `src/scoring/` | Claude | the science — Claude-only |
| `src/viz/` | **Codex** | spec: `specs/03_viz_report.md` (builds vs data contracts) |
| `src/report/` | **Codex** | spec: `specs/03_viz_report.md` (plumbing; Claude supplies prose) |
| `site/` | **Codex** | spec: `specs/02_frontend.md` (consumes site_data JSON only) |
| `tests/` | **Codex** | spec: `specs/03_viz_report.md` (Claude supplies math assertions) |
| `outputs/site_data/*.json` | Claude writes real; Codex writes synthetic via `synthetic.py` | shared output dir, distinct files |
| report prose, `PITCH.md`, `QA.md`, `DEMO.md`, `JUDGING.md`, `README.md`, slide deck text | Claude | Claude-only |

## Interfaces Codex must conform to
- Every fetcher: `fetch(universe_df, settings) -> writes parquet to data/raw/, returns DataFrame`,
  disk-cached (skip if cache fresh), retry w/ exponential backoff + jitter, structured failure log.
- Output schemas: exactly as in `SCHEMAS.md`. Do not invent columns.

## Status log
- 2026-06-12: contracts frozen; universe + GDELT in progress by Claude; specs/ published for Codex.
- 2026-06-13: universe built (477 names). Live fetchers coded but never executed. Delegation
  package published: `CODEX_WORK_ORDERS.md` (WO-1 fetcher execution = critical path; WO-2 frontend
  validation; WO-3 live-mode viz/report plumbing; WO-4 raw-contract tests; WO-5 build/QA, npm-gated).
- 2026-06-13 (later): Claude science core complete (`src/composite`, `src/validation`, `src/scoring`)
  and verified on the synthetic planted-signal panel (recovery corr 0.705, placebo p=0). GDELT fetch
  running in background (resumable). Real-data run blocked on WO-1 fetcher outputs.
