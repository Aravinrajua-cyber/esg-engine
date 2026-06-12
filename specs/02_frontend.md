# SPEC 02 — Frontend (Codex)

Read `AGENTS.md`, `COORDINATION.md`, `SCHEMAS.md` first.
**You own only:** `site/`. You consume `outputs/site_data/*.json` (read-only) — never write into
the pipeline or edit any `src/` file. Build against **synthetic mode** first
(`outputs/site_data/companies.json` with `data_mode:"synthetic"`, produced by `src/fetchers/synthetic.py`).
If that file doesn't exist yet, generate a tiny local mock that matches SCHEMAS.md and swap later —
the real file is drop-in compatible.

## Stack
Vite + React + TypeScript, static export. Plotly **code-split to the Results/Methodology pages
only**; the leaderboard uses lightweight inline SVG sparklines (no Plotly). State via React hooks +
URL query for filters. No backend — everything client-side from the JSON.

## Design system (apple.com product-launch bar — this is graded)
- Type: Inter (system-stack fallback). Display h1 64–80px desktop, tight tracking; body line-height
  generous; max measure 68ch.
- Palette: bg `#FAFAF8`, text `#0B0B0C`, single accent deep indigo `#3B3BFF`; semantic green/red for
  data only, never decoration. Implement a dark-mode variant of the same tokens.
- Space: 8px grid; section padding 120–160px desktop; separate with whitespace, not borders.
- Motion: scroll-triggered fade+rise (12px, 400ms ease-out via IntersectionObserver); number
  count-ups on stat reveal; transform/opacity only (60fps); respect `prefers-reduced-motion`;
  skeleton loaders, no spinners. No parallax.
- If a `frontend-design` skill/guide is available, read it before writing components.

## Pages / sections (IA)
1. **Hero** — "ESG scores are slow. The signal isn't." + one animated headline stat
   (`model.headline.net_q5q1_spread_annual_pct`); scroll cue; sticky minimal top bar after scroll.
2. **The Idea** — 3 scroll-told panels (lagging scores → alternative signals → early entry), small
   inline animated SVG diagrams, zero jargon.
3. **Leaderboard** — all ~500 companies. **Virtualized** table (60fps), instant search, filters
   (country, sector, grade, classification, risk flags), sortable cols: rank, company, country,
   sector, Score (+grade badge + confidence range bar), classification chip, coverage %, flags.
   Row → company page. Keyboard navigable. Mobile = card collapse.
   - **Weight sandbox** panel: sliders per pillar (sentiment_dynamics, transition_readiness,
     governance_credibility, disclosure_credibility). On change, recompute
     `overall = Σ weight_i × pillar_scores[i]` (exclude `data_coverage` from the sum) and re-rank
     with FLIP row animations; show "Custom weights — rankings differ from the validated model"
     banner; one-click reset to `model.validated_weights`.
4. **Company detail** — animated radial score + confidence band; pillar bars; the `explanation`
   sentence prominent; 2×2 classification mini-map with the company's dot (axes
   `esg_level_pctile` × `esg_momentum_pctile`); price+sentiment+score overlay (from `timeseries`,
   show honest "no timeseries" state when null); risk-flag chips with tooltips; data-coverage card.
   - **Compare view**: 2–4 companies side by side (pillar bars aligned, scores+ranges, chips,
     overlaid timelines), sticky headers, smooth add/remove.
5. **Methodology** — variables/composites/validation for a smart non-finance reader; "How to read
   this" progressive-disclosure toggle on every chart; placebo chart + train/test chart get full
   sections.
6. **Results** — interactive money chart (Q5 vs Q1 vs benchmark vs naive-ESG, train/test line, net),
   2×2 scatter (hover names), by-country bars. Read `backtest.json`, `ic_table.json`,
   `placebo.json`, `by_country.json`.
7. **Risks** — severity-graded cards (placeholder copy ok; Claude supplies final text). Honest tone.
8. **Footer** — citations/sources/retrieval-dates placeholders + "Built for PolyFinTech100 2026 ·
   CGS International ESG Intelligence."

## Global requirements
- If `data_mode === "synthetic"`, show a persistent, unmissable **"SYNTHETIC DEMONSTRATION DATA"**
  banner. A visible "Research demonstration — not investment advice" disclaimer site-wide.
- Every metric shows a one-line tooltip definition on hover/tap.
- Responsive 360px→4K. Lighthouse ≥95 perf+a11y on the static build. Zero lorem ipsum / dead links /
  default-styled components.
- All copy can be placeholder where marked; Claude will replace prose. Do NOT invent statistics —
  numbers come only from the JSON.

## Acceptance
`npm run build` clean; loads synthetic companies.json; leaderboard scrolls at 60fps; weight sandbox
re-ranks live; 5 random company pages match the JSON; mobile + reduced-motion pass.

Report back: dev-server command, build command, and a screenshot/description of hero + leaderboard.
