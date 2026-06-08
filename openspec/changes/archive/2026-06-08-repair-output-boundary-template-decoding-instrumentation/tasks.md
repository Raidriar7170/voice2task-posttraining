## 1. Baseline And TDD

- [x] 1.1 Inspect current first-pass prediction prompt, retry boundary metadata, strict parser behavior, and prior A100 wrapper-boundary evidence.
- [x] 1.2 Add focused failing tests for first-pass output-boundary visibility, metadata propagation, and strict rejection of wrapped first-pass JSON fragments.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Prompt And Metadata Implementation

- [x] 2.1 Strengthen first-pass prediction prompt output-boundary clauses without changing parser, evaluator, retry, training, or prediction repair behavior.
- [x] 2.2 Add first-pass output-boundary summary metadata to prediction metadata and prompt snapshots.
- [x] 2.3 Run focused tests and confirm RED-to-GREEN behavior.

## 3. Local Evidence And Human Brief

- [x] 3.1 Generate `reports/public-sample/repair-output-boundary-template-decoding-instrumentation/` with summary JSON/Markdown, manifest, source links, validation notes, and leak scans.
- [x] 3.2 Generate `docs/human-briefs/2026-06-08-repair-output-boundary-template-decoding-instrumentation.html` with current status, evidence links, validation, risks, and recommended next step.
- [x] 3.3 Ensure evidence states no A100 execution, no training, no parser relaxation, no prediction repair, no metric reinterpretation, and no model-quality claim.

## 4. Validation, Review, Archive, Integration

- [x] 4.1 Run focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, public leak scans, `git diff --check`, and `openspec validate --all --strict`.
- [x] 4.2 Complete Reviewer pass in the main thread, fix in-scope Must Fix items only, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, generate post-archive/final leak scans when applicable, rerun post-archive validation, and commit the phase under guarded auto integration.
