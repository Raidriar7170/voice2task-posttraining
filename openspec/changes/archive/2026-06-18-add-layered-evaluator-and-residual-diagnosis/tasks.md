## 1. OpenSpec Scope And RED Tests

- [x] 1.1 Confirm the change is bounded to
  `add-layered-evaluator-and-residual-diagnosis` and does not apply
  `merge-scaled-clarify-slot-boundary-candidates`.
- [x] 1.2 Add failing tests that prove existing strict evaluator behavior and
  `contract_exact_match` semantics are preserved.
- [x] 1.3 Add failing tests for layered metrics, deterministic normalization
  boundaries, unsafe false negatives, executable-contract pass rate, residual
  family attribution, report generation, and public-safety checks.

## 2. Additive Evaluator Implementation

- [x] 2.1 Add deterministic normalization helpers for diagnostic metrics only.
- [x] 2.2 Add layered evaluator logic without modifying
  `evaluate_predictions()` or historical strict metric outputs.
- [x] 2.3 Add residual diagnosis logic that attributes strict exact mismatches
  by failure family and field path with sanitized examples.

## 3. Report Generation And Documentation

- [x] 3.1 Generate layered evaluation reports under
  `reports/public-sample/layered-eval/` for dev/test plus summary Markdown.
- [x] 3.2 Generate residual diagnosis reports under
  `reports/public-sample/residual-diagnosis/` for dev/test plus summary JSON.
- [x] 3.3 Update `docs/evaluation.md` or README evaluation docs, `CONTEXT.md`,
  and `reports/final_status.md` with strict/layered metric boundaries and
  no-overclaim wording.
- [x] 3.4 Generate
  `docs/human-briefs/2026-06-18-add-layered-evaluator-and-residual-diagnosis.html`.

## 4. Validation, Review, And Archive

- [x] 4.1 Run focused RED/GREEN tests for the new layered evaluator and residual
  diagnosis.
- [x] 4.2 Run strict-regression tests for existing evaluator/report behavior,
  including formal held-out prediction and historical scaled residual evidence.
- [x] 4.3 Run public leak scan over new report directories and the Human Brief.
- [x] 4.4 Run `openspec validate add-layered-evaluator-and-residual-diagnosis --strict`,
  `openspec validate --all --strict`, lint/type checks available in the repo,
  and `git diff --check`.
- [x] 4.5 Run Reviewer review, fix in-scope Must Fix findings only, then archive
  the completed OpenSpec change.
