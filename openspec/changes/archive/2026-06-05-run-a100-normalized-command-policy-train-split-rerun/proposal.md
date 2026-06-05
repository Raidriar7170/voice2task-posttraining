## Why

The archived `define-normalized-command-canonicalization-policy` phase made the target-writing policy visible in the SFT/prediction prompt without changing evaluator semantics. The next smallest evidence step is one explicitly authorized A100 prediction-only train-split rerun to observe whether that prompt-policy change affects the existing private adapter outputs on the same three train rows.

## What Changes

- Run one bounded A100 prediction-only train-split rerun using the current normalized-command canonicalization prompt, strict schema guard, greedy decoding, and existing private train-split adapter.
- Keep `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, and `schema_repair_applied=false`.
- Import only sanitized public-safe evidence: prediction metadata, predictions, prompt snapshot, raw decoded summary, generation trace, train-split gold rows, strict metrics, normalized-command diagnosis, manifest, reports, leak scans, and Human Briefs.
- Compare narrowly against `reports/public-sample/a100-confirmation-required-train-split-rerun/` as the pre-normalized-command-policy A100 baseline.
- Preserve the result honestly whether `normalized_command` exact string mismatches improve, remain partial, or stay unchanged.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add an explicitly authorized A100 train-split prediction rerun path after normalized-command canonicalization prompt policy.
- `contract-evaluation`: add public-safe evidence requirements and non-claim boundaries for normalized-command train-split rerun diagnostics.

## Impact

- Affected runtime path: `voice2task.cli.train sft-predict` on A100 with a repo-external private adapter config and approved private output root represented in public artifacts as `<a100_project_root>`.
- Affected evidence: new public-safe report directory under `reports/public-sample/a100-normalized-command-policy-train-split-rerun/` and Chinese Human Briefs under `docs/human-briefs/`.
- Non-goals: no generic chat fine-tuning, no skill routing, no GUI action policy learning, no first-phase GRPO, no public release of the full local corpus, no SFT/DPO training, no dev/test or full-public-sample rerun, no checkpoint or adapter release, no production-readiness claim, no held-out generalization claim, no public full-corpus release, no model-quality improvement claim, no live-browser benchmark improvement claim, no evaluator metric change, no semantic-equivalence scoring, and no prediction repair/re-score.
