# Public-readonly output-boundary retry policy

This is local prompt/retry hardening only. It links the prior A100 public-readonly train-split failure to current prompt and retry constraints without running A100, training, prediction rerun, schema repair, decoder repair, prediction repair, semantic-equivalence scoring, slot normalization, or evaluator metric changes.

## Boundary

- No A100 execution was performed in this phase.
- No training or prediction rerun was performed.
- No parser, evaluator, metric, schema coercion, prediction repair, prediction re-score, or slot normalization change was performed.
- This is not model recovery evidence, model-quality improvement evidence, held-out generalization, production readiness, checkpoint release, adapter release, or live-browser benchmark evidence.

## Source Prior Phase

- `reports/public-sample/a100-public-readonly-search-policy-train-split-rerun`

## Prior A100 Failure Pattern

- Strict final JSON-valid rate: `0.0`
- Strict final contract exact match: `0.0`
- Raw `task_type=search_web` route-alias rows: `3/3`
- Strict retry parser rejected JSON fragment/prose wrapper rows: `3/3`
- Raw public-readonly field bundle visible: `3/3`

## Prompt Constraint Flags

- `single_root_json_object_visible`: `True`
- `no_premature_root_close_visible`: `True`
- `public_readonly_task_type_search_not_search_web_visible`: `True`
- `public_readonly_search_policy_visible`: `True`
- `task_type_not_route_enum_visible`: `True`
- `whole_object_boundary_visible`: `True`

## Retry Prompt Constraint Flags

- `minified_json_only_visible`: `True`
- `single_root_json_object_visible`: `True`
- `no_premature_root_close_visible`: `True`
- `task_type_search_not_search_web_visible`: `True`
- `no_markdown_prose_visible`: `True`
- `first_last_brace_visible`: `True`

## Source Artifacts

- `public_readonly_search_policy_diagnosis`: `reports/public-sample/a100-public-readonly-search-policy-train-split-rerun/public_readonly_search_policy_diagnosis.json`
- `schema_guard_summary`: `reports/public-sample/a100-public-readonly-search-policy-train-split-rerun/schema_guard_summary.json`
- `source_manifest`: `reports/public-sample/a100-public-readonly-search-policy-train-split-rerun/manifest.json`
- `source_report`: `reports/public-sample/a100-public-readonly-search-policy-train-split-rerun/public_readonly_search_policy_diagnosis.md`
