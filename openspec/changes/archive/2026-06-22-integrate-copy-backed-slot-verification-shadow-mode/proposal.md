## Why

The copy-backed verification slice proved deterministic source provenance for task-scoped `query`, `field`, and `target`, but it is still a standalone audit surface. The next bounded step is to integrate the verifier as shadow-mode sidecars over current Control/Treatment predictions without changing V1 contracts, evaluator semantics, runtime behavior, or action handling.

## What Changes

- Add a read-only shadow-mode integration script that emits one sidecar record per prediction contract and nested verifier diagnostics per slot.
- Reuse the existing copy-backed verifier and task-scoped policy; do not introduce new matching semantics.
- Validate the prior copy-slice readiness boundary before writing success reports, and fail closed with a blocked artifact when the boundary is invalid.
- Generate compact public-safe shadow-mode reports under `reports/public-sample/copy-backed-verification-shadow-mode/`.
- Document shadow-mode semantics, sidecar schema, enforcement boundaries, action exclusion, and claims not to overstate.
- Update README/CONTEXT/evidence index and generate a concise Chinese Human Brief.

## Capabilities

### New Capabilities

- `copy-backed-verification-shadow-mode`: Sidecar-only integration of copy-backed slot verification over current prediction contracts, with no contract mutation or runtime enforcement.

### Modified Capabilities

- None. Existing `copy-backed-slot-verification`, `BrowserTaskContract` V1, `ContractCoreV2`, evaluators, recovered predictions, training targets, data, and runtime behavior remain behaviorally unchanged.

## Impact

- Adds a shadow-mode report script, focused tests, docs, public-safe reports, and OpenSpec artifacts.
- Reads current recovered raw inputs and the archived copy-backed verification slice reports.
- Does not mutate predictions, gold contracts, public sample data, V1 evaluator inputs/outputs, schemas, prompts, training artifacts, runtime code, or browser automation.
- Does not enable `action`, runtime enforcement, production gating, prediction repair, LLM judging, fuzzy matching, URL/date/entity resolvers, or model-quality claims.
