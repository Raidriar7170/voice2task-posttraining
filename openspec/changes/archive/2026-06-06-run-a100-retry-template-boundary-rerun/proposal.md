## Why

The local retry template boundary phase proved that the retry prompt now uses a machine-only chat-template/fallback boundary, but it did not prove private-adapter behavior changed. A small A100 prediction-only rerun is the next bounded check to measure whether the trained adapter still emits prose/Markdown-wrapped retry fragments under the new retry template boundary.

## What Changes

- Run an authorized A100 prediction-only train-split rerun using the current retry template boundary implementation, an existing private adapter, and a repo-external private override.
- Preserve strict parser/evaluator behavior: invalid wrapped fragments remain invalid; no embedded JSON extraction, prediction repair, re-score, semantic-equivalence scoring, slot normalization, or metric relaxation.
- Publish only sanitized public evidence under `reports/public-sample/a100-retry-template-boundary-rerun/`, including predictions, metrics, prompt snapshot, raw decoded summary, generation trace, prediction metadata, retry-template boundary diagnosis, schema guard summary, manifest, report, and leak-scan sidecars.
- Generate a concise Chinese Human Brief comparing the rerun against the prior A100 retry JSON-only rerun and the local retry template boundary evidence.
- Do not train, release checkpoints/adapters, publish private configs/logs/paths, change decoding parameters, change evaluator metrics, or claim model-quality improvement unless strict evidence supports the narrow observation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: support a bounded A100 prediction-only rerun that exercises the machine-only retry template boundary against the existing private adapter.
- `contract-evaluation`: publish public-safe rerun evidence that compares strict final metrics and retry-wrapper behavior without overclaiming recovery or quality improvement.

## Impact

- Affected execution: A100 prediction-only rerun with current code, existing private adapter, train split rows, and sanitized public artifacts.
- Affected artifacts: `reports/public-sample/a100-retry-template-boundary-rerun/`, `docs/human-briefs/2026-06-06-run-a100-retry-template-boundary-rerun.html`, and archived OpenSpec artifacts after implementation.
- No dependency changes, no model training, no parser relaxation, no evaluator metric change, no prediction repair/re-score, no public full-corpus release, no checkpoint/adapter release, and no live-browser benchmark claim.
