# A100 formal public held-out prediction

Status: prediction-only current-manifest held-out evidence. This phase does not train, mutate data, repair predictions, normalize slots, or change evaluator semantics.

## Scope

- Dataset manifest: `public-sample-20260616T165835Z`
- Run status: `observed`
- Source adapter runtime: `a100-form-fill-remediation-sft-v3`
- Overall interpretation: `formal_public_heldout_partial_signal`

## Split Results

| split | rows | contract_exact_match | slot_f1 | slot_f1_soft | json_valid_rate | residual rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 69 | 0.4638 | 0.5652 | 0.8157 | 1.0000 | 37 |
| test | 69 | 0.3478 | 0.4976 | 0.7646 | 1.0000 | 45 |

## Comparison Boundary

- Current dataset manifest: `public-sample-20260616T165835Z`
- Prior formal held-out manifest: `public-sample-20260616T074315Z`
- Prior evidence: `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery`
- Prior blocked evidence: `reports/public-sample/a100-form-fill-remediation-sft-v3`
- Prior formal held-out metrics used a different public sample boundary and are not a clean direct improvement/regression comparison.
- Boundary note: The blocked-payment repair materialization added train-only rows; dev/test row counts remain 69 each, so unchanged metrics are expected but must still be bound to the current manifest.

## Boundary

- Strict `contract_exact_match` remains primary.
- `slot_f1_soft` is diagnostic only.
- Predictions are not repaired, replaced, normalized, or re-scored.
- This is not held-out recovery unless dev/test strict exact both reach `1.0`; it is not a checkpoint release, adapter release, production-readiness claim, private-corpus generalization claim, public full-corpus release, or live-browser benchmark claim.
