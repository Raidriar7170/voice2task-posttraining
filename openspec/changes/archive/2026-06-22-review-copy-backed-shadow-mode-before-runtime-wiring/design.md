# Design: Copy-backed Shadow Interface Review

## Current Evidence
The previous shadow-mode phase already proves one diagnostic sidecar per current Control/Treatment prediction contract and preserves V1 evaluator behavior. Its report remains authoritative for that stage, but its sidecar diagnostics include offline correctness fields such as `gold_correct_exact`. This phase keeps the old artifact immutable and writes a new review bundle with a stricter boundary.

## Frozen Policy
The review uses `configs/copy-backed-scope-policy-v1.json` as a deterministic policy artifact. The effective hash is computed from the canonical JSON payload with the `policy_hash` field omitted. Replay validates that:

- `policy_id == copy-backed-scope-policy-v1`
- `action_enabled == false`
- `normalized_trusted == false`
- enabled triples are exactly the three approved query/field/target triples
- the stored policy hash matches the canonical hash

Any drift blocks with `SHADOW_REVIEW_BLOCKED_POLICY_DRIFT`.

## Interface Split
`OnlineShadowSidecar` is generated without gold input. It contains request/sample identity, input/prediction hashes, policy identity/hash, task/route, enforcement flags, and slot-level provenance diagnostics. It must not contain fields whose names or values expose gold/evaluator correctness.

`EvaluationAudit` is generated in a separate step by joining the online sidecar with the gold contract. It may contain correctness fields and is treated as offline evaluation evidence only.

## Trust Semantics
Trusted provenance is intentionally narrower than verifier success:

- `VERIFIED_EXACT_UNIQUE` with `match_kind=exact` can be trusted only after the full span gate passes.
- `VERIFIED_NORMALIZED_UNIQUE` is candidate provenance only; it records the normalization rule but never sets trusted provenance.
- All other statuses remain untrusted.
- `action` and all disabled scopes stay untrusted even if a text span is findable.

The false-accept counter increments only when a diagnostic is trusted but full validation or policy validation fails.

## Metrics
The report uses explicit denominators:

- `total_slot_event_count` includes every predicted slot event.
- `out_of_scope_rate` is over total slot events.
- `trusted_exact_rate`, `normalized_candidate_rate`, and `eligible_verification_failure_rate` are over eligible slot events.
- `global_non_verified_rate` is over total slot events.
- gold correctness rates are over trusted exact events.

The historical shadow `fail_closed_rate` is renamed to `legacy_global_non_verified_rate` when carried forward.

## Decision Labels
The final review label is:

- `SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK` when interface safety and evidence gates pass.
- `SHADOW_INTERFACE_READY_WITH_SCOPE_LIMITATIONS` when safety gates pass but per-scope evidence shows a scope limitation that should be handled before the hook.
- `SHADOW_INTERFACE_NOT_READY` for unsafe interface boundaries.
- `SHADOW_REVIEW_BLOCKED_INVALID_INPUT` for invalid source artifacts.
- `SHADOW_REVIEW_BLOCKED_POLICY_DRIFT` for frozen policy drift.

The next change may only be a prediction-hook shadow integration or a scope-refinement review. It is never runtime enforcement.
