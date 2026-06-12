# AGENTS.md — read this first (Claude + Codex)

This repo is built by **two agents in parallel**. Codex reads this file automatically.

- **Claude (lead):** research design, universe, GDELT fetcher, signals, all Phase-4 statistics,
  scoring/explanation logic, and **all written content**. Reviews every Codex diff.
- **Codex (implementation):** the workstreams assigned in `specs/` only.

## Hard rules (non-negotiable)
1. **Stay in your lane.** Only create/edit files inside directories assigned to you in
   `COORDINATION.md`. Never edit a file owned by the other agent.
2. **Frozen contracts — read-only for Codex:** `config/settings.yaml`, `SCHEMAS.md`,
   `RESEARCH_LOG.md`, `BIAS_REGISTER.md`. If you think one must change, STOP and say so; do not edit.
3. **No fabricated data, ever.** Missing values stay missing. Failed fetches are logged, not faked.
   No hardcoded results that should come from the pipeline.
4. **Build against the schema in `SCHEMAS.md`** (it is the single source of truth for every artifact).
5. Log major actions via `src/util/log.py` (`log_action`). Keep error handling explicit.

Your task specs live in `specs/`. The live status board is `COORDINATION.md`.
