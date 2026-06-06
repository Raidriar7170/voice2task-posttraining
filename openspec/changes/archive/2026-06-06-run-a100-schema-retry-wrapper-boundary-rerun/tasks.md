## 1. Setup and Preflight

- [x] 1.1 Confirm clean `main`, no active OpenSpec changes, latest retry-wrapper repair commit, and A100 standing authorization under repo rules.
- [x] 1.2 Validate the OpenSpec proposal/design/spec/tasks strictly before remote execution.

## 2. A100 Prediction Rerun

- [x] 2.1 Prepare or locate a repo-external private A100 override under the approved private A100 project root without copying private details into git.
- [x] 2.2 Inspect GPU/process occupancy with `nvidia-smi`, select an idle A100 without interrupting other users, and run one prediction-only `voice2task.cli.train sft-predict` train-split rerun with explicit `CUDA_VISIBLE_DEVICES`.
- [x] 2.3 Preserve remote raw logs/configs/checkpoints/adapters/caches outside git and bring back only sanitized prediction rows plus public-safe sidecars.

## 3. Evidence and Diagnostics

- [x] 3.1 Generate `reports/public-sample/a100-schema-retry-wrapper-boundary-rerun/` with predictions, metadata, prompt snapshot, raw decoded summary, generation trace, train-split gold rows, metrics, schema guard summary, retry-wrapper diagnosis, manifest, report, and leak scans.
- [x] 3.2 Add focused tests for evidence shape, privacy boundaries, strict metrics, prompt/retry wrapper constraints, row-level counts, and no semantic-equivalence/slot-normalization/re-score claims.
- [x] 3.3 Generate a concise Chinese Human Brief HTML.

## 4. Validation, Review, Archive, and Integration

- [x] 4.1 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak-scan, `git diff --check`, and `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, rerun post-archive validation, defer loop closeout evidence until a valid autonomous-loop stop condition, and apply guarded auto integration when safe.
