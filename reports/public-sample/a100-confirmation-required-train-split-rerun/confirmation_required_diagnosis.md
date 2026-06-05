# Confirmation-Required Diagnosis

Status: partial train-internal improvement only. Missing-field failure changed from `3/3` in the prior route-ontology rerun to `1/3` in this rerun, while final validated schema-valid output improved to `2/3`.

## Counts

- confirmation_required boolean emission: `2/3`
- Missing `confirmation_required`: `1/3`
- confirmation_required=false count: `2/3`
- Raw attempt schema-valid: `2/3`
- Final validated schema-valid: `2/3`
- Strict final contract exact match: `0.0000`

## Interpretation

This is a bounded positive signal for the prompt repair on the same train rows, not full model recovery. Two rows are strict schema-valid, but exact contract match is still `0.0000`, and one row still fails because the raw attempt omitted `confirmation_required` and the retry attempt was rejected as a wrapped fragment.

## Boundary

This is train-internal evidence only, with no held-out generalization claim and no release, production-readiness, model-quality, or live-browser benchmark claim.
