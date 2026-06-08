## Why

The compact query slot preservation repair made the `city/date/topic` decomposed slot shape an explicit rejected DPO hard negative and kept compact `slots.query` visible in model prompts. A bounded A100 prediction-only rerun is now needed to test whether the current private adapter path emits the strict compact query target for the previously failing train row without changing evaluator semantics.

## What Changes

- Run one authorized A100 prediction-only train-split rerun using the current compact query slot preservation prompt/data policy.
- Keep the rerun scoped to the three committed public-sample train rows and preserve strict evaluator behavior.
- Publish sanitized public evidence under `reports/public-sample/a100-compact-query-slot-preservation-rerun/`.
- Generate a concise Chinese Human Brief for the phase.
- Keep training, DPO, evaluator relaxation, parser relaxation, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, re-score, checkpoint release, adapter release, public full-corpus release, production-readiness claims, held-out generalization claims, and live-browser benchmark claims out of scope.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add a bounded A100 prediction-only train-split rerun after compact query slot preservation repair.
- `contract-evaluation`: publish public-safe rerun evidence that compares the previous `city/date/topic` residual with strict compact `slots.query` results while preserving non-claim boundaries.

## Impact

- Affected runtime: private A100 prediction-only execution path through the existing trained-adapter export command.
- Affected evidence: new sanitized report directory under `reports/public-sample/a100-compact-query-slot-preservation-rerun/` and Human Brief under `docs/human-briefs/`.
- Affected tests: focused evidence/manifest/privacy/no-overclaim tests for the new rerun pack.
- No runtime browser agent changes, no GUI action policy learning, no skill routing, no generic chat fine-tuning, no first-phase GRPO, no public full-corpus release, no checkpoint or adapter release, and no live-browser benchmark claim.
