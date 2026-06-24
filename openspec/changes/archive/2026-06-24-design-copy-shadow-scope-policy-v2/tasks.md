## 1. OpenSpec and input audit

- [x] 1.1 Validate the new OpenSpec proposal, design, specs, and task list.
- [x] 1.2 Run read-only exploration of diagnosis, evaluation, policy, prediction, and sidecar artifact schemas.
- [x] 1.3 Confirm prior diagnosis branch is integrated to main and no other OpenSpec changes are active before implementing Policy V2 design.

## 2. Tests first

- [x] 2.1 Add focused unit tests for Wilson 95 percent interval calculations.
- [x] 2.2 Add gate threshold tests for enabled, limited, candidate-only, insufficient-evidence, disable, adapter-gap, high-risk, and small-sample cases.
- [x] 2.3 Add tests that 3/3 samples, single-adapter evidence, and hard-coded slot-name logic cannot enable a scope.
- [x] 2.4 Add tests for downward-only overrides and upward override rejection.
- [x] 2.5 Add tests for taxonomy migration, fixture-guided attribution fields, canonical-string mismatch, and true fixture/gold ambiguity.
- [x] 2.6 Add tests for proposed policy inactive flags, Policy V1 unchanged, challenge/prediction artifacts unchanged, source-only semantics, execution eligibility false, and bounded report filenames.

## 3. Implementation

- [x] 3.1 Add `src/voice2task/copy_shadow_scope_policy_design.py` with metric, gate, override, taxonomy, validation, and serialization helpers.
- [x] 3.2 Add a report-generation script for the bounded Policy V2 design artifact set.
- [x] 3.3 Regenerate the current diagnosis interpretation artifacts with migrated taxonomy and fixture-guided attribution fields.
- [x] 3.4 Write `configs/copy-backed-scope-policy-v2.proposed.json` as inactive proposal-only policy.
- [x] 3.5 Write bounded reports under `reports/public-sample/copy-shadow-scope-policy-v2-design/`.
- [x] 3.6 Add `docs/copy-shadow-scope-policy-v2.md` and a concise Chinese Human Brief under `docs/human-briefs/2026-06-24-design-copy-shadow-scope-policy-v2.html`.
- [x] 3.7 Update truth surfaces only enough to point to the review-only Policy V2 design result and boundaries.

## 4. Validation and review

- [x] 4.1 Run focused tests for the new design module and existing evidence surfaces.
- [x] 4.2 Run full `pytest`, `ruff`, OpenSpec strict validation, truth-surface checker, leak scan, and `git diff --check`.
- [x] 4.3 Run a read-only Reviewer pass over the git diff.
- [x] 4.4 Fix Must Fix items only, rerun affected validation, and commit the bounded phase.
