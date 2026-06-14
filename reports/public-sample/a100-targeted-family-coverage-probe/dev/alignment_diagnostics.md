# Targeted family coverage dev alignment diagnostics

This diagnostic is evidence-only: invalid predictions remain invalid. It reports field-level public-sample evidence only and does not repair, normalize, coerce, or replace prediction fields.

## Boundary

- This is not a checkpoint release.
- This is not an adapter release.
- This makes no production-readiness claim.
- This makes no full-private-corpus claim.
- This is not a live-browser benchmark or benchmark-improvement claim.

## Summary

- Gold rows: `6`
- Predictions: `6`
- Rows with mismatches: `5`
- Schema-invalid predictions: `0`

## Field Mismatch Counts

- `normalized_command`: `2`
- `slots`: `3`

## Mismatch Category Counts

- `value_mismatch`: `5`

## Row Mismatches

### `seed-open-example`

- `normalized_command` (value_mismatch): gold string(6): 打开示例网站; prediction string(6): 打开示例页面

### `seed-open-example-aug-2`

- `normalized_command` (value_mismatch): gold string(6): 打开示例网站; prediction string(11): 访问Example网站

### `seed-clarify-ambiguous`

- `slots` (value_mismatch): gold object with keys: ambiguity; prediction object with keys: ambiguity

### `seed-clarify-ambiguous-aug-1`

- `slots` (value_mismatch): gold object with keys: ambiguity; prediction object with keys: ambiguity

### `seed-clarify-ambiguous-aug-2`

- `slots` (value_mismatch): gold object with keys: ambiguity; prediction object with keys: ambiguity
