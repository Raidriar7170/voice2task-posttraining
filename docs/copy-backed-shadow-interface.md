# Copy-backed Shadow Interface

This document records the reviewed interface boundary for copy-backed slot provenance before any prediction-pipeline shadow hook.

## 1. Interface purpose
The interface emits diagnostic provenance sidecars only. It does not enforce runtime behavior.

## 2. OnlineShadowSidecar dependency boundary
Online sidecars depend on input text, prediction contract, frozen policy, verifier output, request/sample identity, and hashes. They do not accept gold or evaluator inputs.

## 3. EvaluationAudit boundary
Evaluation audits are offline-only rows that join sidecars with gold correctness after sidecar generation.

## 4. Frozen scope policy
Policy `copy-backed-scope-policy-v1` version `1.0.0` has hash `5dc14efb8ded13dc048ddb067c7c63a1a62b6c03896950e861303973d505cbc7`.

## 5. Enabled scopes
Enabled scopes are `search:search_web:query`, `form_fill:fill_form:field`, and `extract:extract_page:target`.

## 6. Disabled scopes
`action` remains disabled and cannot become trusted provenance.

## 7. Trusted status
`VERIFIED_EXACT_UNIQUE` is the only trusted status.

## 8. Normalized status
`VERIFIED_NORMALIZED_UNIQUE` is candidate-only and records its normalization rule.

## 9. Full span gate
Trusted provenance requires policy enablement, exact status/match kind, one candidate span, valid offsets/hash, current input hash, and exact back-slice equality.

## 10. Metric denominators
Total/out-of-scope/global rates use total slot events; trusted/normalized/failure rates use eligible slot events; gold correctness rates use trusted exact events.

## 11. Per-scope review
Per-scope disable recommendations: [].

## 12. False accept and fallback gates
False accepts: 0; silent fallbacks: 0.

## 13. Non-mutation proof
Contract mutation count: 0; runtime decision delta count: 0; V1 evaluator zero delta: True.

## 14. Latency evidence
Local CPU p95 ms: policy lookup 0.000083, exact lookup 0.001750, full span validation 0.000542, serialization 0.006250. These are not production SLOs.

## 15. Decision and claim boundary
Decision: `SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK`. Trusted exact rate is 0.874419; eligible failure rate is 0.125581; out-of-scope rate is 0.543524; trusted-exact gold mismatch rate is 0.077128.

This phase does not implement an online prediction hook, runtime wiring, runtime enforcement, action enablement, model changes, training, evaluator changes, prediction repair, ContractCoreV2 changes, production readiness, or live-browser improvement.

## Review checks
- Online generation has no gold parameter: True.
- Online sidecars have no gold fields: True.
- Evaluation audit isolated: True.
