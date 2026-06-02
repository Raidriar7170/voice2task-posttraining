## ADDED Requirements

### Requirement: Compute contract evaluation ladder metrics
The system SHALL evaluate generated browser task contracts using schema validity, task type accuracy, route accuracy, safety precision/recall, confirmation accuracy, slot F1, and exact-match style contract checks where applicable.

#### Scenario: Evaluate model predictions
- **WHEN** the evaluator receives predictions and gold contracts for a split
- **THEN** it writes machine-readable metrics and a human-readable summary covering every metric in the contract evaluation ladder

### Requirement: Record failure slices
The system SHALL produce failure slices that identify common contract errors.

#### Scenario: Summarize failures
- **WHEN** predictions fail one or more metric checks
- **THEN** the evaluator groups failures by schema, task type, route, safety, confirmation, slot, and unknown categories with example identifiers

### Requirement: Run controlled execution smoke
The system SHALL support an optional execution smoke check that verifies generated contracts can be consumed by controlled Voice-to-Browser Agent validation paths.

#### Scenario: Run execution smoke
- **WHEN** execution smoke is enabled and a Voice-to-Browser Agent validation target is configured
- **THEN** the evaluator sends eligible contracts to the controlled validation path and reports smoke pass/fail separately from pure contract metrics

### Requirement: Keep reports public-safe
The system SHALL prevent public reports from leaking raw private rows, absolute local paths, secrets, tokens, or unreleased private details.

#### Scenario: Generate public report
- **WHEN** a report is written for committed documentation
- **THEN** it contains aggregate metrics, sanitized examples, manifest references, and explicit claim boundaries without raw local/private corpus rows
