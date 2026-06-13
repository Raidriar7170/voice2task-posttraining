# Current tiny adapter held-out prediction evidence

Status: public-sample held-out prediction-only diagnostic. This is not a new training run, not a release, not private-corpus evidence, not production-readiness evidence, and not a live-browser benchmark.

## Scope

- Base model: `Qwen/Qwen2.5-7B-Instruct`
- Dataset manifest: `public-sample-20260613T072200Z`
- Prediction source kind: `private_a100_adapter`
- Adapter source: private adapter from the current-manifest tiny-overfit probe
- Prediction splits: `dev, test`
- Prior train-internal tiny exact match: `1.0000` on `3` rows
- Overall interpretation: `current_tiny_adapter_heldout_strict_generalization_failed`

## Split Results

| split | rows | json_valid_rate | contract_exact_match | slot_f1 | task_type_accuracy | route_accuracy | confirmation_accuracy | safety_recall | schema_invalid | alignment_mismatch_rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 6 | 1.0000 | 0.0000 | 0.3333 | 0.5000 | 0.5000 | 0.5000 | 1.0000 | 0 | 6 |
| test | 6 | 0.6667 | 0.0000 | 0.2889 | 0.6667 | 0.6667 | 0.6667 | 1.0000 | 2 | 6 |

## Interpretation

The prior 3-row train-internal recovery did not carry to the current public held-out rows under strict contract evaluation. Both `dev` and `test` remain `contract_exact_match=0.0000`; `dev` stays schema-valid but still misses clarify/open-url contract fields, while `test` has two schema-invalid form-fill predictions plus slot, safety, and normalized-command residuals.

## Residual Field Counts

- dev: confirmation_required=3, normalized_command=6, route=3, safety.allow=1, safety.reason=2, slots=4, task_type=3
- test: normalized_command=6, safety.allow=1, safety.reason=2, slots=6

## Public Artifacts

- Diagnosis: `reports/public-sample/current-tiny-adapter-heldout-prediction/current_tiny_adapter_heldout_diagnosis.json`
- Manifest: `reports/public-sample/current-tiny-adapter-heldout-prediction/manifest.json`
- Dev metrics: `reports/public-sample/current-tiny-adapter-heldout-prediction/dev/metrics.json`
- Test metrics: `reports/public-sample/current-tiny-adapter-heldout-prediction/test/metrics.json`
- Leak scan: `reports/public-sample/current-tiny-adapter-heldout-prediction/leak_scan_result.json`

## Boundary

The evidence pack contains sanitized public-sample held-out predictions, aggregate metrics, diagnostics, and sidecars. It does not copy raw logs, checkpoints, adapters, remote caches, private overrides, host details, SSH details, tokens, private paths, or private corpus rows into git.

## Recommended Next Step

Archive this phase as a negative held-out transfer diagnostic. The next bounded phase should inspect why the tiny adapter memorizes three train rows but fails current dev/test exact match, with focus on task-family coverage and whether the next move is targeted data coverage, prompt policy, or preference tuning rather than more blind SFT.
