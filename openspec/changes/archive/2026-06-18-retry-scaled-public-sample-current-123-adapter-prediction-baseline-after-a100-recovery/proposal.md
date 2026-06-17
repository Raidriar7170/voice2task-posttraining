## Why

The scaled public-sample manifest is now `public-sample-20260617T152259Z`, but the existing `a100-current-train-split-sft-retry` adapter has not yet produced observed dev/test prediction evidence on that boundary because the first attempt stopped at an A100 SSH timeout. Now that the A100 development machine is reported recovered, the project needs a bounded prediction-only retry to replace the blocked baseline with either observed strict metrics or fresh fail-closed blocked evidence.

## What Changes

- Run a fresh read-only A100 preflight for the existing scaled-manifest prediction configs.
- If the approved A100 path, adapter, environment, and an idle GPU are safe, run dev/test prediction-only exports for `public-sample-20260617T152259Z` using the existing private `a100-current-train-split-sft-retry` adapter.
- Evaluate the generated dev/test predictions with the existing strict contract ladder and publish only sanitized evidence artifacts under `reports/public-sample/`.
- Update `CONTEXT.md`, `reports/final_status.md`, and a concise Human Brief with the observed metrics or the refreshed blocked state.
- Archive the OpenSpec change after validation.
- Do not train, mutate data, change prompts, change evaluator logic, normalize slots, repair predictions, publish adapters/checkpoints, or claim recovery/production readiness.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contract-evaluation`: record observed-or-blocked A100 recovery retry evidence for the scaled public-sample prediction-only baseline while preserving strict metric and public-safe reporting boundaries.

## Impact

- Affected artifacts: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/`, `docs/human-briefs/2026-06-18-retry-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery.html`, `CONTEXT.md`, `reports/final_status.md`, OpenSpec archive metadata, and focused tests.
- Affected systems: the remote A100 development machine for prediction-only execution, with all remote writes constrained under the approved private A100 workspace root and all committed artifacts sanitized.
- No public API, schema, model release, training recipe, evaluator definition, prompt, or dataset contract changes are introduced.
