## 1. Readiness

- [x] 1.1 Verify repo state, active OpenSpec status, source form-fill inspection artifact, source manifest id, and current policy recommendation.
- [x] 1.2 Run an Explorer pass to identify existing helper, report, CLI, test, and public-safety patterns for a policy-only artifact.

## 2. Policy Artifact

- [x] 2.1 Add tests first for the form-fill confirmation and field-specificity policy artifact, including source manifest identity, bucket carry-forward, source consistency, unsupported changes, and claim boundaries.
- [x] 2.2 Implement deterministic policy generation from the committed form-fill boundary inspection JSON.
- [x] 2.3 Add a CLI/report entry point that writes JSON, Markdown, and manifest artifacts under `reports/public-sample/`.
- [x] 2.4 Generate the current form-fill policy artifacts from `public-sample-20260616T022151Z`.

## 3. Reporting And Validation

- [x] 3.1 Generate `docs/human-briefs/2026-06-16-define-form-fill-confirmation-field-policy.html`.
- [x] 3.2 Run focused tests, full tests, ruff, OpenSpec strict validation, leak scan, and `git diff --check`. Dataset building and DPO pair checks are not applicable because this phase does not change data or DPO generation.
- [x] 3.3 Run a Reviewer pass and fix in-scope Must Fix items.
- [x] 3.4 Archive the OpenSpec change after tasks complete and validations pass.
