# A100 retry JSON-only boundary constrained decoding diagnosis

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
- Legacy task_type alias count: `0`
- Path-like route count: `0`
- Prose/Markdown wrapper count: `3`

## Parse Status Counts

### `raw_attempt`

- `json_object`: `3`

### `retry_attempt`

- `json_fragment_object`: `3`

## Symptom Examples

### `legacy_task_type_alias`

- none

### `path_like_route`

- none

### `prose_markdown_wrapper`

- `seed-search-weather` `retry_attempt`: json_fragment_object
- `seed-search-weather-aug-1` `retry_attempt`: json_fragment_object
- `seed-search-weather-aug-2` `retry_attempt`: json_fragment_object
