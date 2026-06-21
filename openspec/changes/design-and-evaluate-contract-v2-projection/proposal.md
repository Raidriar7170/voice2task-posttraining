## Why

The latest step-matched canonical-slot SFT ablation was mixed and inconclusive:
small canonical slot data did not prove stable held-out improvement under the
same optimizer-step budget. Before more training, DPO, or candidate loops, the
project needs an offline answer to whether low strict exact match is driven by
core task/slot understanding or by V1 derived fields such as
`normalized_command`, `language`, and `contract_version`.

## What Changes

- Add an experimental, deterministic Contract V2 Core projection for existing
  V1 Browser Task Contracts without changing the formal V1 schema.
- Generate offline projection metrics from the latest committed
  step-matched canonical-slot ablation artifacts under
  `reports/public-sample/step-matched-canonical-slot-ablation/`.
- Compare the current V1 strict ladder against:
  - L1: V1 without `normalized_command`;
  - L2: V2 Core strict exact;
  - L3: deterministic V2 envelope validation.
- Add a fail-closed deterministic `normalized_command` renderer prototype for
  coverage analysis only.
- Publish public-safe projection evidence under
  `reports/public-sample/contract-v2-projection/`.
- Refresh README, README_en, and CONTEXT current truth surfaces so historical
  77-seed / 231-SFT / 661-DPO and old held-out metrics are not presented as the
  current snapshot.
- End with exactly one bounded decision label:
  `PROCEED_TO_CONTRACT_V2_IMPLEMENTATION`, `PARTIAL_SCHEMA_BENEFIT`,
  `SLOT_BOTTLENECK_PERSISTS`, or `PROJECTION_BLOCKED_OR_INVALID`.
- Stop after this change. Do not implement production Contract V2, train,
  predict, mutate data, launch A100 work, or start the recommended next change.

## Capabilities

### New Capabilities

- `contract-v2-projection`: experimental deterministic projection from V1
  contracts into a V2 Core plus envelope and display renderer prototype.

### Modified Capabilities

- `contract-evaluation`: add offline projection ladder, field-contribution,
  bootstrap, and public-safe report requirements while preserving current V1
  evaluator semantics.

## Impact

- Adds a pure Python projection module, an offline projection evaluator/report
  command, focused tests, and public-safe report artifacts.
- Uses only committed gold/prediction/evaluation artifacts; no A100, SSH, GPU
  job, model adapter, prediction rerun, training, DPO, split mutation, prompt
  change, LLM judge, or semantic-equivalence substitution.
- Preserves BrowserTaskContract V1 fields, existing strict evaluator semantics,
  existing layered evaluator metric meanings, committed gold contracts,
  prediction outputs, runtime consumers, SFT/DPO formatting, and training
  configs.
- Updates documentation truth surfaces to keep the latest step-matched
  ablation result current and older sample/evaluation counts historical.
