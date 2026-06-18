## Context

The current scaled-manifest evidence for `public-sample-20260617T152259Z`
shows a useful but partial model signal: JSON validity is stable and
route/safety metrics are strong, while strict full-contract exact match and
strict slot F1 remain weak. Previous scaled residual diagnosis, cluster
inspection, target selection, and clarify candidate materialization are
historical evidence. This change must not overwrite those artifacts or continue
the clarify candidate merge path.

The user has explicitly constrained this phase to
`add-layered-evaluator-and-residual-diagnosis`: no data expansion, A100
training, prediction rerun, DPO rerun, LoRA parameter tuning, evaluator
relaxation, slot repair, or continuation of
`merge-scaled-clarify-slot-boundary-candidates`.

## Goals / Non-Goals

**Goals:**

- Add a deterministic layered evaluator over existing dev/test predictions and
  gold contracts.
- Preserve the original strict evaluator behavior and strict exact metric
  semantics unchanged.
- Add residual diagnosis that explains strict exact mismatches by failure
  family, field path, and sanitized examples.
- Generate new public-safe reports under
  `reports/public-sample/layered-eval/` and
  `reports/public-sample/residual-diagnosis/`.
- Document the relationship between primary metrics, diagnostic metrics, strict
  exact, deterministic normalization, and executable contract pass rate.

**Non-Goals:**

- No clarify candidate merge, public-sample data expansion, dataset mutation, or
  train/dev/test split change.
- No A100 job, prediction rerun, SFT, DPO, GRPO, LoRA hyperparameter tuning, or
  base-model change.
- No evaluator relaxation, prediction repair, slot repair, semantic-equivalence
  scoring, or LLM judge.
- No checkpoint/adapter release, production-readiness claim, safety-readiness
  claim, held-out recovery claim, or live-browser benchmark claim.
- No overwrite of existing scaled residual diagnosis, cluster inspection, or
  target-selection evidence directories.

## Decisions

1. **Additive evaluator functions instead of modifying strict evaluation.**
   The strict contract ladder remains the source of strict
   `contract_exact_match`. New layered metrics should live in separate
   functions and reports, with `contract_exact_match_strict` copied from the
   existing strict metric output or recomputed with the same exact comparison.

   Alternative considered: fold normalized metrics into the existing evaluator.
   Rejected because it risks reinterpreting strict exact or making future
   reports treat normalized scores as recovery evidence.

2. **Deterministic normalization is local to diagnostic metrics.**
   Normalization may handle conservative whitespace, punctuation,
   full-width/half-width, casing, common verb aliases, and slot-key aliases.
   It must not use LLMs, semantic similarity, embeddings, or broad synonym
   expansion, and it must not mark materially different values as equivalent.

   Alternative considered: use semantic matching for slot values. Rejected
   because the project needs public-reviewable deterministic evidence and the
   user explicitly forbids LLM judge behavior.

3. **Executable contract pass rate is fail-closed for unsafe downgrades.**
   A contract can pass only when schema, route/task type, required slots,
   bounded slot values, risk/confirmation decisions, and runtime-consumable
   shape are acceptable. Any gold high-risk or confirmation/blocking case that
   is predicted as low-risk auto execution must fail and increment unsafe false
   negatives.

   Alternative considered: count otherwise correct contracts as executable even
   with safety downgrade. Rejected because safety decisions are part of the task
   contract, not an optional display metric.

4. **Generate new evidence directories.**
   Reports for this change go only under
   `reports/public-sample/layered-eval/` and
   `reports/public-sample/residual-diagnosis/`. Historical scaled evidence is
   read-only input and must not be regenerated or edited.

   Alternative considered: append to the existing scaled residual diagnosis
   directory. Rejected because that would blur historical diagnosis evidence
   with this new evaluator phase.

## Risks / Trade-offs

- [Risk] Normalized metrics could be mistaken for strict recovery. -> Mitigation:
  name strict output `contract_exact_match_strict`, document diagnostic-only
  normalization, and keep strict exact unchanged in tests.
- [Risk] Existing prediction/gold JSON shape may vary by artifact. ->
  Mitigation: build small parsing helpers around existing public evidence
  formats and cover representative fixtures in tests.
- [Risk] Residual examples could leak private or path-like data. -> Mitigation:
  sanitize examples, cap example counts, and run public leak-scan validation on
  generated reports.
- [Risk] OpenSpec auto loop could drift into the existing clarify merge change.
  -> Mitigation: keep this change id explicit and do not mark or apply tasks
  from `merge-scaled-clarify-slot-boundary-candidates`.

## Migration Plan

1. Add failing tests for layered metrics, normalization boundaries, unsafe false
   negatives, residual attribution, and report generation.
2. Implement additive evaluator/report helpers and CLI support only as needed.
3. Generate dev/test layered evaluation and residual diagnosis reports from
   existing scaled prediction-only evidence.
4. Update docs/status/Human Brief with strict claim boundaries.
5. Validate with focused tests, broader test suite, OpenSpec strict validation,
   leak scan, and git diff checks.

## Open Questions

- None for this bounded phase. Future remediation choices should be made from
  the new residual distribution after this phase, not inside this phase.
