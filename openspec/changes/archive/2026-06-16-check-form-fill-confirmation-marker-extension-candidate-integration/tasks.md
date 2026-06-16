## 1. Readiness

- [x] 1.1 Verify repo state, active OpenSpec status, source candidate seed artifact, formal public sample immutability boundary, and preview-only scope.
- [x] 1.2 Run an Explorer pass or local pattern review for existing preview integration, report, CLI, test, and public-safety patterns.

## 2. Preview Integration

- [x] 2.1 Add failing tests for confirmation-marker extension candidate preview integration, including candidate validation, preview counts, preview validation status, formal public sample immutability, and public-safety claims.
- [x] 2.2 Implement fail-closed validation for the 12 standalone extension candidate seed rows.
- [x] 2.3 Implement a report-scoped preview integration check that combines formal seed rows with extension candidate rows and validates preview SFT/DPO/manifest artifacts.
- [x] 2.4 Add a `voice2task-data` CLI entry point and report writer that publish JSON, Markdown, and manifest preview evidence.
- [x] 2.5 Generate the current committed preview evidence under `reports/public-sample/form-fill-confirmation-marker-extension-candidate-integration-preview/`.

## 3. Reporting And Validation

- [x] 3.1 Generate `docs/human-briefs/2026-06-16-check-form-fill-confirmation-marker-extension-candidate-integration.html`.
- [x] 3.2 Run focused tests, related dataset/form-fill tests, full tests, ruff, OpenSpec strict validation, public dataset validation, DPO check on the unchanged formal public sample, leak scan, and `git diff --check`.
- [x] 3.3 Run a Reviewer pass and fix in-scope Must Fix items.
- [x] 3.4 Archive the OpenSpec change after tasks complete and validations pass.
