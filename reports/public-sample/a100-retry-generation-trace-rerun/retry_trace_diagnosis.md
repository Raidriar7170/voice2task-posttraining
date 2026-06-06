# A100 retry generation trace train-split diagnosis

This diagnosis is evidence-only. It observes retry-attempt generation trace rows from a bounded A100 private-adapter prediction rerun and does not repair, coerce, normalize, or rescore predictions.

## Result

- Predictions: `3` train rows from `private_a100_adapter`.
- Strict final `json_valid_rate`: `0.0000`.
- Strict final `contract_exact_match`: `0.0000`.
- Generation trace rows: `6`; prior comparable phase had `3`.
- Retry attempt trace rows: `3/3`.
- Retry attempt finish state: `{'no_eos_observed': 3}`.
- Retry attempts still parse as JSON fragments/wrapped prose for `3/3` rows.

## Interpretation

- The instrumentation worked on the real A100 private-adapter path: retry attempts now have trace rows.
- The retry trace also shows retry attempts did not observe EOS for all 3 train rows, while raw attempts did observe EOS.
- Strict parser outcomes did not improve: final schema-valid output remains `0/3` and exact contract match remains `0/3`.
- This supports the next diagnostic question about retry stop/boundary behavior, but the retry stop-boundary claim remains unproven and this is not a model recovery claim.

## Non-Claims

- No held-out generalization claim.
- No model-quality improvement claim.
- No parser relaxation, prediction repair, slot normalization, semantic-equivalence scoring, or evaluator metric change.
