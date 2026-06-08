## 1. Scope And Proposal

- [x] 1.1 Confirm this is a local diagnosis phase that reuses the existing public-safe search-query slot rerun evidence and does not launch a new A100 run.
- [x] 1.2 Add OpenSpec proposal, design, spec deltas, and tasks for the wrapper-boundary diagnosis.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. TDD And Local Preparation

- [x] 2.1 Add failing focused tests for the wrapper-boundary diagnosis pack, observed wrapper facts, evidence gaps, source links, leak scans, and strict non-claims.
- [x] 2.2 Inspect the current search-query slot rerun evidence pack and the prior diagnosis/report artifacts that will serve as the only source inputs.

## 3. Local Diagnosis Evidence

- [x] 3.1 Generate `reports/public-sample/a100-search-query-slot-wrapper-boundary-diagnosis/` with diagnosis JSON/Markdown, manifest, and leak scans from existing sanitized artifacts only.
- [x] 3.2 Record observed facts: compact query content is visible in the decoded fragments, final outputs remain Markdown-wrapped, strict schema-valid output stays at `0/3`, and the wrapper origin remains unproven.
- [x] 3.3 Record non-goals and claim boundaries: no A100 execution, no training, no decoding change, no parser relaxation, no metric change, and no model-quality claim.

## 4. Tests And Human Brief

- [x] 4.1 Generate a concise Chinese Human Brief HTML for the local diagnosis phase.

## 5. Validation, Review, Archive, Integration

- [x] 5.1 Run focused tests, full pytest, ruff, mypy, public data validation, DPO check, leak scans, `git diff --check`, and OpenSpec strict validation.
- [x] 5.2 Complete Reviewer pass, fix Must Fix items only, archive the OpenSpec change, generate post-archive/final leak scans, rerun validation, and commit under guarded auto integration.
