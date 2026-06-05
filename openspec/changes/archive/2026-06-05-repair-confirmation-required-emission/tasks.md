## 1. Scope and Regression Tests

- [x] 1.1 Confirm branch, git status, OpenSpec state, and relevant prompt/diagnostic entry points.
- [x] 1.2 Add focused failing tests for `confirmation_required` visibility in shared SFT training text and trained-adapter prediction prompts.
- [x] 1.3 Add focused failing tests for low-risk weather/search examples containing `"confirmation_required": false`.
- [x] 1.4 Add focused failing tests or diagnostics coverage for reporting missing `confirmation_required` counts without repairing predictions.

## 2. Implementation

- [x] 2.1 Strengthen the shared contract prompt/example surface so `confirmation_required` is a required boolean field and low-risk search examples set it to `false`.
- [x] 2.2 Implement or adjust public-safe diagnostic/evidence code to expose missing `confirmation_required` counts while preserving invalid prediction status.
- [x] 2.3 Generate local public-safe evidence or metadata summary for the confirmation-required repair phase.

## 3. Human Brief and Validation

- [x] 3.1 Generate a concise Chinese Human Brief HTML with project-stage progress, key files, validation results, and non-overclaim limits.
- [x] 3.2 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.

## 4. Review, Archive, and Integration

- [x] 4.1 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.2 Archive the OpenSpec change, rerun post-archive validation, update the loop report, and apply guarded auto integration when safe.
