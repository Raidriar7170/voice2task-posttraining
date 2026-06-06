## Why

The archived `repair-public-readonly-output-boundary-retry-policy` phase made the shared prediction prompt and schema retry prompt explicitly require one root JSON object, all eight Browser Task Contract fields inside that root object, no prose/Markdown wrapper, and public-readonly search `task_type="search"` rather than the route enum `search_web`.

The prior A100 public-readonly rerun remains strict negative evidence: all three train rows were schema-invalid, retry outputs were rejected as JSON fragments/prose wrappers, and raw `task_type` stayed `search_web`. The next smallest evidence step is one A100 prediction-only train-split rerun to observe whether the local prompt/retry hardening changes those same private-adapter outputs.

## What Changes

- Run one bounded A100 prediction-only train-split rerun using the current output-boundary and retry-prompt policy, strict schema guard, greedy decoding, and existing private train-split adapter.
- Keep `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, and `schema_repair_applied=false`.
- Import only sanitized public-safe evidence: prediction metadata, predictions, prompt snapshot, raw decoded summary, generation trace, train-split gold rows, strict metrics, schema guard summary, output-boundary retry diagnosis, manifest, reports, leak scans, and Human Briefs.
- Compare narrowly against `reports/public-sample/a100-public-readonly-search-policy-train-split-rerun/` and local repair evidence under `reports/public-sample/public-readonly-output-boundary-retry-policy/`.
- Preserve the result honestly whether JSON validity, task type, route, safety reason, confirmation, slots, normalized-command, retry behavior, or strict exact match improves, remains partial, or regresses.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add an explicitly authorized A100 train-split prediction rerun path after output-boundary and retry-prompt hardening.
- `contract-evaluation`: add public-safe evidence requirements and non-claim boundaries for the output-boundary retry-policy train-split rerun.

## Impact

- Affected runtime path: `voice2task.cli.train sft-predict` on A100 with a repo-external private adapter config and approved private output root represented in public artifacts as `<a100_project_root>`.
- Affected evidence: new public-safe report directory under `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/` and Chinese Human Briefs under `docs/human-briefs/`.
- Non-goals: no generic chat fine-tuning, no skill routing, no GUI action policy learning, no first-phase GRPO, no public release of the full local corpus, no SFT/DPO training, no dev/test or full-public-sample rerun, no checkpoint or adapter release, no production-readiness claim, no held-out generalization claim, no public full-corpus release, no model-quality improvement claim, no live-browser benchmark improvement claim, no evaluator metric change, no semantic-equivalence scoring, no slot normalization, and no prediction repair/re-score.
