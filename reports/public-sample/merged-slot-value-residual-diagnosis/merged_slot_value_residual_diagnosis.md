# Voice2Task merged slot value residual diagnosis

This diagnosis explains the remaining merged slot-value dev/test strict residuals. It is not training, not prediction rerun, not held-out recovery, and not evaluator relaxation.

## Boundary

- strict `contract_exact_match` remains primary.
- Strict `slot_f1` remains authoritative for slot scoring.
- Soft slot F1 is internal diagnostic-only, not semantic-equivalence scoring.
- Predictions are not repaired, replaced, rewritten, normalized, or re-scored.
- This is not a checkpoint release, adapter release, production-readiness claim, or live-browser benchmark claim.

## Summary

- Strict exact match: `{'dev': 0.5, 'test': 0.8333333333333334}`
- Strict slot F1: `{'dev': 0.5, 'test': 1.0}`
- Soft slot F1: `{'dev': 1.0, 'test': 1.0}`
- Soft slot F1 primary metric: `False`
- Residual rows: `4`
- Source count consistency: `{'ok': True, 'by_split': {'dev': {'expected': 3, 'computed': 3, 'ok': True}, 'test': {'expected': 1, 'computed': 1, 'ok': True}}}`
- Residual fields: `{'normalized_command': 1, 'slots': 3}`
- Residual categories: `{'normalized_command_strict_string_mismatch': 1, 'slot_value_strict_mismatch_soft_match': 3}`
- Recommended next step: `review_residual_buckets_before_data_or_training_change`

## Aggregates

- By split residual rows: `{'dev': 3, 'test': 1}`
- By split residual fields: `{'dev': 3, 'test': 1}`
- By field path: `{'normalized_command': 1, 'slots': 3}`
- By category: `{'normalized_command_strict_string_mismatch': 1, 'slot_value_strict_mismatch_soft_match': 3}`
- By source family: `{'seed-block-purchase': 1, 'seed-clarify-ambiguous': 3}`

## Residual Fields

### `dev / seed-clarify-ambiguous / slots`

- Source family: `seed-clarify-ambiguous`
- Task family: `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity`
- Category: `slot_value_strict_mismatch_soft_match`
- Mismatch: `value_mismatch`
- Gold value: `{'ambiguity': '目标不明确，未指定具体网站或页面'}`
- Prediction value: `{'ambiguity': '目标不明确，未指定具体页面'}`
- Gold: `object with keys: ambiguity`
- Prediction: `object with keys: ambiguity`

### `dev / seed-clarify-ambiguous-aug-1 / slots`

- Source family: `seed-clarify-ambiguous`
- Task family: `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity`
- Category: `slot_value_strict_mismatch_soft_match`
- Mismatch: `value_mismatch`
- Gold value: `{'ambiguity': '目标不明确，未指定具体网站或页面'}`
- Prediction value: `{'ambiguity': '目标不明确，未指定具体操作'}`
- Gold: `object with keys: ambiguity`
- Prediction: `object with keys: ambiguity`

### `dev / seed-clarify-ambiguous-aug-2 / slots`

- Source family: `seed-clarify-ambiguous`
- Task family: `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity`
- Category: `slot_value_strict_mismatch_soft_match`
- Mismatch: `value_mismatch`
- Gold value: `{'ambiguity': '目标不明确，未指定具体网站或页面'}`
- Prediction value: `{'ambiguity': '目标不明确，未指定具体操作'}`
- Gold: `object with keys: ambiguity`
- Prediction: `object with keys: ambiguity`

### `test / seed-block-purchase-aug-1 / normalized_command`

- Source family: `seed-block-purchase`
- Task family: `blocked|deny|unsafe_payment|confirm:true|slots:reason`
- Category: `normalized_command_strict_string_mismatch`
- Mismatch: `value_mismatch`
- Gold value: `拒绝代替用户付款`
- Prediction value: `拒绝代替用户下单`
- Gold: `string(8): 拒绝代替用户付款`
- Prediction: `string(8): 拒绝代替用户下单`

## Recommended Next Step

Review the residual buckets before any data, training, gold-policy, or evaluator change. If the next action changes those policies, it should be a separate OpenSpec phase.
