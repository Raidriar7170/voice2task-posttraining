# Recommended Next Change

- Decision label: `HYBRID_DESIGN_READY_COPY_SLICE_FIRST`
- Primary change id: `implement-copy-backed-slot-verification-slice`
- Scope: Implement only the verifier-owned copy-backed span/provenance slice for high-copyability slot paths while keeping BrowserTaskContract V1 external serialization unchanged.
- Target slot paths: query, field, target, action
- Fallback change id: `implement-task-specific-slot-schema-validator`
- Fallback scope: Low-risk validator-only slice for required/optional/forbidden slot keys after the copy verifier if copy ambiguity blocks implementation.

## Why This Slice First

- These paths have high observed copyability and concrete partial/copy residuals.
- The slice can be evaluated offline on current prediction artifacts without training.
- It adds fail-closed verifier-owned metadata without changing the external V1 schema.

## Acceptance Criteria

- No training, data mutation, evaluator relaxation, or V1 schema migration.
- Source spans use half-open Unicode offsets and exact back-slice validation.
- Provenance and verification_status are system-derived only.
- Unsupported or ambiguous spans fail closed or become unresolved.

## Hard Stop

This phase stops after design. It does not implement the vertical slice, train, expand data, modify schema, or build a challenge set.
