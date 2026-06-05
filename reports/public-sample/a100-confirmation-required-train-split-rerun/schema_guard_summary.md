# Confirmation-Required Schema Guard Summary

Status: train-internal A100 prediction-only diagnostic evidence.

## Counts

- Prediction count: `3`
- Raw attempt schema-valid: `2/3`
- Retry attempt schema-valid: `0/3`
- Final validated schema-valid: `2/3`
- Retry attempted: `1/3`
- Strict retry fragment rejections: `1`
- confirmation_required boolean emission: `2/3`
- Missing `confirmation_required`: `1/3`

## Interpretation

The repaired prediction prompt reached the private A100 adapter path and two train rows emitted boolean `confirmation_required=false` as raw JSON objects. One train row still omitted the field in the raw attempt, and its retry attempt was rejected because it was Markdown/prose-wrapped rather than a strict whole JSON object.

## Boundary

No schema repair, output coercion, checkpoint release, adapter release, production-readiness claim, live-browser benchmark claim, or held-out generalization claim is made.
