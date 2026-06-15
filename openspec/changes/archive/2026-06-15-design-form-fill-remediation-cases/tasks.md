## 1. Case Design Logic

- [x] 1.1 Add a fail-closed `form_fill` remediation case-design generator that accepts only the existing plan-only artifact.
- [x] 1.2 Map the three remediation buckets to prompt/policy guidance and review-ready candidate case groups.

## 2. Reporting And CLI

- [x] 2.1 Add a public-safe report writer for JSON, Markdown, and manifest outputs.
- [x] 2.2 Add a `voice2task-eval design-form-fill-remediation-cases` CLI command.
- [x] 2.3 Generate committed evidence under `reports/public-sample/form-fill-remediation-case-design/`.
- [x] 2.4 Generate a concise Chinese Human Brief HTML for the phase.

## 3. Validation And Closeout

- [x] 3.1 Add focused tests for the generator, fail-closed behavior, CLI/report output, committed evidence, and public-safety boundaries.
- [x] 3.2 Run focused tests, full tests, ruff, OpenSpec strict validation, leak scan, and `git diff --check`.
- [x] 3.3 Archive the OpenSpec change after tasks complete.
