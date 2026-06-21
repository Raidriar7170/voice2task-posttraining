## Why

The previous Contract V2 projection phase correctly blocked because current
step-matched raw prediction contracts and aligned gold contracts were missing.
Those inputs have now been recovered from existing committed evidence, so the
same bounded offline projection question can be answered without training,
prediction generation, or evaluator changes.

## What Changes

- Add a bounded rerun path that reads only
  `reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs/`.
- Verify the recovered source boundary before projection, including manifest
  readiness, reproduced metrics, row counts, split disjointness, gold hashes,
  config/prompt/evaluator hashes, and recovery method.
- Reuse or implement deterministic V1-to-V2 Core projection, V2 Core
  validation, canonical JSON, deterministic envelope building, and bounded
  normalized-command rendering.
- Generate a new public-safe evidence bundle under
  `reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/`
  without overwriting the historical blocked root evidence.
- Report L0 V1 strict, L1 V1 without `normalized_command`, L2 V2 Core, and L3
  V2 envelope metrics with conservative counterfactual and bootstrap analysis.
- Emit exactly one bounded decision label and one recommended next change, then
  stop without implementing Contract V2 or starting more model work.

## Capabilities

### New Capabilities
- `contract-v2-projection-rerun`: recovered-input Contract V2 projection rerun,
  source-boundary verification, deterministic V2 core/envelope projection, and
  public-safe rerun evidence.

### Modified Capabilities
- `contract-evaluation`: add recovered-input projection ladder evidence and
  fail-closed boundary checks without changing V1 evaluator semantics.

## Impact

- Affected code: a local-only projection module or existing projection helpers,
  a rerun report command, focused tests, and public-safe report artifacts.
- Affected docs: concise README, README_en, CONTEXT snapshot updates and one
  Chinese Human Brief HTML for the phase.
- No runtime API, production schema, training configuration, prompt, split,
  gold, prediction, adapter, checkpoint, or Voice-to-Browser integration change.
