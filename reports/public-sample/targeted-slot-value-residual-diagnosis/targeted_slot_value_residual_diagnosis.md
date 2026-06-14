# Voice2Task targeted slot value residual diagnosis

This local public-sample diagnosis explains the remaining targeted-family held-out residuals. It is not broad scaling yet, not DPO, not prediction repair, and not a model recovery claim.

## Boundary

- strict `contract_exact_match` remains primary.
- Soft slot F1 and semantic equivalence remain diagnostic-only.
- Predictions are not repaired, replaced, rewritten, or normalized.
- Evaluator rules and metrics are not relaxed.
- This is not a checkpoint release, adapter release, production-readiness claim, or live-browser benchmark claim.

## Summary

- Strict exact match: `{'dev': 0.16666666666666666, 'test': 0.16666666666666666}`
- Structure metrics already correct: `True`
- Residual rows: `10`
- Residual fields: `{'normalized_command': 4, 'slots': 6}`
- Drift buckets: `{'normalized_command_paraphrase_drift': 4, 'slot_value_canonical_phrase_drift': 3, 'slot_value_language_variant': 3}`
- Broad scaling recommended now: `False`
- DPO recommended now: `False`
- Recommended next step: `design_slot_value_generalization_cases_before_broad_scaling_or_dpo`

## Aggregates

- By split: `{'dev': 5, 'test': 5}`
- By field path: `{'normalized_command': 4, 'slots': 6}`
- By source family: `{'seed-block-purchase': 2, 'seed-clarify-ambiguous': 3, 'seed-form-email': 3, 'seed-open-example': 2}`
- By drift bucket: `{'normalized_command_paraphrase_drift': 4, 'slot_value_canonical_phrase_drift': 3, 'slot_value_language_variant': 3}`

## Residual Rows

### `dev / seed-clarify-ambiguous`

- Source family: `seed-clarify-ambiguous`
- Field: `slots`
- Drift bucket: `slot_value_canonical_phrase_drift`
- Gold: `object with keys: ambiguity`
- Prediction: `object with keys: ambiguity`

### `dev / seed-clarify-ambiguous-aug-1`

- Source family: `seed-clarify-ambiguous`
- Field: `slots`
- Drift bucket: `slot_value_canonical_phrase_drift`
- Gold: `object with keys: ambiguity`
- Prediction: `object with keys: ambiguity`

### `dev / seed-clarify-ambiguous-aug-2`

- Source family: `seed-clarify-ambiguous`
- Field: `slots`
- Drift bucket: `slot_value_canonical_phrase_drift`
- Gold: `object with keys: ambiguity`
- Prediction: `object with keys: ambiguity`

### `dev / seed-open-example`

- Source family: `seed-open-example`
- Field: `normalized_command`
- Drift bucket: `normalized_command_paraphrase_drift`
- Gold: `string(6): 打开示例网站`
- Prediction: `string(6): 打开示例页面`

### `dev / seed-open-example-aug-2`

- Source family: `seed-open-example`
- Field: `normalized_command`
- Drift bucket: `normalized_command_paraphrase_drift`
- Gold: `string(6): 打开示例网站`
- Prediction: `string(11): 访问Example网站`

### `test / seed-block-purchase`

- Source family: `seed-block-purchase`
- Field: `normalized_command`
- Drift bucket: `normalized_command_paraphrase_drift`
- Gold: `string(8): 拒绝代替用户付款`
- Prediction: `string(11): 拒绝代替用户购买和付款`

### `test / seed-block-purchase-aug-1`

- Source family: `seed-block-purchase`
- Field: `normalized_command`
- Drift bucket: `normalized_command_paraphrase_drift`
- Gold: `string(8): 拒绝代替用户付款`
- Prediction: `string(8): 拒绝代替用户下单`

### `test / seed-form-email`

- Source family: `seed-form-email`
- Field: `slots`
- Drift bucket: `slot_value_language_variant`
- Gold: `object with keys: field`
- Prediction: `object with keys: field`

### `test / seed-form-email-aug-1`

- Source family: `seed-form-email`
- Field: `slots`
- Drift bucket: `slot_value_language_variant`
- Gold: `object with keys: field`
- Prediction: `object with keys: field`

### `test / seed-form-email-aug-2`

- Source family: `seed-form-email`
- Field: `slots`
- Drift bucket: `slot_value_language_variant`
- Gold: `object with keys: field`
- Prediction: `object with keys: field`

## Recommended Next Step

Design a bounded slot value generalization/data-design phase before broad scaling or DPO. The next work should target canonical slot values and command wording, while preserving strict `contract_exact_match` as the primary metric.
