## 1. TDD And Diagnostic Surface

- [x] 1.1 Add failing tests for current-manifest runtime-label freshness, including stale prior runtime-label evidence and current learning-signal linkage.
- [x] 1.2 Add failing tests for bounded tiny-overfit recommendation and claim boundaries.
- [x] 1.3 Add failing tests for CLI/report generation and public-safe leak-scan behavior.

## 2. Implementation

- [x] 2.1 Implement the minimal diagnostic helper that reads the current manifest, latest learning-signal evidence, prior repair evidence, prior runtime-label artifacts, and prior tiny-overfit artifacts.
- [x] 2.2 Add CLI/report wiring that writes JSON and Markdown evidence under `reports/public-sample/runtime-label-tiny-overfit-diagnostic/`.
- [x] 2.3 Ensure the diagnostic never writes raw rendered prompts, raw assistant targets, private paths, raw logs, checkpoints, adapters, host details, SSH details, or private corpus rows.

## 3. Evidence And Human Brief

- [x] 3.1 Generate the public-safe runtime-label/tiny-overfit diagnostic evidence pack for `public-sample-20260613T072200Z`.
- [x] 3.2 Generate `docs/human-briefs/2026-06-13-run-bounded-runtime-label-or-tiny-overfit-diagnostic.html`.
- [x] 3.3 Generate phase, post-archive, and final leak-scan artifacts.

## 4. Validation And Review

- [x] 4.1 Run focused tests for the new diagnostic and report path.
- [x] 4.2 Run full validation: `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validate, DPO check, OpenSpec strict, leak scan, and `git diff --check`.
- [x] 4.3 Perform a read-only diff/evidence review for Must Fix issues and rerun affected validation.

## 5. Archive And Integration

- [x] 5.1 Archive the OpenSpec change after successful validation and rerun post-archive validation.
- [x] 5.2 Auto-stage and commit only in-scope phase files when guarded auto-integration remains safe.
