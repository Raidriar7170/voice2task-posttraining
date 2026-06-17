# Voice2Task scaled public sample current-123 adapter dev metrics

This report summarizes contract-level metrics only. No live-browser improvement claim is made from these numbers.

## Metrics

- `confirmation_accuracy`: 0.9758
- `contract_exact_match`: 0.2464
- `json_valid_rate`: 1.0000
- `route_accuracy`: 0.9614
- `safety_gold_stop_support`: 27.0000
- `safety_precision`: 1.0000
- `safety_predicted_stop_support`: 27.0000
- `safety_recall`: 1.0000
- `slot_f1`: 0.2874
- `slot_f1_soft`: 0.6372
- `task_type_accuracy`: 0.9614

## Failure Slices

- `confirmation`: 5 examples (seed-open-example-aug-1, family-blocked_payment-dev-1, family-blocked_payment-dev-1-aug-1, family-blocked_payment-dev-1-aug-2, family-blocked_payment-dev-2-aug-2)
- `route`: 8 examples (seed-open-example-aug-1, family-clarify-dev-3, family-clarify-dev-3-aug-1, family-clarify-dev-3-aug-2, family-extract-dev-2-aug-1)
- `safety`: 0 examples (none)
- `schema`: 0 examples (none)
- `slot`: 148 examples (seed-open-example-aug-1, seed-clarify-ambiguous, seed-clarify-ambiguous-aug-1, seed-clarify-ambiguous-aug-2, family-search-dev-1-aug-1)
- `task_type`: 8 examples (seed-open-example-aug-1, family-clarify-dev-3, family-clarify-dev-3-aug-1, family-clarify-dev-3-aug-2, family-extract-dev-2-aug-1)
- `unknown`: 0 examples (none)
