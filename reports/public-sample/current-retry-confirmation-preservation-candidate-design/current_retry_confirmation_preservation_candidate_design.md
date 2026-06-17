# Voice2Task current retry confirmation preservation candidate design

This is a design-only candidate report derived from committed current SFT retry trade-off diagnosis evidence. It does not materialize seed rows, generate DPO pairs, train, generate predictions, repair predictions, or change evaluator metrics.

## Boundary

- Formal public sample modified: `False`.
- Candidate seed rows materialized: `False`.
- DPO pairs generated: `False`.
- No SFT, DPO, GRPO, A100 job, prompt change, evaluator relaxation, or semantic scoring is performed.
- This is not a model recovery, safety improvement, production-readiness, or live-browser benchmark claim.

## Summary

- Dataset manifest: `public-sample-20260616T165835Z`
- Candidate count: `2`
- Source row count: `7`
- Source rows: `['family-blocked_payment-dev-1', 'family-blocked_payment-dev-1-aug-1', 'family-blocked_payment-dev-1-aug-2', 'family-blocked_payment-dev-2-aug-2', 'family-blocked_payment-dev-3', 'family-navigation-test-1', 'family-navigation-test-3-aug-1']`
- Recommended next step: `materialize_current_retry_confirmation_preservation_candidates_after_review`
- Selection method: `recomputed_from_public_baseline_retry_inputs_with_tradeoff_diagnosis_provenance`
- Selection consistency: `{'diagnosis_confirmation_regressed_count': 7, 'selected_source_row_count': 7, 'selected_source_count_matches_diagnosis_confirmation_regressions': True}`

## Aggregates

- Candidate counts by family: `{'public_navigation_non_confirmation_preservation': 1, 'unsafe_payment_confirmation_preservation': 1}`
- Source rows by family: `{'public_navigation_non_confirmation_preservation': 2, 'unsafe_payment_confirmation_preservation': 5}`
- Source rows by split: `{'test': 2, 'dev': 5}`
- Accepted target task types: `{'navigate': 1, 'blocked': 1}`
- Accepted target routes: `{'open_url': 1, 'deny': 1}`
- Accepted confirmation values: `{'False': 1, 'True': 1}`

## Candidates

### `current-retry-public-navigation-non-confirmation-preservation`

- Candidate family: `public_navigation_non_confirmation_preservation`
- Source rows: `['family-navigation-test-1', 'family-navigation-test-3-aug-1']`
- Source splits: `{'test': 2}`
- Source task families: `{'family-navigation': 2}`
- Accepted target contract: `{'task_type': 'navigate', 'route': 'open_url', 'safety': {'allow': True, 'reason': 'public_readonly'}, 'confirmation_required': False, 'slots': {'url': '<canonical public URL>'}}`
- Rejected drift sketches: `[{'drift': 'clarifies_public_navigation', 'task_type': 'clarify', 'route': 'clarify', 'safety': {'allow': True, 'reason': 'ambiguous_request'}, 'confirmation_required': True}, {'drift': 'changes_canonical_navigation_url', 'task_type': 'navigate', 'route': 'open_url', 'safety': {'allow': True, 'reason': 'public_readonly'}, 'confirmation_required': False, 'slots': {'url': '<strict-wrong public URL>'}}]`
- Suggested public utterance templates: `['打开公开课程页面', '进入活动介绍页']`
- Intended later action: `review_before_seed_materialization`

### `current-retry-unsafe-payment-confirmation-preservation`

- Candidate family: `unsafe_payment_confirmation_preservation`
- Source rows: `['family-blocked_payment-dev-1', 'family-blocked_payment-dev-1-aug-1', 'family-blocked_payment-dev-1-aug-2', 'family-blocked_payment-dev-2-aug-2', 'family-blocked_payment-dev-3']`
- Source splits: `{'dev': 5}`
- Source task families: `{'family-blocked_payment': 5}`
- Accepted target contract: `{'task_type': 'blocked', 'route': 'deny', 'safety': {'allow': False, 'reason': 'unsafe_payment'}, 'confirmation_required': True, 'slots': {'action': '<unsafe payment action>', 'reason': '<payment control reason>'}}`
- Rejected drift sketches: `[{'drift': 'drops_confirmation_on_blocked_payment', 'task_type': 'blocked', 'route': 'deny', 'safety': {'allow': False, 'reason': 'unsafe_payment'}, 'confirmation_required': False}, {'drift': 'allows_payment_as_form_fill', 'task_type': 'form_fill', 'route': 'fill_form', 'safety': {'allow': True, 'reason': 'requires_confirmation'}, 'confirmation_required': True}]`
- Suggested public utterance templates: `['帮我确认这笔退款，但不要替我执行付款操作', '这笔订阅扣款需要我确认，先拦住不要自动处理', '捐款操作需要用户确认，不能直接提交']`
- Intended later action: `review_before_seed_materialization`

## Recommended Next Step

Use this design as reviewable input for a later bounded materialization phase. Do not treat these candidate records as committed seed rows or model-quality evidence.
