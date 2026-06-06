# A100 retry JSON-only boundary train-split rerun

Status: train-internal A100 diagnostic rerun after stricter retry JSON-only prompt hardening. This is not a benchmark, not a release, and no held-out generalization claim is made.

## Result

The rerun produced `3` train predictions from the private A100 adapter path. Strict final-contract `json_valid_rate=0.0000` and `contract_exact_match=0.0000` remain unchanged from the bounded prior stop-boundary rerun.

Retry prompt constraints are visible (`15/15` booleans true), including exact JSON-only output, no text outside the root object, no natural-language wrapper/preamble, and machine-readable-only retry response.

Despite that, retry attempts remain prose/Markdown-wrapped JSON fragments for `3/3` rows, and final validated schema-valid output remains `0/3`. This must not be described as schema recovery or model recovery.

## Public Artifacts

- Predictions: `reports/public-sample/a100-retry-json-only-boundary-rerun/predictions.jsonl`
- Prediction metadata: `reports/public-sample/a100-retry-json-only-boundary-rerun/prediction_metadata.json`
- Prompt snapshot: `reports/public-sample/a100-retry-json-only-boundary-rerun/prompt_snapshot.json`
- Raw decoded summary: `reports/public-sample/a100-retry-json-only-boundary-rerun/raw_decoded_summary.jsonl`
- Generation trace: `reports/public-sample/a100-retry-json-only-boundary-rerun/generation_trace.jsonl`
- Metrics: `reports/public-sample/a100-retry-json-only-boundary-rerun/metrics.json` / `reports/public-sample/a100-retry-json-only-boundary-rerun/metrics.md`
- Schema diagnostics: `reports/public-sample/a100-retry-json-only-boundary-rerun/schema_diagnostics.json` / `reports/public-sample/a100-retry-json-only-boundary-rerun/schema_diagnostics.md`
- Schema guard summary: `reports/public-sample/a100-retry-json-only-boundary-rerun/schema_guard_summary.json` / `reports/public-sample/a100-retry-json-only-boundary-rerun/schema_guard_summary.md`
- Retry JSON-only diagnosis: `reports/public-sample/a100-retry-json-only-boundary-rerun/retry_json_only_boundary_diagnosis.json` / `reports/public-sample/a100-retry-json-only-boundary-rerun/retry_json_only_boundary_diagnosis.md`
- Manifest: `reports/public-sample/a100-retry-json-only-boundary-rerun/manifest.json`

## Boundary

The evidence pack contains sanitized public-sample predictions, aggregate metrics, schema diagnostics, constrained decoding diagnosis, schema guard summaries, retry JSON-only boundary diagnosis, and leak-scan status. It does not copy raw logs, checkpoints, adapters, remote caches, private configs, host details, tokens, SSH details, private paths, or private corpus rows into git.

No training, decoding behavior change, parser relaxation, evaluator metric change, schema repair/coercion, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, checkpoint release, adapter release, production-readiness claim, held-out generalization claim, public full-corpus release claim, live-browser benchmark claim, model-quality claim, or model-recovery claim is made.
