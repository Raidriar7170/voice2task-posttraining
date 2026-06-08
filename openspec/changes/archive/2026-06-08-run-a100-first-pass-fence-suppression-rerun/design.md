## Context

The last A100 first-pass output-boundary rerun showed `3/3` Markdown-wrapped predictions and `0/3` strict schema-valid output, even though first-pass output-boundary metadata was visible. The local fence-suppression phase then wired tokenizer-derived Markdown fence strings into generation-time `bad_words_ids`, with tests proving the argument is passed for raw and retry generation calls and strict parser behavior remains unchanged.

This phase is the observation step. It runs prediction only, against the existing private adapter, and imports sanitized public evidence. It does not train or modify model artifacts.

## Goals / Non-Goals

**Goals:**

- Verify A100 runtime placement under the approved private project root and select a safe idle GPU.
- Run one train-split prediction-only export through the current code path with Markdown fence suppression metadata.
- Generate public-safe evidence that records Markdown wrapper counts, strict schema-valid count, strict exact match, raw/retry parse statuses, generation trace, and claim boundaries.
- Compare narrowly against the prior first-pass output-boundary rerun and wrapper-persistence diagnosis.
- Archive the OpenSpec change and commit only sanitized evidence.

**Non-Goals:**

- No training, checkpoint release, adapter release, deployment, private corpus publication, or public full-corpus release.
- No parser relaxation, decoded-output fence stripping, embedded JSON extraction, prediction repair, output coercion, evaluator metric change, re-score, semantic-equivalence scoring, or slot normalization.
- No claim of model recovery, held-out generalization, production readiness, model-quality improvement, or live-browser benchmark improvement.

## Decisions

1. Use prediction-only train-split rerun instead of training.

   The local change affects generation-time decoding, so retraining would mix evidence. Prediction-only rerun isolates whether decoded output wrappers change under the current private adapter and code path.

2. Keep strict metrics as the only success boundary.

   Markdown wrapper count can be reported as diagnostic evidence, but strict schema-valid output and strict exact match remain the metrics. Wrapped fragments still count invalid.

3. Import only sanitized artifacts.

   Remote private config, output root, logs, caches, checkpoints, adapters, host details, and SSH details remain outside git. Public evidence uses placeholders and aggregate/public-sample rows only.

## Risks / Trade-offs

- [Risk] No idle GPU is available or process ownership is unclear. -> Stop before launching remote prediction.
- [Risk] Private adapter path or override is unavailable. -> Stop with blocked evidence, do not fabricate fixture output.
- [Risk] `bad_words_ids` changes wrapper behavior but schema remains invalid for other reasons. -> Report wrapper deltas separately from strict metrics and avoid model-quality claims.
- [Risk] A100 output still contains Markdown fences. -> Preserve it as bounded failure evidence and recommend a later decoding/prompt/training investigation rather than relaxing parser semantics.
