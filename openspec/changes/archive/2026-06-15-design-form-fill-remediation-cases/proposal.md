## Why

The formal public held-out residual diagnosis selected `form_fill` as the first bounded remediation target, and the follow-up plan grouped its 29 strict residual rows into three actionable buckets: confirmation marker loss, field-name specificity drift, and clarify-boundary confusion.

Before any dataset materialization or A100 rerun, the project needs a reviewable, public-safe case-design artifact that turns those buckets into prompt/policy guidance and candidate example shapes while preserving the held-out boundary.

## What Changes

- Add a design-only `form_fill` remediation case generator that reads the existing plan artifact and emits reviewed case groups for the three residual buckets.
- Add a public-safe report writer, CLI command, committed evidence directory, tests, and Human Brief HTML for the case-design phase.
- Preserve current strict evaluation boundaries: no gold-label edits, no public-sample mutation, no materialized seed rows, no SFT/DPO/training run, no prediction rerun, no A100 job, and no evaluator metric relaxation.
- Keep `contract_exact_match` and strict `slot_f1` as primary; `slot_f1_soft` remains diagnostic-only.

## Capabilities

### New Capabilities

### Modified Capabilities
- `contract-evaluation`: Require a public-safe, design-only `form_fill` remediation case-design artifact before later materialization or training phases.

## Impact

- Affected code: `src/voice2task/evaluation.py`, `src/voice2task/reports.py`, and `src/voice2task/cli/eval.py`.
- Affected tests: new focused tests for the `form_fill` case-design generator, CLI, committed evidence, and public-safety boundaries.
- Affected reports: a new `reports/public-sample/form-fill-remediation-case-design/` evidence pack and one concise Human Brief HTML.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, checkpoint/adapter release claims, live-browser benchmark claims, dataset materialization, DPO, and A100 execution.
