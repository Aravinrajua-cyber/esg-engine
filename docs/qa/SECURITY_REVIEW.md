# Security Review

## Current Surface

- Python scripts read local JSON, CSV, parquet, and generated figure/report artifacts.
- The frontend is a static Vite/React app that reads JSON from `outputs/site_data` through the Vite data bridge.
- No authenticated backend, database, file upload endpoint, or public API endpoint exists in this prototype.

## Key Risks For Future Real-Data Mode

| Risk | Severity | Recommended control |
|---|---:|---|
| Formula injection in CSV imports | High | Reject cells beginning with `=`, `+`, `-`, or `@`. |
| Path traversal in file import tooling | High | Resolve paths under approved data directories before reading. |
| Oversized CSV or JSON inputs | Medium | Enforce file-size and row-count limits. |
| Malformed CSV quoting | Medium | Fail closed and report the row/file. |
| Unsupported country or sector values | Medium | Validate against an allowlist before scoring. |
| Sensitive data in logs | High | Redact secrets, tokens, and raw credentials. |
| Unlicensed data redistribution | High | Confirm source terms before publishing generated data. |
| Dependency vulnerability drift | Medium | Run `npm audit` and Python dependency review once npm install works. |
| Client-side trust assumptions | Medium | Treat frontend filters and displays as presentation only, not authorization. |

## Current Findings

- No `.env` file was found during the hygiene pass.
- No obvious API-key pattern was found in the allowed review pass.
- The default npm cache is outside the repo and had permission/locking failures in this session.
- The project-local `.npm-cache` diagnostic directory is ignored by `.gitignore`.
- Generated synthetic outputs are labelled as demonstration data in the report and frontend source.

## Required Before Upload Or API Features

1. Add a dedicated import validation module with unit tests.
2. Validate file extension, MIME type, size, encoding, row count, and schema.
3. Reject formula-like cells and path traversal inputs.
4. Redact all secrets in logs and user-facing errors.
5. Store source metadata and retrieval timestamps with imported data.
6. Run threat-model review for any hosted backend.

