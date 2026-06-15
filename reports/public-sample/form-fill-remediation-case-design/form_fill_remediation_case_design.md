# Voice2Task form-fill remediation case design

This is design-only evidence for a later `form_fill` remediation phase. It does not materialize seed rows, modify public sample splits, change held-out gold labels, launch training, rerun predictions, or relax evaluator metrics.

## Boundary

- strict `contract_exact_match` remains primary.
- Strict `slot_f1` remains authoritative for slot scoring.
- `slot_f1_soft` remains diagnostic-only.
- Candidate cases require user review before materialization.
- Any future dataset, SFT, DPO, prediction, or A100 phase needs separate confirmation.

## Summary

- Target: `form_fill`
- Source residual rows: `29`
- Source residual fields: `49`
- Case groups: `3`
- Candidate cases: `9`
- Covered bucket field counts: `{'clarify_boundary_confusion': 8, 'confirmation_marker_missing_or_reordered': 23, 'field_name_specificity_drift': 18}`
- Public sample modified: `False`
- New data generated: `False`
- Recommended next step: `review_then_materialize_independent_candidate_dataset_in_later_change`

## Policy Guidance

### `form-fill-clarify-boundary-policy`

- Source bucket: `clarify_boundary_confusion`
- Guidance: If the user specifies a concrete form field and asks the assistant to fill or confirm it, route to `form_fill` even when the value itself is absent; use `clarify` only when the target field/action is ambiguous.
- Rationale: A small but high-impact bucket turns concrete field-fill requests into `clarify`, changing task type, route, safety reason, and slot shape.

### `form-fill-confirmation-marker-policy`

- Source bucket: `confirmation_marker_missing_or_reordered`
- Guidance: When the user explicitly asks to confirm after filling a form field, preserve that confirmation intent in `normalized_command`, set `confirmation_required=true`, and keep `safety.reason=requires_confirmation`.
- Rationale: The largest residual bucket drops or reorders the explicit `并确认` marker even when the contract otherwise stays in the form-fill family.

### `form-fill-field-specificity-policy`

- Source bucket: `field_name_specificity_drift`
- Guidance: For `form_fill` slots, preserve the most specific field name from the request; do not collapse domain-specific fields such as 收货地址, 发票抬头, or 预约时间 into generic aliases.
- Rationale: The second-largest bucket keeps the slot shape but loses specificity, for example 收货地址 to 地址 or 发票抬头 to 抬头.

## Candidate Case Groups

### `form-fill-clarify-boundary-protection`

- Source bucket: `clarify_boundary_confusion`
- Source bucket rows: `2`
- Source bucket fields: `8`
- Source field paths: `{'route': 2, 'safety.reason': 2, 'slots': 2, 'task_type': 2}`
- Purpose: A small but high-impact bucket turns concrete field-fill requests into `clarify`, changing task type, route, safety reason, and slot shape.
- Recommended split role: `candidate_dataset_design_only`
- Requires user review before materialization: `True`

Candidate cases:
- `ff-boundary-appointment-time`: 填写预约时间并确认 -> `填写预约时间并确认`, slots `{'field': '预约时间'}`
- `ff-boundary-delivery-info`: 确认前填写配送信息 -> `填写配送信息并确认`, slots `{'field': '配送信息'}`
- `ff-boundary-contact-phone`: 填联系电话，提交前确认 -> `填写联系电话并确认`, slots `{'field': '联系电话'}`

### `form-fill-confirmation-marker-preservation`

- Source bucket: `confirmation_marker_missing_or_reordered`
- Source bucket rows: `23`
- Source bucket fields: `23`
- Source field paths: `{'normalized_command': 23}`
- Purpose: The largest residual bucket drops or reorders the explicit `并确认` marker even when the contract otherwise stays in the form-fill family.
- Recommended split role: `candidate_dataset_design_only`
- Requires user review before materialization: `True`

Candidate cases:
- `ff-confirm-phone`: 填写手机号并确认 -> `填写手机号并确认`, slots `{'field': '手机号'}`
- `ff-confirm-shipping-address`: 填写收货地址并确认 -> `填写收货地址并确认`, slots `{'field': '收货地址'}`
- `ff-confirm-invoice-title`: 填写发票抬头并确认 -> `填写发票抬头并确认`, slots `{'field': '发票抬头'}`

### `form-fill-field-specificity-preservation`

- Source bucket: `field_name_specificity_drift`
- Source bucket rows: `16`
- Source bucket fields: `18`
- Source field paths: `{'normalized_command': 4, 'slots': 14}`
- Purpose: The second-largest bucket keeps the slot shape but loses specificity, for example 收货地址 to 地址 or 发票抬头 to 抬头.
- Recommended split role: `candidate_dataset_design_only`
- Requires user review before materialization: `True`

Candidate cases:
- `ff-field-shipping-address`: 填写收货地址 -> `填写收货地址`, slots `{'field': '收货地址'}`
- `ff-field-invoice-title`: 填写发票抬头 -> `填写发票抬头`, slots `{'field': '发票抬头'}`
- `ff-field-appointment-time`: 填写预约时间 -> `填写预约时间`, slots `{'field': '预约时间'}`

## Recommended Next Step

Review these case groups. If accepted, open a later bounded OpenSpec change to materialize the reviewed cases into an independent candidate dataset. Do not merge them into active held-out splits or start training from this design artifact alone.
