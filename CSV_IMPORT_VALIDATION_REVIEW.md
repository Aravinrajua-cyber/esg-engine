# CSV Import Validation Review

## Scope

Reviewed provider-neutral CSV templates, invalid fixtures, and `tests/test_csv_import_fixtures.py`. There is no production CSV import endpoint in the current prototype.

## Covered By Existing Fixtures And Tests

- Missing required field.
- Duplicate company identifier or history key.
- Invalid ISO date.
- Non-numeric score.
- Score outside the `0..100` range.
- Impossible confidence interval.
- Malformed CSV quoting.
- Formula-injection cells beginning with `=`, `+`, `-`, or `@`.
- Excessively large text field.
- Unsupported country code.

## Added In This Support Pass

- Invalid ordinary numeric fields.
- Out-of-range `controversy_level`.
- Unsupported financial period.
- Negative price or volume.

## Future Production Controls

- Enforce file size, row count, and encoding limits before parsing.
- Resolve import paths under approved directories only.
- Preserve missing values instead of imputing during import.
- Log validation failures without exposing secrets or raw credentials.
- Keep provider-specific field mapping outside the stable CSV contract.
