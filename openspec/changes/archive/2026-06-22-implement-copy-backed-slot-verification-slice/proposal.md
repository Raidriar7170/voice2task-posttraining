## Why

Hybrid Slot Representation V1 selected a copy-backed verification slice first, but its `copy_backed_coverage` was only a strategy-candidate metric, not proof that slot values can be uniquely verified against source spans. This change implements the smallest offline verifier needed to separate source provenance from task correctness for task-scoped `query`, `field`, and `target` values.

## What Changes

- Add a standalone copy-backed slot verification module for exact and bounded normalized source-span lookup.
- Add a read-only report script that validates current input boundaries, builds a task-scoped eligibility policy, verifies gold and Control/Treatment prediction slot values, and writes sidecar diagnostics.
- Generate compact public-safe reports under `reports/public-sample/copy-backed-slot-verification-slice/`.
- Document source-span semantics, fail-closed behavior, source provenance versus gold correctness, action exclusion, and claim boundaries.
- Update README/CONTEXT/evidence index with concise current evidence.

## Capabilities

### New Capabilities

- `copy-backed-slot-verification`: Offline system-owned source-span verifier for eligible task-scoped copy-backed slot values, with fail-closed sidecars and provenance metrics.

### Modified Capabilities

- None. Existing V1 contract, ContractCoreV2, evaluator, dataset, training, runtime, and hybrid representation capabilities remain behaviorally unchanged.

## Impact

- Adds `src/voice2task/copy_backed_slot_verification.py`, a report script, focused tests, docs, reports, and OpenSpec artifacts.
- Does not mutate recovered predictions, gold contracts, data splits, evaluator output, `BrowserTaskContract` V1, `ContractCoreV2`, training targets, prompts, runtime behavior, or model weights.
- Does not enable `action`, `ambiguity`, `reason`, URL resolver, shadow integration, enforcement, training, or production/runtime execution.
