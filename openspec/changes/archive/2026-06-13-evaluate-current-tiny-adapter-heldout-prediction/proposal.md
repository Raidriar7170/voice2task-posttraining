## Why

The current-manifest tiny-overfit probe showed that the 7B adapter can memorize
three current train rows, but that result is train-internal only. Before changing
training strategy, data volume, DPO, prompts, or evaluator behavior, we need a
bounded held-out diagnostic that reuses the same private adapter on the current
public manifest's `dev` and `test` splits.

## What Changes

- Add public-safe prediction-only config templates for the current-manifest tiny
  adapter on `dev` and `test`.
- Run A100 prediction-only exports with private overrides, using the existing
  private 7B adapter from `run-current-manifest-tiny-overfit-probe`.
- Import only sanitized split evidence and a combined public-safe manifest/report.
- Keep interpretation explicitly separate from private-corpus generalization,
  production readiness, adapter release, checkpoint release, and live-browser
  benchmark claims.

## Non-Goals

- No new SFT or DPO training.
- No dataset expansion or hard-negative generation.
- No evaluator relaxation, semantic-equivalence scoring, slot normalization, or
  prediction repair.
- No release or production-readiness claim.

## Expected Outcome

We will know whether the current tiny adapter's 3-row train-internal success
transfers at all to the current manifest's held-out `dev` and `test` rows. The
result may be negative; either way it becomes the evidence boundary for deciding
whether the next stage should diagnose data coverage, training objective, prompt
policy, or preference tuning.
