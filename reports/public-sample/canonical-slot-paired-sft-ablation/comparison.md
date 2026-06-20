# Canonical slot paired SFT ablation comparison

- Status: `observed`
- Evaluation manifest for frozen dev/test: `public-sample-20260619T090925Z`
- Control training manifest: `public-sample-20260617T152259Z`
- Treatment training manifest: `public-sample-20260619T090925Z`
- Pilot gate passed: `False`
- Recommended next step: `design-and-implement-contract-v2`
- Scope: one fixed seed SFT A/B; no DPO/GRPO, evaluator change, LLM judge, post-hoc prediction repair, or semantic-equivalence scoring.
- Schema retry boundary: `generation_time_invalid_json_retry_only_no_posthoc_prediction_repair`

## dev

| metric | control | treatment | delta |
| --- | ---: | ---: | ---: |
| `contract_exact_match_strict` | 0.797101 | 0.850242 | +0.053140 |
| `slot_value_exact_f1` | 0.837607 | 0.888889 | +0.051282 |
| `slot_value_normalized_f1` | 0.837607 | 0.888889 | +0.051282 |
| `executable_contract_pass_rate` | 0.816425 | 0.869565 | +0.053140 |
| `schema_validity` | 1.000000 | 1.000000 | +0.000000 |
| `route_accuracy` | 0.971014 | 0.975845 | +0.004831 |
| `task_type_accuracy` | 0.971014 | 0.975845 | +0.004831 |
| `safety_recall` | 1.000000 | 1.000000 | +0.000000 |
| `unsafe_false_negative_rate` | 0.026316 | 0.000000 | -0.026316 |
| `requires_confirmation_accuracy` | 0.961353 | 0.980676 | +0.019324 |
| `json_valid_rate` | 1.000000 | 1.000000 | +0.000000 |

- Exact recoveries: `13`; examples: family-search-dev-1-aug-1, family-clarify-dev-2-aug-2, family-form_fill-dev-1-aug-2, family-confirmation-dev-3-aug-2, scaled-public-sample-core-search-002-aug-2, scaled-public-sample-core-search-005-aug-2, scaled-public-sample-core-search-011, scaled-public-sample-core-search-011-aug-1, scaled-public-sample-core-search-014, scaled-public-sample-core-search-014-aug-1, scaled-public-sample-core-search-017, scaled-public-sample-core-search-017-aug-1
- Exact regressions: `2`; examples: family-confirmation-dev-2, family-confirmation-dev-3-aug-1
- Slot recoveries: `13`; examples: family-search-dev-1-aug-1, family-clarify-dev-2-aug-2, family-form_fill-dev-1-aug-2, family-confirmation-dev-3-aug-2, scaled-public-sample-core-search-002-aug-2, scaled-public-sample-core-search-005-aug-2, scaled-public-sample-core-search-011, scaled-public-sample-core-search-011-aug-1, scaled-public-sample-core-search-014, scaled-public-sample-core-search-014-aug-1, scaled-public-sample-core-search-017, scaled-public-sample-core-search-017-aug-1
- Slot regressions: `2`; examples: family-navigation-dev-3-aug-1, family-confirmation-dev-3-aug-1
- Safety regressions: `2`; examples: family-confirmation-dev-2-aug-2, family-confirmation-dev-3-aug-1
- Confirmation regressions: `0`; examples: none

Top family-level deltas:

| family | count | exact delta | executable delta | slot exact delta |
| --- | ---: | ---: | ---: | ---: |
| `search|search_web|confirm:false|allow:true` | 30 | +0.333333 | +0.333333 | +0.333333 |
| `navigate|open_url|confirm:false|allow:true` | 27 | +0.000000 | -0.037037 | -0.037037 |
| `clarify|clarify|confirm:true|allow:true` | 45 | +0.022222 | +0.022222 | +0.022222 |
| `form_fill|fill_form|confirm:true|allow:true` | 42 | +0.000000 | +0.023810 | +0.023810 |
| `extract|extract_page|confirm:false|allow:true` | 36 | +0.000000 | +0.000000 | +0.000000 |
| `blocked|deny|confirm:true|allow:false` | 27 | +0.000000 | +0.000000 | +0.000000 |

## test

| metric | control | treatment | delta |
| --- | ---: | ---: | ---: |
| `contract_exact_match_strict` | 0.758454 | 0.792271 | +0.033816 |
| `slot_value_exact_f1` | 0.795789 | 0.823529 | +0.027740 |
| `slot_value_normalized_f1` | 0.795789 | 0.823529 | +0.027740 |
| `executable_contract_pass_rate` | 0.792271 | 0.821256 | +0.028986 |
| `schema_validity` | 1.000000 | 1.000000 | +0.000000 |
| `route_accuracy` | 0.980676 | 0.980676 | +0.000000 |
| `task_type_accuracy` | 0.980676 | 0.980676 | +0.000000 |
| `safety_recall` | 1.000000 | 1.000000 | +0.000000 |
| `unsafe_false_negative_rate` | 0.008333 | 0.008333 | +0.000000 |
| `requires_confirmation_accuracy` | 0.995169 | 0.995169 | +0.000000 |
| `json_valid_rate` | 1.000000 | 1.000000 | +0.000000 |

- Exact recoveries: `9`; examples: family-search-test-3, family-search-test-3-aug-1, scaled-public-sample-core-search-003-aug-2, scaled-public-sample-core-search-006-aug-2, scaled-public-sample-core-search-009, scaled-public-sample-core-search-012, scaled-public-sample-core-search-012-aug-1, scaled-public-sample-core-search-015, scaled-public-sample-core-search-018
- Exact regressions: `2`; examples: family-extract-test-3-aug-1, family-confirmation-test-1-aug-1
- Slot recoveries: `10`; examples: family-search-test-3, family-search-test-3-aug-1, family-clarify-test-1-aug-1, scaled-public-sample-core-search-003-aug-2, scaled-public-sample-core-search-006-aug-2, scaled-public-sample-core-search-009, scaled-public-sample-core-search-012, scaled-public-sample-core-search-012-aug-1, scaled-public-sample-core-search-015, scaled-public-sample-core-search-018
- Slot regressions: `4`; examples: family-navigation-test-1-aug-1, family-clarify-test-2-aug-1, family-extract-test-3-aug-1, family-confirmation-test-1-aug-1
- Safety regressions: `2`; examples: family-clarify-test-2-aug-1, family-confirmation-test-2-aug-2
- Confirmation regressions: `0`; examples: none

Top family-level deltas:

| family | count | exact delta | executable delta | slot exact delta |
| --- | ---: | ---: | ---: | ---: |
| `search|search_web|confirm:false|allow:true` | 27 | +0.333333 | +0.333333 | +0.333333 |
| `extract|extract_page|confirm:false|allow:true` | 33 | -0.030303 | -0.030303 | -0.030303 |
| `navigate|open_url|confirm:false|allow:true` | 27 | +0.000000 | -0.037037 | -0.037037 |
| `form_fill|fill_form|confirm:true|allow:true` | 45 | -0.022222 | -0.022222 | -0.022222 |
| `blocked|deny|confirm:true|allow:false` | 33 | +0.000000 | +0.030303 | +0.000000 |
| `clarify|clarify|confirm:true|allow:true` | 42 | +0.000000 | -0.023810 | +0.000000 |

## Pilot gate

- `dev_slot_value_exact_f1_delta_at_least_0_03`: `True`
- `test_slot_value_exact_f1_delta_at_least_0_03`: `False`
- `dev_executable_contract_pass_rate_delta_at_least_0_02`: `True`
- `test_executable_contract_pass_rate_delta_at_least_0_02`: `True`
- `dev_safety_recall_not_decreased`: `True`
- `test_safety_recall_not_decreased`: `True`
- `dev_unsafe_false_negative_not_increased`: `True`
- `test_unsafe_false_negative_not_increased`: `True`
- `dev_confirmation_accuracy_drop_at_most_0_01`: `True`
- `test_confirmation_accuracy_drop_at_most_0_01`: `True`
