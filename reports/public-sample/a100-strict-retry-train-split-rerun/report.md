# A100 Strict-Retry Train-Split Rerun

Status: train-internal strict-retry diagnostic evidence. This is not a benchmark, not a release, and not a live-browser improvement claim.

## Result

The rerun produced 3 train predictions. Observed schema-valid Browser Task Contract `json_valid_rate=0.0000`, `contract_exact_match=0.0000`, `route_accuracy=0.0000`, `slot_f1=0.0000`, and `task_type_accuracy=0.0000`.

Schema guard observed raw schema-valid `0/3`, retry schema-valid `0/3`, and validated schema-valid `0/3`. strict retry rejected JSON fragments wrapped in Markdown/prose for `3` retry attempts. The train split is not recovered and must not be described as schema recovery.

## What Changed Versus Prior Rerun

- This uses the same bounded public-sample train split and private adapter context as the required-field repair rerun.
- The current prediction code now interprets retry output with the whole-string JSON-only strict parser.
- Markdown/prose-wrapped retry fragments remain invalid evidence instead of being accepted as repaired contracts.

## Public Artifacts

- Predictions: `reports/public-sample/a100-strict-retry-train-split-rerun/predictions.jsonl`
- Metrics: `reports/public-sample/a100-strict-retry-train-split-rerun/metrics.json` / `reports/public-sample/a100-strict-retry-train-split-rerun/metrics.md`
- Schema guard summary: `reports/public-sample/a100-strict-retry-train-split-rerun/schema_guard_summary.json` / `reports/public-sample/a100-strict-retry-train-split-rerun/schema_guard_summary.md`
- Constrained decoding diagnosis: `reports/public-sample/a100-strict-retry-train-split-rerun/constrained_decoding_diagnosis.json` / `reports/public-sample/a100-strict-retry-train-split-rerun/constrained_decoding_diagnosis.md`
- Prompt snapshot: `reports/public-sample/a100-strict-retry-train-split-rerun/prompt_snapshot.json`
- Raw decoded summary: `reports/public-sample/a100-strict-retry-train-split-rerun/raw_decoded_summary.jsonl`
- Generation trace: `reports/public-sample/a100-strict-retry-train-split-rerun/generation_trace.jsonl`
- Prediction metadata: `reports/public-sample/a100-strict-retry-train-split-rerun/prediction_metadata.json`
- Leak scan: `reports/public-sample/a100-strict-retry-train-split-rerun/leak_scan_result.json`

## Policy Fields

- Release status: `not_released`
- Schema guard enabled: `True`
- Schema retry enabled: `True`
- Schema retry max attempts: `1`
- Strict retry interpretation: `whole_string_json_only_retry_parser`
- Decoding strategy: `greedy`
- Raw decoded sidecar written: `True`
- Generation trace sidecar written: `True`

## Boundary

The evidence pack contains sanitized public-sample contract predictions, aggregate metrics, schema guard summaries, constrained decoding diagnosis, and leak-scan status. It does not copy raw logs, checkpoints, adapters, remote caches, private paths, host details, tokens, SSH details, or private corpus rows into git.

Claim boundaries: no checkpoint release, no adapter release, no held-out generalization claim, no production-readiness claim, no public full-corpus release, no A100 model recovery claim, and no live-browser benchmark improvement claim.
