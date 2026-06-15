## ADDED Requirements

### Requirement: Publish formal held-out residual family diagnosis
The system SHALL publish public-safe residual/family diagnosis evidence for the
current formal public held-out prediction artifacts without changing model
outputs or evaluator semantics.

#### Scenario: Diagnose formal held-out residual rows
- **WHEN** formal public held-out dev/test gold rows, predictions, and manifest
  metrics are available
- **THEN** the diagnosis MUST list strict residual rows by split, row id, source
  family id, contract family key, field path, mismatch category, and sanitized
  gold/prediction value summaries
- **AND** it MUST aggregate residuals by split, field path, source family,
  contract family, and category
- **AND** it MUST fail rather than publish if computed residual row counts do
  not match the source manifest residual counts

#### Scenario: Preserve strict metric boundaries
- **WHEN** the diagnosis references `contract_exact_match`, strict `slot_f1`,
  or `slot_f1_soft`
- **THEN** strict `contract_exact_match` and strict `slot_f1` MUST remain the
  primary metrics
- **AND** `slot_f1_soft` MUST be labeled as internal diagnostic-only and MUST
  NOT repair, normalize, re-score, or replace strict predictions

#### Scenario: Recommend a bounded next phase only
- **WHEN** the diagnosis summarizes likely residual clusters
- **THEN** it MAY recommend a next bounded OpenSpec phase
- **AND** it MUST NOT automatically materialize new data, change gold policy,
  launch training, launch DPO, modify evaluator behavior, or claim production
  readiness, model recovery, checkpoint release, adapter release,
  private-corpus generalization, public full-corpus release, or live-browser
  benchmark improvement
