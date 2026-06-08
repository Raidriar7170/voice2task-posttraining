# A100 search query slot wrapper-boundary diagnosis

This is a local evidence-only diagnosis. It does not run A100, retrain, change decoding, relax the parser, normalize slots, repair predictions, or re-score outputs.

## Conclusion

Compact `slots.query` content is visible inside the decoded fragments, but all three predictions remain Markdown-wrapped and strict schema-valid output stays `0/3`; the wrapper origin remains unproven.

## Observed Facts

- Predictions: `3`
- Embedded compact query fragments: `3/3`
- Markdown-wrapped predictions: `3/3`
- Strict schema-valid outputs: `0/3`
- Strict exact match: `0.0000`
- Raw generation EOS observed: `3/3`
- Retry generation EOS observed: `3/3`
- Raw/retry max-token hits: `0`

## Evidence Gaps

- The wrapper origin remains unproven from the current public-safe sidecars.
- EOS observed on raw and retry attempts does not mean the wrapper boundary is fixed.
- Compact query fragments do not count as schema recovery under the strict whole-string parser.

## Boundary

- No A100 execution or prediction rerun in this phase.
- No training, decoding change, parser relaxation, slot normalization, prediction repair, or re-score.
- No model-quality, held-out generalization, production-readiness, or live-browser benchmark improvement claim.
