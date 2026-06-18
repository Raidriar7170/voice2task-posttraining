# Layered Contract Evaluation

- Manifest: `public-sample-20260617T152259Z`
- Scope: existing dev/test predictions only; no training, prediction rerun, data merge, slot repair, or evaluator relaxation.
- `contract_exact_match_strict` preserves the original strict evaluator semantics.
- Normalized metrics are deterministic diagnostics only and do not claim recovery.

## Split Metrics

| split | total | strict pass | strict fail | executable pass | normalized slot F1 | strict exact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 207 | 51 | 156 | 0.2705 | 0.2821 | 0.2464 |
| test | 207 | 42 | 165 | 0.2512 | 0.2390 | 0.2029 |
