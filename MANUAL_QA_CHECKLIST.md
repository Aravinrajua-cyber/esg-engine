# Manual QA Checklist

Use this checklist after `scripts\verify_local.bat` passes and the frontend dev server is running.

## Website

- [ ] Homepage loads.
- [ ] Leaderboard loads.
- [ ] Exactly 500 synthetic companies can be screened.
- [ ] Search works.
- [ ] Filters work.
- [ ] Sorting works.
- [ ] Score breakdown is understandable.
- [ ] Confidence range is visible.
- [ ] Risk score is visible.
- [ ] Synthetic-demo warning is obvious.
- [ ] Long company names wrap correctly.
- [ ] Empty states are readable.
- [ ] Mobile layout works.
- [ ] Tablet layout works.
- [ ] Desktop layout works.
- [ ] Keyboard navigation works.
- [ ] Focus indicators are visible.
- [ ] Reduced-motion behaviour is respected.
- [ ] Charts remain readable.
- [ ] No console errors appear.

## Word Report

- [ ] Table of contents updates correctly.
- [ ] Graphs are readable.
- [ ] Captions remain attached to figures.
- [ ] No graph is cut off.
- [ ] No table exceeds page margins.
- [ ] Bibliography formatting is consistent.
- [ ] Synthetic findings are labelled clearly.
- [ ] Page breaks are clean.
- [ ] Appendix dictionary is readable.
- [ ] Final PDF export looks correct.

## Notes

- Browser visual QA has not passed until it is checked in a real browser at desktop, tablet, and mobile widths.
- Word visual QA has not passed until the `.docx` is opened, the table of contents is updated, and a PDF export is inspected.

