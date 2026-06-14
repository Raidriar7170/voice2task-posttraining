## 1. Proposal and Contract

- [x] 1.1 Add OpenSpec proposal, design, task list, and contract-evaluation spec delta for targeted slot value residual diagnosis.
- [x] 1.2 Validate the OpenSpec change strictly before implementation.

## 2. Local Diagnosis Implementation

- [x] 2.1 Add RED tests for residual taxonomy, CLI output, committed evidence, and non-claim boundaries.
- [x] 2.2 Add diagnosis logic that classifies the targeted probe dev/test value residuals without changing predictions or metrics.
- [x] 2.3 Add a public-safe report writer and CLI command.

## 3. Evidence and Brief

- [x] 3.1 Generate committed public-safe residual diagnosis JSON, Markdown, and manifest artifacts.
- [x] 3.2 Generate a concise Chinese Human Brief with status, metrics, residual taxonomy, boundaries, and recommended next step.

## 4. Validation and Closeout

- [x] 4.1 Run focused pytest, related regression tests, OpenSpec validation, leak scans, and `git diff --check`.
- [x] 4.2 Run a reviewer pass over the diff and fix Must Fix items in scope.
- [x] 4.3 Archive the change if complete and apply guarded auto integration.
