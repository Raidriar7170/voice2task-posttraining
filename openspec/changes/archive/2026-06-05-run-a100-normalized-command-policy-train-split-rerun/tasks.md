## 1. Setup and Preflight

- [x] 1.1 Confirm branch, clean git status, no active OpenSpec conflicts, latest local archive commit, and explicit A100 approval.
- [x] 1.2 Run read-only Explorer over prior A100 rerun commands, evidence shape, tests, and validation entry points.
- [x] 1.3 Validate the OpenSpec proposal/design/spec/tasks strictly before remote execution.

## 2. A100 Prediction Rerun

- [x] 2.1 Prepare a repo-external private A100 override under the approved private A100 project root that resolves output root, base model, and existing private adapter path without copying private details into git.
- [x] 2.2 Select an idle A100 GPU without interrupting other users and run one prediction-only `voice2task.cli.train sft-predict` train-split rerun.
- [x] 2.3 Preserve remote raw logs/configs/checkpoints/adapters/caches outside git and bring back only sanitized prediction rows plus public-safe sidecars.

## 3. Evidence and Diagnostics

- [x] 3.1 Generate `reports/public-sample/a100-normalized-command-policy-train-split-rerun/` with predictions, metadata, prompt snapshot, raw decoded summary, generation trace, train-split gold rows, metrics, normalized-command diagnosis, manifest, report, and leak scans.
- [x] 3.2 Add focused tests for evidence shape, privacy boundaries, normalized-command exact-string counts, strict metrics, prompt-policy visibility, and no semantic-equivalence/re-score claims.
- [x] 3.3 Generate a concise Chinese Human Brief HTML and autonomous loop closeout HTML for this A100 phase.

## 4. Validation, Review, Archive, and Integration

- [x] 4.1 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, rerun post-archive validation, generate final loop closeout evidence, and apply guarded auto integration when safe.
