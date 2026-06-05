## 1. Scope And Proposal

- [x] 1.1 Confirm this is a local evidence-only phase with no A100 execution.
- [x] 1.2 Add OpenSpec proposal, design, spec delta, and tasks for the narrow row-level diagnosis.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Implementation

- [x] 2.1 Add focused tests for normalized-rerun row-mismatch evidence, privacy boundaries, family counts, source strict metrics, and no semantic-equivalence/no-repair claims.
- [x] 2.2 Add a narrow helper/report writer for normalized-command policy rerun row-mismatch diagnosis without relabeling it as the prior confirmation rerun.
- [x] 2.3 Generate `reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis/` from prior public-safe artifacts only.
- [x] 2.4 Generate leak-scan result artifacts and a concise Chinese Human Brief.

## 3. Validation And Closeout

- [x] 3.1 Run focused tests for the new evidence pack.
- [x] 3.2 Run full local validation: pytest, ruff, mypy, data validation, DPO check, leak scan, diff whitespace check, and OpenSpec strict validation.
- [x] 3.3 Review the diff, fix must-fix findings, archive the OpenSpec change, and rerun post-archive validation.
