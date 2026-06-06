## 1. Setup and Preflight

- [x] 1.1 Confirm clean `main`, no active OpenSpec changes, latest A100 output-boundary retry-policy archive commit, and no A100 execution needed for this local phase.
- [x] 1.2 Inspect the prior A100 output-boundary diagnosis, retry prompt, schema guard tests, and local evidence patterns.
- [x] 1.3 Validate the OpenSpec proposal/design/spec/tasks strictly before implementation.

## 2. Retry Boundary Repair

- [x] 2.1 Add a failing focused test that requires explicit no-wrapper retry boundary language in `_schema_retry_prompt()`.
- [x] 2.2 Implement the minimal retry prompt wording change without changing strict parser semantics, evaluator metrics, or prediction artifacts.
- [x] 2.3 Rerun focused tests and confirm wrapped retry outputs remain rejected rather than repaired.

## 3. Evidence and Human Brief

- [x] 3.1 Generate `reports/public-sample/schema-retry-wrapper-boundary-policy/` with repair summary, manifest, and leak scans.
- [x] 3.2 Add focused evidence tests for prompt constraints, privacy boundaries, and no A100/training/parser/metric/repair claims.
- [x] 3.3 Generate a concise Chinese Human Brief HTML for this local phase.

## 4. Validation, Review, Archive, and Integration

- [x] 4.1 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, rerun post-archive validation, defer loop closeout evidence until a valid autonomous-loop stop condition, and apply guarded auto integration when safe.
