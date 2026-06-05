# A100 normalized-command rerun row mismatch diagnosis

This is a local evidence-only analysis derived from prior public-sample artifacts. It does not repair, normalize, semantically score, coerce, replace, or re-score predictions.

## Boundary

- No A100 execution was performed in this phase.
- No training, prediction rerun, prompt change, decoding change, schema change, parser change, retry change, or evaluator metric change was performed.
- Invalid source predictions remain invalid.
- This is not semantic-equivalence scoring.
- This is not normalized-command normalization.
- This is not a checkpoint release.
- This is not an adapter release.
- This is not held-out generalization evidence.
- This makes no production-readiness claim.
- This makes no public full-corpus release claim.
- This is not a live-browser benchmark improvement claim.
- This is not model-quality improvement evidence.

## Summary

- Gold rows: `3`
- Predictions: `3`
- Rows with mismatches: `3`
- Schema-invalid predictions: `2`
- Validated output schema-valid rows: `1`
- Normalized-command exact-string matches: `2`
- Normalized-command mismatches: `1`
- Strict final JSON-valid rate remains `0.3333333333333333`
- Strict final contract_exact_match remains `0.0`

## Failure Families

- `schema_invalid_task_type_enum`: `1`
- `schema_missing_confirmation_required`: `1`
- `schema_valid_task_route_safety_slot_mismatch`: `1`

## Field Mismatch Counts

- `confirmation_required`: `1`
- `normalized_command`: `1`
- `route`: `1`
- `safety.reason`: `2`
- `slots`: `3`
- `task_type`: `2`

## Mismatch Category Counts

- `missing_prediction_field`: `1`
- `value_mismatch`: `9`

## Source Artifacts

- `manifest`: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/manifest.json`
- `metrics`: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/metrics.json`
- `normalized_command_diagnosis`: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/normalized_command_diagnosis.json`
- `predictions`: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/predictions.jsonl`
- `schema_guard_summary`: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/schema_guard_summary.json`
- `train_split_gold`: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/train_split_gold.jsonl`

## Row Diagnosis

### `seed-search-weather`

- Primary failure family: `schema_missing_confirmation_required`
- Source schema-valid prediction: `False`
- Validated output schema-valid: `False`
- Validated output source: `none`
- Raw attempt missing required fields: `confirmation_required`
- Raw attempt validation error: `missing required fields: confirmation_required`
- `confirmation_required` (missing_prediction_field): gold bool: False; prediction missing
- `slots` (value_mismatch): gold object with keys: query; prediction object with keys: city, date
- `normalized_command` (value_mismatch): gold string(8): 搜索北京明天天气; prediction string(9): 搜索北京明天的天气

### `seed-search-weather-aug-1`

- Primary failure family: `schema_valid_task_route_safety_slot_mismatch`
- Source schema-valid prediction: `True`
- Validated output schema-valid: `True`
- Validated output source: `raw_attempt`
- Raw attempt missing required fields: `none`
- Raw attempt validation error: `none`
- `task_type` (value_mismatch): gold string(6): search; prediction string(9): form_fill
- `route` (value_mismatch): gold string(10): search_web; prediction string(8): open_url
- `safety.reason` (value_mismatch): gold string(15): public_readonly; prediction string(9): form_fill
- `slots` (value_mismatch): gold object with keys: query; prediction object with keys: query

### `seed-search-weather-aug-2`

- Primary failure family: `schema_invalid_task_type_enum`
- Source schema-valid prediction: `False`
- Validated output schema-valid: `False`
- Validated output source: `none`
- Raw attempt missing required fields: `none`
- Raw attempt validation error: `task_type must be one of ['blocked', 'clarify', 'extract', 'form_fill', 'navigate', 'search']`
- `task_type` (value_mismatch): gold string(6): search; prediction string(10): search_web
- `safety.reason` (value_mismatch): gold string(15): public_readonly; prediction string(8): open_url
- `slots` (value_mismatch): gold object with keys: query; prediction object with keys: query
