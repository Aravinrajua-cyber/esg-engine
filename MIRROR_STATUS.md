# Mirror Status

## Copy Record

- Source path: `C:\Hackathon\esg-engine`
- Mirror path: `C:\Users\aravi\esg-engine-codex-mirror`
- Copy date/time: `2026-06-13T04:23:05+08:00`
- Copy command:

```bat
robocopy C:\Hackathon\esg-engine C:\Users\aravi\esg-engine-codex-mirror /E /XD .venv node_modules .npm-cache __pycache__ .pytest_cache /XF *.pyc /TEE /LOG:C:\Users\aravi\esg-engine-codex-mirror\mirror_robocopy.log /NP /R:1 /W:1
```

## Copied Content

Robocopy reported 125 directories and 265 files copied, including:

- `.git`
- `config`
- `data`
- `logs`
- `outputs`
- `scripts`
- `site`
- `specs`
- `src`
- `tests`
- repository Markdown documents and requirements files

## Excluded Content

The copy excluded only large generated or environment-specific directories/files:

- `.venv`
- `node_modules`
- `.npm-cache`
- `__pycache__`
- `.pytest_cache`
- `*.pyc`

## Git Metadata

`.git` was preserved. The mirror started from branch `codex-independent-review` at `885b4c8`, with an inherited dirty worktree copied from the original repository. Codex created branch `codex-mirror-support-pass` inside the mirror for this support pass.

## Original Repository

The original repository at `C:\Hackathon\esg-engine` was not modified, overwritten, deleted, or renamed by the mirror copy process. All subsequent changes in this pass are confined to `C:\Users\aravi\esg-engine-codex-mirror`.
