# Final Submission Assembler

One command produces the final report, site export, deck, and package README once real Phase 4 and Phase 5 data are present.

## Usage

```bat
python tools/submit/assemble_submission.py
```

Outputs are written to:

```text
outputs/submission/
```

## Inputs

- `data/processed/phase4_results.pkl`
- `outputs/figures/*.png`
- `site/src/site_content.json`
- `site/src/site_data.json`
- `tools/deck/deck_content.yaml`
- `tools/submit/submission_prose.yaml`

## Notes

- The site export runs `npm run build` in `site/` by default, then copies `site/dist/` to `outputs/submission/site/`.
- Use `--skip-site-build` only for local smoke tests when npm dependencies are unavailable.
- `submission_prose.yaml` fills `[CLAUDE_WRITES_HERE]` report markers by section name.
