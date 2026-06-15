## Why

The family-stratified candidate dataset has been generated and reviewed as the
next data-generalization surface, but it is still outside the formal public
sample. To make it usable for future held-out prediction-only evaluation and
training configs, the reviewed candidate seeds need an explicit, reproducible,
public-safe merge into the formal sample.

This change updates the formal public sample data boundary without launching
training, changing evaluator semantics, or claiming model-quality recovery.

## What Changes

- Add a merge path for the reviewed family-stratified candidate seed file.
- Append exactly the reviewed family-stratified candidate seeds to
  `data/public-samples/seed_traces.jsonl`.
- Preserve each candidate seed's `train`, `dev`, or `test` split instead of
  forcing all rows into train.
- Rebuild `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, and
  `manifest_public_sample.json` from the merged formal seed file.
- Extend manifest source summary with family-stratified formal-sample metadata.
- Add a public-safe merge evidence report and concise Chinese Human Brief.
- Add tests for merge validation, CLI behavior, committed artifact counts,
  split preservation, provenance, and public-safety boundaries.

## Non-Goals

- Do not run SFT, DPO, GRPO, A100 prediction, or live-browser evaluation.
- Do not change strict `contract_exact_match`, normalized-command scoring,
  prediction repair, semantic-equivalence scoring, or any evaluator semantics.
- Do not add visual-reference, GUI action policy, skill-routing, generic chat
  data, or public release of a full local/private corpus.
- Do not claim held-out generalization recovery, model recovery, checkpoint
  release, adapter release, production readiness, private-corpus
  generalization, or live-browser benchmark improvement.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `voice2task-dataset-preparation`: add an explicitly approved merge path for
  reviewed family-stratified candidates into the formal public sample.

## Impact

- `src/voice2task/dataset.py`: add reviewed family-stratified merge validation,
  formal provenance conversion, manifest source-summary metadata, and merge
  evidence generation.
- `src/voice2task/reports.py`: add a public-safe family-stratified merge report
  writer.
- `src/voice2task/cli/data.py`: add a CLI command to run the merge.
- `data/public-samples/`: update formal seed, SFT, DPO, and manifest artifacts.
- `reports/public-sample/`: add merge evidence artifacts.
- `docs/human-briefs/`: add a concise Chinese phase brief.
- `tests/`: add focused TDD coverage and update committed formal-sample
  expectations.
