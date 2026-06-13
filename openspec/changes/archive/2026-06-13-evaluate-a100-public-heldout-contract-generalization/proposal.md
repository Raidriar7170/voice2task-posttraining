## Why

The previous 7B A100 canonical wording rerun reached strict exact match on the public train split, but that evidence only proves train-internal recovery. This phase is needed to check whether the same private adapter preserves Browser Task Contract behavior on committed public `dev` and `test` rows before considering any private-corpus or broader training work.

## What Changes

- Add public-safe A100 prediction config templates for `dev` and `test` held-out public-sample prediction using the existing 7B canonical wording adapter.
- Run prediction-only A100 evaluation for `dev` and `test`; do not retrain, change prompts, relax the evaluator, normalize predictions, or replace predictions with fixtures.
- Publish split-specific strict metrics, diagnostics, sidecars, and a combined held-out evidence manifest/report.
- Keep all claims bounded: this is public held-out diagnostic evidence, not checkpoint release, adapter release, private-corpus generalization, live-browser benchmark improvement, or production readiness.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: support bounded A100 public held-out prediction templates that reuse an existing private adapter without retraining.
- `contract-evaluation`: publish public-safe held-out diagnostic evidence that reports `dev`/`test` strict metrics separately and preserves non-claim boundaries.

## Impact

- Affected public artifacts: held-out A100 prediction config templates, `reports/public-sample/a100-public-heldout-contract-generalization/`, and a concise Chinese Human Brief.
- Affected tests: config/evidence-boundary tests for public-safe held-out prediction and split-separated metrics.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, new training runs, evaluator normalization, semantic-equivalence scoring, prediction repair/replacement, private full-corpus evaluation, released checkpoint/adapter claims, and live-browser benchmark claims.
