## Why

The local `instrument-retry-generation-trace` phase added attempt-level `generation_trace.jsonl` rows for future trained-adapter prediction exports. The next bounded evidence question is whether a real A100 private-adapter prediction-only rerun now records retry attempt token/finish evidence for the same train split that previously lacked retry traces.

## What Changes

- Run one bounded A100 prediction-only train-split rerun with the current retry generation trace instrumentation.
- Preserve strict parser semantics, retry prompts, evaluator metrics, and invalid model outputs exactly as observed.
- Publish only public-safe predictions, metadata, prompt snapshot, raw decoded summary, generation trace, metrics, retry-trace diagnosis, manifest, report, Human Brief, and leak scans.
- Compare narrowly against the prior A100 schema retry wrapper-boundary rerun and the local instrumentation evidence.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add bounded A100 evidence that retry attempt generation trace rows are emitted in private-adapter prediction exports.
- `contract-evaluation`: publish public-safe retry trace rerun diagnostics without changing strict metrics or historical claims.

## Impact

- Affected runtime path: `voice2task.cli.train sft-predict` on A100 with a repo-external private adapter config and approved private output root.
- Affected evidence: `reports/public-sample/a100-retry-generation-trace-rerun/`.
- Affected tests: focused evidence boundary tests.
- Affected docs: OpenSpec archive and `docs/human-briefs/2026-06-06-run-a100-retry-generation-trace-rerun.html`.
- Non-goals: no SFT/DPO/GRPO training, no checkpoint or adapter release, no decoding behavior change, no retry prompt change, no parser relaxation, no evaluator metric change, no prediction repair/re-score, no semantic-equivalence scoring, no slot normalization, no held-out generalization claim, no model-quality claim, no production-readiness claim, no public full-corpus release, and no live-browser benchmark improvement claim.
