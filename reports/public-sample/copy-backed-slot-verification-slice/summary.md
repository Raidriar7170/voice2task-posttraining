# Copy-backed Slot Verification Slice

Decision: `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`.

This is an offline sidecar-only verification slice. Source-backed provenance is not correctness.

## 17-question closeout

1. Enabled task-scoped triples: `extract:extract_page:target, form_fill:fill_form:field, search:search_web:query`.
2. Action not enabled: Action semantics are tied to blocked/clarify/safety contexts and are analysis-only in this slice.
3. strategy_assignment_rate: 1.000000.
4. copy_strategy_candidate_coverage: 0.573248.
5. Gold unique exact span rate: 0.863850.
6. Gold unique normalized span rate: 0.000000.
7. Duplicate ambiguity rate: 0.000000.
8. Span not-found rate: 0.136150.
9. Control/Treatment source-verified prediction rate: 0.874419.
10. Source-verified-and-gold-correct rate: 0.922872.
11. Source-verified-but-gold-mismatch rate: 0.077128.
12. provenance_false_accept_count=0: `True`.
13. silent_fallback_count=0: `True`.
14. V1 evaluator zero delta: `True`.
15. Final decision label: `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`.
16. Unique next change: `integrate-copy-backed-slot-verification-shadow-mode`.
17. Current cannot claim: source-backed provenance is task correctness; slot accuracy improved; executable pass improved; model quality improved; training target changed; BrowserTaskContract V1 migrated; ContractCoreV2 changed; runtime or shadow integration exists; action verification is enabled; production or safety readiness; held-out recovery; live browser improvement.

## Metrics

- Eligible gold copy events: 213.
- Unique verified gold span rate: 0.863850.
- Eligible prediction events: 430.
- Source-verified prediction count: 376.
- Source span roundtrip pass rate: 1.000000.
- Provenance false accept count: 0.
- Silent fallback count: 0.

## Claim Boundary

No training, prediction rerun, V1 schema migration, evaluator relaxation, runtime integration, action enablement, model-improvement claim, slot-accuracy claim, executable-quality claim, production-readiness claim, held-out-recovery claim, or live-browser claim occurred.
