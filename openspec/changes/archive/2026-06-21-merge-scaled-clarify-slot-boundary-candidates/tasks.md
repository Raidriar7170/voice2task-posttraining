## 1. Formal Merge Implementation

- [ ] 1.1 Add scaled clarify candidate validation and formal provenance promotion helpers.
- [ ] 1.2 Add a guarded `merge_scaled_clarify_slot_boundary_candidates_into_public_sample` dataset helper.
- [ ] 1.3 Extend formal manifest source summary with candidate seed/SFT counts, split counts, source manifest ids, source artifact identity, and comparison-boundary warning.

## 2. CLI And Evidence

- [ ] 2.1 Add `merge-scaled-clarify-slot-boundary-candidates` CLI support.
- [ ] 2.2 Add fail-closed merge evidence generation and report writing under `reports/public-sample/scaled-clarify-slot-boundary-public-sample-merge/`.
- [ ] 2.3 Rebuild formal public sample artifacts from the promoted seed file.

## 3. Tests And Documentation

- [ ] 3.1 Add focused tests for counts, provenance, candidate rejection, CLI evidence, committed artifacts, and fail-closed claims.
- [ ] 3.2 Update scaled clarify materialization tests for the new post-merge formal boundary.
- [ ] 3.3 Update `CONTEXT.md`, `reports/final_status.md`, OpenSpec spec, and Human Brief.

## 4. Validation And Archive

- [ ] 4.1 Run focused pytest, full pytest, ruff, public data validation, DPO checks, OpenSpec strict validation, leak scan, and `git diff --check`.
- [ ] 4.2 Archive the OpenSpec change after validation succeeds, then use guarded auto-integration only if the user resumes `/opsx auto`.
