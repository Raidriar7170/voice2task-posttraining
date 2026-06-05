## ADDED Requirements

### Requirement: Diagnose missing confirmation-required failures
The system SHALL surface missing `confirmation_required` as an explicit public-safe schema failure detail when predictions are contract-like enough for required-field diagnostics.

#### Scenario: Count missing confirmation-required
- **WHEN** diagnostic evidence is generated for prediction rows that omit `confirmation_required`
- **THEN** the diagnostic output MUST report a missing `confirmation_required` count without repairing, normalizing, coercing, or counting the affected predictions as schema-valid

#### Scenario: Bound confirmation-required repair interpretation
- **WHEN** local repair evidence, Human Briefs, or loop reports describe `confirmation_required` prompt or diagnostic changes
- **THEN** they MUST state that the phase is local prompt/evidence hardening only and MUST NOT claim private-adapter recovery, checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, or live-browser benchmark improvement
