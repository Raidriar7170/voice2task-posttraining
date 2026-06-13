# A100 public held-out contract generalization evidence

Status: public held-out diagnostic evidence. This is not a release, not private-corpus evidence, not production-readiness evidence, and not a live-browser benchmark.

## Scope

- Base model: `Qwen/Qwen2.5-7B-Instruct`
- Dataset manifest: `public-sample-20260613T063029Z`
- Prediction source kind: `private_a100_adapter`
- Prediction splits: `dev, test`
- Prior train split exact match: `1.0000`
- Overall interpretation: `public_heldout_strict_generalization_failed`

## Split Results

| split | rows | json_valid_rate | contract_exact_match | slot_f1 | confirmation_accuracy | safety_recall |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 6 | 1.0000 | 0.0000 | 0.0000 | 0.5000 | 1.0000 |
| test | 6 | 1.0000 | 0.0000 | 0.0000 | 0.3333 | 0.6667 |

## Interpretation

The prior train-split recovery does not carry to the public held-out rows under strict contract evaluation. Both held-out splits are schema-valid but `contract_exact_match=0.0`, with slot, normalized-command, clarify, form-confirmation, and blocked-action residuals.

## Public Artifacts

- Diagnosis: `reports/public-sample/a100-public-heldout-contract-generalization/heldout_contract_generalization_diagnosis.json`
- Manifest: `reports/public-sample/a100-public-heldout-contract-generalization/manifest.json`
- Dev metrics: `reports/public-sample/a100-public-heldout-contract-generalization/dev/metrics.json`
- Test metrics: `reports/public-sample/a100-public-heldout-contract-generalization/test/metrics.json`
- Leak scan: `reports/public-sample/a100-public-heldout-contract-generalization/leak_scan_result.json`

## Boundary

The evidence pack contains sanitized public-sample held-out predictions, aggregate metrics, diagnostics, and sidecars. It does not copy raw logs, checkpoints, adapters, remote caches, private overrides, host details, SSH details, tokens, private paths, or private corpus rows into git.
