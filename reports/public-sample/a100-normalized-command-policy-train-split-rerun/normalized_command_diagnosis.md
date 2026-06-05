# A100 normalized-command policy train-split diagnosis

This diagnosis is field-level evidence from one private-adapter A100 train-split prediction rerun. It reports exact string matches only: no normalization, no semantic-equivalence scoring, no prediction repair, and no metric re-score were performed.

## Boundary

- Prediction split: `train`
- Overfit diagnostic: `True`
- Held-out generalization claim: `False`
- Strict evaluator metric change: `False`
- Checkpoint or adapter release: `False`

## Summary

- Normalized-command exact-string matches: `2/3`
- Normalized-command exact-string mismatches: `1/3`
- Strict final json_valid_rate: `0.3333333333333333`
- Strict final contract_exact_match: `0.0`
- Final schema-valid rows: `1/3`

## Row Evidence

- `seed-search-weather`: gold `搜索北京明天天气`, prediction `搜索北京明天的天气`, exact `False`, context `co_occurs_with_schema_failure`
- `seed-search-weather-aug-1`: gold `搜索北京明天天气`, prediction `搜索北京明天天气`, exact `True`, context `exact_match`
- `seed-search-weather-aug-2`: gold `搜索北京明天天气`, prediction `搜索北京明天天气`, exact `True`, context `exact_match`

The result is narrower than full recovery: two rows still fail final schema validation and strict `contract_exact_match` remains `0.0`.
