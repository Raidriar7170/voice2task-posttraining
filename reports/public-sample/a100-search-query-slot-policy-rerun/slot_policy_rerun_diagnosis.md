# A100 search query slot policy rerun diagnosis

This is train-split-only prediction evidence from an A100 private-adapter rerun.

## Result

- Strict JSON/schema valid rate: `0.0`
- Strict exact match: `0.0`
- Exact-match rows: `0/3`
- Gold compact slots.query rows: `3/3`
- Embedded compact slots.query fragments: `3/3`
- Markdown-wrapped strict predictions: `3/3`

## Interpretation

The model emitted compact slots.query content inside JSON code fences, but strict parser/evaluator semantics reject the wrappers. This is not slot normalization, not prediction repair, and not a model-quality improvement claim.
