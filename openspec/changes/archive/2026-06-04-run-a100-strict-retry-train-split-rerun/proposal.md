## Why

The local constrained-decoding repair made retry parsing fail closed: retry outputs wrapped in Markdown or explanatory prose are no longer accepted as valid Browser Task Contracts. The previous required-field A100 rerun already has a private train-split adapter and sanitized decoded evidence, but that prediction path predated the strict retry parser. A narrow A100 prediction-only rerun can test whether the current strict retry/canonical prompt changes validated train-split output without spending another training run.

## What Changes

- Run a bounded A100 prediction-only rerun using the prior required-field repair private adapter and the current strict retry/canonical prediction code.
- Keep prediction scoped to public-sample train rows with `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and `schema_retry_enabled=true`.
- Copy back only sanitized public-safe evidence: predictions, prediction metadata, prompt snapshot, raw decoded summary, generation trace, metrics, schema guard summary, constrained decoding diagnosis, manifest, report, leak-scan result, and Human Brief HTML.
- Preserve raw and retry attempts exactly as observed; do not replace invalid model outputs with fixture, rule-baseline, gold-contract, or locally coerced contracts.
- Compare narrowly against the required-field repair rerun as pre-strict-retry evidence.

## Capabilities

### New Capabilities

### Modified Capabilities

- `supervised-contract-tuning`: add a bounded A100 prediction-only strict-retry rerun path after constrained decoding repair.
- `contract-evaluation`: add public-safe evidence requirements for strict-retry train-split prediction rerun results and non-claim boundaries.

## Impact

- Affected runtime path: `voice2task.cli.train sft-predict` on A100 with a repo-external private adapter config.
- Affected evidence surface: a new public-safe report directory under `reports/public-sample/`, one phase Human Brief under `docs/human-briefs/`, and an archived OpenSpec change.
- No new SFT training, DPO/GRPO, hyperparameter sweep, private-corpus training, checkpoint release, adapter release, public full-corpus release, held-out generalization claim, production-readiness claim, or live-browser benchmark improvement claim.
