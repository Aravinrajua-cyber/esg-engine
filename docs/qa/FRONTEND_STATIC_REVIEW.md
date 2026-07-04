# Frontend Static Review

## Scope

Reviewed `site/src/App.tsx`, `site/src/styles.css`, `site/src/data.ts`, `site/src/types.ts`, and `site/src/Plot.tsx` from source only. Browser execution remains gated by npm dependency installation.

## Findings

- Synthetic labelling is present in source via the exact banner string `SYNTHETIC DEMONSTRATION DATA`.
- The disclaimer `Research demonstration - not investment advice.` is always rendered in the footer.
- The leaderboard recomputes custom scores from the four model pillars only; `data_coverage` is displayed separately.
- React text rendering is used for company fields; no `dangerouslySetInnerHTML`, `eval`, `new Function`, or `document.write` usage was found in the source scan.
- The frontend currently trusts JSON payload shape at runtime. If `/site_data/*.json` can become untrusted, add runtime validation before rendering.
- The synthetic banner is only rendered for `feed.data_mode === "synthetic"`. A visible live-mode tag is not currently rendered for `data_mode === "live"`.

## Build Status

No frontend build pass is claimed from this support pass. Dependency installation requires npm registry access and should be rerun in a normal terminal.
