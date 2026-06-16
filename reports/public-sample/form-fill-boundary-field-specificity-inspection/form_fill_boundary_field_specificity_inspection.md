# Voice2Task form-fill boundary and field-specificity inspection

This is an analysis-only form-fill boundary and field-specificity inspection derived from committed formal public held-out residual-cluster evidence. It is not a prediction run, not training, not data mutation, not held-out recovery, and not evaluator relaxation.

## Boundary

- strict `contract_exact_match` remains primary.
- Strict `slot_f1` remains authoritative for slot scoring.
- `slot_f1_soft` remains internal diagnostic-only.
- Predictions are not repaired, replaced, rewritten, normalized, or re-scored.
- This report does not authorize data, training, prompt, or evaluator changes.

## Summary

- Source manifest id: `public-sample-20260616T022151Z`
- Source cluster artifact: `reports/public-sample/formal-heldout-residual-cluster-inspection/formal_heldout_residual_cluster_inspection.json`
- Strict exact match: `{'dev': 0.30434782608695654, 'test': 0.2898550724637681}`
- Strict slot F1: `{'dev': 0.391304347826087, 'test': 0.5072463768115942}`
- Soft slot F1: `{'dev': 0.7315387631291138, 'test': 0.7609315000619348}`
- Soft slot F1 primary metric: `False`
- Form-fill clusters: `5`
- Form-fill cluster-row incidence total: `49`
- Form-fill residual fields: `49`
- Buckets: `3`
- Top bucket: `missing_confirmation_marker`
- Source count consistency: `{'source_form_fill_cluster_count': 5, 'bucketed_form_fill_cluster_count': 5, 'source_form_fill_cluster_row_incidence_total': 49, 'bucketed_form_fill_cluster_row_incidence_total': 49, 'source_form_fill_residual_fields': 49, 'bucketed_form_fill_residual_fields': 49, 'ok': True}`
- Recommended next step: `define_form_fill_confirmation_and_field_specificity_policy_before_data_or_training`

## Buckets

### `missing_confirmation_marker`

- Diagnostic interpretation: normalized_command omits or alters explicit confirmation wording such as 并确认
- Clusters: `1`
- Cluster-row incidence total: `27`
- Residual fields: `27`
- Split counts: `{'dev': 11, 'test': 16}`
- Field paths: `['normalized_command']`
- Categories: `{'normalized_command_strict_string_mismatch': 27}`
- Source family counts: `{'family-confirmation-dev-1': 1, 'family-confirmation-dev-2': 2, 'family-confirmation-dev-3': 2, 'family-confirmation-test-1': 2, 'family-confirmation-test-2': 2, 'family-confirmation-test-3': 3, 'family-form_fill-dev-1': 2, 'family-form_fill-dev-2': 1, 'family-form_fill-dev-3': 3, 'family-form_fill-test-1': 3, 'family-form_fill-test-2': 3, 'family-form_fill-test-3': 3}`
- Recommended action candidate: `define_form_fill_confirmation_marker_policy_before_data_or_training`

Representative examples:

- `dev / family-form_fill-dev-1 / normalized_command`: gold string(8): 填写手机号并确认; prediction string(5): 填写手机号
- `dev / family-form_fill-dev-1-aug-2 / normalized_command`: gold string(8): 填写手机号并确认; prediction string(6): 填写手机号码
- `dev / family-form_fill-dev-2-aug-1 / normalized_command`: gold string(9): 填写收货地址并确认; prediction string(7): 填写地址到表单
- `dev / family-form_fill-dev-3 / normalized_command`: gold string(9): 填写发票抬头并确认; prediction string(6): 填写发票抬头
- `dev / family-form_fill-dev-3-aug-1 / normalized_command`: gold string(9): 填写发票抬头并确认; prediction string(6): 填写发票抬头

### `field_specificity_or_alias_drift`

- Diagnostic interpretation: slot field labels differ by specificity or alias while staying in form-fill shape
- Clusters: `1`
- Cluster-row incidence total: `16`
- Residual fields: `16`
- Split counts: `{'dev': 10, 'test': 6}`
- Field paths: `['slots']`
- Categories: `{'slot_strict_mismatch': 16}`
- Source family counts: `{'family-confirmation-dev-1': 2, 'family-confirmation-dev-2': 1, 'family-confirmation-dev-3': 3, 'family-confirmation-test-3': 2, 'family-form_fill-dev-2': 1, 'family-form_fill-dev-3': 3, 'family-form_fill-test-1': 1, 'family-form_fill-test-2': 2, 'family-form_fill-test-3': 1}`
- Recommended action candidate: `define_form_fill_field_specificity_policy_before_data_or_training`

Representative examples:

- `dev / family-form_fill-dev-2-aug-1 / slots`: gold object with keys: field; prediction object with keys: field
- `dev / family-form_fill-dev-3 / slots`: gold object with keys: field; prediction object with keys: field
- `dev / family-form_fill-dev-3-aug-1 / slots`: gold object with keys: field; prediction object with keys: field
- `dev / family-form_fill-dev-3-aug-2 / slots`: gold object with keys: field; prediction object with keys: field
- `dev / family-confirmation-dev-1-aug-1 / slots`: gold object with keys: field; prediction object with keys: field

### `route_intent_leakage`

- Diagnostic interpretation: form-fill request is interpreted as a different intent or route boundary
- Clusters: `3`
- Cluster-row incidence total: `6`
- Residual fields: `6`
- Split counts: `{'dev': 3, 'test': 3}`
- Field paths: `['route', 'safety.reason', 'task_type']`
- Categories: `{'route_strict_mismatch': 2, 'safety_field_strict_mismatch': 2, 'task_type_strict_mismatch': 2}`
- Source family counts: `{'family-confirmation-dev-1': 3, 'family-form_fill-test-3': 3}`
- Recommended action candidate: `inspect_form_fill_clarify_boundary_before_data_or_training`

Representative examples:

- `dev / family-confirmation-dev-1-aug-2 / task_type`: gold string(9): form_fill; prediction string(7): clarify
- `test / family-form_fill-test-3-aug-2 / task_type`: gold string(9): form_fill; prediction string(7): clarify
- `dev / family-confirmation-dev-1-aug-2 / route`: gold string(9): fill_form; prediction string(7): clarify
- `test / family-form_fill-test-3-aug-2 / route`: gold string(9): fill_form; prediction string(7): clarify
- `dev / family-confirmation-dev-1-aug-2 / safety.reason`: gold string(21): requires_confirmation; prediction string(17): ambiguous_request

## Unsupported Buckets

- `harmless_strict_wording_mismatch`: not observed from current form-fill cluster-only evidence

## Recommended Next Step

Use this inspection to define a bounded form-fill confirmation and field-specificity policy before any data, prompt, training, or evaluator change.
