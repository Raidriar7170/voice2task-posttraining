## 1. Runtime Readiness

- [x] 1.1 Verify local repo state, current manifest id, dev/test split counts, and prediction configs.
- [x] 1.2 Inspect A100 GPU/process occupancy and select an idle GPU only if safe.
- [x] 1.3 Prepare private runtime overrides on the A100 machine under the authorized private A100 workspace without committing private paths.

## 2. Prediction-Only Evidence

- [x] 2.1 Run dev split prediction-only export with the existing private adapter and updated formal public manifest.
- [x] 2.2 Run test split prediction-only export with the existing private adapter and updated formal public manifest.
- [x] 2.3 Run strict metrics plus schema, constrained-decoding, alignment, and residual diagnostics for both splits.
- [x] 2.4 Import only sanitized public evidence into `reports/public-sample/a100-formal-public-heldout-prediction/`.

## 3. Reporting And Tests

- [x] 3.1 Refresh or add focused tests for the new observed manifest id, split counts, metrics, evidence boundaries, and residual-family reporting.
- [x] 3.2 Generate `docs/human-briefs/2026-06-16-evaluate-form-fill-remediation-heldout.html`.
- [x] 3.3 Run formal public validation, focused tests, full tests, ruff, OpenSpec strict validation, leak scan, and `git diff --check`.
- [x] 3.4 Run a Reviewer pass and fix in-scope Must Fix items.
- [x] 3.5 Archive the OpenSpec change after tasks complete.
