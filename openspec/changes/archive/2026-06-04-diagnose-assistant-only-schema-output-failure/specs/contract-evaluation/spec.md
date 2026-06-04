## ADDED Requirements

### Requirement: Publish assistant-only schema-output diagnosis
The system SHALL publish a public-safe diagnosis for assistant-only A100 rerun outputs that are raw-JSON parseable but fail the Browser Task Contract schema.

#### Scenario: Separate raw JSON parseability from contract schema validity
- **WHEN** assistant-only rerun raw decoded outputs are parseable JSON objects but contract metrics report `json_valid_rate=0.0000`
- **THEN** the diagnosis MUST state that raw JSON parseability is not the same as schema-valid Browser Task Contract output

#### Scenario: Report row-level schema-output failure patterns
- **WHEN** the diagnosis analyzes assistant-only rerun predictions
- **THEN** it MUST report prediction count, raw JSON parseable count, contract schema-valid count, affected row ids, missing required fields, contract field mismatches, and likely failure family without repairing or coercing the predictions

#### Scenario: Preserve train-internal and public-safe boundaries
- **WHEN** the diagnosis is prepared for commit or Human Brief documentation
- **THEN** it MUST state `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, and MUST NOT expose private paths, host details, SSH details, raw logs, checkpoints, adapters, private rows, tokens, or make checkpoint release, adapter release, production readiness, held-out generalization, public full-corpus release, or live-browser benchmark improvement claims
