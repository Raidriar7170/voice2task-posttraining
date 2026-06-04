## 1. Rerun Setup

- [x] 1.1 Confirm worktree git status, branch, OpenSpec state, baseline evidence, and local validation before private execution.
- [x] 1.2 Identify the existing A100 access path and prior adapter reference without recording host/IP/private path details in committed artifacts.
- [x] 1.3 Prepare or reuse a repo-external private A100 prediction override under the approved private project root with explicit private-prediction opt-in.
- [x] 1.4 Confirm an idle A100 GPU and avoid interrupting other users' processes.

## 2. Strict-Retry A100 Prediction Execution

- [x] 2.1 Sync or use the current strict retry/canonical prediction code on A100.
- [x] 2.2 Run private-adapter prediction only on `prediction_split=train` with `schema_retry_enabled=true`, `overfit_diagnostic=true`, and `generalization_claim=false`.
- [x] 2.3 Preserve raw attempts, retry attempts, schema guard metadata, schema-invalid outputs, partial outputs, non-JSON outputs, path-like routes, and Markdown/prose-wrapped outputs as observed model evidence.

## 3. Public-Safe Evidence Pack

- [x] 3.1 Copy back only sanitized public-sample evidence into a new strict-retry rerun evidence directory.
- [x] 3.2 Generate metrics, schema guard summary, constrained decoding diagnosis, manifest, report, and comparison context against the prior required-field repair rerun.
- [x] 3.3 Run leak-scan over the new evidence pack and reject raw private rows, private paths, secrets, IPs, SSH details, raw logs, checkpoints, adapters, caches, and oversized generated corpora.
- [x] 3.4 Add or update focused tests if the rerun evidence, schema guard report shape, diagnosis shape, or manifest shape introduces new committed behavior.

## 4. Validation, Review, Archive, and Integration

- [x] 4.1 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Generate a concise Chinese Human Brief HTML with project-stage progress, observed metrics, A100 evidence links, validation results, and non-overclaim limits.
- [x] 4.3 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.4 Archive the OpenSpec change, rerun post-archive validation, update the loop report, and apply auto integration when safe.
