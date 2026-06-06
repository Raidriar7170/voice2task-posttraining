## 1. Setup and Preflight

- [x] 1.1 Confirm clean `main`, no active OpenSpec changes, and latest A100 retry-wrapper rerun closeout commit.
- [x] 1.2 Inspect latest A100 generation trace, raw decoded summary, metadata, and retry-wrapper diagnosis.
- [x] 1.3 Validate the OpenSpec proposal/design/spec/tasks strictly before evidence generation.

## 2. Local Diagnosis Evidence

- [x] 2.1 Generate `reports/public-sample/retry-decoding-stop-boundary-diagnosis/` with diagnosis JSON/Markdown, manifest, and leak scans.
- [x] 2.2 Record observed facts: raw generation EOS observed, retry wrapper persisted, retry forbidden prefaces/trailing analysis visible, and retry generation trace missing.
- [x] 2.3 Record non-goals and claim boundaries: no A100 execution, no decoding change, no parser relaxation, no prediction repair, and no model recovery claim.

## 3. Tests and Human Brief

- [x] 3.1 Add focused tests for evidence shape, privacy boundaries, observed facts, evidence gaps, and non-claims.
- [x] 3.2 Generate a concise Chinese Human Brief HTML for this local diagnostic phase.

## 4. Validation, Review, Archive, and Integration

- [x] 4.1 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, rerun post-archive validation, generate/refresh final leak scans, and apply guarded auto integration when safe.
