# A100 current train split SFT retry test

This report summarizes contract-level metrics only. No live-browser improvement claim is made from these numbers.

## Metrics

- `confirmation_accuracy`: 0.9565
- `contract_exact_match`: 0.4058
- `json_valid_rate`: 1.0000
- `route_accuracy`: 0.8986
- `safety_gold_stop_support`: 12.0000
- `safety_precision`: 0.9231
- `safety_predicted_stop_support`: 13.0000
- `safety_recall`: 1.0000
- `slot_f1`: 0.5386
- `slot_f1_soft`: 0.7682
- `task_type_accuracy`: 0.8986

## Failure Slices

- `confirmation`: 3 examples (family-navigation-test-1, family-navigation-test-3, family-navigation-test-3-aug-1)
- `route`: 7 examples (family-navigation-test-1, family-navigation-test-3, family-navigation-test-3-aug-1, family-clarify-test-2-aug-1, family-form_fill-test-3-aug-2)
- `safety`: 1 examples (family-clarify-test-2-aug-1)
- `schema`: 0 examples (none)
- `slot`: 34 examples (seed-block-purchase-aug-1, seed-block-purchase-aug-2, family-search-test-1-aug-1, family-search-test-1-aug-2, family-search-test-2)
- `task_type`: 7 examples (family-navigation-test-1, family-navigation-test-3, family-navigation-test-3-aug-1, family-clarify-test-2-aug-1, family-form_fill-test-3-aug-2)
- `unknown`: 0 examples (none)
