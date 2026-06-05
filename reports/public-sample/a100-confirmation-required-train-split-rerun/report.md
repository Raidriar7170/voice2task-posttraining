# A100 Confirmation-Required Train-Split Rerun

Status: train-internal confirmation-required diagnostic evidence. This is not a benchmark, not a release, and no held-out generalization claim is made.

## Result

The rerun produced `3` train predictions from the private A100 adapter path. The prediction prompt metadata shows `confirmation_required_boolean_visible=True` and `weather_to_search_confirmation_false_visible=True`.

Observed strict final-contract Browser Task Contract `json_valid_rate=0.6667`, `contract_exact_match=0.0000`, `task_type_accuracy=0.3333`, and `route_accuracy=0.3333`.

confirmation_required boolean emission improved to `2/3` and final validated schema-valid `2/3`. This is partial recovery on the same train rows: one row still omits `confirmation_required`, and its retry attempt is rejected by the strict whole-object parser.

## What Changed Versus Baseline

- Prior route-ontology rerun: missing `confirmation_required` was `3/3`, and final validated schema-valid was `0/3`.
- This rerun: missing `confirmation_required` is `1/3`, and final validated schema-valid is `2/3`.
- The remaining exact-match gap is still real: strict final contract exact match remains `0.0000`.

## Public Artifacts

- Predictions: `reports/public-sample/a100-confirmation-required-train-split-rerun/predictions.jsonl`
- Train gold subset used for metrics: `reports/public-sample/a100-confirmation-required-train-split-rerun/train_split_gold.jsonl`
- Metrics: `reports/public-sample/a100-confirmation-required-train-split-rerun/metrics.json` / `reports/public-sample/a100-confirmation-required-train-split-rerun/metrics.md`
- Schema guard summary: `reports/public-sample/a100-confirmation-required-train-split-rerun/schema_guard_summary.json` / `reports/public-sample/a100-confirmation-required-train-split-rerun/schema_guard_summary.md`
- Confirmation-required diagnosis: `reports/public-sample/a100-confirmation-required-train-split-rerun/confirmation_required_diagnosis.json` / `reports/public-sample/a100-confirmation-required-train-split-rerun/confirmation_required_diagnosis.md`
- Prompt snapshot: `reports/public-sample/a100-confirmation-required-train-split-rerun/prompt_snapshot.json`
- Raw decoded summary: `reports/public-sample/a100-confirmation-required-train-split-rerun/raw_decoded_summary.jsonl`
- Generation trace: `reports/public-sample/a100-confirmation-required-train-split-rerun/generation_trace.jsonl`
- Prediction metadata: `reports/public-sample/a100-confirmation-required-train-split-rerun/prediction_metadata.json`
- Manifest: `reports/public-sample/a100-confirmation-required-train-split-rerun/manifest.json`

## Boundary

The evidence pack contains sanitized public-sample contract predictions, aggregate metrics, schema guard summaries, confirmation-required diagnosis, and leak-scan status. It does not copy raw logs, checkpoints, adapters, remote caches, private configs, host details, tokens, SSH details, or private corpus rows into git.

Claim boundaries: no checkpoint release, no adapter release, no held-out generalization claim, no production-readiness claim, no public full-corpus release, no model-quality claim, and no live-browser benchmark improvement claim. The result must not be described as full model recovery.

## Recommended Next Step

Archive this bounded rerun after review if validation stays green. A later phase can decide whether the remaining row-level mismatch and exact-match failures justify training or decoding changes.
