## Why

The confirmation-marker extension candidates are now materialized as standalone seed/SFT rows, but they have not yet been checked through the public dataset builder together with the current formal public sample. A local preview integration check can prove the candidate file is build-compatible while preserving the formal public sample boundary.

## What Changes

- Add a deterministic preview integration check for the standalone confirmation-marker extension candidate seed file.
- Build a report-scoped preview dataset by combining the current formal public sample seed rows with the 12 standalone extension candidate rows.
- Publish JSON, Markdown, and manifest evidence under `reports/public-sample/` with formal counts, preview counts, candidate contribution counts, validation status, and claim boundaries.
- Add a `voice2task-data` CLI command for this preview-only integration check.
- Preserve preview-only boundaries: no formal public sample mutation, no committed split rebuild, no DPO mutation in the formal files, no prediction, no training, no A100 execution, no evaluator relaxation, and no held-out/model recovery claims.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `voice2task-dataset-preparation`: require a local preview integration check for standalone form-fill confirmation-marker extension candidates before any later formal merge, training, or held-out evaluation decision.

## Impact

- Affected code: `src/voice2task/dataset.py`, `src/voice2task/cli/data.py`, and `src/voice2task/reports.py`.
- Affected tests: new focused tests for confirmation-marker extension candidate integration preview.
- Affected artifacts: new preview evidence under `reports/public-sample/form-fill-confirmation-marker-extension-candidate-integration-preview/`.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, formal public sample mutation, prompt change, evaluator relaxation, prediction repair, prediction run, SFT/DPO/GRPO training, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement claims.
