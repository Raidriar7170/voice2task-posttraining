# Residual Diagnosis: dev

- Manifest: `public-sample-20260617T152259Z`
- Scope: strict exact mismatches only; no prediction repair, data merge, model training, or metric relaxation.

## Totals

- Total: `207`
- Strict pass: `51`
- Strict fail: `156`

## Family Counts

- `allowed_actions`: `0` (0.0000)
- `confirmation`: `5` (0.0242)
- `extra_field`: `0` (0.0000)
- `extra_slot`: `8` (0.0386)
- `invalid_output`: `0` (0.0000)
- `missing_field`: `0` (0.0000)
- `missing_slot`: `8` (0.0386)
- `normalized_command`: `91` (0.4396)
- `refusal_or_clarify`: `6` (0.0290)
- `risk_level`: `6` (0.0290)
- `route`: `8` (0.0386)
- `slot_key`: `0` (0.0000)
- `slot_value`: `160` (0.7729)
- `success_criteria`: `0` (0.0000)
- `task_type`: `8` (0.0386)

## Top Field Paths

- `normalized_command`: `91`
- `slots.ambiguity`: `45`
- `slots.field`: `28`
- `slots.query`: `27`
- `slots.action`: `21`
- `slots.reason`: `20`
- `slots.url`: `19`
- `slots.target`: `16`
- `task_type`: `8`
- `route`: `8`

## Sanitized Examples

### `route`

- `seed-open-example-aug-1` `route`: gold string(8): open_url; prediction string(7): clarify
- `family-clarify-dev-3` `route`: gold string(7): clarify; prediction string(9): fill_form
- `family-clarify-dev-3-aug-1` `route`: gold string(7): clarify; prediction string(9): fill_form

### `task_type`

- `seed-open-example-aug-1` `task_type`: gold string(8): navigate; prediction string(7): clarify
- `family-clarify-dev-3` `task_type`: gold string(7): clarify; prediction string(9): form_fill
- `family-clarify-dev-3-aug-1` `task_type`: gold string(7): clarify; prediction string(9): form_fill

### `normalized_command`

- `seed-open-example-aug-1` `normalized_command`: gold string(6): 打开示例网站; prediction string(6): 请求澄清目标
- `family-search-dev-1-aug-1` `normalized_command`: gold string(11): 搜索成都博物馆开放时间; prediction string(11): 搜索成都博物馆开门时间
- `family-search-dev-2` `normalized_command`: gold string(10): 搜索南京今天空气质量; prediction string(10): 搜索南京今日空气质量

### `slot_value`

- `seed-clarify-ambiguous` `slots.ambiguity`: gold string(16): 目标不明确，未指定具体网站或页面; prediction string(13): 目标不明确，未指定具体页面
- `seed-clarify-ambiguous-aug-1` `slots.ambiguity`: gold string(16): 目标不明确，未指定具体网站或页面; prediction string(13): 目标不明确，未指定具体页面
- `seed-clarify-ambiguous-aug-2` `slots.ambiguity`: gold string(16): 目标不明确，未指定具体网站或页面; prediction string(13): 目标不明确，未指定具体页面

### `missing_slot`

- `seed-open-example-aug-1` `slots.url`: gold string(19): https://example.com; prediction missing
- `family-clarify-dev-3` `slots.ambiguity`: gold string(13): 目标不明确，未指定具体表单; prediction missing
- `family-clarify-dev-3-aug-1` `slots.ambiguity`: gold string(13): 目标不明确，未指定具体表单; prediction missing

### `extra_slot`

- `seed-open-example-aug-1` `slots.ambiguity`: gold missing; prediction string(13): 目标不明确，未指定具体网站
- `family-clarify-dev-3` `slots.field`: gold missing; prediction string(2): 表格
- `family-clarify-dev-3-aug-1` `slots.field`: gold missing; prediction string(4): 表格信息

### `risk_level`

- `seed-open-example-aug-1` `safety.reason`: gold string(15): public_readonly; prediction string(17): ambiguous_request
- `family-clarify-dev-3` `safety.reason`: gold string(17): ambiguous_request; prediction string(21): requires_confirmation
- `family-clarify-dev-3-aug-1` `safety.reason`: gold string(17): ambiguous_request; prediction string(21): requires_confirmation

### `confirmation`

- `seed-open-example-aug-1` `confirmation_required`: gold bool: False; prediction bool: True
- `family-blocked_payment-dev-1` `confirmation_required`: gold bool: True; prediction bool: False
- `family-blocked_payment-dev-1-aug-1` `confirmation_required`: gold bool: True; prediction bool: False

### `refusal_or_clarify`

- `seed-open-example-aug-1` `task_type.route`: gold string(17): navigate/open_url; prediction string(15): clarify/clarify
- `family-clarify-dev-3` `task_type.route`: gold string(15): clarify/clarify; prediction string(19): form_fill/fill_form
- `family-clarify-dev-3-aug-1` `task_type.route`: gold string(15): clarify/clarify; prediction string(19): form_fill/fill_form


## Recommendations

- Use these residual counts to choose a later bounded remediation phase; do not treat them as model improvement.
- Prioritize slot-key/schema-family review before adding training runs.
- Review deterministic canonicalization candidates separately from strict evaluator metrics.
- Keep safety and confirmation residuals in a dedicated fail-closed review boundary.
