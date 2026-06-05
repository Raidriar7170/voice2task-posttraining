# Confirmation-required emission repair summary

Status: local prompt and diagnostic hardening only. This is not A100 improvement evidence and does not prove model recovery.

## What changed

- Strengthened the shared Voice2Task prompt so `confirmation_required` is explicitly described as a required boolean Browser Task Contract top-level field.
- Added a low-risk weather/public-readonly search example with `task_type=search`, `route=search_web`, `confirmation_required=false`, and a query-shaped `slots` object.
- Added prompt-constraint metadata for `confirmation_required` boolean visibility and weather-to-search confirmation-false visibility.
- Added public-safe source diagnostics that count missing `confirmation_required` without repairing or coercing invalid predictions.

## Prior evidence context

- Prior A100 route-ontology train-split rerun: `reports/public-sample/a100-route-ontology-train-split-rerun/`.
- That rerun produced three train predictions with raw `route=search_web` and raw route/gold match `3/3`.
- Strict final-contract schema-valid remained `0/3` because all three predictions omitted `confirmation_required`.
- This local phase does not change or reinterpret those predictions.

## Prompt constraints

- `task_type_enum_visible`: true
- `route_enum_visible`: true
- `route_not_url_or_path_visible`: true
- `route_execution_channel_visible`: true
- `route_domain_values_not_route_visible`: true
- `weather_to_search_route_example_visible`: true
- `weather_to_search_confirmation_false_visible`: true
- `confirmation_required_boolean_visible`: true
- `slots_object_not_array_visible`: true
- `required_field_skeleton_visible`: true
- `required_field_checklist_visible`: true
- `canonical_json_one_shot_visible`: true
- `whole_object_boundary_visible`: true

## Diagnostic changes

- Missing `confirmation_required` count is visible in source diagnostics.
- Missing `confirmation_required` examples are reported as symptoms only.
- Invalid predictions remain invalid.
- The repair does not normalize, coerce, replace, or fill prediction outputs.

## Validation

- `PYTHONPATH=src pytest -q tests/test_formatting_training.py tests/test_evaluator_reports.py::test_source_diagnostics_report_targets_prompt_split_prediction_and_decoding_evidence tests/test_a100_sft_prediction_smoke.py::test_real_sft_prediction_rejects_markdown_wrapped_retry_even_when_fragment_is_valid tests/test_a100_sft_prediction_smoke.py::test_real_sft_prediction_skips_retry_when_raw_attempt_is_valid`: 17 passed.

## Boundary

- This phase did not train.
- This phase did not run private prediction or A100 execution.
- This phase did not repair or coerce model outputs.
- This phase does not fill missing confirmation_required in prediction artifacts.
- This phase does not prove model recovery.
- This phase does not prove held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement.

## Recommended next step

After local validation, review, archive, and guarded integration, a later separately authorized A100 prediction-only train-split rerun can test whether this local repair changes actual private-adapter outputs.
