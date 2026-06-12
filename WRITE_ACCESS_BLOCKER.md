# Write-Access Blocker

## Summary

The Codex session could read `C:\Hackathon\esg-engine` but could not write to it. The original repository remains authoritative and was not modified by this support pass.

## Failed Write Probes

The following probes failed in the original repository:

```bat
Add-Content -LiteralPath CODEX_RESULTS.md -Value "" -Encoding utf8 -ErrorAction Stop
```

Error excerpt:

```text
Access to the path 'C:\Hackathon\esg-engine\CODEX_RESULTS.md' is denied.
```

```bat
'probe' | Set-Content -LiteralPath data\raw\codex_write_probe.tmp -Encoding utf8 -ErrorAction Stop
```

Error excerpt:

```text
Access to the path 'C:\Hackathon\esg-engine\data\raw\codex_write_probe.tmp' is denied.
```

`pytest -q` also failed in the original repository because `tests/test_companies_json.py::test_synthetic_generation_is_deterministic_with_seed_42` attempted to rewrite:

```text
C:\Hackathon\esg-engine\outputs\site_data\companies.json
```

and received:

```text
PermissionError: [Errno 13] Permission denied
```

## Impact

WO-1 could not create:

- `data/raw/fx_daily.parquet`
- `data/raw/prices_daily.parquet`
- `data/raw/esg_snapshot.parquet`
- `data/raw/fundamentals.parquet`
- fetcher failure CSV files

The remaining network-independent support work was completed in the mirror at:

```text
C:\Users\aravi\esg-engine-codex-mirror
```
