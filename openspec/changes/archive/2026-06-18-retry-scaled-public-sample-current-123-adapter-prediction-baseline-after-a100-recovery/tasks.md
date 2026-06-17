## 1. Local Readiness

- [x] 1.1 Confirm the repo branch, worktree state, active OpenSpec change, target manifest id, and existing scaled-manifest prediction configs.
- [x] 1.2 Confirm the retry uses only `public-sample-20260617T152259Z` dev/test prediction configs and the existing `a100-current-train-split-sft-retry` adapter.

## 2. A100 Preflight

- [x] 2.1 Run a fresh read-only A100 connectivity, path, environment, adapter, and GPU occupancy preflight under the approved private A100 workspace boundary.
- [x] 2.2 If any preflight check is unsafe, write refreshed blocked evidence and do not start prediction.

## 3. Prediction-Only Execution

- [x] 3.1 Create private remote override configs outside git with resolved approved paths.
- [x] 3.2 Run dev and test prediction-only exports with `CUDA_VISIBLE_DEVICES` pinned to a safe GPU; do not launch training.
- [x] 3.3 Run strict dev and test evaluation with the existing evaluator and copy back only sanitized prediction, metadata, trace, prompt snapshot, metrics, and gold artifacts.

## 4. Public Evidence And Documentation

- [x] 4.1 Generate observed-or-blocked formal public held-out evidence under a new recovery-retry report directory, preserving comparison-boundary semantics.
- [x] 4.2 Update `CONTEXT.md`, `reports/final_status.md`, and a concise Chinese Human Brief with current status, strict metrics, boundaries, and remaining risks.
- [x] 4.3 Add or update focused tests for the new recovery-retry evidence and public-safe claim boundaries.

## 5. Validation And Archive

- [x] 5.1 Run focused tests, full pytest, ruff, `openspec validate --all --strict`, leak scans, and `git diff --check`.
- [x] 5.2 Archive the completed OpenSpec change and re-run validation affected by archive.
- [x] 5.3 Commit and push the guarded integration if the worktree is safe and validation passes.
