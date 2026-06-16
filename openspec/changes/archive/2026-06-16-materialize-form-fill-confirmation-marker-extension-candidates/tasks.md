## 1. Readiness

- [x] 1.1 Verify repo state, active OpenSpec status, source extension design artifact, formal public sample immutability boundary, and no-training/no-prediction scope.
- [x] 1.2 Run an Explorer pass to identify existing candidate materialization, report, CLI, test, and public-safety patterns.

## 2. Candidate Materialization

- [x] 2.1 Add failing tests for confirmation-marker extension candidate materialization, including source design validation, exact candidate counts, seed/SFT shape, non-derivable field-label provenance, and formal public sample immutability.
- [x] 2.2 Implement deterministic materialization from the committed extension design into standalone candidate seed rows and candidate SFT rows.
- [x] 2.3 Add a `voice2task-data` CLI entry point and report writer that publish JSON, Markdown, manifest, seed, and SFT artifacts.
- [x] 2.4 Generate the current committed confirmation-marker extension candidate artifacts under `data/public-samples/` and `reports/public-sample/`.

## 3. Reporting And Validation

- [x] 3.1 Generate `docs/human-briefs/2026-06-16-materialize-form-fill-confirmation-marker-extension-candidates.html`.
- [x] 3.2 Run focused tests, related dataset/form-fill tests, full tests, ruff, OpenSpec strict validation, public dataset validation, DPO check on the unchanged formal public sample, leak scan, and `git diff --check`.
- [x] 3.3 Run a Reviewer pass and fix in-scope Must Fix items.
- [x] 3.4 Archive the OpenSpec change after tasks complete and validations pass.
