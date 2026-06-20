# Treatment test canonical slot paired SFT metrics

- Training manifest: `public-sample-20260619T090925Z`
- Evaluation manifest: `public-sample-20260619T090925Z`
- Gold rows: `207`
- Predictions: `207`
- Schema retry boundary: `generation_time_invalid_json_retry_only_no_posthoc_prediction_repair`

| metric | value |
| --- | ---: |
| `contract_exact_match_strict` | 0.792271 |
| `slot_value_exact_f1` | 0.823529 |
| `slot_value_normalized_f1` | 0.823529 |
| `executable_contract_pass_rate` | 0.821256 |
| `schema_validity` | 1.000000 |
| `route_accuracy` | 0.980676 |
| `task_type_accuracy` | 0.980676 |
| `safety_recall` | 1.000000 |
| `unsafe_false_negative_rate` | 0.008333 |
| `requires_confirmation_accuracy` | 0.995169 |
| `json_valid_rate` | 1.000000 |

No DPO/GRPO, LLM judge, post-hoc prediction repair, semantic-equivalence scoring, adapter release, or checkpoint release was performed.
