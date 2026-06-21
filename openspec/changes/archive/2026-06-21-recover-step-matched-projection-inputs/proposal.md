## Why

The latest Contract V2 projection phase correctly blocked because the committed
step-matched canonical-slot ablation lacks row-level Control/Treatment
predictions and aligned gold contracts. Those missing inputs are experiment
artifacts, not new model capability, so the next bounded phase must recover
existing originals or fail closed before any Contract V2 projection rerun.

## What Changes

- Recover the latest step-matched Control/Treatment dev/test raw prediction
  artifacts and aligned dev/test gold contracts, or fail closed if they cannot
  be verified.
- Recompute committed aggregate metrics from recovered row-level artifacts and
  require reproduction within strict tolerance before marking projection inputs
  ready.
- Write public-safe artifacts under
  `reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs/`.
- Add a minimal retention hook and tests only if the current prediction/eval
  path lacks a durable row-level artifact retention surface.
- Update README, README_en, CONTEXT, and a concise Human Brief with the recovery
  result.
- Stop after this change. Do not run Contract V2 projection, train, run DPO,
  mutate data, alter evaluators, change prompts/decoding, or implement schema
  changes.

## Capabilities

### New Capabilities

- `step-matched-projection-input-recovery`: recovery, validation,
  sanitization, metric reproduction, and fail-closed reporting for the raw
  inputs needed by the Contract V2 projection rerun.

### Modified Capabilities

- `contract-evaluation`: require row-level artifact retention and metric
  reproduction checks when step-matched prediction artifacts are used as inputs
  for later offline projection.

## Impact

- Adds OpenSpec artifacts, recovery report artifacts, optional focused helper
  code/tests, and a Chinese Human Brief.
- May inspect local and approved A100 run roots for existing outputs; any new
  remote files must remain under the approved private A100 workspace root and
  must not be recorded in public artifacts.
- Does not change BrowserTaskContract V1, evaluator semantics, layered
  evaluator semantics, gold contracts, train/dev/test split, prompt template,
  decoding policy, model weights, LoRA config, adapters, or dataset contents.
- Does not claim model improvement, held-out recovery, production readiness,
  safety readiness, live-browser benchmark gain, checkpoint release, adapter
  release, or Contract V2 result.
