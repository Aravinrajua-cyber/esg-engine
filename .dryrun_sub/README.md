# ESG Momentum Engine Submission Package

This folder contains the final generated submission artifacts.

## Contents

- `ESG_Momentum_Engine_Report.docx` - final Word report assembled from Phase 4 results and figure PNGs.
- `ESG_Momentum_Engine.pptx` - final slide deck generated from `tools/deck/deck_content.yaml`.
- `site/` - not generated in this run (`--skip-site-build`).

## Inputs Read

- Phase 4 keys: backtest_metrics, config_train_net_spread, fama_macbeth_coefficients, frozen_winner, ic_results, results, tables
- Figure PNG count: 14
- Site content brand: ESG Momentum Engine
- Site data mode: synthetic
- Remaining Claude prose markers in report: 0

## How To Rebuild

```bat
python tools/submit/assemble_submission.py
```

The build requires npm dependencies to be installed in `site/` for the final site export.
