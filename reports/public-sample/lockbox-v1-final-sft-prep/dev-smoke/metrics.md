# Voice2Task final SFT non-lockbox dev smoke metrics

This report summarizes contract-level metrics only. No live-browser improvement claim is made from these numbers.

## Metrics

- `confirmation_accuracy`: 1.0000
- `contract_exact_match`: 0.3333
- `json_parse_count`: 24.0000
- `json_parse_rate`: 1.0000
- `json_valid_rate`: 1.0000
- `route_accuracy`: 0.9583
- `safety_fn`: 0.0000
- `safety_fp`: 0.0000
- `safety_gold_positive_support`: 0.0000
- `safety_gold_stop_support`: 0.0000
- `safety_precision`: null
- `safety_predicted_positive_support`: 0.0000
- `safety_predicted_stop_support`: 0.0000
- `safety_recall`: null
- `safety_tp`: 0.0000
- `semantic_contract_valid_count`: 24.0000
- `semantic_contract_valid_rate`: 1.0000
- `slot_f1`: 0.5000
- `slot_f1_soft`: 0.9583
- `strict_schema_valid_count`: 24.0000
- `strict_schema_valid_rate`: 1.0000
- `task_type_accuracy`: 0.9583

## Failure Slices

- `confirmation`: 0 examples (none)
- `route`: 1 examples (family-search-dev-1)
- `safety`: 0 examples (none)
- `schema`: 0 examples (none)
- `semantic`: 0 examples (none)
- `slot`: 12 examples (seed-clarify-ambiguous, seed-clarify-ambiguous-aug-1, seed-clarify-ambiguous-aug-2, family-search-dev-1, family-search-dev-1-aug-1)
- `task_type`: 1 examples (family-search-dev-1)
- `unknown`: 0 examples (none)
