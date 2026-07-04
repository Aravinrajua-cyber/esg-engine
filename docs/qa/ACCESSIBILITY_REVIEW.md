# Accessibility Review

## Scope

Source-only review of the static React frontend. Browser, screen-reader, Lighthouse, and color-contrast tooling were not run in this pass.

## Current Strengths

- The page uses semantic sections, headings, a `main` region, and a footer.
- Keyboard focus styles exist for links, buttons, inputs, selects, and virtual leaderboard rows.
- Leaderboard rows are focusable and open the detail view with Enter.
- The theme toggle has a `title` attribute.
- Reduced motion is handled with `@media (prefers-reduced-motion: reduce)`.
- Plot containers use `role="img"` and an `aria-label` based on chart title.

## Risks To Verify In Browser

- Focus order through the virtualized leaderboard and detail panel.
- Whether row buttons and row-level keyboard handlers create duplicate or confusing tab stops.
- Color contrast for muted text, chips, and chart colors in both themes.
- Screen-reader usefulness of chart titles; richer chart summaries may be needed.
- Mobile layout at 375px width, especially table rows, filters, and score confidence bands.
- Whether the fixed synthetic banner and sticky topbar obscure anchor targets.

## Recommended Browser QA

Use `MANUAL_QA_CHECKLIST.md` after npm install/build succeeds. Record desktop, tablet, and mobile viewport results separately.
