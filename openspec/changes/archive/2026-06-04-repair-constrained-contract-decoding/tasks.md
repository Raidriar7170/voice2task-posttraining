## 1. Setup and Diagnosis

- [x] 1.1 Confirm worktree git status, branch, OpenSpec state, and baseline validation.
- [x] 1.2 Inspect current retry prompt, schema guard, prediction sidecars, and required-field rerun evidence.
- [x] 1.3 Create a public-safe local diagnosis target for constrained decoding failure families.

## 2. Constrained Decoding Repair

- [x] 2.1 Add failing tests for canonical JSON-only retry prompt requirements and fail-closed invalid retry preservation.
- [x] 2.2 Implement the minimal retry prompt/output-shape repair without changing schema, metrics, or training.
- [x] 2.3 Add or update local diagnosis generation and evidence-boundary tests.

## 3. Evidence and Reporting

- [x] 3.1 Generate public-safe constrained decoding diagnosis artifacts under `reports/public-sample/`.
- [x] 3.2 Generate a concise Chinese Human Brief HTML with current model limitation, local repair scope, validation, and next-stage plan.
- [x] 3.3 Run leak-scan over diagnosis artifacts, Human Brief, and OpenSpec artifacts.

## 4. Validation, Review, Archive, and Integration

- [x] 4.1 Run focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, rerun post-archive validation, update the loop report, and apply auto integration when safe.
