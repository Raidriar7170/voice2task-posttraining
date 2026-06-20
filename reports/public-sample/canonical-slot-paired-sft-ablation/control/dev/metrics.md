# Control dev canonical slot paired SFT metrics

- Training manifest: `public-sample-20260617T152259Z`
- Evaluation manifest: `public-sample-20260619T090925Z`
- Gold rows: `207`
- Predictions: `207`
- Schema retry boundary: `generation_time_invalid_json_retry_only_no_posthoc_prediction_repair`

| metric | value |
| --- | ---: |
| `contract_exact_match_strict` | 0.797101 |
| `slot_value_exact_f1` | 0.837607 |
| `slot_value_normalized_f1` | 0.837607 |
| `executable_contract_pass_rate` | 0.816425 |
| `schema_validity` | 1.000000 |
| `route_accuracy` | 0.971014 |
| `task_type_accuracy` | 0.971014 |
| `safety_recall` | 1.000000 |
| `unsafe_false_negative_rate` | 0.026316 |
| `requires_confirmation_accuracy` | 0.961353 |
| `json_valid_rate` | 1.000000 |

No DPO/GRPO, LLM judge, post-hoc prediction repair, semantic-equivalence scoring, adapter release, or checkpoint release was performed.
