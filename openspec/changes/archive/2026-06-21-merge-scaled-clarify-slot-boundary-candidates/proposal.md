## Why

The scaled clarify slot-boundary candidates are now materialized as reviewed,
public-safe standalone seed/SFT sidecars. The next bounded step is to promote
those 9 clarify candidates into the formal public sample so future evidence can
bind to a new explicit manifest boundary instead of treating standalone
candidate artifacts as formal data.

## What Changes

- Merge `data/public-samples/scaled_clarify_slot_boundary_seed_candidates.jsonl`
  into the formal public seed file.
- Rebuild `seed_traces.jsonl`, `sft_public_sample.jsonl`,
  `dpo_public_sample.jsonl`, and `manifest_public_sample.json`.
- Publish merge evidence under
  `reports/public-sample/scaled-clarify-slot-boundary-public-sample-merge/`.
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
  reviewed scaled clarify slot-boundary candidates with explicit comparison
  boundary and strict-metric claim warnings.

## Impact

- Affected code:
  - `src/voice2task/dataset.py`
  - `src/voice2task/cli/data.py`
  - `src/voice2task/reports.py`
- Affected tests:
  - `tests/test_scaled_clarify_slot_boundary_public_sample_merge.py`
  - `tests/test_scaled_clarify_slot_boundary_candidate_materialization.py`
- Affected artifacts:
  - `data/public-samples/seed_traces.jsonl`
  - `data/public-samples/sft_public_sample.jsonl`
  - `data/public-samples/dpo_public_sample.jsonl`
  - `data/public-samples/manifest_public_sample.json`
  - `reports/public-sample/scaled-clarify-slot-boundary-public-sample-merge/`
  - `docs/human-briefs/2026-06-18-merge-scaled-clarify-slot-boundary-candidates.html`
- Non-goals:
  - generic chat fine-tuning, skill routing, or GUI action policy learning
  - SFT, DPO, GRPO, or A100 execution
  - prediction generation
  - prompt or evaluator changes
  - slot normalization or prediction repair
  - checkpoint or adapter publication
  - public release of the full local/private corpus
  - model recovery, safety improvement, production-readiness,
    private-corpus generalization, public full-corpus release, or live-browser
    benchmark claims
