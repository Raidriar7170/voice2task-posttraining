## Why

The reviewed scaled public-sample candidates have already been materialized as
standalone public-safe artifacts. The next bounded step is to promote those
candidates into the formal public sample so future evaluation or training phases
can bind to a new explicit manifest boundary instead of treating standalone
candidate evidence as formal data.

## What Changes

- Merge `data/public-samples/scaled_public_sample_seed_candidates.jsonl` into
  the formal public seed file.
- Rebuild `seed_traces.jsonl`, `sft_public_sample.jsonl`,
  `dpo_public_sample.jsonl`, and `manifest_public_sample.json`.
- Publish merge evidence under
  `reports/public-sample/scaled-public-sample-merge/`.
- Add a CLI command and focused tests for the guarded formal merge flow.
- Update project status docs and a concise Chinese Human Brief.
- Preserve boundaries: no training, no prediction, no A100 execution, no prompt
  change, no evaluator change, no slot normalization, no checkpoint/adapter
  release, and no model-quality claim.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `voice2task-dataset-preparation`: require a guarded formal merge path for
  reviewed scaled public-sample candidates with explicit comparison-boundary
  warnings.

## Impact

- Affected code:
  - `src/voice2task/dataset.py`
  - `src/voice2task/cli/data.py`
  - `src/voice2task/reports.py`
- Affected tests:
  - `tests/test_scaled_public_sample_public_sample_merge.py`
  - `tests/test_scaled_public_sample_candidate_materialization.py`
- Affected artifacts:
  - `data/public-samples/seed_traces.jsonl`
  - `data/public-samples/sft_public_sample.jsonl`
  - `data/public-samples/dpo_public_sample.jsonl`
  - `data/public-samples/manifest_public_sample.json`
  - `reports/public-sample/scaled-public-sample-merge/`
  - `docs/human-briefs/2026-06-17-merge-scaled-public-sample-candidates.html`
- Non-goals:
  - SFT, DPO, GRPO, or A100 execution
  - prediction generation
  - prompt or evaluator changes
  - slot normalization
  - checkpoint or adapter publication
  - model recovery, safety improvement, production-readiness, or live-browser
    benchmark claims
