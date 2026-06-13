# A100 public held-out contract generalization diagnosis

Overall interpretation: `public_heldout_strict_generalization_failed`.

## Split Metrics

| split | json_valid_rate | contract_exact_match | slot_f1 | task_type_accuracy | route_accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| dev | 1.0000 | 0.0000 | 0.0000 | 0.5000 | 0.5000 |
| test | 1.0000 | 0.0000 | 0.0000 | 0.5000 | 0.8333 |

## Interpretation

All held-out predictions are schema-valid, but strict exact match is 0.0 on both public held-out splits. This means the prior train-split recovery should not be treated as held-out generalization.

This diagnosis is not a release, not private-corpus evidence, not production-readiness evidence, and not a live-browser benchmark.
