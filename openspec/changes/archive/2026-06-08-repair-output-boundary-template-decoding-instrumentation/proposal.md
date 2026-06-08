## Why

The latest A100 search-query slot rerun and follow-up local diagnosis show compact `slots.query` content inside decoded fragments, but every prediction remains Markdown-wrapped and strict schema-valid output stays `0/3`. The next bounded step is to change the model-visible output boundary and local instrumentation so future prediction attempts are explicitly shaped as machine-only JSON payloads before any new A100 rerun is interpreted.

## What Changes

- Strengthen first-pass prediction prompt output-boundary language so it mirrors the strict retry boundary: exactly one root Browser Task Contract JSON object, no Markdown/code fences/prose, no preamble, no suffix/trailing analysis, and no second JSON object.
- Record machine-readable prompt-boundary metadata for first-pass prediction prompts, separate from retry prompt metadata.
- Add local behavior tests proving the prediction prompt boundary is visible and that strict parsing still rejects wrapped JSON fragments.
- Publish a public-safe local evidence pack and concise Chinese Human Brief for this behavior-change phase.
- Keep strict parser behavior, evaluator metrics, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, training, and A100 prediction reruns out of this phase.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: harden first-pass prediction output-boundary prompt/instrumentation while preserving strict parsing and prediction provenance behavior.
- `contract-evaluation`: publish public-safe local evidence that separates output-boundary behavior change from model-quality, rerun, or metric-improvement claims.

## Impact

- Affected code: `src/voice2task/formatting.py`, `src/voice2task/training.py`, and focused tests.
- Affected artifacts: a local evidence pack under `reports/public-sample/repair-output-boundary-template-decoding-instrumentation/` and a Human Brief under `docs/human-briefs/`.
- No dependency changes, no A100 execution, no training, no parser relaxation, no evaluator metric change, no prediction repair/re-score, no public full-corpus release, no released checkpoint/adapter, no generic chat fine-tuning, no skill routing, no GUI action policy learning, no first-phase GRPO, and no live-browser benchmark improvement claim.
