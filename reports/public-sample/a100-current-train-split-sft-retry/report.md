# Voice2Task current train split SFT retry

Status: training completed for one bounded private A100 current-train-split SFT retry, followed by dev/test prediction-only strict evaluation.

## Scope

- Dataset manifest: `public-sample-20260616T165835Z`
- Source adapter runtime: `a100-current-train-split-sft-retry`
- Training status: `training_completed`
- Training rows used: `118`
- Overall interpretation: `current_train_split_sft_retry_partial_signal`

## Split Results

| split | rows | contract_exact_match | slot_f1 | slot_f1_soft | safety_recall | json_valid_rate | residual rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 69 | 0.4348 | 0.5797 | 0.8671 | 1.0000 | 1.0000 | 39 |
| test | 69 | 0.4058 | 0.5386 | 0.7682 | 1.0000 | 1.0000 | 41 |

## Current Baseline Comparison

- Direct comparison valid: `True`
- Strict exact delta: `{'dev': -0.02898550724637683, 'test': 0.05797101449275366}`
- Strict slot F1 delta: `{'dev': 0.01449275362318847, 'test': 0.04106280193236728}`
- Safety recall delta: `{'dev': 0.4444444444444444, 'test': 0.0}`

## Boundary

- Strict `contract_exact_match` and strict `slot_f1` remain primary.
- `slot_f1_soft` is diagnostic only.
- Predictions are not repaired, replaced, normalized, or re-scored.
- This report does not release a checkpoint or adapter and does not claim production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement.
