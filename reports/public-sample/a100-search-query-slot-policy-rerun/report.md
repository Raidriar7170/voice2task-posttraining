# A100 search query slot policy rerun

## Conclusion

The A100 prediction-only rerun observed compact slots.query content, but every row was Markdown-wrapped and strict schema-valid output fell to 0/3.

## Evidence

- Predictions: `reports/public-sample/a100-search-query-slot-policy-rerun/predictions.jsonl`
- Metrics: `reports/public-sample/a100-search-query-slot-policy-rerun/metrics.json`
- Diagnosis: `reports/public-sample/a100-search-query-slot-policy-rerun/slot_policy_rerun_diagnosis.json`

## Boundaries

- A100 prediction-only, train-split-only prediction evidence.
- No training, no slot normalization, no parser relaxation, no semantic-equivalence scoring, no prediction repair, and no re-score.
- Do not claim model recovery, held-out generalization, production readiness, or live-browser benchmark improvement.
