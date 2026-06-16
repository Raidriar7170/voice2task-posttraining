# A100 formal public held-out prediction

Status: prediction-only current-manifest held-out evidence. This phase does not train, mutate data, repair predictions, normalize slots, or change evaluator semantics.

## Scope

- Dataset manifest: `public-sample-20260616T074315Z`
- Run status: `blocked`
- Source adapter runtime: `a100-merged-slot-value-heldout-eval`
- Overall interpretation: `formal_public_heldout_prediction_blocked`
- Blocked reason: `a100_ssh_timeout_remote_dependency_unavailable`

## Blocked Status

Blocked before private prediction. No model-quality metrics, held-out recovery claim, or adapter release claim is made from this artifact.

## Comparison Boundary

- Current dataset manifest: `public-sample-20260616T074315Z`
- Prior formal held-out manifest: `public-sample-20260616T022151Z`
- Prior evidence: `reports/public-sample/a100-formal-public-heldout-prediction`
- Prior formal held-out metrics used a different public sample boundary and are not a clean direct improvement/regression comparison.

## Boundary

- Strict `contract_exact_match` remains primary.
- `slot_f1_soft` is diagnostic only.
- Predictions are not repaired, replaced, normalized, or re-scored.
- This is not held-out recovery unless dev/test strict exact both reach `1.0`; it is not a checkpoint release, adapter release, production-readiness claim, private-corpus generalization claim, public full-corpus release, or live-browser benchmark claim.
