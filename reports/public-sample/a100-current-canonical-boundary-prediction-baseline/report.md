# A100 formal public held-out prediction

Status: prediction-only current-manifest held-out evidence. This phase does not train, mutate data, repair predictions, normalize slots, or change evaluator semantics.

## Scope

- Dataset manifest: `public-sample-20260619T090925Z`
- Run status: `blocked`
- Source adapter runtime: `a100-current-train-split-sft-retry`
- Overall interpretation: `formal_public_heldout_prediction_blocked`
- Blocked reason: `a100_ssh_preflight_timeout_no_safe_prediction_execution`

## Blocked Status

Blocked before private prediction. No model-quality metrics, held-out recovery claim, or adapter release claim is made from this artifact.

## Comparison Boundary

- Current dataset manifest: `public-sample-20260619T090925Z`
- Prior formal held-out manifest: `public-sample-20260617T152259Z`
- Prior evidence: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery`
- Prior blocked evidence: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline`
- Prior formal held-out metrics used a different public sample boundary and are not a clean direct improvement/regression comparison.
- Boundary note: target manifest changed to the canonical slot-boundary merge; old metrics are historical and not a direct improvement/regression comparison

## Boundary

- strict `contract_exact_match` and strict `slot_f1` remain primary.
- `slot_f1_soft` is diagnostic only.
- Predictions are not repaired, replaced, normalized, or re-scored.
- This is not held-out recovery unless dev/test strict exact both reach `1.0`; it is not a checkpoint release, adapter release, production-readiness claim, private-corpus generalization claim, public full-corpus release, or live-browser benchmark claim.
