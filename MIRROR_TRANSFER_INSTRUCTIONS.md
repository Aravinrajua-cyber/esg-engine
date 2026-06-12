# Mirror Transfer Instructions

The original repository remains authoritative:

```text
C:\Hackathon\esg-engine
```

The mirror containing this support pass is:

```text
C:\Users\aravi\esg-engine-codex-mirror
```

## Preferred Review Flow

1. Open the mirror and inspect the branch:

```bat
cd /d C:\Users\aravi\esg-engine-codex-mirror
git status --short
git log --oneline -1
```

2. Review the support patch:

```bat
type CODEX_SUPPORT_PATCH.diff
```

3. In the original repository, create a review branch:

```bat
cd /d C:\Hackathon\esg-engine
git switch -c codex-mirror-support-review
```

4. Apply the patch carefully:

```bat
git apply --check C:\Users\aravi\esg-engine-codex-mirror\CODEX_SUPPORT_PATCH.diff
git apply C:\Users\aravi\esg-engine-codex-mirror\CODEX_SUPPORT_PATCH.diff
```

If `CODEX_RESULTS.md` or other support files already exist as untracked files in the original repository, `git apply --check` may fail. In that case, inspect the patch and manually merge the relevant sections rather than overwriting existing files.

5. Run the network-independent tests:

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m pytest -q
```

6. Review the staged diff:

```bat
git diff
git status --short
```

7. Only after Claude Code approves the support changes, commit them in the original repository.

## What Not To Transfer Automatically

- Do not copy the mirror over the original repository.
- Do not overwrite `data/raw`, `outputs`, or `.git` in the original repository.
- Do not rerun live Yahoo fetchers until network access and write access are confirmed.
- Do not claim browser QA, Word QA, npm build, or live-data validation passed until those checks run in the original environment.

## Local Rerun Commands After Transfer

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m pytest -q
```

When npm registry access works:

```bat
cd /d C:\Hackathon\esg-engine\site
npm.cmd install
npm.cmd run build
```

When Yahoo and write access work:

```bat
cd /d C:\Hackathon\esg-engine
.\.venv\Scripts\python.exe -m src.fetchers.fx
.\.venv\Scripts\python.exe -m src.fetchers.prices
.\.venv\Scripts\python.exe -m src.fetchers.esg
.\.venv\Scripts\python.exe -m src.fetchers.fundamentals
```
