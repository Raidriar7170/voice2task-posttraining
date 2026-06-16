## 1. Evidence Refresh

- [x] 1.1 Regenerate formal residual-family diagnosis from `a100-formal-public-heldout-prediction-after-a100-recovery`.
- [x] 1.2 Regenerate formal remediation target-selection from the refreshed diagnosis.
- [x] 1.3 Confirm refreshed artifacts record manifest `public-sample-20260616T074315Z`.
- [x] 1.4 Regenerate formal residual-cluster inspection from the refreshed diagnosis.
- [x] 1.5 Refresh confirmation-marker coverage source evidence to point at the current residual-cluster source while preserving legacy policy provenance.

## 2. Tests

- [x] 2.1 Update residual-family diagnosis tests to use the current recovery evidence path and manifest id.
- [x] 2.2 Update target-selection tests or assertions so committed artifacts cannot point at stale evidence.
- [x] 2.3 Run focused tests for formal residual diagnosis and target selection.
- [x] 2.4 Update residual-cluster inspection assertions so committed artifacts cannot point at stale evidence.
- [x] 2.5 Update downstream form-fill coverage assertions so current residual evidence and legacy remediation provenance stay distinct.

## 3. Human Brief

- [x] 3.1 Add a concise Chinese Human Brief under `docs/human-briefs/`.
- [x] 3.2 State that this phase is diagnosis-only and does not train, mutate data, or change metrics.
- [x] 3.3 Update `CONTEXT.md` and `reports/final_status.md` so they no longer recommend the now-completed residual diagnosis as the next step.

## 4. Validation and Closeout

- [x] 4.1 Run full tests with the supported Python >=3.10 interpreter.
- [x] 4.2 Run `ruff`, `openspec validate --all --strict`, leak scan, and `git diff --check`.
- [x] 4.3 Archive the OpenSpec change if all tasks complete.
