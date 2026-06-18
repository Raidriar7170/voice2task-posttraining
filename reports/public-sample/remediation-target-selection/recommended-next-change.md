# Recommended Next OpenSpec Change

- proposed change id: `design-safety-repair-candidates`

## Problem Statement

Unsafe false negatives can incorrectly downgrade blocked, payment, delete, send, upload, login, or other high-risk instructions into executable contracts.

## Evidence from Current Layered/Residual Artifacts

- target_family: `unsafe_false_negative`
- evidence_count: `1`
- strategy: `SAFETY_REPAIR`
- primary_source: `layered_eval_summary`
- supporting_sources: `layered_eval`, `residual_diagnosis`

## Scope

- design public-safe safety repair candidates
- define fail-closed safety policy examples
- add deterministic safety-boundary tests

## Acceptance Criteria

- Preserve strict evaluator semantics and existing layered/residual artifacts.
- Keep all artifacts public-safe and leak-scan clean.
- Measure the next bounded phase against strict exact, executable contract pass, slot metrics, and safety metrics as applicable.

## Non-goals

- no training
- no prediction repair
- no production safety claim
- no evaluator relaxation

## Expected Metrics to Watch

- `contract_exact_match_strict`
- `executable_contract_pass_rate`
- `slot_value_exact_f1`
- `slot_value_normalized_f1`
- `unsafe_false_negative_rate`
- `requires_confirmation_accuracy`
- `risk_level_accuracy`

## Claim boundaries

- Do not claim held-out recovery.
- Do not claim model improvement.
- Do not claim production readiness.
- Do not claim safety readiness.
- Do not claim live-browser benchmark improvement.
- Do not treat normalized slot metrics as recovery evidence.
