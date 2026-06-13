# Current tiny adapter held-out dev alignment diagnostics

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
- Rows with mismatches: `6`
- Schema-invalid predictions: `0`

## Field Mismatch Counts

- `confirmation_required`: `3`
- `normalized_command`: `6`
- `route`: `3`
- `safety.allow`: `1`
- `safety.reason`: `2`
- `slots`: `4`
- `task_type`: `3`

## Mismatch Category Counts

- `value_mismatch`: `22`

## Row Mismatches

### `seed-open-example`

- `normalized_command` (value_mismatch): gold string(6): 打开示例网站; prediction string(14): 打开 example.com

### `seed-open-example-aug-1`

- `task_type` (value_mismatch): gold string(8): navigate; prediction string(6): search
- `route` (value_mismatch): gold string(8): open_url; prediction string(10): search_web
- `slots` (value_mismatch): gold object with keys: url; prediction empty object
- `normalized_command` (value_mismatch): gold string(6): 打开示例网站; prediction string(8): 打开示例网站看看

### `seed-open-example-aug-2`

- `normalized_command` (value_mismatch): gold string(6): 打开示例网站; prediction string(13): 去 example.com

### `seed-clarify-ambiguous`

- `task_type` (value_mismatch): gold string(7): clarify; prediction string(6): search
- `route` (value_mismatch): gold string(7): clarify; prediction string(10): search_web
- `safety.reason` (value_mismatch): gold string(17): ambiguous_request; prediction string(15): public_readonly
- `confirmation_required` (value_mismatch): gold bool: True; prediction bool: False
- `slots` (value_mismatch): gold object with keys: ambiguity; prediction empty object
- `normalized_command` (value_mismatch): gold string(6): 请求澄清目标; prediction string(6): 帮我打开那个

### `seed-clarify-ambiguous-aug-1`

- `safety.allow` (value_mismatch): gold bool: True; prediction bool: False
- `confirmation_required` (value_mismatch): gold bool: True; prediction bool: False
- `slots` (value_mismatch): gold object with keys: ambiguity; prediction object with keys: ambiguity
- `normalized_command` (value_mismatch): gold string(6): 请求澄清目标; prediction string(7): 帮我弄一下那个

### `seed-clarify-ambiguous-aug-2`

- `task_type` (value_mismatch): gold string(7): clarify; prediction string(6): search
- `route` (value_mismatch): gold string(7): clarify; prediction string(10): search_web
- `safety.reason` (value_mismatch): gold string(17): ambiguous_request; prediction string(15): public_readonly
- `confirmation_required` (value_mismatch): gold bool: True; prediction bool: False
- `slots` (value_mismatch): gold object with keys: ambiguity; prediction empty object
- `normalized_command` (value_mismatch): gold string(6): 请求澄清目标; prediction string(4): 处理一下
