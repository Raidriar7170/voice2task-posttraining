# Hybrid Slot Representation V1

- Decision label: `HYBRID_DESIGN_READY_COPY_SLICE_FIRST`
- Evidence kind: design-only feasibility projection, not model-quality evidence.
- HybridSlotValue final fields: `value`, `value_type`, `representation_kind`, `source_span`, `normalization_rule`, `verification_status`, `provenance`, `fallback_behavior`.
- Model target recommendation: model outputs V1-compatible value; system verifies and attaches source span/provenance. The model does not directly output offsets.
- Source span semantics: Unicode character offsets, start inclusive, end exclusive, exact back-slice required, `source_text_hash` required.
- Overall representation coverage: 100.00%
- Copy-backed coverage: 57.32%
- Copy-normalize possible coverage: 1.70%
- Bounded structured coverage: 31.21%
- Limited free-generation coverage: 0.00%
- Unresolved coverage: 11.46%
- Currently verifiable prediction rate: 51.80%
- Currently fail-closed prediction rate: 48.20%
- Recommended next change: `implement-copy-backed-slot-verification-slice`
- Fallback next change: `implement-task-specific-slot-schema-validator`

## Claim Boundary

No training, prediction rerun, data mutation, schema migration, evaluator relaxation, runtime integration, checkpoint release, model improvement claim, slot performance improvement claim, or executable-quality improvement claim occurred.
