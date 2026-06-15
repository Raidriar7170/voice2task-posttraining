## Why

The merged slot-value 7B A100 held-out evaluation recovered train exact match but still has strict residuals on dev/test. Before adding more data or changing training policy, we need a row-level, public-safe diagnosis of what those residuals actually are.

## What Changes

- Add a merged slot-value residual diagnosis path that consumes existing gold rows plus private prediction artifacts and emits only sanitized residual summaries.
- Publish a public-safe residual evidence pack that explains remaining dev/test strict mismatches by split, row id, contract field, slot behavior, and strict-vs-soft interpretation.
- Add focused tests for residual classification and public-safety boundaries.
- Generate a concise Chinese Human Brief for the diagnosis phase.
- Do not train a model, rerun prediction, alter evaluator semantics, repair predictions, normalize predictions, or change the formal public sample.
- Do not pursue generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, or public release of the full local corpus.
- Do not claim checkpoint release, adapter release, held-out recovery, production readiness, public full-corpus release, or live-browser benchmark improvement.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contract-evaluation`: add public-safe merged slot-value residual diagnosis evidence for dev/test strict residuals.

## Impact

- Affected code: evaluation/reporting helpers and a small CLI/reporting entry point.
- Affected artifacts: new OpenSpec change artifacts, focused tests, a public-safe residual diagnosis report, leak scan, and Human Brief.
- External systems: may read already-authorized A100 private prediction artifacts to derive a sanitized summary, but commits must not include private paths, raw logs, checkpoints, adapters, caches, host details, or secrets.
