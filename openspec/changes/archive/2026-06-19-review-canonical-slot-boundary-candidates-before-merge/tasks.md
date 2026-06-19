## 1. Test-First Coverage

- [x] 1.1 Add focused tests for review artifact presence, source traceability,
  review classification schema, and execution-scope flags.
- [x] 1.2 Add tests that slot-key alias and conservative slot-value boundary
  classes are only eligible for a later bounded formal-merge proposal, not
  approved for immediate merge.
- [x] 1.3 Add tests that normalized-command examples stay
  diagnostic/display-only and excluded non-equivalence cases stay blocked or
  deferred.
- [x] 1.4 Add tests that formal public sample files and the existing stale
  `merge-scaled-clarify-slot-boundary-candidates` change remain unmodified.

## 2. Review Evidence

- [x] 2.1 Generate
  `reports/public-sample/canonical-slot-boundary-candidate-review/summary.json`.
- [x] 2.2 Generate
  `reports/public-sample/canonical-slot-boundary-candidate-review/summary.md`.
- [x] 2.3 Generate a report-local leak scan record.
- [x] 2.4 Record class-level decisions for slot-key aliases, slot-value
  boundaries, normalized-command diagnostics, and excluded non-equivalence
  examples.
- [x] 2.5 Record a bounded recommended next step without implementing it.

## 3. Documentation and Human Brief

- [x] 3.1 Update `CONTEXT.md` and `reports/final_status.md` with the
  review-only result if the phase completes.
- [x] 3.2 Generate
  `docs/human-briefs/2026-06-18-review-canonical-slot-boundary-candidates-before-merge.html`.

## 4. Review and Validation

- [x] 4.1 Run Worker implementation in the approved current workspace with
  minimal task-related changes.
- [x] 4.2 Run Reviewer diff review and address in-scope Must Fix items.
- [x] 4.3 Run focused tests, full `python -m pytest -q`,
  `openspec validate --all --strict`, `git diff --check`, and public leak-scan
  checks.
- [x] 4.4 Archive the completed OpenSpec change only after validation and
  review pass.
