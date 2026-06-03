# A100 Train-Split Overfit Diagnostic Evidence

Status: train-internal overfit diagnostic evidence. This is not a benchmark, not a release, and not a live-browser improvement claim.

## Scope

- Base model: `Qwen/Qwen2.5-0.5B-Instruct`
- Model source: `modelscope`
- Dataset manifest: `public-sample-20260601T162313Z`
- Prediction source kind: `public_sample_contract_fixture`
- Prediction split: `train`
- Overfit diagnostic: `True`
- Generalization claim: `False`
- Release status: `not_released`

## Interpretation

If `prediction_source_kind` is `public_sample_contract_fixture`, the predictions are deterministic public-sample contract fixtures used to validate the evidence pipeline. They are not private adapter model outputs and must not be presented as model-quality evidence.
If `prediction_source_kind` is `private_a100_adapter`, the predictions came from the private A100 adapter path, but the metrics and controlled smoke results still only describe this bounded public sample. Failed schema or smoke results must be reported as failures, not hidden behind the existence of a completed training run.
For a train-internal overfit diagnostic, recovery on `prediction_split=train` can only support a narrow train-internal sanity check. It does not prove dev/test generalization, production readiness, checkpoint release, adapter release, or live-browser benchmark improvement. There is no release claim.

## Public Artifacts

- Predictions: `reports/public-sample/a100-train-split-overfit-diagnostic/predictions.jsonl`
- Metrics: `reports/public-sample/a100-train-split-overfit-diagnostic/metrics.json`
- Prompt snapshot: `reports/public-sample/a100-train-split-overfit-diagnostic/prompt_snapshot.json`
- Raw decoded summary: `reports/public-sample/a100-train-split-overfit-diagnostic/raw_decoded_summary.jsonl`
- Generation trace: `reports/public-sample/a100-train-split-overfit-diagnostic/generation_trace.jsonl`
- Objective inspection: `reports/public-sample/a100-train-split-overfit-diagnostic/objective_inspection.json`
- Leak scan artifact: `reports/public-sample/a100-train-split-overfit-diagnostic/leak_scan_result.json`
- Controlled smoke: `not_run_for_train_split_diagnostic`
- Leak scan ok: `True`

## Boundary

The evidence pack may contain sanitized public-sample contract predictions, aggregate metrics, controlled smoke status, and leak-scan status. It does not copy raw logs, checkpoints, adapters, remote caches, private paths, host details, tokens, or private corpus rows into git.
