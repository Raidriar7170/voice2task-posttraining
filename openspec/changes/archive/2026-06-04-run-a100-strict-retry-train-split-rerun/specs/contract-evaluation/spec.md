## ADDED Requirements

### Requirement: Publish strict-retry A100 train-split prediction rerun evidence
The system SHALL publish a public-safe evidence pack for the strict-retry A100 train-split prediction rerun that separates raw attempt schema validity, retry attempt schema validity, validated output source, final contract metrics, constrained-decoding diagnosis, and non-claim boundaries.

#### Scenario: Import sanitized strict-retry rerun evidence
- **WHEN** strict-retry prediction metadata, predictions, prompt snapshot, sanitized raw decoded summary, generation trace, metrics, schema guard summary, constrained-decoding diagnosis, and leak-scan results are available
- **THEN** the manifest and report MUST link those sanitized artifacts, record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, prediction source kind, release status, schema retry policy, strict retry interpretation, and claim boundaries without private runtime details

#### Scenario: Report strict-retry recovery status
- **WHEN** the strict-retry rerun report is generated from real private-adapter train-split predictions
- **THEN** it MUST report raw attempt schema-valid count, retry attempt schema-valid count, validated output schema-valid count, validated output source distribution, parse status counts, and final contract metrics separately

#### Scenario: Compare strict retry narrowly
- **WHEN** the rerun evidence references prior required-field repair evidence
- **THEN** it MUST identify the prior evidence as pre-strict-retry context and MUST NOT treat any before/after difference as held-out generalization, checkpoint release, adapter release, production readiness, or live-browser benchmark improvement

#### Scenario: Keep strict-retry evidence public-safe
- **WHEN** strict-retry rerun evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

#### Scenario: Bound strict-retry interpretation
- **WHEN** public documentation, metrics reports, Human Briefs, or loop reports describe the strict-retry rerun
- **THEN** they MUST state that train-split prediction-only evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, A100 model recovery, or live-browser benchmark improvement
