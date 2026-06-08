## Why

The local `repair-first-pass-markdown-fence-suppression` phase added tokenizer-derived `bad_words_ids` wiring for Markdown fence suppression, but local tests cannot prove whether the private adapter will stop emitting fenced JSON. The next smallest evidence step is a prediction-only A100 train-split rerun that observes the same three train rows under the new decoding policy while preserving strict whole-string parsing.

## What Changes

- Run one bounded A100 prediction-only train-split rerun using the existing private adapter path and current first-pass Markdown fence suppression decoding policy.
- Keep all A100 outputs, private overrides, model caches, raw logs, adapters, checkpoints, SSH details, host details, tokens, and private paths outside git.
- Import only sanitized public-sample evidence: predictions, prediction metadata, prompt snapshot, raw decoded summary, generation trace, metrics, schema guard summary, rerun diagnosis, leak scans, manifest, report, and Human Brief.
- Compare narrowly against `reports/public-sample/a100-first-pass-output-boundary-rerun/` and `reports/public-sample/a100-first-pass-wrapper-persistence-diagnosis/`.
- Preserve strict parser/evaluator semantics: no parser relaxation, no fence stripping after decode, no prediction repair, no re-score, no semantic-equivalence scoring, and no slot normalization.
- Keep training, adapter/checkpoint release, public full-corpus release, generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, and live-browser benchmark claims out of this phase.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add a bounded A100 prediction-only train-split rerun path after first-pass Markdown fence suppression.
- `contract-evaluation`: add public-safe evidence requirements and non-claim boundaries for the first-pass fence-suppression A100 rerun.

## Impact

- Affected runtime path: `voice2task.cli.train sft-predict` on A100 with a repo-external private override and approved private output root.
- Affected evidence: new public-safe report directory under `reports/public-sample/a100-first-pass-fence-suppression-rerun/` and a Chinese Human Brief under `docs/human-briefs/`.
- No committed dependency changes, no training run, no parser/evaluator change, no prediction repair/re-score, no checkpoint/adapter publication, and no live-browser benchmark improvement claim.
