## 1. Scope And Proposal

- [x] 1.1 Confirm this is local prompt/policy hardening only with no A100 execution.
- [x] 1.2 Add OpenSpec proposal, design, spec deltas, and tasks.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Implementation

- [x] 2.1 Add focused failing tests for public-readonly search policy visibility in training and prediction prompts.
- [x] 2.2 Add focused failing tests for prompt constraint metadata and evidence-pack privacy/claim boundaries.
- [x] 2.3 Implement the minimal shared prompt and metadata changes without adding row-specific gold contracts.
- [x] 2.4 Generate `reports/public-sample/public-readonly-search-contract-policy/` from local prompt metadata and prior public row-mismatch evidence only.
- [x] 2.5 Generate leak-scan artifacts and a concise Chinese Human Brief.

## 3. Validation And Closeout

- [x] 3.1 Run focused tests for prompt policy and evidence pack.
- [x] 3.2 Run full local validation: pytest, ruff, mypy, data validation, DPO check, leak scan, diff whitespace check, and OpenSpec strict validation.
- [x] 3.3 Review the diff, fix must-fix findings, archive the OpenSpec change, and rerun post-archive validation.
