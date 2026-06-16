## 1. Readiness

- [x] 1.1 Verify repo state, source residual-cluster report, manifest id, top form-fill clusters, and prior form-fill remediation artifacts.
- [x] 1.2 Run an Explorer pass to identify existing helpers, tests, and public-safety constraints for form-fill bucket inspection.

## 2. Form-Fill Inspection

- [x] 2.1 Implement deterministic form-fill boundary and field-specificity bucket inspection from the committed residual-cluster report.
- [x] 2.2 Add a CLI or report entry point that writes JSON, Markdown, and manifest artifacts under `reports/public-sample/`.
- [x] 2.3 Generate the current form-fill inspection artifacts from `public-sample-20260616T022151Z`.

## 3. Reporting And Tests

- [x] 3.1 Add focused tests for bucket counts, source consistency, claim boundaries, and leak-scan public safety.
- [x] 3.2 Generate `docs/human-briefs/2026-06-16-inspect-form-fill-boundary-field-specificity.html`.
- [x] 3.3 Run focused tests, full tests, ruff, OpenSpec strict validation, leak scan, and `git diff --check`.
- [x] 3.4 Run a Reviewer pass and fix in-scope Must Fix items.
- [x] 3.5 Archive the OpenSpec change after tasks complete.
