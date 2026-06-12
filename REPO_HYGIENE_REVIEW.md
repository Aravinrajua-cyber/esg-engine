# Repository Hygiene Review

## Scope

Reviewed the repository for local secrets, dependency caches, generated outputs, large temporary files, and OS/editor artifacts.

## Commands Used

```bat
cd /d C:\Hackathon\esg-engine
git status --short
Get-ChildItem -Force -Recurse -File | Where-Object { $_.Name -match '^\.env($|\.)|\.npmrc$|id_rsa|id_dsa|credentials|secret|token|key' }
rg -n --hidden --glob '!/.git/**' --glob '!site/.npm-cache/**' --glob '!.venv/**' --glob '!**/__pycache__/**' "(api[_-]?key|secret|token|password|BEGIN RSA|PRIVATE KEY|AWS_ACCESS_KEY|AIza|sk-[A-Za-z0-9])" .
Get-ChildItem -Force -Recurse -Directory | Where-Object { $_.Name -in @('node_modules','__pycache__','.pytest_cache','.npm-cache','.venv','.vscode') }
Get-ChildItem -Force -Recurse -File | Where-Object { $_.Length -gt 5MB }
```

## Sensitive Files Found

No project `.env`, `.npmrc`, private key, credential file, or obvious source-code API key was found.

Search hits for words such as `token`, `secret`, and `key` were documentation or ordinary source text, not exposed credentials. No secret values are printed here.

## Cache And Generated Files Found

| Category | Found | Action |
|---|---:|---|
| Python virtual environment | Yes: `.venv/` | Already ignored. |
| Python bytecode/cache | Yes: `__pycache__/`, `.pytest_cache/` | Already ignored. |
| npm project cache | Yes: `site/.npm-cache/` | Ignored. |
| `node_modules` | Not present | Ignore rule already present. |
| Generated report files | Yes: `outputs/report/*.docx` | Added ignore rules. |
| Generated figure files | Yes: `outputs/figures/*.png`, `*.html` | Already ignored. |
| Generated logs | Yes: `logs/actions.jsonl` | Added ignore rule. |
| Synthetic parquet data | Yes: `data/_synth/*.parquet` | Added ignore rule. |
| Raw/interim/processed data | Raw/interim present; processed directory present | Added/confirmed ignore rules. |
| OS/editor files | None found beyond ignored patterns | `.DS_Store`, `Thumbs.db`, `.vscode/` ignored. |

## What Should Be Committed

- Source code under `src/`, except generated caches.
- Frontend source and configuration under `site/`, excluding `node_modules`, `dist`, and `.npm-cache`.
- Tests under `tests/`.
- Specs and coordination docs.
- Support docs: `README.md`, `LOCAL_RUN_GUIDE.md`, `MANUAL_QA_CHECKLIST.md`, `DEMO_SCRIPT.md`, `DATA_IMPORT_GUIDE.md`, `SECURITY_REVIEW.md`, `REPO_HYGIENE_REVIEW.md`, `CODEX_SUPPORT_RESULTS.md`.
- CSV templates under `data/templates/`.
- Invalid CSV fixtures under `data/examples/invalid/`.
- Windows helper scripts under `scripts/`.

## What Should Be Ignored

- `.venv/`
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`
- `.env`, `.env.*`
- `site/node_modules/`
- `site/dist/`
- `site/.npm-cache/`
- `data/raw/`
- `data/interim/`
- `data/processed/`
- `data/_synth/`
- `*.parquet`
- `logs/*.jsonl`
- `outputs/figures/*.png`
- `outputs/figures/*.html`
- `outputs/report/*.docx`
- `outputs/report/*.pdf`
- `outputs/report/*_render/`

## Notes

The final Word report and synthetic figures remain in the workspace for local demonstration, but they are generated artifacts. They should be regenerated from scripts rather than treated as source files.

