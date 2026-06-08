# A100 first-pass fence-suppression rerun diagnosis

## Conclusion
The A100 prediction-only rerun observed zero Markdown-wrapped predictions and 3/3 strict schema-valid raw outputs after generation-time Markdown fence suppression was active in metadata.

## Comparison
- Prior Markdown-wrapped predictions: `3`
- Current Markdown-wrapped predictions: `0`
- Prior strict JSON-valid rate: `0.0`
- Current strict JSON-valid rate: `1.0`
- Current contract exact match: `0.6666666666666666`
- Current slot F1: `0.6666666666666666`

## Remaining Mismatch
One train row still has a strict slot mismatch: the model emitted city/date/topic slots instead of the compact query slot. This is not normalized or repaired here.

## Boundary
- A100 prediction-only, train-split-only evidence.
- No training, parser relaxation, decoded-output fence stripping, evaluator metric change, prediction repair, re-score, slot normalization, semantic-equivalence scoring, checkpoint release, or adapter release.
- This is not a held-out generalization claim, production readiness claim, live-browser benchmark claim, model recovery claim, or model-quality improvement claim.
