## Why

The current public sample has advanced to `public-sample-20260616T165835Z` after the blocked-payment repair materialization, but the latest model-quality evidence is still bound to `public-sample-20260616T074315Z`. A bounded prediction-only baseline is needed so the project can answer "current model effect" without carrying metrics across a manifest comparison boundary.

## What Changes

- Run dev/test prediction-only evaluation for the current formal public sample using the existing private SFT v3 adapter.
- Publish a distinct public-safe evidence pack under `reports/public-sample/` bound to `public-sample-20260616T165835Z`.
- Record current manifest counts, split counts, prediction metadata, strict metrics, failure slices, leak scan results, comparison-boundary notes, and source adapter runtime.
- Keep strict `contract_exact_match` and strict `slot_f1` as public headline metrics; keep `slot_f1_soft` diagnostic-only.
- Do not train SFT/DPO/GRPO, mutate datasets, change prompts, relax evaluator metrics, repair or replace predictions, publish adapters/checkpoints, or claim production/live-browser improvement.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, public checkpoint or adapter release, private-corpus generalization, production readiness, or live-browser benchmark claims.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contract-evaluation`: require current-manifest prediction-only evidence for the existing SFT v3 private adapter after the blocked-payment repair public-sample merge, with explicit comparison-boundary and source-adapter-runtime reporting.

## Impact

- Affected configs: `configs/sft-a100-form-fill-remediation-v3-dev-prediction.json` and `configs/sft-a100-form-fill-remediation-v3-test-prediction.json`.
- Affected reports: a new public-safe evidence pack, a Human Brief, `CONTEXT.md`, and `reports/final_status.md`.
- Affected runtime: one prediction-only A100 run per dev/test split if GPU and adapter placement are safe.
- Affected code: minimal report-writer support to record the SFT v3 source adapter runtime instead of assuming the older merged-slot adapter.
