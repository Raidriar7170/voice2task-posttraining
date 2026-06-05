## 1. Setup and Explorer

- [x] 1.1 Confirm branch, git status, OpenSpec state, explicit A100 authorization, and current validation baseline.
- [x] 1.2 Run Explorer read-only analysis for the A100 prediction-only command path, private override requirements, prior evidence, import targets, and stop conditions.
- [x] 1.3 Confirm the A100 SSH alias and approved private project root without committing or documenting private host details.

## 2. A100 Prediction-Only Execution

- [x] 2.1 Prepare or reuse a repo-external private A100 prediction override under the approved private project root with `allow_private_prediction=true`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and `schema_retry_enabled=true`.
- [x] 2.2 Sync the current repo state to the approved A100 project root without copying committed evidence back into private logs or exposing secrets.
- [x] 2.3 Confirm an idle A100 GPU and avoid interrupting other users' processes.
- [x] 2.4 Run `voice2task.cli.train sft-predict` in prediction-only mode using the existing private adapter and current confirmation-required prompt code.
- [x] 2.5 Keep raw logs, private overrides, model caches, checkpoints, adapters, host details, SSH details, private paths, tokens, and private corpus rows out of git.

## 3. Sanitized Evidence and Documentation

- [x] 3.1 Import only sanitized public-safe evidence into `reports/public-sample/a100-confirmation-required-train-split-rerun/`.
- [x] 3.2 Generate metrics, schema guard summary, confirmation-required diagnosis, manifest, report Markdown, and leak-scan results that separate raw attempt, retry attempt, validated output source, missing `confirmation_required`, prompt constraints, and final metrics.
- [x] 3.3 Generate a concise Chinese Human Brief HTML with project-stage progress, A100 result, evidence links, validation results, remaining risks, and recommended next step.

## 4. Validation, Review, Archive, and Integration

- [x] 4.1 Run fresh validation: focused A100 evidence tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, rerun post-archive validation, generate loop closeout report, and apply guarded auto integration when safe.
