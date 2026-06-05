# A100 Confirmation-Required Train-Split Metrics

Status: train-internal prediction-only diagnostic evidence. This is not a benchmark, release, production-readiness signal, or held-out generalization claim.

## Strict Final Contract Metrics

- prediction_source_kind: `private_a100_adapter`
- prediction_split: `train`
- generalization_claim: `False`
- json_valid_rate: `0.6667`
- contract_exact_match: `0.0000`
- task_type_accuracy: `0.3333`
- route_accuracy: `0.3333`
- confirmation_accuracy: `0.6667`

## Confirmation-Required Counts

- confirmation_required boolean emission: `2/3`
- Missing `confirmation_required`: `1/3`
- Raw attempt schema-valid: `2/3`
- Retry attempt schema-valid: `0/3`
- Final validated schema-valid: `2/3`
- Validated output source counts: `{'none': 1, 'raw_attempt': 2}`

## Boundary

No schema repair, default insertion, output coercion, checkpoint release, adapter release, production-readiness claim, model-quality claim, live-browser benchmark claim, or held-out generalization claim is made.
