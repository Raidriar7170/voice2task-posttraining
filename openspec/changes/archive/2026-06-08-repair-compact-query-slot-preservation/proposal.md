## Why

The A100 first-pass fence-suppression rerun reached strict schema-valid output on all three train rows, but strict exact match remains `2/3` because one weather-search row emits decomposed `city/date/topic` slots instead of the gold compact `query` slot. The next bounded behavior step is to make compact search-query slot preservation explicit in the model-visible SFT/prediction policy before any further A100 rerun.

## What Changes

- Reinforce the public preference data with a rejected `city/date/topic` decomposed-slot hard negative for public-readonly weather/search contracts.
- Keep the existing model-visible prompt policy for compact `slots.query` and add tests/evidence that tie it to the new DPO hard negative.
- Generate public-safe local evidence showing the compact-query preservation policy is visible in prompts and represented in public DPO data without changing evaluator behavior or repairing predictions.
- Generate a Chinese Human Brief for the phase.
- Keep A100 execution, training, prediction reruns, evaluator relaxation, slot normalization, semantic-equivalence scoring, prediction repair, and release claims out of scope for this phase.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: model-visible SFT and prediction prompts must preserve compact `slots.query` for search/weather commands rather than decomposing the slot object.
- `voice2task-dataset-preparation`: public DPO hard negatives must include decomposed search-slot shapes as rejected contracts without changing chosen compact-query targets.
- `contract-evaluation`: public-safe evidence must distinguish compact-query policy visibility from proof of A100/model-quality recovery.

## Impact

- Affected code: SFT/prediction prompt construction and tests.
- Affected evidence: new public-safe report directory under `reports/public-sample/compact-query-slot-preservation/` and a Chinese Human Brief under `docs/human-briefs/`.
- No runtime browser agent changes, no GUI action policy learning, no skill routing, no generic chat fine-tuning, no first-phase GRPO, no public full-corpus release, no checkpoint or adapter release, and no live-browser benchmark claim.
