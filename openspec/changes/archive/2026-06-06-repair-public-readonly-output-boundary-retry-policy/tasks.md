## 1. Setup and Preflight

- [x] 1.1 Confirm clean `main`, no active OpenSpec changes, latest A100 evidence commit, and no A100 execution needed for this phase.
- [x] 1.2 Inspect the prior A100 public-readonly rerun diagnosis, prompt formatter, retry prompt, and validation tests.
- [x] 1.3 Validate the OpenSpec proposal/design/spec/tasks strictly before implementation.

## 2. Prompt and Retry Policy Repair

- [x] 2.1 Add failing tests for single-root JSON object guidance, retry-only JSON guidance, public-readonly `task_type="search"` guidance, and prompt-length guard.
- [x] 2.2 Implement the minimal prompt/retry wording changes without changing parser semantics or repairing predictions.
- [x] 2.3 Rerun focused tests and keep training/prediction prompt metadata public-safe.

## 3. Evidence and Briefs

- [x] 3.1 Generate `reports/public-sample/public-readonly-output-boundary-retry-policy/` with repair summary, manifest, and leak scans.
- [x] 3.2 Generate a concise Chinese Human Brief and loop closeout report.

## 4. Validation, Review, Archive, and Integration

- [x] 4.1 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, rerun post-archive validation, generate final loop closeout evidence, and apply guarded auto integration when safe.
