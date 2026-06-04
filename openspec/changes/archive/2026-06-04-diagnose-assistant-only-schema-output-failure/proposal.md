## Why

The A100 assistant-only train-split rerun proved that prompt tokens are masked and assistant contract tokens carry loss, but all three train predictions still failed the Browser Task Contract schema. Before changing decoding, prompt constraints, sample recipes, or training objectives, the project needs a bounded public-safe diagnosis of what kind of schema-output failure remains.

## What Changes

- Add a public-safe schema-output diagnosis for the assistant-only A100 rerun evidence.
- Distinguish raw JSON parseability from schema-valid Browser Task Contract output.
- Attribute failures by row id and contract field, including required-field omissions and field-level mismatch patterns.
- Preserve observed invalid outputs without repair, coercion, fixture replacement, or gold-contract substitution.
- Record a recommended next bounded phase without claiming checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, or live-browser benchmark improvement.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contract-evaluation`: require a public-safe assistant-only schema-output diagnosis that explains why the train-split rerun remains schema-invalid.

## Impact

- Adds diagnostic evidence under `reports/public-sample/a100-assistant-only-train-split-rerun/`.
- Adds a focused regression test for the diagnosis artifact and report wording.
- Adds a concise Chinese Human Brief for the diagnostic phase.
- Does not change model training, decoding behavior, public data, runtime execution, or release posture.
