# A100 strict-retry constrained decoding diagnosis

This diagnosis is local decoder/output-shape hardening evidence only: invalid predictions remain invalid, and the report does not repair, normalize, coerce, or replace model outputs.

## Boundary

- This is not a checkpoint release.
- This is not an adapter release.
- This is not a model recovery claim.
- This is not held-out generalization evidence.
- This makes no production-readiness claim.
- This makes no full-private-corpus claim.
- This is not a live-browser benchmark or benchmark-improvement claim.

## Summary

- Predictions: `3`
- Decoded summary rows: `3`
- Prediction schema-valid count: `0`
- Invalid predictions: `3`
- Raw attempt schema-valid count: `0`
- Retry attempt schema-valid count: `0`
- Validated output schema-valid count: `0`
- Legacy task_type alias count: `2`
- Path-like route count: `0`
- Prose/Markdown wrapper count: `3`

## Parse Status Counts

### `raw_attempt`

- `json_object`: `2`
- `non_json`: `1`

### `retry_attempt`

- `json_fragment_object`: `3`

## Symptom Examples

### `legacy_task_type_alias`

- `seed-search-weather` `raw_attempt`: string(10): search_web
- `seed-search-weather-aug-2` `raw_attempt`: string(10): search_web

### `path_like_route`

- none

### `prose_markdown_wrapper`

- `seed-search-weather` `retry_attempt`: json_fragment_object
- `seed-search-weather-aug-1` `retry_attempt`: json_fragment_object
- `seed-search-weather-aug-2` `retry_attempt`: json_fragment_object

## Strict Retry Interpretation

- JSON fragment retry attempts: `3`
- Strict retry rejected fragment count: `3`
- Retry fragments wrapped in Markdown/prose are not accepted as schema-valid Browser Task Contracts.
