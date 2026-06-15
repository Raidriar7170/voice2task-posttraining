## 1. OpenSpec Readiness

- [x] 1.1 Create proposal, design, contract-evaluation delta spec, and task list for the residual diagnosis phase.
- [x] 1.2 Validate the OpenSpec change strictly before implementation.

## 2. Residual Diagnosis Implementation

- [x] 2.1 Add focused failing tests for merged slot-value residual classification and public-safety claim boundaries.
- [x] 2.2 Implement a diagnosis helper that compares gold contracts with prediction artifacts and classifies residuals by split, row id, task family, field path, category, and strict-vs-soft interpretation.
- [x] 2.3 Add a report/CLI entry point that writes public-safe JSON and Markdown diagnosis artifacts.

## 3. Evidence Generation

- [x] 3.1 Import or read ignored/private merged dev/test prediction artifacts only as local inputs and keep raw sidecars out of committed evidence.
- [x] 3.2 Generate the public-safe residual diagnosis report, manifest, and leak-scan result.
- [x] 3.3 Generate the Chinese Human Brief HTML for this phase.

## 4. Validation and Closeout

- [x] 4.1 Run focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair validation, public leak scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Run Reviewer review on the final diff and resolve in-scope Must Fix items.
- [x] 4.3 Archive the completed OpenSpec change and prepare guarded auto-integration.
