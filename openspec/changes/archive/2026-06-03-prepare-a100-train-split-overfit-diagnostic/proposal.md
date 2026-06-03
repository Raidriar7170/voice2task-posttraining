## Why

The source-alignment phase showed that public targets are clean, while A100 predictions still emit path-like routes and list slots. Before another private A100 rerun, the repository needs a bounded train-split/overfit diagnostic path that can prove what prompt, objective, decoding, and row-level evidence were used without leaking private infrastructure or overstating generalization.

## What Changes

- Add local preparation for an A100 train-split overfit diagnostic rerun: public-safe config templates, run metadata fields, and evidence boundaries.
- Add prediction-side evidence artifacts for future private-adapter runs: prompt snapshot, sanitized raw decoded summary, generation trace, and explicit train-split prediction metadata.
- Add an SFT objective inspection surface that can verify whether prompt/system/user tokens are masked and assistant contract tokens remain trainable before treating overfit loss as meaningful.
- Extend report/manifest support for train-split overfit evidence with clear claim boundaries: train-internal recovery only, no generalization claim.
- Non-goals: directly launching remote A100 execution in this local phase, generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local/private corpus, checkpoint release, adapter release, production-readiness claims, and live-browser benchmark improvement claims.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add train-split overfit diagnostic preparation, objective inspection, and prediction evidence sidecars.
- `contract-evaluation`: add public-safe train-split overfit evidence reporting and claim boundaries.

## Impact

- Affected code: SFT/prediction training helpers, CLI surfaces, reports, leak-safe evidence generation, and tests.
- Affected configs: public-safe A100 train-split diagnostic templates that still require private override resolution before remote execution.
- Affected artifacts: new local diagnostic evidence templates and Chinese Human Brief HTML.
- No new checkpoint, adapter, raw log, remote cache, host, SSH, private path, or private corpus artifact may be committed.
