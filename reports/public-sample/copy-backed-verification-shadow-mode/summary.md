# Copy-backed Verification Shadow Mode

Decision: `SHADOW_MODE_READY_FOR_REVIEW`.

Shadow mode is not enforcement. Source-backed provenance is not correctness.

## Metrics

- Prediction contracts: 828.
- Shadow sidecars: 828.
- Sidecar attachment rate: 1.000000.
- Enabled slot diagnostics: 430.
- Source-verified predictions: 376.
- Source-verified prediction rate: 0.874419.
- Source-verified and gold-correct: 347.
- Source-verified but gold-mismatch: 29.
- Action disabled diagnostics: 114.
- Enforcement enabled count: 0.
- Provenance false accepts: 0.
- Silent fallbacks: 0.

## Boundary

The sidecar file is diagnostic evidence only. It does not mutate predictions, gold contracts, schema, evaluator inputs, runtime behavior, or action semantics.
