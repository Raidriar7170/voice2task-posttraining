# Voice2Task scaled residual remediation target selection

This report selects the first bounded remediation target from the scaled residual-cluster inspection. It is target-selection evidence only: not data materialization, not training, not a prediction rerun, not model recovery, and not evaluator relaxation.

## Boundary

- strict `contract_exact_match` remains primary.
- Strict `slot_f1` remains authoritative for slot scoring.
- `slot_f1_soft` remains diagnostic-only.
- No raw prediction stream is copied as the planning artifact.
- No A100 job, SFT, DPO, GRPO, new data, prompt change, gold rewrite, prediction repair, or metric change is performed.
- Blocked-payment residuals are deferred to a dedicated safety boundary phase, not treated as solved.

## Selected Target

- Source manifest id: `public-sample-20260617T152259Z`
- Selected target: `clarify`
- Selected task family: `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity`
- Selected field path: `slots`
- Residual rows: `78`
- Residual fields: `78`
- Source residual rows: `321`
- Source residual fields: `540`
- Ranked clusters: `29`
- Recommended next change: `design-scaled-clarify-slot-boundary-candidates`
- Recommended next step: `open_bounded_design-scaled-clarify-slot-boundary-candidates_before_data_training_prompt_or_metric_changes`

## Why This Target

- largest strict residual cluster in the scaled cluster inspection
- selected cluster is a non-safety slots boundary before higher-risk safety remediation
- clarify slots residuals point to ambiguous-request boundary design before data or training

## Selected Cluster

- Rank: `1`
- Rows by split: `{'dev': 42, 'test': 36}`
- Recommended action candidate: `route_intent_boundary_inspection_before_data_or_training`

## Deferred High-Ranked Targets

- rank `2` `blocked` / `slots` (51 rows): defer_to_dedicated_safety_boundary_phase
- rank `3` `search` / `slots` (51 rows): defer_to_later_label_canonicalization_phase
- rank `4` `form_fill` / `slots` (50 rows): defer_until_clarify_boundary_target_is_reviewed
- rank `5` `blocked` / `normalized_command` (47 rows): defer_to_dedicated_safety_boundary_phase
- rank `6` `navigate` / `slots` (41 rows): defer_to_later_label_canonicalization_phase

## Ranked Clusters

- rank `1` `clarify` / `slots` / `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity`: 78 rows, 78 fields
- rank `2` `blocked` / `slots` / `blocked|deny|unsafe_payment|confirm:true|slots:action,reason`: 51 rows, 51 fields
- rank `3` `search` / `slots` / `search|search_web|public_readonly|confirm:false|slots:query`: 51 rows, 51 fields
- rank `4` `form_fill` / `slots` / `form_fill|fill_form|requires_confirmation|confirm:true|slots:field`: 50 rows, 50 fields
- rank `5` `blocked` / `normalized_command` / `blocked|deny|unsafe_payment|confirm:true|slots:action,reason`: 47 rows, 47 fields
- rank `6` `navigate` / `slots` / `navigate|open_url|public_readonly|confirm:false|slots:url`: 41 rows, 41 fields
- rank `7` `search` / `normalized_command` / `search|search_web|public_readonly|confirm:false|slots:query`: 41 rows, 41 fields
- rank `8` `navigate` / `normalized_command` / `navigate|open_url|public_readonly|confirm:false|slots:url`: 40 rows, 40 fields
- rank `9` `extract` / `slots` / `extract|extract_page|public_readonly|confirm:false|slots:target`: 31 rows, 31 fields
- rank `10` `extract` / `normalized_command` / `extract|extract_page|public_readonly|confirm:false|slots:target`: 31 rows, 31 fields

## Representative Sanitized Examples

- `dev / seed-clarify-ambiguous / slots`: gold object with keys: ambiguity; prediction object with keys: ambiguity
- `dev / seed-clarify-ambiguous-aug-1 / slots`: gold object with keys: ambiguity; prediction object with keys: ambiguity
- `dev / seed-clarify-ambiguous-aug-2 / slots`: gold object with keys: ambiguity; prediction object with keys: ambiguity
- `dev / family-clarify-dev-2 / slots`: gold object with keys: ambiguity; prediction object with keys: ambiguity
- `dev / family-clarify-dev-2-aug-1 / slots`: gold object with keys: ambiguity; prediction object with keys: ambiguity

## Recommended Next Step

Open a separate bounded OpenSpec phase for clarify slot-boundary candidate design. That phase may design public-safe cases or policy guidance, but this selection report does not authorize materialization, training, prompts, predictions, or evaluator changes.
