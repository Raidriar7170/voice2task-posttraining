## Why

The retry trace finish-state diagnosis showed that `finish_state=no_eos_observed` only proves tokenizer EOS was not found in the generated token slice; it does not record the model/generation stop reason. Without a public-safe stop-boundary evidence field, future A100 reruns can easily overstate what `generation_trace.jsonl` proves.

## What Changes

- Add public-safe stop-boundary evidence fields to trained-adapter `generation_trace.jsonl` rows so raw and retry attempts distinguish tokenizer EOS visibility, max-token-hit status, and whether an actual stop reason was recorded.
- Preserve existing generation trace fields and strict prediction behavior; no decoding parameters, retry prompt text, parser semantics, evaluator metrics, prediction repair, or re-scoring changes.
- Publish a bounded local evidence pack and Human Brief documenting the instrumentation and non-claim boundaries.
- Do not run A100, train, release checkpoints/adapters, publish private corpus rows, or claim model-quality/live-browser benchmark improvement in this phase.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: trained-adapter prediction trace rows gain stop-boundary evidence fields while preserving decoding behavior.
- `contract-evaluation`: local evidence and reports must bound claims about what stop-boundary instrumentation proves and does not prove.

## Impact

- Affected code: `src/voice2task/training.py`.
- Affected tests/evidence: focused generation trace tests, public-safe local evidence under `reports/public-sample/`, and a Chinese Human Brief under `docs/human-briefs/`.
- No new runtime dependencies, no public full-corpus release, and no changes to SFT/DPO training, generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, or live browser execution.
