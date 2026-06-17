# Voice2Task current-manifest SFT v3 dev metrics

This report summarizes contract-level metrics only. No live-browser improvement claim is made from these numbers.

## Metrics

- `confirmation_accuracy`: 0.9710
- `contract_exact_match`: 0.4638
- `json_valid_rate`: 1.0000
- `route_accuracy`: 0.8696
- `safety_gold_stop_support`: 9.0000
- `safety_precision`: 1.0000
- `safety_predicted_stop_support`: 5.0000
- `safety_recall`: 0.5556
- `slot_f1`: 0.5652
- `slot_f1_soft`: 0.8157
- `task_type_accuracy`: 0.8696

## Failure Slices

- `confirmation`: 2 examples (seed-open-example-aug-1, family-navigation-dev-2-aug-2)
- `route`: 9 examples (seed-open-example-aug-1, family-navigation-dev-2-aug-2, family-clarify-dev-3, family-clarify-dev-3-aug-1, family-clarify-dev-3-aug-2)
- `safety`: 4 examples (family-blocked_payment-dev-1, family-blocked_payment-dev-1-aug-1, family-blocked_payment-dev-1-aug-2, family-blocked_payment-dev-2-aug-2)
- `schema`: 0 examples (none)
- `slot`: 30 examples (seed-open-example-aug-1, seed-clarify-ambiguous, seed-clarify-ambiguous-aug-1, seed-clarify-ambiguous-aug-2, family-search-dev-1-aug-1)
- `task_type`: 9 examples (seed-open-example-aug-1, family-navigation-dev-2-aug-2, family-clarify-dev-3, family-clarify-dev-3-aug-1, family-clarify-dev-3-aug-2)
- `unknown`: 0 examples (none)
