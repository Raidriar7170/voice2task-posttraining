# Public-readonly search contract policy

This is local prompt/policy hardening only. It links the prior row-level mismatch diagnosis to model-visible contract-field guidance without running A100, training, prediction rerun, schema repair, decoder repair, prediction repair, semantic-equivalence scoring, slot normalization, or evaluator metric changes.

## Boundary

- No A100 execution was performed in this phase.
- No training or prediction rerun was performed.
- No decoder repair, schema repair, prediction repair, prediction re-score, slot normalization, or evaluator metric change was performed.
- This is not model-quality improvement, held-out generalization, production readiness, checkpoint release, adapter release, or live-browser benchmark evidence.

## Source Prior Phase

- `reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis`

## Source Failure Families

- `schema_invalid_task_type_enum`: `1`
- `schema_missing_confirmation_required`: `1`
- `schema_valid_task_route_safety_slot_mismatch`: `1`

## Prompt Policy

- public-readonly search contract policy: task_type="search"; route="search_web"; safety.allow=true; safety.reason="public_readonly"; confirmation_required=false；slots.query=简洁查询词；task_type 不能复用 route enum 值，search_web 不是 task_type。

## Prompt Constraint Flags

- `public_readonly_search_policy_visible`: `True`
- `public_readonly_safety_reason_visible`: `True`
- `search_query_slot_guidance_visible`: `True`
- `task_type_not_route_enum_visible`: `True`

## Source Artifacts

- `row_mismatch_diagnosis`: `reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis/row_mismatch_diagnosis.json`
- `source_manifest`: `reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis/manifest.json`
- `source_report`: `reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis/row_mismatch_diagnosis.md`
