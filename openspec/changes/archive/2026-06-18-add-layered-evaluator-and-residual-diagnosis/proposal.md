## Why

The latest scaled-manifest model evidence has stable JSON output and strong
route/safety signals, but strict full-contract exact match and strict slot F1
remain low. Before any further data merge, rerun, or training attempt, the
project needs a deterministic layered evaluator and residual diagnosis surface
that explains which fields and task families drive strict failures.

## What Changes

- Add a deterministic layered evaluator that coexists with the existing strict
  evaluator and preserves strict `contract_exact_match` semantics unchanged.
- Add residual diagnosis reports for dev/test strict exact mismatches using the
  existing scaled prediction-only outputs and gold contracts.
- Add bounded deterministic normalization helpers for diagnostic
  slot-value-normalized metrics and executable-contract pass rate only.
- Generate new public-safe reports under new directories:
  `reports/public-sample/layered-eval/` and
  `reports/public-sample/residual-diagnosis/`.
- Update evaluator documentation and status surfaces to explain primary metrics,
  diagnostic metrics, strict-exact boundaries, no-LLM-judge boundaries, and
  non-claims.
- Add focused tests covering strict evaluator preservation, layered metrics,
  normalization boundaries, unsafe false negatives, residual attribution, report
  generation, and public-safety leak checks.
- Do not continue `merge-scaled-clarify-slot-boundary-candidates`; existing
  scaled residual diagnosis, cluster inspection, and target selection remain
  historical evidence only and must not be overwritten.

## Capabilities

### New Capabilities

### Modified Capabilities

- `contract-evaluation`: add deterministic layered evaluation, bounded
  diagnostic normalization, executable-contract pass rate, and dev/test
  residual diagnosis requirements while preserving strict evaluator semantics.

## Impact

- Affected code: `src/voice2task/evaluation.py`, `src/voice2task/reports.py`,
  and the report CLI only if needed for generation ergonomics.
- Affected tests: focused evaluator/report tests plus public-safety report
  checks.
- Affected docs/reports: `docs/evaluation.md` or README evaluation sections,
  `CONTEXT.md`, `reports/final_status.md`, a concise Chinese Human Brief, and
  new generated evidence packs.
- No SFT, DPO, GRPO, prediction rerun, A100 execution, dataset mutation,
  split change, LoRA hyperparameter change, evaluator relaxation, slot repair,
  checkpoint/adapter release, public full-corpus release, or live-browser
  benchmark claim is in scope.
