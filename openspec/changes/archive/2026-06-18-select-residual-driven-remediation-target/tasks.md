## 1. Test-First Coverage

- [x] 1.1 Add tests proving remediation target selection reads current layered-eval and residual-diagnosis artifact layouts.
- [x] 1.2 Add tests for dev/test failure-family aggregation, strategy mapping, safety prioritization, and top-target limit.
- [x] 1.3 Add tests that required report files are written and pass the public leak scan.

## 2. Core Implementation

- [x] 2.1 Implement remediation target-selection artifact discovery and ingestion from committed public-sample reports.
- [x] 2.2 Implement residual family aggregation, normalized attachment-facing family names, sanitized examples, and top affected hints.
- [x] 2.3 Implement deterministic remediation strategy mapping and at-most-two next-target selection.

## 3. Report Artifacts

- [x] 3.1 Generate `reports/public-sample/remediation-target-selection/summary.json`.
- [x] 3.2 Generate `reports/public-sample/remediation-target-selection/summary.md`.
- [x] 3.3 Generate `reports/public-sample/remediation-target-selection/top-failures.md`.
- [x] 3.4 Generate `reports/public-sample/remediation-target-selection/recommended-next-change.md`.

## 4. Documentation, Review, and Validation

- [x] 4.1 Generate the Chinese Human Brief HTML for this OpenSpec phase.
- [x] 4.2 Verify no historical layered evaluator, strict evaluator, residual diagnosis, scaled residual diagnosis, or scaled target-selection artifacts were overwritten.
- [x] 4.3 Run `python -m pytest -q`, `openspec validate --all --strict`, `git diff --check`, and a public leak scan over new artifacts/docs/archive candidates.
