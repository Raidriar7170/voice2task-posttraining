## 1. Retry Preflight

- [x] 1.1 Validate the OpenSpec retry change and confirm local git status.
- [x] 1.2 Verify A100 SSH connectivity without recording private endpoint details.
- [x] 1.3 Inspect GPU/process occupancy and select a safe idle GPU.
- [x] 1.4 Verify approved remote root, disk/cache/temp placement, repo snapshot, and manifest counts.

## 2. Private A100 Execution

- [x] 2.1 Create repo-external private override files under the approved A100 root.
- [x] 2.2 Run SFT v3 training on the selected GPU with the current public train split.
- [x] 2.3 Run dev prediction-only generation with the new private adapter.
- [x] 2.4 Run test prediction-only generation with the new private adapter.
- [x] 2.5 Run strict dev/test evaluation on the generated predictions.

## 3. Evidence Import

- [x] 3.1 Import only sanitized metadata, metrics, manifests, and reports into a new retry evidence directory.
- [x] 3.2 Generate a concise Chinese Human Brief.
- [x] 3.3 Refresh `CONTEXT.md` and `reports/final_status.md` with observed/blocked retry status and strict metric boundaries.

## 4. Validation And Archive

- [x] 4.1 Run focused evidence tests or add them if report shape changes.
- [x] 4.2 Run full tests, ruff, OpenSpec strict validation, leak scan, manifest count check, DPO pair count check, and `git diff --check`.
- [x] 4.3 Review the diff for overclaiming, private-path leakage, and unrelated changes.
- [x] 4.4 Archive the OpenSpec change if validation passes.
