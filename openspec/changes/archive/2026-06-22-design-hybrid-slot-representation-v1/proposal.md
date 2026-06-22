## Why

The completed slot error mechanism analysis concluded `MIXED_SLOT_REPRESENTATION_REQUIRED`: roughly half of gold slot events are exact/normalized source-copyable, while roughly half are source-absent or generation-required, with typed-derivable coverage currently at 0.00%. A single slot representation cannot cover copyable entities, schema/key constraints, URL resolution boundaries, ambiguity/reason fields, and fail-closed unsupported cases without either overclaiming span extraction or leaving unrestricted free generation as the default.

## What Changes

- Design Hybrid Slot Representation V1 as an internal-only future boundary proposal while keeping `BrowserTaskContract` V1 external behavior unchanged.
- Define representation kinds, verifier-owned source span/provenance semantics, normalization-rule ownership, model-authored vs system-derived field boundaries, and fail-closed unsupported behavior.
- Produce a task-type / slot-path representation matrix from current public-safe evidence, including copy-backed, copy-then-normalize, enum/classification, task-schema-constrained, bounded-structured, limited-free-generation, and unresolved strategies.
- Generate a read-only offline feasibility projection over current gold/prediction artifacts without mutating predictions, changing evaluator semantics, or recalculating model success metrics.
- Recommend one bounded next vertical slice and one fallback at most.
- Update only concise truth-surface documentation and evidence indexes for the design outcome.

## Capabilities

### New Capabilities

- `hybrid-slot-representation-v1`: Design-only capability for an internal hybrid slot value representation, source-span/provenance semantics, representation matrix, feasibility projection, and next-slice decision.

### Modified Capabilities

- None. Existing `contract-evaluation`, `internal-contract-core-v2`, `slot-canonicalization-policy`, and training/data capabilities remain behaviorally unchanged.

## Impact

- New design/report artifacts under `docs/` and `reports/public-sample/hybrid-slot-representation-v1/`.
- One bounded read-only design/feasibility script and focused tests may be added.
- `README.md`, `README_en.md`, `CONTEXT.md`, and `reports/public-sample/EVIDENCE_INDEX.md` may receive short evidence-surface updates.
- No training, DPO/GRPO, A100/GPU work, prediction rerun, data mutation, schema implementation, evaluator relaxation, runtime integration, checkpoint/adapter release, generic chat fine-tuning, skill routing, GUI action policy learning, public full-corpus release, or live-browser benchmark claim is in scope.
