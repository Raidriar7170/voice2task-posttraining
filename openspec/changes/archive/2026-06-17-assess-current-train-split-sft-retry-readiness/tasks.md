## 1. Readiness Inputs

- [x] 1.1 Add public-safe current-train-split SFT retry train/dev/test config templates with distinct runtime labels and private override placeholders.
- [x] 1.2 Add focused tests that the configs bind to `public-sample-20260616T165835Z`, require private overrides, and contain no private paths.
- [x] 1.3 Run a local dry-run on the current public train split and verify 118 selected rows plus repair-family coverage.

## 2. Readiness Evidence

- [x] 2.1 Add a report/CLI helper that writes current-train-split SFT retry readiness evidence.
- [x] 2.2 Generate the committed readiness-only evidence pack under `reports/public-sample/current-train-split-sft-retry-readiness/`.
- [x] 2.3 Generate `docs/human-briefs/2026-06-17-assess-current-train-split-sft-retry-readiness.html`.

## 3. Documentation

- [x] 3.1 Refresh `CONTEXT.md` with readiness status, current strict metric inputs, and next bounded retry guidance.
- [x] 3.2 Refresh `reports/final_status.md` with the readiness evidence and claim boundaries.

## 4. Validation And Archive

- [x] 4.1 Run focused readiness tests.
- [x] 4.2 Run full pytest, ruff, OpenSpec strict validation, leak scan, manifest count check, DPO pair count check, and `git diff --check`.
- [x] 4.3 Review the diff for overclaiming, private-path leakage, and unrelated changes.
- [x] 4.4 Archive the OpenSpec change if validation passes, then stage/commit/push under the guarded auto-integration policy.
