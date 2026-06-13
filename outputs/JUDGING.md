# JUDGING — rubric → evidence map (one page)

Answer each criterion before the judges ask. `‹FROZEN: …›` fills from `phase4_results.pkl` post-freeze.

| Criterion | What they're really asking | Specific evidence in this build |
|-----------|----------------------------|----------------------------------|
| **Feasibility** | Does it actually work end-to-end, today? | A live, free-data pipeline runs the whole chain — universe build → fetchers → signals → validation → scoring → site — on **477 real ASEAN names** across 5 markets. One command (`python tools/submit/assemble_submission.py`) regenerates the report, deck, and site. When the free ESG feed died mid-build, the pipeline **kept running on alternative data** — feasibility under real-world failure, not just on a happy path. |
| **Originality** | Is there a genuine idea here, or a dashboard? | The momentum-beats-level thesis applied to **ASEAN**, where thin coverage (Berg et al. 2022, avg rating corr 0.54) means a larger underreaction; an **alternative-data** composite that survives an ESG-provider blackout; and rigor most teams skip — **Benjamini–Hochberg FDR**, **Deflated Sharpe**, a **1,000× placebo**, a **once-touched** out-of-sample window. The "Hidden Winners" 2×2 turns the thesis into a product category. |
| **Presentation** | Can a non-quant grasp it in seconds, and is it credible? | A clean leaderboard with per-row grade, **confidence band**, and **coverage**; a deterministic one-sentence **explanation** per company; a **weight sandbox** that defuses "it's just your weights"; the **money chart** with a train/test line; and the **placebo chart** as the credibility centerpiece. The 90-second demo path is scripted (`DEMO.md`); the 7-minute pitch is structured (`PITCH.md`). |
| **Implementation** | Is it engineered, or duct tape? | Frozen config + fixed seed for reproducibility; **schema contracts** (`SCHEMAS.md`) between every stage; a **test suite** (schema-contract, signal-math, frontend-contract, CSV-validation, report-builder, deck) — currently green; **runtime JSON validation** on the frontend; and a clean Claude-owned-science / Codex-owned-plumbing separation with reviewed merges. |
| **Time-to-market** | How fast could CGS run this for real? | The **CSV/API import layer** (`src/csv_import/`, validated) is the licensed-data on-ramp: drop a CGS/Sustainalytics-grade feed behind the **same frozen schemas** and the proxied ESG-momentum variable becomes a true measured B2 across the panel — **no re-engineering**. The model, scoring, and site consume the same contracts whether the data is free or licensed. |
| **Fit to target segment** | Does it serve CGS's actual business? | Built for a **broker/research-desk** workflow on an **ASEAN-focused** universe — CGS's home market. The headline is an **implementable, long-only** top-quintile screen (we don't claim shorting where ASEAN can't short), reported **net of a per-market transaction-cost matrix** (25 bps SG large → 60 bps VN mid). It's a screen a desk could put in front of clients tomorrow, with disclaimers and uncertainty surfaced by design. |

---

### The three lines that win the room
1. **"Level is contested; momentum is observable."** — the thesis, and the answer to half the room's doubts.
2. **"We tried to kill our own result."** — the placebo + DSR + FDR, i.e. why this isn't another overfit backtest.
3. **"This is real data with real limits. The limits are the story."** — the honest-data narrative that a dead ESG feed turned into our strongest proof point.

### Headline numbers to have frozen and memorized
- Winning composite: `‹FROZEN: winning_composite›`
- Net Q5−Q1 spread (annual, net of costs): `‹FROZEN: net_q5q1_spread›` · 95% CI `‹FROZEN: spread_ci›`
- Deflated Sharpe: `‹FROZEN: deflated_sharpe›` · Placebo p: `‹FROZEN: placebo_p›`
- FDR survivors: `‹FROZEN: survivors›`
- Universe: 477 scored / 198 validated · 5 markets · train ≤2021-12-31, test 2022+
