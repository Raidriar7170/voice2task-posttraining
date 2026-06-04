## 1. Evidence Analysis

- [x] 1.1 Confirm branch, git status, OpenSpec state, and source evidence files.
- [x] 1.2 Analyze predictions, raw decoded summary, generation trace, metrics, manifest, and prompt snapshot without using private runtime artifacts.
- [x] 1.3 Identify aggregate and row-level failure patterns, including raw JSON parseability, missing required fields, and field mismatches.

## 2. Public-Safe Artifacts

- [x] 2.1 Generate a machine-readable schema-output diagnosis JSON artifact.
- [x] 2.2 Generate a short Markdown diagnosis report with claim boundaries and recommended next bounded phase.
- [x] 2.3 Run leak-scan over the new diagnosis artifacts and relevant public surfaces.

## 3. Regression Coverage and Human Brief

- [x] 3.1 Add focused regression coverage for the diagnosis artifact and report wording.
- [x] 3.2 Generate a concise Chinese Human Brief HTML with project-stage progress and evidence links.
- [x] 3.3 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.

## 4. Review, Archive, and Integration

- [x] 4.1 Run a focused diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.2 Archive the OpenSpec change, rerun post-archive validation, update the loop report, and apply auto integration when safe.
