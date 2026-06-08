## 1. Data And Prompt Repair

- [x] 1.1 Add failing tests for a public-readonly search/weather DPO rejected contract that uses decomposed `city/date/topic` slots while the chosen contract keeps compact `slots.query`.
- [x] 1.2 Add failing tests for model-visible compact-query prompt guidance that explicitly rejects decomposed `city/date/topic` search slots without exposing row-specific gold targets in prediction prompts.
- [x] 1.3 Implement the minimal dataset-builder and prompt-policy changes to pass the new tests.
- [x] 1.4 Rebuild committed public sample SFT/DPO artifacts and manifest, preserving public-safe boundaries.

## 2. Evidence And Human Brief

- [x] 2.1 Generate `reports/public-sample/compact-query-slot-preservation/` with JSON/Markdown evidence, manifest, and leak scans.
- [x] 2.2 Generate `docs/human-briefs/2026-06-08-repair-compact-query-slot-preservation.html`.
- [x] 2.3 Add focused tests for evidence contents, privacy boundaries, DPO pair counts/categories, prompt metadata, source residual link, and no-overclaim wording.

## 3. Validation, Review, Archive

- [x] 3.1 Run focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak scans, `git diff --check`, and `openspec validate --all --strict`.
- [x] 3.2 Complete Reviewer pass, fix in-scope Must Fix items only, and rerun required validation.
- [x] 3.3 Archive the OpenSpec change, rerun post-archive validation, and commit the phase under guarded auto integration.
