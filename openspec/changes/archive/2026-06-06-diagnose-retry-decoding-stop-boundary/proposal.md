## Why

The archived `run-a100-schema-retry-wrapper-boundary-rerun` phase showed that retry wrapper-boundary prompt constraints reached A100 metadata, but the private adapter still emitted prose/Markdown-wrapped retry attempts for `3/3` train rows. The next safe step is not another A100 rerun and not parser relaxation. It is a local diagnosis of decoding stop/boundary evidence to understand what is known, what is missing, and which fix path would need user confirmation.

## What Changes

- Publish a local public-safe diagnosis of retry decoding stop/boundary evidence using the latest A100 sidecars.
- Record that current `generation_trace.jsonl` captures raw attempt generation finish state but does not capture retry attempt token/finish state.
- Separate observed facts from hypotheses: raw generation reached EOS before `max_new_tokens`, retry wrapper persisted, retry text contains forbidden prefaces/trailing analysis, and retry EOS/stop evidence is currently missing.
- Add focused tests and a Human Brief.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contract-evaluation`: publish local evidence for retry decoding stop/boundary diagnosis without changing metrics or reinterpreting predictions.
- `supervised-contract-tuning`: document the diagnostic boundary before any future decoding/stop-boundary behavior change.

## Impact

- Affected evidence: `reports/public-sample/retry-decoding-stop-boundary-diagnosis/`.
- Affected tests: focused evidence boundary tests.
- Affected docs: OpenSpec archive and `docs/human-briefs/`.
- Non-goals: no A100 execution, no training, no private prediction rerun, no decoding change, no parser relaxation, no evaluator metric change, no prediction repair/re-score, no semantic-equivalence scoring, no slot normalization, no checkpoint or adapter release, no model recovery claim, and no live-browser benchmark improvement claim.
