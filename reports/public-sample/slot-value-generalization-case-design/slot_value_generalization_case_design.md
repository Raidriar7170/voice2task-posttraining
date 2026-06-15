# Voice2Task slot value generalization case design

This is design-only evidence for a later slot value generalization phase. It is not materialized into seed_traces.jsonl, not broad scaling, not DPO, not training evidence, and not a model recovery claim.

## Boundary

- Candidate cases are not public sample rows yet.
- No dataset was rebuilt and no training or prediction run was launched.
- strict `contract_exact_match` remains primary.
- Soft slot F1 and semantic equivalence remain diagnostic-only.
- Predictions are not repaired, replaced, rewritten, normalized, or re-scored.

## Summary

- Candidate groups: `4`
- Covered residual buckets: `{'normalized_command_paraphrase_drift': 4, 'slot_value_canonical_phrase_drift': 3, 'slot_value_language_variant': 3}`
- Public sample modified: `False`
- New data generated: `False`
- Recommended next step: `materialize_reviewed_cases_in_later_openspec_change`

## Candidate Case Groups

### `blocked-payment-normalized-command-paraphrase`

- Source family: `seed-block-purchase`
- Residual bucket: `normalized_command_paraphrase_drift`
- Affected fields: `['normalized_command']`
- Residual rows: `['seed-block-purchase', 'seed-block-purchase-aug-1']`
- Canonical gold values: `[{'field_path': 'normalized_command', 'value': '拒绝代替用户付款'}]`
- Observed wrong values: `[{'field_path': 'normalized_command', 'value': '拒绝代替用户购买和付款'}, {'field_path': 'normalized_command', 'value': '拒绝代替用户下单'}]`
- Purpose: teach blocked-payment canonical command wording without accepting action paraphrase drift
- Recommended split role: `candidate_train_or_validation_design_only`
- Requires user review before materialization: `True`

### `clarify-ambiguous-slot-value-canonical-phrase`

- Source family: `seed-clarify-ambiguous`
- Residual bucket: `slot_value_canonical_phrase_drift`
- Affected fields: `['slots']`
- Residual rows: `['seed-clarify-ambiguous', 'seed-clarify-ambiguous-aug-1', 'seed-clarify-ambiguous-aug-2']`
- Canonical gold values: `[{'field_path': 'slots', 'value': {'ambiguity': '目标不明确，未指定具体网站或页面'}}]`
- Observed wrong values: `[{'field_path': 'slots', 'value': {'ambiguity': '目标不明确，未指定具体页面'}}, {'field_path': 'slots', 'value': {'ambiguity': '目标不明确，未指定具体操作'}}, {'field_path': 'slots', 'value': {'ambiguity': '目标不明确，无法确定具体操作'}}]`
- Purpose: teach the canonical ambiguity scope phrase without evaluator-side normalization
- Recommended split role: `candidate_train_or_validation_design_only`
- Requires user review before materialization: `True`

### `form-email-slot-value-language-variant`

- Source family: `seed-form-email`
- Residual bucket: `slot_value_language_variant`
- Affected fields: `['slots']`
- Residual rows: `['seed-form-email', 'seed-form-email-aug-1', 'seed-form-email-aug-2']`
- Canonical gold values: `[{'field_path': 'slots', 'value': {'field': '邮箱'}}]`
- Observed wrong values: `[{'field_path': 'slots', 'value': {'field': 'email'}}]`
- Purpose: teach Chinese canonical slot values instead of English aliases
- Recommended split role: `candidate_train_or_validation_design_only`
- Requires user review before materialization: `True`

### `navigate-open-url-normalized-command-paraphrase`

- Source family: `seed-open-example`
- Residual bucket: `normalized_command_paraphrase_drift`
- Affected fields: `['normalized_command']`
- Residual rows: `['seed-open-example', 'seed-open-example-aug-2']`
- Canonical gold values: `[{'field_path': 'normalized_command', 'value': '打开示例网站'}]`
- Observed wrong values: `[{'field_path': 'normalized_command', 'value': '打开示例页面'}, {'field_path': 'normalized_command', 'value': '访问Example网站'}]`
- Purpose: teach open-url canonical command wording without accepting paraphrase drift
- Recommended split role: `candidate_train_or_validation_design_only`
- Requires user review before materialization: `True`

## Recommended Next Step

Open a later bounded OpenSpec change to materialize reviewed cases into public-safe seed traces or a separate candidate dataset. That later change should decide split policy explicitly and still avoid broad scaling, DPO, evaluator relaxation, or release claims unless separately approved.
