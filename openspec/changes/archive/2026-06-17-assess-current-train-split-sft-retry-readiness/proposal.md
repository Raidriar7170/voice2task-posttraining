## Why

The current model evidence is now bound to `public-sample-20260616T165835Z`, but the newest blocked-payment repair rows have only entered the train split. Before launching another A100 SFT retry, the project needs a bounded readiness/design artifact that proves the current 118-row train split, repair rows, configs, and evidence boundaries are coherent.

## What Changes

- Add public-safe SFT retry config templates for a distinct current-train-split retry runtime.
- Run a local dry-run against the current formal public train split to confirm row counts and candidate-family coverage.
- Publish a readiness-only evidence pack that records current manifest counts, prior prediction-only metrics, train split coverage, repair-row coverage, config placeholders, and recommended next action.
- Refresh `CONTEXT.md`, `reports/final_status.md`, and a Human Brief with the readiness result and claim boundaries.
- Do not launch A100 training, DPO, GRPO, prediction, dataset mutation, evaluator changes, prompt changes, adapter/checkpoint publication, production-readiness claims, or live-browser benchmark claims.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, public checkpoint or adapter release, private-corpus generalization, production readiness, or live-browser benchmark claims.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: add a requirement for current-manifest SFT retry readiness evidence before launching a new bounded A100 SFT retry after train-only repair rows are materialized.

## Impact

- Affected configs: new public-safe current-train-split retry training and dev/test prediction config templates.
- Affected reports: new readiness-only evidence pack, Human Brief, `CONTEXT.md`, and `reports/final_status.md`.
- Affected code: small report/CLI helper and tests for current-train-split SFT retry readiness.
- Affected runtime: local dry-run only; no A100 training or prediction in this phase.
