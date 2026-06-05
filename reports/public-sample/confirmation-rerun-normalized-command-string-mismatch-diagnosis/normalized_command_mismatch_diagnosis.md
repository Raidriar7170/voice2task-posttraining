# Normalized-command string mismatch diagnosis

This is a local evidence-only analysis derived from prior public-sample row-mismatch artifacts. It does not normalize or semantically score `normalized_command` strings, does not mark `搜索/查询` or `明天的天气/明天天气` as equivalent, and does not repair, coerce, replace, or re-score predictions.

## Boundary

- No A100 execution was performed in this phase.
- No training, prediction rerun, prompt change, decoding change, schema change, parser change, retry change, or evaluator metric change was performed.
- This is not semantic-equivalence scoring.
- This is not a checkpoint release.
- This is not an adapter release.
- This is not held-out generalization evidence.
- This makes no production-readiness claim.
- This makes no public full-corpus release claim.
- This is not a live-browser benchmark improvement claim.
- This is not model-quality improvement evidence.

## Summary

- Normalized-command mismatch rows: `3`
- Strict string-only rows: `1`
- Co-occurs with schema failure: `1`
- Co-occurs with task/route/safety mismatch: `1`
- Strict metrics preserved: `True`
- Strict final JSON-valid rate remains `0.6666666666666666`
- Strict final contract_exact_match remains `0.0`

## Context Counts

- `co_occurs_with_schema_failure`: `1`
- `co_occurs_with_semantic_task_route_safety`: `1`
- `strict_string_only`: `1`

## Source Artifacts

- `row_mismatch_diagnosis`: `reports/public-sample/confirmation-rerun-row-mismatch-diagnosis/row_mismatch_diagnosis.json`
- `row_mismatch_manifest`: `reports/public-sample/confirmation-rerun-row-mismatch-diagnosis/manifest.json`

## Transitive Source Artifacts

These artifacts are inherited through the source row-mismatch diagnosis for traceability only; this phase derives its counts from the row-mismatch diagnosis artifacts above.
- `manifest`: `reports/public-sample/a100-confirmation-required-train-split-rerun/manifest.json`
- `metrics`: `reports/public-sample/a100-confirmation-required-train-split-rerun/metrics.json`
- `predictions`: `reports/public-sample/a100-confirmation-required-train-split-rerun/predictions.jsonl`
- `schema_guard_summary`: `reports/public-sample/a100-confirmation-required-train-split-rerun/schema_guard_summary.json`
- `train_split_gold`: `reports/public-sample/a100-confirmation-required-train-split-rerun/train_split_gold.jsonl`

## Row Diagnosis

### `seed-search-weather`

- Context: `co_occurs_with_schema_failure`
- Source primary failure family: `missing_required_field_schema_failure`
- Co-occurring field paths: `confirmation_required`
- `normalized_command` (value_mismatch): gold string(8): 搜索北京明天天气; prediction string(9): 搜索北京明天的天气

### `seed-search-weather-aug-1`

- Context: `co_occurs_with_semantic_task_route_safety`
- Source primary failure family: `semantic_task_route_safety_mismatch`
- Co-occurring field paths: `route, safety.reason, task_type`
- `normalized_command` (value_mismatch): gold string(8): 搜索北京明天天气; prediction string(8): 查询北京明天天气

### `seed-search-weather-aug-2`

- Context: `strict_string_only`
- Source primary failure family: `strict_string_field_exact_match_mismatch`
- Co-occurring field paths: `none`
- `normalized_command` (value_mismatch): gold string(8): 搜索北京明天天气; prediction string(9): 搜索北京明天的天气
