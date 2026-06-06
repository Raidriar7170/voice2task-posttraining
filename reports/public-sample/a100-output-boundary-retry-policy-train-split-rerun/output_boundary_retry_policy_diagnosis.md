# A100 output-boundary retry-policy diagnosis

Status: train-internal A100 diagnostic rerun. Strict final-contract recovery was not observed.

## Result

- Strict final `json_valid_rate`: 0.0000
- Strict final `contract_exact_match`: 0.0000
- Raw whole JSON object count: 3/3
- Raw missing `task_type`: 3/3
- Retry `task_type=search` visible but prose/Markdown-wrapped: 3/3
- Validated output schema-valid rows: 0/3

## Interpretation

The local output-boundary/retry prompt repair produced a useful shape change: raw model output is now a whole JSON object rather than prior non-JSON text. The remaining blocker is still row-level schema validity: every raw object omits `task_type`, and every retry is rejected because it is wrapped in prose or Markdown instead of being the single minified JSON object required by the parser.

No semantic-equivalence scoring, no slot normalization, no prediction repair, no re-score, and no evaluator metric relaxation was performed.
