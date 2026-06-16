# Voice2Task form-fill confirmation-marker coverage extension design

This is a design-only coverage extension. It proposes source-family-level confirmation-marker cases from committed public-safe artifacts; it does not materialize candidate rows, mutate datasets, run predictions, train, repair predictions, or relax evaluation.

## Boundary

- strict `contract_exact_match` and strict `slot_f1` remain authoritative.
- `slot_f1_soft` remains diagnostic-only.
- Proposed cases are design descriptors, not seed/SFT/DPO rows.
- This report makes no held-out recovery claim.
- Any materialization, data, prompt, evaluator, prediction, checkpoint, adapter, or training change requires a separate OpenSpec phase.

## Summary

- Source manifest id: `public-sample-20260616T022151Z`
- Source bucket: `missing_confirmation_marker`
- Source count consistency: `True`
- Source families: `12`
- Proposed cases: `12`
- Represented source-family incidence total: `27`
- Legacy confirmation candidate cases: `3`
- Legacy represented field labels: `3`
- Field labels derived from committed examples: `3`
- Field labels not derivable: `9`
- Design decision: `extend_confirmation_marker_coverage_with_source_family_cases`
- Recommended next step: `materialize_bounded_confirmation_marker_extension_candidates_in_later_phase`

## Proposed Candidate Cases

- `ff-confirm-marker-extension-family-confirmation-dev-1`: family `family-confirmation-dev-1`, incidences `1`, field `not derivable`, status `not_derivable_from_committed_coverage_policy_artifacts`
- `ff-confirm-marker-extension-family-confirmation-dev-2`: family `family-confirmation-dev-2`, incidences `2`, field `not derivable`, status `not_derivable_from_committed_coverage_policy_artifacts`
- `ff-confirm-marker-extension-family-confirmation-dev-3`: family `family-confirmation-dev-3`, incidences `2`, field `not derivable`, status `not_derivable_from_committed_coverage_policy_artifacts`
- `ff-confirm-marker-extension-family-confirmation-test-1`: family `family-confirmation-test-1`, incidences `2`, field `not derivable`, status `not_derivable_from_committed_coverage_policy_artifacts`
- `ff-confirm-marker-extension-family-confirmation-test-2`: family `family-confirmation-test-2`, incidences `2`, field `not derivable`, status `not_derivable_from_committed_coverage_policy_artifacts`
- `ff-confirm-marker-extension-family-confirmation-test-3`: family `family-confirmation-test-3`, incidences `3`, field `not derivable`, status `not_derivable_from_committed_coverage_policy_artifacts`
- `ff-confirm-marker-extension-family-form_fill-dev-1`: family `family-form_fill-dev-1`, incidences `2`, field `手机号`, status `derived_from_committed_coverage_examples`
- `ff-confirm-marker-extension-family-form_fill-dev-2`: family `family-form_fill-dev-2`, incidences `1`, field `收货地址`, status `derived_from_committed_coverage_examples`
- `ff-confirm-marker-extension-family-form_fill-dev-3`: family `family-form_fill-dev-3`, incidences `3`, field `发票抬头`, status `derived_from_committed_coverage_examples`
- `ff-confirm-marker-extension-family-form_fill-test-1`: family `family-form_fill-test-1`, incidences `3`, field `not derivable`, status `not_derivable_from_committed_coverage_policy_artifacts`
- `ff-confirm-marker-extension-family-form_fill-test-2`: family `family-form_fill-test-2`, incidences `3`, field `not derivable`, status `not_derivable_from_committed_coverage_policy_artifacts`
- `ff-confirm-marker-extension-family-form_fill-test-3`: family `family-form_fill-test-3`, incidences `3`, field `not derivable`, status `not_derivable_from_committed_coverage_policy_artifacts`

## Unsupported Changes

- `candidate_materialization`: extension design does not create rows
- `data_mutation`: extension design does not mutate public samples or corpora
- `prompt_change`: prompt changes require a separate OpenSpec phase
- `training_run`: training requires a separate A100 phase and fresh evaluation
- `evaluator_relaxation`: strict contract metrics remain authoritative
- `prediction_repair`: predictions are not repaired, replaced, normalized, or re-scored
- `held_out_recovery_claim`: candidate design is not held-out recovery evidence
