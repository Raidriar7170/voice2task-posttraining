# Voice2Task form-fill SFT v3 test metrics

This report summarizes contract-level metrics only. No live-browser improvement claim is made from these numbers.

## Metrics

- `confirmation_accuracy`: 0.9855
- `contract_exact_match`: 0.3478
- `json_valid_rate`: 1.0000
- `route_accuracy`: 0.9275
- `safety_gold_stop_support`: 12.0000
- `safety_precision`: 0.9231
- `safety_predicted_stop_support`: 13.0000
- `safety_recall`: 1.0000
- `slot_f1`: 0.4976
- `slot_f1_soft`: 0.7646
- `task_type_accuracy`: 0.9275

## Failure Slices

- `confirmation`: 1 examples (family-navigation-test-3)
- `route`: 5 examples (family-navigation-test-3, family-clarify-test-2-aug-1, family-form_fill-test-3-aug-2, family-extract-test-1-aug-1, family-extract-test-2-aug-1)
- `safety`: 1 examples (family-clarify-test-2-aug-1)
- `schema`: 0 examples (none)
- `slot`: 38 examples (seed-block-purchase, seed-block-purchase-aug-1, seed-block-purchase-aug-2, family-search-test-1-aug-1, family-search-test-1-aug-2)
- `task_type`: 5 examples (family-navigation-test-3, family-clarify-test-2-aug-1, family-form_fill-test-3-aug-2, family-extract-test-1-aug-1, family-extract-test-2-aug-1)
- `unknown`: 0 examples (none)
