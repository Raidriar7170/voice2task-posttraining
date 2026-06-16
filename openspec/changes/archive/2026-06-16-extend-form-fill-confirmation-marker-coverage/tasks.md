## 1. Readiness

- [x] 1.1 Verify repo state, active OpenSpec status, source coverage artifact, source policy artifact, and no-mutation boundaries.
- [x] 1.2 Run an Explorer pass to identify existing helper, report, CLI, test, and public-safety patterns for confirmation-marker extension design.

## 2. Extension Design

- [x] 2.1 Add tests first for the confirmation-marker extension design, including source artifact identity, source-family coverage, proposed case shape, source count consistency, and no-recovery/no-mutation boundaries.
- [x] 2.2 Implement deterministic extension design from committed coverage and policy artifacts.
- [x] 2.3 Add a CLI/report entry point that writes JSON, Markdown, and manifest artifacts under `reports/public-sample/`.
- [x] 2.4 Generate the current confirmation-marker extension design artifacts. Dataset building and DPO pair checks are not applicable because this phase must not materialize candidate rows or mutate DPO artifacts.

## 3. Reporting And Validation

- [x] 3.1 Generate `docs/human-briefs/2026-06-16-extend-form-fill-confirmation-marker-coverage.html`.
- [x] 3.2 Run focused tests, full tests, ruff, OpenSpec strict validation, leak scan, and `git diff --check`.
- [x] 3.3 Run a Reviewer pass and fix in-scope Must Fix items.
- [x] 3.4 Archive the OpenSpec change after tasks complete and validations pass.
