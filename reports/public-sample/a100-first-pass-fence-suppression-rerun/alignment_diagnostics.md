# A100 first-pass fence-suppression alignment diagnostics

This diagnostic is evidence-only: invalid predictions remain invalid. It reports field-level public-sample evidence only and does not repair, normalize, coerce, or replace prediction fields.

## Boundary

- This is not a checkpoint release.
- This is not an adapter release.
- This makes no production-readiness claim.
- This makes no full-private-corpus claim.
- This is not a live-browser benchmark or benchmark-improvement claim.

## Summary

- Gold rows: `3`
- Predictions: `3`
- Rows with mismatches: `1`
- Schema-invalid predictions: `0`

## Field Mismatch Counts

- `slots`: `1`

## Mismatch Category Counts

- `value_mismatch`: `1`

## Row Mismatches

### `seed-search-weather-aug-1`

- `slots` (value_mismatch): gold object with keys: query; prediction object with keys: city, date, topic
