# A100 formal public held-out prediction

Status: prediction-only current-manifest held-out evidence. This phase does not train, mutate data, repair predictions, normalize slots, or change evaluator semantics.

## Scope

- Dataset manifest: `public-sample-20260617T152259Z`
- Run status: `observed`
- Source adapter runtime: `a100-current-train-split-sft-retry`
- Overall interpretation: `formal_public_heldout_partial_signal`

## Split Results

| split | rows | contract_exact_match | slot_f1 | slot_f1_soft | json_valid_rate | residual rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 207 | 0.2464 | 0.2874 | 0.6372 | 1.0000 | 156 |
| test | 207 | 0.2029 | 0.2593 | 0.6108 | 1.0000 | 165 |

## Comparison Boundary

- Current dataset manifest: `public-sample-20260617T152259Z`
- Prior formal held-out manifest: `public-sample-20260617T045941Z`
- Prior evidence: `reports/public-sample/a100-current-123-train-split-sft-retry`
- Prior blocked evidence: `not_provided`
- Prior formal held-out metrics used a different public sample boundary and are not a clean direct improvement/regression comparison.
- This run is a runtime-recovery prediction-only retry, not a training change, evaluator relaxation, prediction repair, or model-recovery claim.

## Boundary

- Strict `contract_exact_match` remains primary.
- `slot_f1_soft` is diagnostic only.
- Predictions are not repaired, replaced, normalized, or re-scored.
- This is not held-out recovery unless dev/test strict exact both reach `1.0`; it is not a checkpoint release, adapter release, production-readiness claim, private-corpus generalization claim, public full-corpus release, or live-browser benchmark claim.
