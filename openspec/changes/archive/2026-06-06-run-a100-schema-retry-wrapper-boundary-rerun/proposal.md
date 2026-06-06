## Why

The local `repair-schema-retry-wrapper-boundary` phase strengthened schema retry prompt wording after the prior A100 rerun showed retry completions containing `task_type="search"` but wrapped in prose/Markdown. The next bounded evidence question is whether this local retry-boundary prompt reaches the real A100 private-adapter prediction path and changes retry wrapper behavior on the same train split.

## What Changes

- Run one A100 prediction-only train-split rerun with the current schema retry wrapper-boundary prompt.
- Preserve strict parser semantics, evaluator metrics, and invalid model outputs exactly as observed.
- Publish only public-safe predictions, metadata, prompt snapshot, raw decoded summary, generation trace, metrics, diagnosis, manifest, report, and leak scans.
- Generate a concise Chinese Human Brief.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add bounded A100 evidence for retry wrapper-boundary prompt visibility in private-adapter prediction.
- `contract-evaluation`: publish public-safe rerun diagnostics comparing against the prior output-boundary A100 rerun and local retry-wrapper repair.

## Impact

- Affected evidence: `reports/public-sample/a100-schema-retry-wrapper-boundary-rerun/`.
- Affected tests: focused A100 evidence boundary tests.
- Affected docs: OpenSpec archive and `docs/human-briefs/`.
- Non-goals: no SFT/DPO/GRPO training, no checkpoint or adapter release, no parser relaxation, no evaluator metric change, no prediction repair/re-score, no semantic-equivalence scoring, no slot normalization, no held-out generalization claim, no model-quality claim, no production-readiness claim, and no live-browser benchmark improvement claim.
