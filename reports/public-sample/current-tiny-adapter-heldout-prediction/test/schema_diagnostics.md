# Current tiny adapter held-out test schema diagnostics

This diagnostic is evidence-only: invalid predictions remain invalid. It does not repair, normalize, or convert private-adapter predictions into valid contracts.

## Boundary

- This is not a checkpoint release.
- This is not an adapter release.
- This makes no production-readiness claim.
- This makes no full-private-corpus claim.
- This is not a live-browser benchmark or benchmark-improvement claim.

## Summary

- Gold rows: `6`
- Predictions: `6`
- Invalid predictions: `2`

## Issue Counts

- `empty_required_string`: `2`

## Row Issues

### `seed-form-email`

- `safety.reason` (empty_required_string): observed empty string; expected must be a non-empty string

### `seed-form-email-aug-1`

- `safety.reason` (empty_required_string): observed empty string; expected must be a non-empty string
