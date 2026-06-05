# A100 normalized-command policy train-split metrics

Status: strict train-internal metrics plus separate normalized-command exact-string counts. This is not a benchmark, not a release, and not held-out generalization evidence.

## Strict Final Contract Metrics

- json_valid_rate: `0.3333`
- contract_exact_match: `0.0000`
- task_type_accuracy: `0.0000`
- route_accuracy: `0.0000`
- confirmation_accuracy: `0.3333`
- slot_f1: `0.0000`

## Normalized-command Exact String Counts

- exact-string matches: `2/3`
- exact-string mismatches: `1/3`
- semantic-equivalence scoring performed: `False`
- prediction repair or re-score performed: `False`

Strict `contract_exact_match` remains a full-contract exact-match metric. The normalized-command count is explanatory field-level evidence only.
