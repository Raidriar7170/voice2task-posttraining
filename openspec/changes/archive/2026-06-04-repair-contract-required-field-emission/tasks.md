## 1. Scope and Tests

- [x] 1.1 Confirm branch, git status, OpenSpec state, and relevant prediction/prompt entry points.
- [x] 1.2 Add focused tests for required-field prompt skeleton visibility without gold contract leakage.
- [x] 1.3 Add focused tests for schema-validation guard/retry metadata on invalid and valid private-adapter prediction attempts.

## 2. Implementation

- [x] 2.1 Strengthen the shared SFT prompt with a complete Browser Task Contract skeleton and required-field checklist.
- [x] 2.2 Add bounded schema-validation guard/retry helpers that reuse `BrowserTaskContract.from_dict`.
- [x] 2.3 Wire guard/retry metadata into private-adapter prediction export without changing fixture-mode evidence semantics.

## 3. Evidence and Human Brief

- [x] 3.1 Generate public-safe local repair evidence or metadata summary for the prompt/guard repair phase.
- [x] 3.2 Generate a concise Chinese Human Brief HTML with project-stage progress, validation results, and non-overclaim limits.
- [x] 3.3 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.

## 4. Review, Archive, and Integration

- [x] 4.1 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.2 Archive the OpenSpec change, rerun post-archive validation, update the loop report, and apply auto integration when safe.
