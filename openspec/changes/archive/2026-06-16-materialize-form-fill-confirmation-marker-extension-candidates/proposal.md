## Why

The confirmation-marker extension design proposes 12 source-family-level cases, but they are still reviewable design rows rather than runnable candidate data. Materializing them as a standalone candidate dataset gives the project a public-safe, testable next artifact without mutating the formal public sample or claiming model recovery.

## What Changes

- Add a deterministic materializer that reads `form_fill_confirmation_marker_coverage_extension.json` and writes standalone confirmation-marker extension candidate seed rows plus candidate SFT rows.
- Publish JSON, Markdown, and manifest evidence under `reports/public-sample/` with source design identity, candidate counts, provenance, and strict no-mutation/no-training boundaries.
- Add a CLI command for local candidate-only materialization.
- Add focused tests for source design validation, candidate row shape, provenance, public-sample immutability, report boundaries, and public-safety scanning.
- Preserve candidate-only boundaries: no formal public sample merge, no seed trace mutation, no DPO mutation, no prompt change, no evaluator relaxation, no prediction run, no A100 job, no SFT/DPO/GRPO training, no checkpoint or adapter release, and no held-out recovery claim.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `voice2task-dataset-preparation`: require public-safe, standalone materialization of reviewed form-fill confirmation-marker extension candidates before any later merge, training, or held-out evaluation decision.

## Impact

- Affected code: `src/voice2task/dataset.py`, `src/voice2task/cli/data.py`, and `src/voice2task/reports.py`.
- Affected tests: new focused tests for confirmation-marker extension candidate materialization.
- Affected artifacts: new candidate data under `data/public-samples/` and evidence under `reports/public-sample/`.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, formal public sample mutation, prompt change, evaluator relaxation, prediction repair, prediction run, SFT/DPO/GRPO training, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement claims.
