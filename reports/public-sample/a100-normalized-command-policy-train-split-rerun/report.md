# A100 normalized-command policy train-split rerun

Status: train-internal normalized-command policy observation. This is not a benchmark, not a release, and no held-out generalization claim is made.

## Result

The rerun produced `3` train predictions from the private A100 adapter path. The prediction metadata shows `normalized_command_canonical_policy_visible=True`, `normalized_command_public_examples_visible=True`, and `normalized_command_no_metric_relaxation_visible=True`.

Observed strict final-contract `json_valid_rate=0.3333` and `contract_exact_match=0.0000`.
Observed normalized-command exact-string matches were `2/3`; the prior confirmation-required rerun had `0/3`. This is field-level train-internal evidence only, not model-quality or held-out evidence.
Final schema-valid rows were `1/3`, so the rerun must not be described as full train-row recovery.

## Public Artifacts

- Predictions: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/predictions.jsonl`
- Train gold subset used for metrics: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/train_split_gold.jsonl`
- Metrics: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/metrics.json` / `reports/public-sample/a100-normalized-command-policy-train-split-rerun/metrics.md`
- Schema guard summary: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/schema_guard_summary.json` / `reports/public-sample/a100-normalized-command-policy-train-split-rerun/schema_guard_summary.md`
- Normalized-command diagnosis: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/normalized_command_diagnosis.json` / `reports/public-sample/a100-normalized-command-policy-train-split-rerun/normalized_command_diagnosis.md`
- Prompt snapshot: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/prompt_snapshot.json`
- Raw decoded summary: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/raw_decoded_summary.jsonl`
- Generation trace: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/generation_trace.jsonl`
- Prediction metadata: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/prediction_metadata.json`
- Manifest: `reports/public-sample/a100-normalized-command-policy-train-split-rerun/manifest.json`

## Boundary

The evidence pack contains sanitized public-sample contract predictions, aggregate metrics, schema guard summaries, normalized-command diagnosis, and leak-scan status. It does not copy raw logs, checkpoints, adapters, remote caches, private configs, host details, tokens, SSH details, or private corpus rows into git.

No semantic-equivalence scoring, normalized-command normalization, evaluator metric relaxation, prediction repair, re-score, SFT/DPO/GRPO training, checkpoint release, adapter release, production-readiness claim, or live-browser benchmark improvement claim is made.
