# A100 formal public held-out prediction

Status: prediction-only current-manifest held-out evidence. This phase does not train, mutate data, repair predictions, normalize slots, or change evaluator semantics.

## Scope

- Dataset manifest: `public-sample-20260616T022151Z`
- Run status: `observed`
- Source adapter runtime: `a100-merged-slot-value-heldout-eval`
- Overall interpretation: `formal_public_heldout_partial_signal`

## Split Results

| split | rows | contract_exact_match | slot_f1 | slot_f1_soft | json_valid_rate | residual rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 69 | 0.3043 | 0.3913 | 0.7315 | 1.0000 | 48 |
| test | 69 | 0.2899 | 0.5072 | 0.7609 | 1.0000 | 49 |

## Boundary

- Strict `contract_exact_match` remains primary.
- `slot_f1_soft` is diagnostic only.
- Predictions are not repaired, replaced, normalized, or re-scored.
- This is not held-out recovery unless dev/test strict exact both reach `1.0`; it is not a checkpoint release, adapter release, production-readiness claim, private-corpus generalization claim, public full-corpus release, or live-browser benchmark claim.
