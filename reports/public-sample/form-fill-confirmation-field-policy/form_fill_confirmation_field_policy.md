# Voice2Task form-fill confirmation and field-specificity policy

This is a policy-only form-fill confirmation and field-specificity artifact derived from the committed public form-fill inspection. It does not repair, replace, normalize, or re-score predictions.

## Boundary

- strict `contract_exact_match` and strict `slot_f1` remain authoritative.
- `slot_f1_soft` remains diagnostic-only.
- The contract evaluation ladder remains authoritative.
- No prediction run, A100 job, dataset mutation, prompt change, or training occurred.
- Any data, prompt, gold policy, evaluator, prediction, checkpoint, adapter, or training change requires a separate OpenSpec phase.

## Summary

- Source manifest id: `public-sample-20260616T022151Z`
- Source inspection artifact: `reports/public-sample/form-fill-boundary-field-specificity-inspection/form_fill_boundary_field_specificity_inspection.json`
- Source bucket count: `3`
- Policy sections: `3`
- cluster-row incidence total: `49`
- Residual fields: `49`
- Strict exact match: `{'dev': 0.30434782608695654, 'test': 0.2898550724637681}`
- Strict slot F1: `{'dev': 0.391304347826087, 'test': 0.5072463768115942}`
- Soft slot F1 diagnostic: `{'dev': 0.7315387631291138, 'test': 0.7609315000619348}`
- Soft slot F1 primary metric: `False`
- Source count consistency: `{'bucketed_form_fill_cluster_count': 5, 'bucketed_form_fill_cluster_row_incidence_total': 49, 'bucketed_form_fill_residual_fields': 49, 'ok': True, 'source_form_fill_cluster_count': 5, 'source_form_fill_cluster_row_incidence_total': 49, 'source_form_fill_residual_fields': 49}`
- Recommended next step: `open_separate_policy_remediation_phase_after_review`

## Policy Sections

### Confirmation markers

- Source bucket: `missing_confirmation_marker`
- Policy statement: Future form-fill remediation should preserve explicit user confirmation wording in normalized_command when the source command asks to submit or confirm a filled form.
- Clusters: `1`
- cluster-row incidence total: `27`
- Residual fields: `27`
- Split counts: `{'dev': 11, 'test': 16}`
- Field paths: `['normalized_command']`
- Source family counts: `{'family-confirmation-dev-1': 1, 'family-confirmation-dev-2': 2, 'family-confirmation-dev-3': 2, 'family-confirmation-test-1': 2, 'family-confirmation-test-2': 2, 'family-confirmation-test-3': 3, 'family-form_fill-dev-1': 2, 'family-form_fill-dev-2': 1, 'family-form_fill-dev-3': 3, 'family-form_fill-test-1': 3, 'family-form_fill-test-2': 3, 'family-form_fill-test-3': 3}`
- Candidate next action: `propose_bounded_confirmation_marker_data_or_prompt_remediation_after_policy_review`
- Separate OpenSpec required: `True`

### Field specificity or alias drift

- Source bucket: `field_specificity_or_alias_drift`
- Policy statement: Future remediation should decide field-label canonicalization and alias boundaries before adding examples or changing prompt wording for slots.
- Clusters: `1`
- cluster-row incidence total: `16`
- Residual fields: `16`
- Split counts: `{'dev': 10, 'test': 6}`
- Field paths: `['slots']`
- Source family counts: `{'family-confirmation-dev-1': 2, 'family-confirmation-dev-2': 1, 'family-confirmation-dev-3': 3, 'family-confirmation-test-3': 2, 'family-form_fill-dev-2': 1, 'family-form_fill-dev-3': 3, 'family-form_fill-test-1': 1, 'family-form_fill-test-2': 2, 'family-form_fill-test-3': 1}`
- Candidate next action: `propose_bounded_field_specificity_or_alias_policy_remediation_after_policy_review`
- Separate OpenSpec required: `True`

### Route or intent boundary leakage

- Source bucket: `route_intent_leakage`
- Policy statement: Future remediation should keep form-fill route and intent boundaries separate from search, clarification, and safety-stop behavior unless a later OpenSpec phase changes that contract.
- Clusters: `3`
- cluster-row incidence total: `6`
- Residual fields: `6`
- Split counts: `{'dev': 3, 'test': 3}`
- Field paths: `['route', 'safety.reason', 'task_type']`
- Source family counts: `{'family-confirmation-dev-1': 3, 'family-form_fill-test-3': 3}`
- Candidate next action: `inspect_route_intent_boundary_before_any_remediation`
- Separate OpenSpec required: `True`

## Unsupported Changes

- `evaluator_relaxation`: strict contract_exact_match and strict slot_f1 remain authoritative
- `soft_metric_promotion`: slot_f1_soft remains diagnostic-only and is not promoted to a primary metric
- `data_mutation`: policy definition does not add, delete, rewrite, or regenerate dataset rows
- `training_run`: policy definition does not run SFT, DPO, GRPO, or any A100 job
- `prediction_repair`: policy definition does not repair, replace, normalize, or re-score predictions
- `prompt_change`: prompt or formatting changes require a separate approved OpenSpec phase
- `gold_policy_mutation`: gold contract policy changes require a separate approved OpenSpec phase

## Candidate Next Actions

- `propose_bounded_confirmation_marker_data_or_prompt_remediation_after_policy_review`
- `propose_bounded_field_specificity_or_alias_policy_remediation_after_policy_review`
- `inspect_route_intent_boundary_before_any_remediation`
