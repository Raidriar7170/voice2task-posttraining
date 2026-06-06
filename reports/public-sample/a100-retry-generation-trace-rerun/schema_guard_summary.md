# A100 retry generation trace schema guard summary

This summary preserves strict schema outcomes. It reports retry trace coverage without repairing, coercing, or rescoring predictions.

## Summary

- Predictions: `3`
- Raw schema-valid attempts: `0`
- Retry attempts: `3`
- Retry schema-valid attempts: `0`
- Final schema-valid outputs: `0`
- Generation trace rows: `6` (prior comparable phase: `3`)
- Raw attempt trace rows: `3`
- Retry attempt trace rows: `3`
- Retry finish states: `{'no_eos_observed': 3}`

## Boundary

- Retry trace rows are diagnostic instrumentation evidence only.
- Strict metrics remain based on final Browser Task Contract validation.
- This is not model recovery evidence and not a model-quality improvement claim.
