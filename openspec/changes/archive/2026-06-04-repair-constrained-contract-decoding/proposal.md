## Why

The required-field repair A100 train-split rerun preserved raw and retry attempt evidence, but all three train predictions remained Browser Task Contract schema-invalid. The observed failures are local output-shape failures: legacy enum values such as `search_web`/`open_url`, Markdown or explanatory retry text, missing `safety.allow`, and path-like routes. Continuing A100 training before fixing this decoding surface risks spending compute on a failure mode we can reproduce locally.

## What Changes

- Add a bounded local constrained contract decoding repair that makes retry prompts emit JSON-only canonical Browser Task Contract objects with legal enum values.
- Preserve raw and retry attempts as observed model evidence; do not coerce, normalize, or replace invalid private-adapter outputs with gold or fixture contracts.
- Add a local diagnosis/report surface using the required-field rerun evidence to classify raw/retry failure families and recommend whether a later A100 rerun is justified.
- Keep all outputs public-safe and explicit that this phase is local decoder/output-shape hardening, not model recovery, release, held-out generalization, production readiness, or live-browser benchmark evidence.

## Capabilities

### New Capabilities

### Modified Capabilities

- `supervised-contract-tuning`: add canonical JSON-only retry/constrained decoding requirements for trained-adapter prediction.
- `contract-evaluation`: add public-safe constrained-decoding diagnosis/report requirements using the required-field rerun evidence.

## Impact

- Affected runtime path: `voice2task.training` prediction prompt/retry/schema guard path.
- Affected tests: focused fake-model prediction tests and evidence-boundary tests.
- Affected evidence surface: a local public-safe diagnosis report under `reports/public-sample/` and one Human Brief under `docs/human-briefs/`.
- No A100 rerun, no private adapter release, no checkpoint release, no DPO/GRPO, no live-browser benchmark, no production-readiness claim, and no held-out generalization claim.
