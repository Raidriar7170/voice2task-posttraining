# A100 first-pass wrapper persistence diagnosis

This is a local evidence-only diagnosis. It does not run A100, retrain, change decoding, relax the parser, repair predictions, or re-score outputs.

## Conclusion

The first-pass output boundary is visible in metadata and prompt snapshots, but all three predictions remain Markdown-wrapped JSON fragments. EOS observed does not mean schema-valid output.

## Observed Facts

- Predictions: `3`
- Boundary visible: `true`
- Markdown-wrapped predictions: `3/3`
- Strict schema-valid outputs: `0/3`
- Raw generation EOS observed: `3/3`
- Retry generation EOS observed: `3/3`
- Raw/retry max-token hits: `0`

## Evidence Gaps

- Wrapper origin remains unproven from current public-safe sidecars.
- Boundary prompt visibility alone did not remove Markdown wrappers.
- EOS observed does not mean schema-valid output under the strict whole-string parser.

## Boundary

- No A100 execution or prediction rerun in this phase.
- No training, parser relaxation, prediction repair, slot normalization, semantic-equivalence scoring, or re-score.
- No model-quality, model-recovery, held-out generalization, production-readiness, or live-browser benchmark improvement claim.
