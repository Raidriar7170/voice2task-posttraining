## Why

The A100 first-pass output-boundary rerun proved the new boundary prompt was visible, but all three train-split predictions still arrived as Markdown-wrapped JSON fragments. A small local diagnosis is needed now to explain that persistence without changing parser behavior, repairing predictions, or overstating model quality.

## What Changes

- Publish a public-safe local diagnosis under `reports/public-sample/a100-first-pass-wrapper-persistence-diagnosis/`.
- Preserve the completed A100 rerun artifacts as immutable source evidence.
- Compare prompt boundary visibility, raw/retry wrapper counts, parse status, finish-state evidence, and strict schema-valid counts.
- Generate a concise Chinese Human Brief at `docs/human-briefs/2026-06-08-diagnose-first-pass-wrapper-persistence.html`.
- Keep training, A100 reruns, parser relaxation, evaluator metric changes, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, checkpoint/adapter release, and live-browser benchmark claims out of scope.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contract-evaluation`: add a bounded local evidence diagnosis for persistent Markdown wrapper output after first-pass boundary visibility is confirmed.

## Impact

- Affected artifacts: local diagnosis JSON/Markdown, manifest, leak scans, Human Brief, and a focused public-safety test.
- Affected runtime: none.
- Affected model behavior: none.
- No committed private config, raw remote log, private path, host detail, SSH detail, checkpoint, adapter, cache, or private corpus row.
