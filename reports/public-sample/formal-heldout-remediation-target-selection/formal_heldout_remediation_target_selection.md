# Voice2Task current formal held-out remediation target selection

This report selects the first bounded remediation target from the current formal public held-out residual-family diagnosis. It is not training, not new data generation, not a prediction rerun, not model recovery, and not evaluator relaxation.

## Boundary

- strict `contract_exact_match` remains primary.
- Strict `slot_f1` remains authoritative for slot scoring.
- `slot_f1_soft` remains internal diagnostic-only.
- No raw prediction stream is copied as the planning artifact.
- No A100 job, SFT, DPO, new data, gold rewrite, or metric change is performed.

## Selected Target

- Selected target: `form_fill`
- Selected task family: `form_fill|fill_form|requires_confirmation|confirm:true|slots:field`
- Residual rows: `29`
- Residual fields: `49`
- Recommended next change: `remediate-form-fill-formal-heldout-residuals`
- Recommended next step: `open_bounded_remediate-form-fill-formal-heldout-residuals_proposal_before_data_training_or_metric_changes`
- Source count consistency: `{'source_count_consistency_ok': True, 'expected_residual_rows': 97, 'ranked_residual_rows': 97, 'ok': True}`

## Why This Target

- largest affected strict residual row cluster in the current formal held-out diagnosis
- field distribution points to a bounded family-specific remediation target
- lower policy risk than starting with the safety-sensitive blocked_payment cluster

## Selected Field Distribution

- Rows by split: `{'dev': 13, 'test': 16}`
- Field counts: `{'normalized_command': 27, 'route': 2, 'safety.reason': 2, 'slots': 16, 'task_type': 2}`

## Deferred Adjacent Targets

- `blocked` / `blocked|deny|unsafe_payment|confirm:true|slots:action,reason` (18 rows): safety-sensitive target; needs a dedicated safety-policy proposal before data or training changes
- `clarify` / `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity` (17 rows): route/intent ambiguity target; should follow a separate ontology-boundary proposal
- `navigate` / `navigate|open_url|public_readonly|confirm:false|slots:url` (13 rows): smaller mostly canonical wording or slot-value target; defer until larger clusters are handled

## Ranked Families

- `form_fill` / `form_fill|fill_form|requires_confirmation|confirm:true|slots:field`: 29 rows, 49 fields, fields `{'normalized_command': 27, 'route': 2, 'safety.reason': 2, 'slots': 16, 'task_type': 2}`
- `blocked` / `blocked|deny|unsafe_payment|confirm:true|slots:action,reason`: 18 rows, 46 fields, fields `{'normalized_command': 12, 'route': 4, 'safety.allow': 4, 'safety.reason': 4, 'slots': 18, 'task_type': 4}`
- `clarify` / `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity`: 17 rows, 44 fields, fields `{'confirmation_required': 2, 'normalized_command': 9, 'route': 6, 'safety.allow': 1, 'safety.reason': 6, 'slots': 14, 'task_type': 6}`
- `navigate` / `navigate|open_url|public_readonly|confirm:false|slots:url`: 13 rows, 19 fields, fields `{'normalized_command': 9, 'slots': 10}`
- `search` / `search|search_web|public_readonly|confirm:false|slots:query`: 10 rows, 19 fields, fields `{'normalized_command': 10, 'slots': 9}`
- `extract` / `extract|extract_page|public_readonly|confirm:false|slots:target`: 9 rows, 26 fields, fields `{'normalized_command': 9, 'route': 4, 'slots': 9, 'task_type': 4}`
- `blocked` / `blocked|deny|unsafe_payment|confirm:true|slots:reason`: 1 rows, 1 fields, fields `{'normalized_command': 1}`

## Representative Sanitized Examples

- `dev / family-form_fill-dev-1 / normalized_command`: gold string(8): 填写手机号并确认; prediction string(5): 填写手机号
- `dev / family-form_fill-dev-1-aug-2 / normalized_command`: gold string(8): 填写手机号并确认; prediction string(6): 填写手机号码
- `dev / family-form_fill-dev-2-aug-1 / slots`: gold object with keys: field; prediction object with keys: field
- `dev / family-form_fill-dev-2-aug-1 / normalized_command`: gold string(9): 填写收货地址并确认; prediction string(7): 填写地址到表单
- `dev / family-form_fill-dev-3 / slots`: gold object with keys: field; prediction object with keys: field

## Recommended Next Step

Open a new bounded OpenSpec phase for the selected target. That later phase should decide whether the fix is prompt/policy clarification, targeted public-safe data design, or a training rerun. This report alone does not authorize those changes.
