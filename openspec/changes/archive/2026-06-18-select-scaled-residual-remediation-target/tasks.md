## 1. Readiness

- [x] 1.1 Confirm the scaled residual-cluster inspection exists, is leak-clean, and targets `public-sample-20260617T152259Z`.
- [x] 1.2 Confirm this phase will read committed cluster artifacts only and will not launch A100, train, predict, mutate data, materialize data, or change evaluator semantics.

## 2. Target Selection Evidence

- [x] 2.1 Implement or reuse a bounded selector that reads scaled cluster-inspection evidence and chooses one first remediation target.
- [x] 2.2 Generate target-selection artifacts under `reports/public-sample/scaled-residual-remediation-target-selection/`.
- [x] 2.3 Ensure the artifacts record selected target, deferred targets, strict metric boundary, source cluster-inspection link, and diagnosis-only claim boundaries.

## 3. Documentation And Tests

- [x] 3.1 Update `CONTEXT.md`, `reports/final_status.md`, and a concise Chinese Human Brief with the selected target and next recommended phase.
- [x] 3.2 Add focused tests for source boundary, selected target, deferred safety rationale, claim boundaries, output-directory manifest paths, and leak-scan status.

## 4. Validation And Archive

- [x] 4.1 Run focused tests, full pytest, ruff, `openspec validate --all --strict`, leak scans, and `git diff --check`.
- [x] 4.2 Archive the completed OpenSpec change and re-run validation affected by archive.
- [x] 4.3 Commit and push the guarded integration if the worktree is safe and validation passes.
