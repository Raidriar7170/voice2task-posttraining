# A100 retry JSON-only boundary schema diagnostics

This diagnostic is evidence-only: invalid predictions remain invalid. It does not repair, normalize, or convert private-adapter predictions into valid contracts.

## Boundary

- This is not a checkpoint release.
- This is not an adapter release.
- This makes no production-readiness claim.
- This makes no full-private-corpus claim.
- This is not a live-browser benchmark or benchmark-improvement claim.

## Summary

- Gold rows: `3`
- Predictions: `3`
- Invalid predictions: `3`

## Issue Counts

- `missing_required_field`: `3`

## Row Issues

### `seed-search-weather`

- `task_type` (missing_required_field): observed null; expected Browser Task Contract requires this top-level field

### `seed-search-weather-aug-1`

- `task_type` (missing_required_field): observed null; expected Browser Task Contract requires this top-level field

### `seed-search-weather-aug-2`

- `task_type` (missing_required_field): observed null; expected Browser Task Contract requires this top-level field
