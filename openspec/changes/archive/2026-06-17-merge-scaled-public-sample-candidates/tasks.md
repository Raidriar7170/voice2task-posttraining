## 1. Formal Merge Implementation

- [x] 1.1 Add scaled candidate validation and formal provenance promotion helpers.
- [x] 1.2 Add a guarded `merge_scaled_public_sample_candidates_into_public_sample` dataset helper.
- [x] 1.3 Extend formal manifest source summary with scaled candidate counts, group counts, family counts, split counts, and comparison-boundary warning.

## 2. CLI And Evidence

- [x] 2.1 Add `merge-scaled-public-sample-candidates` CLI support.
- [x] 2.2 Add fail-closed merge evidence generation and report writing under `reports/public-sample/scaled-public-sample-merge/`.
- [x] 2.3 Rebuild formal public sample artifacts from the promoted seed file.

## 3. Tests And Documentation

- [x] 3.1 Add focused tests for counts, provenance, duplicate/unreviewed rejection, CLI evidence, committed artifacts, and fail-closed claims.
- [x] 3.2 Update candidate materialization tests for the new post-merge formal boundary.
- [x] 3.3 Update `CONTEXT.md`, `reports/final_status.md`, OpenSpec spec, and Human Brief.

## 4. Validation And Archive

- [x] 4.1 Run focused pytest, full pytest, ruff, public data validate, DPO check, OpenSpec strict validation, leak scan, and `git diff --check`.
- [x] 4.2 Archive the OpenSpec change after validation succeeds.
