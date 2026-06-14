# A100 targeted family coverage probe evidence

Status: targeted family coverage probe with partial held-out movement. This is not a release, not private-corpus evidence, not production-readiness evidence, and not a live-browser benchmark.

## Scope

- Base model: `Qwen/Qwen2.5-7B-Instruct`
- Dataset manifest: `public-sample-20260613T072200Z`
- Prediction source kind: `private_a100_adapter`
- Training source IDs: `['seed-open-help', 'seed-clarify-target', 'seed-form-nickname', 'seed-block-transfer']`
- Training rows used: `12`
- Overall interpretation: `targeted_family_coverage_partial_transfer`

## Split Results

| split | rows | json_valid_rate | contract_exact_match | slot_f1 | slot_f1_soft | task_type | route | confirmation | schema invalid | mismatch rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 18 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0 | 0 |
| dev | 6 | 1.0000 | 0.1667 | 0.5000 | 0.9333 | 1.0000 | 1.0000 | 1.0000 | 0 | 5 |
| test | 6 | 1.0000 | 0.1667 | 0.5000 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 0 | 5 |

## Comparison

- Current tiny adapter held-out exact: `{'dev': 0.0, 'test': 0.0}`
- Prior broad residual repair exact: `{'train': 0.3333333333333333, 'dev': 0.0, 'test': 0.0}`
- Targeted family coverage exact: `{'train': 1.0, 'dev': 0.16666666666666666, 'test': 0.16666666666666666}`
- Interpretation: targeted source-family coverage fixed train memorization (`train=1.0000`) and moved dev/test strict exact from `0.0000` to `0.1667`, but did not fully recover held-out generalization.

## Remaining Residuals

- dev: normalized_command=2, slots=3
- test: normalized_command=2, slots=3

## Boundary

- This is not a checkpoint release.
- This is not an adapter release.
- This is not full private-corpus generalization evidence.
- This is not production-readiness evidence.
- This is not a live-browser benchmark or benchmark-improvement claim.
- Soft slot F1 is diagnostic context only; strict `contract_exact_match` remains primary.

## Recommended Next Step

Open a very small diagnosis phase for the remaining slot value residuals before broad scaling or DPO. The next question is no longer basic family coverage; it is why clarify/form slot values remain strict-wrong while task, route, safety, confirmation, and JSON validity are now correct.
