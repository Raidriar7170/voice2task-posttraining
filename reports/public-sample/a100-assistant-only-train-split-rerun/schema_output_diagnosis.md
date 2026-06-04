# Assistant-only schema-output failure diagnosis

Status: evidence-only train-split diagnosis. Invalid predictions remain invalid; this report does not repair, normalize, coerce, or replace private-adapter outputs.

## Summary

- Prediction split: `train`
- Prediction count: `3`
- Raw JSON parseable count: `3`
- Browser Task Contract schema-valid count: `0`
- Contract schema-valid rate: `0.0000`
- Truncation or decode-limit count: `0`
- Dominant failure family: `parseable_json_contract_shape_missing_required_fields`

## Interpretation

The assistant-only rerun outputs are parseable JSON objects, but parseable JSON is not the same as schema-valid Browser Task Contract output. All three rows omit `safety`; two rows also omit `normalized_command`, and one row omits `contract_version`. Generation traces show EOS completion below `max_new_tokens`, so this evidence does not point to truncation as the primary failure.

## Missing Required Fields

- `contract_version`: `1` rows
- `normalized_command`: `2` rows
- `safety`: `3` rows

## Field Mismatches Against Gold

- `normalized_command`: `1` rows
- `slots`: `3` rows
- `task_type`: `1` rows

## Row Diagnostics

- `seed-search-weather`: raw_json_parseable=`True`, contract_schema_valid=`False`, missing=`safety`, `normalized_command`, mismatches=`slots`, finish_state=`eos_observed`.
- `seed-search-weather-aug-1`: raw_json_parseable=`True`, contract_schema_valid=`False`, missing=`safety`, `contract_version`, mismatches=`task_type`, `slots`, `normalized_command`, finish_state=`eos_observed`.
- `seed-search-weather-aug-2`: raw_json_parseable=`True`, contract_schema_valid=`False`, missing=`safety`, `normalized_command`, mismatches=`slots`, finish_state=`eos_observed`.

## Recommended Next Bounded Phase

Recommended next phase: `repair-contract-required-field-emission`. Start by choosing one small fix path after review: decoding/postprocessor guard, prompt target emphasis, or training sample/template adjustment. Do not combine all three in one phase without a new OpenSpec decision.

## Boundaries

- This is not held-out generalization evidence.
- This is not checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement evidence.
- This phase does not modify decoding, prompt templates, schemas, data generation, or training objectives.
