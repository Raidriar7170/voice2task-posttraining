## ADDED Requirements

### Requirement: Publish confirmation-required A100 train-split rerun evidence
The system SHALL publish a public-safe evidence pack for the confirmation-required A100 train-split prediction rerun that separates raw attempt schema validity, retry attempt schema validity, validated output source, parse statuses, `confirmation_required` presence, prompt constraints, and final contract metrics.

#### Scenario: Import sanitized confirmation-required rerun evidence
- **WHEN** confirmation-required prediction metadata, predictions, prompt snapshot, sanitized raw decoded summary, generation trace, metrics, schema guard summary, confirmation-required diagnosis, and leak-scan results are available
- **THEN** the committed evidence MUST contain only public-safe artifacts and MUST omit private override files, raw private logs, private paths, host details, checkpoints, adapters, model caches, tokens, and private corpus rows

#### Scenario: Report confirmation-required rerun status
- **WHEN** the confirmation-required rerun report is generated from real private-adapter train-split predictions
- **THEN** it MUST report prediction count, raw attempt schema-valid count, retry attempt schema-valid count, validated output schema-valid count, missing `confirmation_required` count, validated output source distribution, parse status distribution, prompt constraints present at prediction time, and final contract metrics separately

#### Scenario: Compare only against the route-ontology baseline
- **WHEN** the report compares this rerun to prior evidence
- **THEN** it MUST identify `reports/public-sample/a100-route-ontology-train-split-rerun/` as pre-confirmation-required-repair context and MUST NOT treat any before/after difference as held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Keep confirmation-required rerun evidence public-safe
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths

#### Scenario: Bound confirmation-required rerun interpretation
- **WHEN** public documentation, metrics reports, Human Briefs, or loop reports describe the confirmation-required rerun
- **THEN** they MUST state that train-split prediction-only evidence does not prove dev/test generalization, production readiness, checkpoint release, adapter release, public full-corpus release, A100 model recovery, or live-browser benchmark improvement
