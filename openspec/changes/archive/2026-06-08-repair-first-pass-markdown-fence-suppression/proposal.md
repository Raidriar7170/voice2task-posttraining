## Why

The latest A100 first-pass output-boundary rerun showed that the boundary prompt is visible and EOS can be observed, but all sampled train-split predictions still arrived as Markdown-wrapped JSON fragments and strict schema-valid output remained `0/3`. The next bounded step is a local behavior change at generation time: suppress Markdown fence token sequences before another private A100 observation, while preserving the strict whole-string parser and evaluator semantics.

## What Changes

- Add first-pass prediction decoding policy metadata for Markdown fence suppression.
- Configure trained-adapter generation to pass tokenizer-derived Markdown fence token sequences as `bad_words_ids` when available.
- Keep strict parser behavior unchanged: Markdown-wrapped JSON fragments remain invalid and are not extracted, repaired, coerced, normalized, re-scored, or replaced.
- Add local TDD coverage for metadata visibility and generation-time suppression wiring.
- Publish a public-safe local evidence pack and concise Chinese Human Brief for this phase.
- Keep A100 execution, training, adapter/checkpoint release, prior evidence rewrite, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, and public release of the full local corpus out of this phase.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add first-pass prediction generation-time Markdown fence suppression wiring and metadata while preserving strict parsing and prediction provenance behavior.
- `contract-evaluation`: publish bounded public-safe evidence that separates local decoding-policy hardening from model-quality or metric-improvement claims.

## Impact

- Affected code: `src/voice2task/training.py` and focused tests.
- Affected artifacts: a local evidence pack under `reports/public-sample/first-pass-markdown-fence-suppression/` and a Human Brief under `docs/human-briefs/`.
- No dependency changes, no A100 execution in this phase, no training, no parser relaxation, no evaluator metric change, no prediction repair/re-score, no public full-corpus release, no released checkpoint/adapter, and no live-browser benchmark improvement claim.
