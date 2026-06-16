## Why

The formal held-out residual cluster inspection shows the largest strict residual cluster is `form_fill / normalized_command` with 27 residual rows, followed by another `form_fill / slots` cluster with 16 residual rows. Before adding more data or running training again, the project needs a public-safe analysis that separates form-fill boundary errors, field-specificity errors, and harmless strict wording mismatches.

## What Changes

- Add a deterministic form-fill boundary and field-specificity inspection derived from the committed residual-cluster report.
- Classify form-fill residual examples into bounded diagnostic buckets such as missing confirmation wording, field alias drift, underspecified field labels, and route/task leakage.
- Publish JSON, Markdown, and manifest artifacts under `reports/public-sample/`.
- Generate a concise Human Brief for this phase.
- Preserve analysis-only boundaries: no new predictions, no SFT/DPO/GRPO training, no dataset mutation, no evaluator relaxation, no prediction repair/re-score, no checkpoint/adapter release, and no held-out recovery claim.

## Capabilities

### New Capabilities

### Modified Capabilities

- `contract-evaluation`: require a form-fill boundary/field-specificity inspection before recommending data, prompt, training, or evaluator changes for the top form-fill residual clusters.

## Impact

- Affected code: evaluation/report helpers and CLI entry point for the form-fill inspection.
- Affected reports: add a new public-safe form-fill inspection report under `reports/public-sample/`.
- Affected tests: add focused tests for bucket counts, source consistency, public-safety scanning, and claim boundaries.
- Affected specs: extend `contract-evaluation` with a form-fill inspection evidence requirement.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, any new prediction/training run, evaluator relaxation, prediction repair, checkpoint release, adapter release, production readiness, live-browser benchmark improvement, or private-corpus generalization claims.
