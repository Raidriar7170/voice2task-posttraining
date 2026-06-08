## 1. Baseline And TDD

- [x] 1.1 Inspect current first-pass decoding, retry decoding, strict parser behavior, metadata propagation, and prior A100 wrapper-persistence evidence.
- [x] 1.2 Add focused failing tests for generation-time Markdown fence suppression wiring, metadata propagation, and strict rejection of fenced JSON fragments.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Decoding Policy Implementation

- [x] 2.1 Implement tokenizer-derived Markdown fence suppression token sequence construction without hardcoding tokenizer ids.
- [x] 2.2 Pass suppression sequences to real trained-adapter prediction generation when available.
- [x] 2.3 Expose suppression policy in prediction metadata and prompt snapshots without changing parser, evaluator, retry, or prediction repair semantics.

## 3. Local Evidence And Human Brief

- [x] 3.1 Generate `reports/public-sample/first-pass-markdown-fence-suppression/` with summary JSON/Markdown, manifest, source links, validation notes, and leak scans.
- [x] 3.2 Generate `docs/human-briefs/2026-06-08-repair-first-pass-markdown-fence-suppression.html` with status, evidence links, validation, risks, and recommended next step.
- [x] 3.3 Ensure evidence states no A100 execution, no training, no parser relaxation, no prediction repair, no metric reinterpretation, and no model-quality claim.

## 4. Validation, Review, Archive, Integration

- [x] 4.1 Run focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, public leak scans, `git diff --check`, and `openspec validate --all --strict`.
- [x] 4.2 Complete Reviewer pass, fix in-scope Must Fix items only, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, generate post-archive/final leak scans when applicable, rerun post-archive validation, and commit the phase under guarded auto integration.
