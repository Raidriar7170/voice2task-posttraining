## 1. Test-First Coverage

- [x] 1.1 Add focused tests for standalone candidate artifact presence, source-policy traceability, candidate schema, and execution-scope flags.
- [x] 1.2 Add tests that excluded non-equivalence cases are not accepted candidates and `normalized_command` examples remain diagnostic/display-only.
- [x] 1.3 Add tests that formal public sample files and the existing `merge-scaled-clarify-slot-boundary-candidates` change are not modified.

## 2. Candidate Materialization

- [x] 2.1 Generate `reports/public-sample/canonical-slot-boundary-candidates/summary.json`.
- [x] 2.2 Generate `reports/public-sample/canonical-slot-boundary-candidates/summary.md`.
- [x] 2.3 Generate accepted candidate groups for slot key aliases, slot value boundaries, and normalized-command display/diagnostic examples.
- [x] 2.4 Generate excluded non-equivalence examples for date, city/location, product, URL host, and price/amount changes.
- [x] 2.5 Generate a report-local manifest or metadata section proving standalone-only scope.

## 3. Documentation and Human Brief

- [x] 3.1 Update `CONTEXT.md` and `reports/final_status.md` with the standalone materialization result if the phase completes.
- [x] 3.2 Generate `docs/human-briefs/2026-06-18-materialize-canonical-slot-boundary-candidates.html`.

## 4. Review and Validation

- [x] 4.1 Run Worker implementation in the approved current workspace with minimal task-related changes.
- [x] 4.2 Run Reviewer diff review and address in-scope Must Fix items.
- [x] 4.3 Run focused tests, full `python -m pytest -q`, `openspec validate --all --strict`, `git diff --check`, and public leak-scan checks.
- [x] 4.4 Archive the completed OpenSpec change only after validation and review pass.
