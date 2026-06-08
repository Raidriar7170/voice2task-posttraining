## ADDED Requirements

### Requirement: Publish compact query slot preservation A100 rerun evidence
The system SHALL publish public-safe train-split evidence for the compact query slot preservation A100 rerun that compares strict slot-shape outcomes against the previous `city/date/topic` residual without changing evaluator semantics.

#### Scenario: Generate compact query rerun evidence pack
- **WHEN** sanitized A100 rerun predictions, sidecars, metrics, and leak scans are available
- **THEN** the evidence pack MUST include prediction count, `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metrics, row-level slot-shape outcomes, prompt/policy visibility, schema guard summary, source residual links, validation commands, and leak-scan results
- **AND** it MUST record whether `seed-search-weather-aug-1` uses compact `slots.query` or remains a decomposed `city/date/topic` strict mismatch
- **AND** it MUST avoid private paths, host details, SSH details, raw logs, checkpoints, adapters, caches, tokens, secrets, and private corpus rows

#### Scenario: Bound compact query rerun interpretation
- **WHEN** reports, Human Briefs, loop reports, or archived OpenSpec artifacts describe the rerun
- **THEN** they MUST state that this is A100 prediction-only train-split diagnostic evidence
- **AND** they MUST NOT claim held-out generalization, production readiness, model-quality improvement, model recovery, checkpoint release, adapter release, public full-corpus release, live-browser benchmark improvement, evaluator relaxation, parser relaxation, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, or re-score

#### Scenario: Preserve strict comparison to prior residual
- **WHEN** the rerun evidence compares against prior compact-query residual evidence
- **THEN** it MUST preserve prior A100 predictions and metrics as historical evidence and MUST NOT repair, normalize, re-score, or reinterpret prior `city/date/topic` outputs as exact-match recovery
