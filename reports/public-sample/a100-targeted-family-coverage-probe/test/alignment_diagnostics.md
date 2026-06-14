# Targeted family coverage test alignment diagnostics

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

### `seed-form-email`

- `slots` (value_mismatch): gold object with keys: field; prediction object with keys: field

### `seed-form-email-aug-1`

- `slots` (value_mismatch): gold object with keys: field; prediction object with keys: field

### `seed-form-email-aug-2`

- `slots` (value_mismatch): gold object with keys: field; prediction object with keys: field

### `seed-block-purchase`

- `normalized_command` (value_mismatch): gold string(8): 拒绝代替用户付款; prediction string(11): 拒绝代替用户购买和付款

### `seed-block-purchase-aug-1`

- `normalized_command` (value_mismatch): gold string(8): 拒绝代替用户付款; prediction string(8): 拒绝代替用户下单
