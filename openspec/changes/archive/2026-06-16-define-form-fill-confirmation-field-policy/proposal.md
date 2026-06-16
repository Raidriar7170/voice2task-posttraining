## Why

The current form-fill residual inspection shows the largest remaining form-fill buckets are missing confirmation wording and field specificity or alias drift. Before changing labels, prompts, training data, or evaluator behavior, the project needs a public-safe policy artifact that states how these residual surfaces should be interpreted and what future remediation is allowed to change.

## What Changes

- Add a deterministic form-fill confirmation and field-specificity policy definition derived from the committed form-fill boundary inspection report.
- Publish JSON, Markdown, and manifest artifacts under `reports/public-sample/` that record policy sections, supporting bucket evidence, explicit non-authorized changes, and recommended next actions.
- Generate a concise Human Brief for this policy-definition phase.
- Preserve policy-only boundaries: no new prediction run, no SFT/DPO/GRPO training, no dataset mutation, no prompt change, no evaluator relaxation, no prediction repair/re-score, no checkpoint/adapter release, and no held-out recovery claim.

## Capabilities

### New Capabilities

### Modified Capabilities

- `contract-evaluation`: require a public-safe form-fill confirmation and field-specificity policy artifact before any future data, prompt, training, or evaluator remediation for the observed form-fill residual buckets.

## Impact

- Affected code: evaluation/report helpers and CLI entry point for the form-fill policy artifact.
- Affected reports: add a new public-safe policy report under `reports/public-sample/`.
- Affected tests: add focused tests for source evidence consistency, policy boundaries, unsupported changes, and public-safety scanning.
- Affected specs: extend `contract-evaluation` with a form-fill policy evidence requirement.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, any new prediction/training run, evaluator relaxation, prediction repair, checkpoint release, adapter release, production readiness, live-browser benchmark improvement, private-corpus generalization, or public full-corpus release claims.
