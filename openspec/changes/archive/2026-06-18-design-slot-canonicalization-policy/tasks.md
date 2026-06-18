## 1. OpenSpec and Source Evidence

- [x] 1.1 Read current `CONTEXT.md`, layered-eval, residual-diagnosis, remediation-target-selection, schema, dataset, and evaluator source evidence.
- [x] 1.2 Confirm this phase is design-only and leaves existing active changes and historical evidence untouched.

## 2. Policy Artifacts

- [x] 2.1 Generate `summary.md` and `summary.json` under `reports/public-sample/slot-canonicalization-policy/`.
- [x] 2.2 Generate `slot-key-policy.md` with canonical keys, aliases, disallowed keys, task-type boundaries, and examples.
- [x] 2.3 Generate `slot-value-policy.md` with conservative normalization boundaries and non-equivalence examples.
- [x] 2.4 Generate `normalized-command-policy.md` with diagnostic/display positioning, metric impact, and non-goals.
- [x] 2.5 Generate `model-target-boundary.md` with model-predicted versus deterministic-derived field classifications.
- [x] 2.6 Generate `recommended-next-change.md` with a bounded next change recommendation and claim boundaries.

## 3. Tests and Documentation

- [x] 3.1 Add focused tests for deterministic slot-key aliases, non-equivalence boundaries, strict-exact preservation, required artifact presence, boundary classifications, and public leak-scan cleanliness.
- [x] 3.2 Update `README.md` or `docs/evaluation.md` with the slot/canonical contract consistency bottleneck and design-only boundary.
- [x] 3.3 Generate `docs/human-briefs/2026-06-18-design-slot-canonicalization-policy.html`.

## 4. Review and Validation

- [x] 4.1 Run Worker implementation in the approved current workspace with minimal task-related changes.
- [x] 4.2 Run Reviewer diff review and address in-scope Must Fix items.
- [x] 4.3 Run `python -m pytest -q`, `openspec validate --all --strict`, `git diff --check`, and public leak-scan checks for new artifacts.
- [x] 4.4 Archive the completed OpenSpec change only after validation and review pass.
