# Residual-Driven Remediation Target Selection

This is analysis and target-selection evidence only: strict exact is the canonical diagnostic, executable contract pass is a deterministic layered metric, normalized slot metrics are diagnostic only, and the current stage does not claim model improvement.

## Current Evaluation State

| split | samples | strict exact | executable contract pass | slot key F1 | slot value exact F1 | slot value normalized F1 | route acc | task type acc | risk acc | confirmation acc | unsafe FN rate | refusal/clarify acc |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev | 207 | 0.2464 | 0.2705 | 0.9872 | 0.2821 | 0.2821 | 0.9614 | 0.9614 | 1.0000 | 0.9758 | 0.0000 | 0.8667 |
| test | 207 | 0.2029 | 0.2512 | 0.9769 | 0.2390 | 0.2390 | 0.9758 | 0.9758 | 0.9952 | 0.9952 | 0.0083 | 0.9605 |

## Selected Next Targets

### safety-repair-unsafe-false-negative

- Strategy: `SAFETY_REPAIR`
- Target family: `unsafe_false_negative`
- Evidence count: `1`
- Proposed next change: `design-safety-repair-candidates`
- Why it matters: Unsafe false negatives can incorrectly downgrade blocked, payment, delete, send, upload, login, or other high-risk instructions into executable contracts.
- Expected measurable effect: Future bounded phase should reduce unsafe false negatives and preserve or improve requires-confirmation/risk-level accuracy without lowering strict exact.

### slot-value-canonicalization-policy

- Strategy: `SCHEMA_CANONICALIZATION`
- Target family: `slot_related_mismatches`
- Evidence count: `365`
- Proposed next change: `design-slot-canonicalization-policy`
- Why it matters: Slot value mismatches dominate residual fields while slot keys are comparatively stable, so the next bounded phase should decide canonical wording and value-policy boundaries before another training run.
- Expected measurable effect: Future bounded phase should improve slot value exact/normalized diagnostics and executable contract pass rate only after separate implementation/evaluation evidence.

## Boundaries

- No training, prediction rerun, data expansion, candidate merge, split change, DPO expansion, LoRA/base-model change, evaluator relaxation, LLM judge, semantic scoring, or prediction repair was performed.
- Do not claim held-out recovery, production readiness, safety readiness, released checkpoint/adapter, or live-browser benchmark improvement.
