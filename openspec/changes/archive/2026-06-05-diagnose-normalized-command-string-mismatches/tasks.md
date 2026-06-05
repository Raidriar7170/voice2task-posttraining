## 1. Setup and Explorer

- [x] 1.1 Confirm branch, clean git status, no active OpenSpec conflicts, validation baseline, and local-only/no-A100 scope.
- [x] 1.2 Run Explorer read-only analysis for source evidence files, diagnosis counts, report targets, test entry points, and stop conditions.
- [x] 1.3 Validate the OpenSpec proposal/design/spec/tasks strictly before implementation.

## 2. Normalized-Command Diagnosis Evidence

- [x] 2.1 Add focused failing tests for the normalized-command helper/report and evidence-pack privacy/claim boundaries.
- [x] 2.2 Add a minimal derived diagnostic helper and report writer without changing evaluator metrics or prediction status.
- [x] 2.3 Generate `reports/public-sample/confirmation-rerun-normalized-command-string-mismatch-diagnosis/` from committed row-mismatch evidence only.
- [x] 2.4 Include machine-readable normalized-command comparisons, context counts, source artifact links, manifest, Markdown report, and leak-scan results.
- [x] 2.5 Ensure the diagnosis does not normalize, semantically score, repair, coerce, replace, or re-score predictions.

## 3. Documentation

- [x] 3.1 Generate a concise Chinese Human Brief HTML with project-stage progress, diagnosis result, evidence links, validation results, remaining risks, and recommended next step.

## 4. Validation, Review, Archive, and Integration

- [x] 4.1 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, rerun post-archive validation, generate loop closeout report, and apply guarded auto integration when safe.
