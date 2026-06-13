# Claude ⇄ Codex Frontend Integration

Date: 2026-06-13 · Authoritative repo: `C:\Hackathon\esg-engine` · Mirror (reference only):
`C:\Users\aravi\esg-engine-codex-mirror`

**Outcome:** the original investment-screening product is fully preserved, and Codex's new
**Model Performance** experience was integrated as an additional page. The Codex mirror frontend was
treated as a component source and design reference, **not** applied as a replacement.

---

## Mirror artifacts reviewed

| Artifact | Verdict |
|----------|---------|
| `CODEX_FRONTEND_HANDOFF.md` | Read in full — documents the inline-SVG chart contracts and explicitly warns to preserve the screener. Followed. |
| `MODEL_PERFORMANCE_PAGE_SPEC.md` | Read — used for per-chart "what it shows / permitted vs prohibited conclusion" framing. |
| `MODEL_PERFORMANCE_QA_CHECKLIST.md` | Read — used as the acceptance checklist (see status below). |
| `site/src/App.tsx` (mirror) | Reviewed — harvested the inline SVG chart components; rejected its removal of the screener. |
| `site/src/styles.css` (mirror) | Reviewed — harvested chart/waterfall/funnel CSS; rejected the Google Fonts `@import`. |
| `site/src/Plot.tsx`, `declarations.d.ts` (mirror) | Reviewed — adopted the "Plotly removed → stub" approach. |
| `tests/test_frontend_static_contract.py` (mirror) | Reviewed — selectively merged (see Rejected for the conflicting assertions). |
| `tests/test_local_synthetic_edge_cases.py` (mirror) | Reviewed and **copied** verbatim (passes against authoritative code). |
| `CODEX_FRONTEND_PATCH.diff`, `CODEX_NEXT_PASS_RESULTS.md`, `scripts/verify_local.bat` | Acknowledged; the patch was **not** applied (it deletes the screener). Integrated by hand from the source files instead. |

---

## Codex changes RETAINED (adapted into the authoritative app)

- **Dark monochrome visual system** (`#0a0a0a` page / `#111` / `#1a1a1a` surfaces, `#e8e8e8` text,
  `#888` secondary, `#2a2a2a`/`#333` borders) with a **single `#c8ff00` accent used sparingly** —
  score rings, active/selected states (`.activeSort`, `.compare.on`, range sliders), the highlighted
  MASTER/A chart series, and a hairline on the synthetic banner. No purple/violet/blue anywhere.
- **Five Model Performance sections**, rebuilt as dependency-neutral inline React SVG in a new
  module `site/src/ModelPerformance.tsx`: Signal IC Timeline, Composite Returns, Signal Decision
  Waterfall, Placebo Test, Universe Funnel. Each has a title, axis labels + units, legend, a
  two-line plain-language annotation, an **"Illustrative Data"** badge, and a mobile-safe `viewBox`
  (no horizontal overflow).
- **Plotly removed from the runtime.** `Plot.tsx` is a `return null` stub; `declarations.d.ts` no
  longer declares the module; `plotly.js-dist-min` uninstalled. Bundle dropped from ~4.9 MB to
  **229 KB JS / 14 KB CSS**.
- **`test_local_synthetic_edge_cases.py`** (synthetic-generator determinism/bounds + CSV
  edge-case + country-code rejection) — copied; passes.
- New **Model Performance contract assertions** merged into the authoritative
  `test_frontend_static_contract.py`.

## Codex changes REJECTED (and what was done instead)

- **Removal of the screener** (leaderboard, search/filter/sort, company drilldown, E/S/G + non-ESG
  pillar bars, overall score, risk index, confidence range, comparison, navbar link). **Rejected** —
  all preserved unchanged in the authoritative `App.tsx`. Model Performance was *added*, not swapped.
- **Google Fonts `@import`** in CSS. **Rejected** (network dependency / offline-fragile). Replaced
  with the offline-safe stack `Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.
- **`recharts`.** **Rejected** — not added (per the integration rule); inline SVG used instead. (It
  was briefly installed during an earlier pass and has been uninstalled.)
- **Mirror test assertions that contradict the authoritative app** — `assert "fonts.googleapis.com"
  in css` (we require the opposite) and the screener-deletion tests. Not merged; the authoritative
  screener tests were kept and inverted-where-needed (`fonts.googleapis.com` **not** in css).
- **`PH` in the universe-funnel country split.** The mirror (and an interim spec) listed `PH`, but
  PH was dropped from the universe (no resolvable PSE tickers — documented in §3 methodology and
  `RESEARCH_LOG.md`). Shipping `PH` would contradict the report. Used the **real** breakdown
  `SG 47 / MY 46 / ID 43 / TH 37 / VN 25 = 198`.
- **Hard-coded chart values in `App.tsx`.** Moved into `site/src/synthData.ts` (single,
  clearly-labelled, swappable source) so frozen Phase 4 artifacts can replace them in minutes.

---

## Authoritative files added / modified

**Added**
- `site/src/ModelPerformance.tsx` — the Model Performance page (inline SVG charts).
- `site/src/synthData.ts` — illustrative, swappable chart data (deterministic; real numbers for the
  funnel + waterfall).
- `tests/test_local_synthetic_edge_cases.py` — copied from the mirror.
- `CLAUDE_CODEX_FRONTEND_INTEGRATION.md` — this file.

**Modified**
- `site/src/App.tsx` — added the `<ModelPerformance />` section + navbar link; removed the Plotly
  charts from Methodology/Results and the light/dark theme toggle (now pure dark). **Screener
  untouched.**
- `site/src/styles.css` — rebuilt as the dark monochrome system; preserved the leaderboard
  responsive grid rules and `:focus-visible`; added Model Performance styles; no Google Fonts.
- `site/src/Plot.tsx`, `site/src/declarations.d.ts` — reduced to no-op stubs (Plotly removed).
- `tests/test_frontend_static_contract.py` — added Model Performance + no-Plotly + offline-fonts
  assertions; kept all screener assertions.
- `site/package.json`, `site/package-lock.json` — removed `plotly.js-dist-min`; `recharts` absent.

---

## Pages / sections present after integration

Single-page app (anchor navigation; no router dependency added):

1. **Landing / hero** (`#hero`)
2. **Leaderboard & screener** (`#leaderboard`) — 500-company synthetic dataset, search, country /
   sector / grade / class / flag filters, sortable virtualized table
3. **Company-detail drilldown** — overall research score ring, E/S/G + non-ESG pillar bars,
   ESG level×momentum matrix, score timeline, **risk index**, **confidence range**, risk flags
4. **Company comparison** interface
5. **Model Performance** (`#model-performance`) — Signal IC Timeline, Composite Returns, Signal
   Decision Waterfall, Placebo Test, Universe Funnel
6. **Methodology** (`#methodology`) · **Results** metrics (`#results`) · **Risks** (`#risks`)
7. **Footer** with the persistent disclaimer

Navbar: Leaderboard · Model Performance · Methodology · Risks. The fixed **`SYNTHETIC
DEMONSTRATION DATA`** banner remains; every Model Performance chart carries an **"Illustrative
Data"** badge.

---

## Synthetic-data labelling (confirmed)

- 500-company dataset → persistent top banner `SYNTHETIC DEMONSTRATION DATA` (driven by
  `data_mode === "synthetic"`).
- Every Model Performance chart → `Illustrative Data` badge + annotations stating what can/can't be
  concluded ("…unlikely to be chance" but explicitly *illustrative until Phase 4 is frozen").
- No synthetic metric is described as live or validated predictive evidence; the footer disclaimer
  ("Research demonstration - not investment advice.") is always visible; report and frontend wording
  are consistent.

---

## Validation

- **Python tests:** `.venv\Scripts\python.exe -m pytest -q` → **97 passed, 3 skipped** (screener
  contract + new Model Performance contract + synthetic/CSV edge cases).
- **Frontend build:** `npm run build` → **success, zero errors.** `dist/` populated
  (`index.html`, `assets/index-*.css` 14 KB, `assets/index-*.js` 229 KB, `site_data/*.json`).
  Confirmed **no `plotly`/`recharts` strings in the built bundle**.
- **TypeScript:** `tsc` (strict) passes as the first half of `npm run build`.
- **Browser QA:** **NOT performed** — no browser/display is available in this environment. Static
  review only (viewBox-based SVGs scale; responsive rules at 1100px/900px/760px; reduced-motion
  honored; `:focus-visible` present; offline fonts). See commands below to run it locally.

## Remaining blockers / follow-ups

- **Browser QA pending** — verify desktop/tablet/mobile and keyboard/focus in a real browser.
- **Chart data is illustrative** — swap `site/src/synthData.ts` for frozen Phase 4 artifacts
  (`validation_results.json` / `phase4_results.pkl`) once the discovery-universe run is frozen; the
  funnel and waterfall already use real numbers.
- The GDELT discovery fetch is still running; the Model Performance numbers update to real on freeze.

## Exact commands to run next (locally)

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m pytest -q

cd /d C:\Hackathon\esg-engine\site
npm.cmd install
npm.cmd run build
npm.cmd run dev
```

Then open the dev URL and check, at 1280 / 768 / 375 px widths: the screener (search, filters,
sort, row → drilldown, score ring, E/S/G + non-ESG bars, risk index, confidence range, compare),
the Model Performance page (all five charts render, no horizontal overflow, "Illustrative Data"
badges visible), the synthetic banner, and keyboard/focus navigation.
