# A100 form-fill remediation SFT v3 retry after SSH recovery

Status: observed private A100 SFT v3 training plus dev/test prediction on the current formal public sample. Adapter/checkpoint/log/private override artifacts are not released.

## Scope

- Dataset manifest: `public-sample-20260616T074315Z`
- Training rows used: `114` (`21` form-fill remediation / marker rows)
- Overall interpretation: `form_fill_sft_v3_partial_improvement_with_safety_regression_risk`
- Primary evidence remains strict `contract_exact_match` and strict `slot_f1`; `slot_f1_soft` is diagnostic only.

## Split Results

| split | exact | strict slot_f1 | route | safety_recall | confirmation | json_valid |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 0.4638 | 0.5652 | 0.8696 | 0.5556 | 0.9710 | 1.0000 |
| test | 0.3478 | 0.4976 | 0.9275 | 1.0000 | 0.9855 | 1.0000 |

## Same-Manifest Comparison

| split | exact delta | strict slot_f1 delta | route delta | safety_recall delta | confirmation delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| dev | +0.1594 | +0.1739 | +0.0145 | -0.1111 | -0.0145 |
| test | +0.0580 | -0.0097 | +0.0145 | +0.0833 | +0.0000 |

## Interpretation

- Dev exact and strict slot_f1 improved substantially, matching the targeted form-fill remediation intent.
- Test exact improved, while test strict slot_f1 is effectively flat/slightly lower.
- Dev safety_recall regressed, so this is not a model recovery or production-readiness result.
- The result is evidence for a useful but incomplete SFT v3 direction; the next bounded phase should diagnose safety/blocked_payment regression before any further training claim.

## Non-Claims

- No adapter, checkpoint, private override, remote cache, raw log, private corpus, or live-browser benchmark is released.
- No prediction repair/replacement/rescore, evaluator relaxation, data mutation, or soft-metric promotion was performed.
