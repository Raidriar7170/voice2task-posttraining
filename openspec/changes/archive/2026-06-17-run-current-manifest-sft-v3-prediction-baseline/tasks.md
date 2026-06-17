## 1. Readiness

- [x] 1.1 Validate repo status, current manifest id/counts, SFT v3 prediction configs, existing SFT v3 adapter evidence, and output directory plan.
- [x] 1.2 Add/verify report-writer coverage for recording `source_adapter_runtime=a100-form-fill-remediation-sft-v3`.
- [x] 1.3 Inspect A100 GPU/process occupancy and private SFT v3 adapter availability under the approved private root before launching prediction.

## 2. Prediction-Only Execution

- [x] 2.1 Prepare repo-external private A100 dev/test prediction overrides resolving placeholders to approved private paths.
- [x] 2.2 Run dev prediction-only export with explicit `CUDA_VISIBLE_DEVICES`, no training flags, and sanitized sidecars.
- [x] 2.3 Run test prediction-only export with explicit `CUDA_VISIBLE_DEVICES`, no training flags, and sanitized sidecars.
- [x] 2.4 Run strict dev/test evaluation on generated predictions.

## 3. Public Evidence

- [x] 3.1 Import sanitized dev/test predictions, prediction metadata, sidecars, metrics, manifest, report, and leak scan results into a new current-manifest evidence directory.
- [x] 3.2 Refresh `CONTEXT.md` and `reports/final_status.md` with current-manifest prediction-only results and comparison-boundary wording.
- [x] 3.3 Generate `docs/human-briefs/2026-06-17-run-current-manifest-sft-v3-prediction-baseline.html`.

## 4. Validation And Archive

- [x] 4.1 Run focused tests for report shape and committed evidence boundaries.
- [x] 4.2 Run full pytest, ruff, OpenSpec strict validation, leak scan, manifest count check, DPO pair count check, and `git diff --check`.
- [x] 4.3 Review the diff for overclaiming, private-path leakage, and unrelated changes.
- [x] 4.4 Archive the OpenSpec change if validation passes, then stage/commit/push under the guarded auto-integration policy.
