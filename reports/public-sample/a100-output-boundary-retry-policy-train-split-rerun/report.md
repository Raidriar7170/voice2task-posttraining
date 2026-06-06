# A100 output-boundary retry-policy train-split rerun

Status: train-internal A100 diagnostic rerun after local output-boundary/retry prompt hardening. This is not a benchmark, not a release, and no held-out generalization claim is made.

## Result

The rerun produced `3` train predictions from the private A100 adapter path. The prompt snapshot confirms `single_root_json_object_visible=True`, `no_premature_root_close_visible=True`, `whole_object_boundary_visible=True`, and `public_readonly_task_type_search_not_search_web_visible=True`.

Observed strict final-contract `json_valid_rate=0.0000` and `contract_exact_match=0.0000`. The local prompt repair produced a narrower diagnostic improvement: raw outputs are now whole JSON objects for `3/3` rows, but all three omit `task_type`. Retry attempts visibly include `task_type=search` for `3/3` rows, but the model wraps the retry response in prose/Markdown, so the strict parser still rejects every retry.

## Public Artifacts

- Predictions: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/predictions.jsonl`
- Train gold subset used for metrics: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/train_split_gold.jsonl`
- Metrics: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/metrics.json` / `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/metrics.md`
- Schema guard summary: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/schema_guard_summary.json` / `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/schema_guard_summary.md`
- Output-boundary retry diagnosis: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/output_boundary_retry_policy_diagnosis.json` / `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/output_boundary_retry_policy_diagnosis.md`
- Prompt snapshot: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/prompt_snapshot.json`
- Raw decoded summary: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/raw_decoded_summary.jsonl`
- Generation trace: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/generation_trace.jsonl`
- Prediction metadata: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/prediction_metadata.json`
- Manifest: `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/manifest.json`

## Boundary

The evidence pack contains sanitized public-sample contract predictions, aggregate metrics, schema guard summaries, row-level output-boundary diagnosis, and leak-scan status. It does not copy raw logs, checkpoints, adapters, remote caches, private configs, host details, tokens, SSH details, or private corpus rows into git.

No semantic-equivalence scoring, slot normalization, normalized-command normalization, evaluator metric relaxation, prediction repair, re-score, SFT/DPO/GRPO training, checkpoint release, adapter release, production-readiness claim, held-out generalization claim, model-quality claim, or live-browser benchmark improvement claim is made.
