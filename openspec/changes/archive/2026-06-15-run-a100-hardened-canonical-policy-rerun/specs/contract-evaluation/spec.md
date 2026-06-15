## ADDED Requirements

### Requirement: Publish hardened canonical policy rerun evidence
The system SHALL publish public-safe evidence for the hardened canonical policy
prediction rerun while preserving strict metric semantics and claim boundaries.

#### Scenario: Compare rerun metrics against prior merged evidence
- **WHEN** train/dev/test metrics are available for the hardened-policy rerun
- **THEN** the evidence pack MUST record strict `contract_exact_match`,
  `slot_f1`, `slot_f1_soft`, `json_valid_rate`, and residual row counts by
  split
- **AND** it MUST compare those strict exact metrics with the prior merged
  slot-value held-out evidence

#### Scenario: Keep strict evidence boundaries
- **WHEN** public reports or Human Briefs describe the rerun
- **THEN** they MUST state that dev/test strict `contract_exact_match` remains
  primary
- **AND** they MUST NOT claim private-corpus generalization, checkpoint release,
  adapter release, production readiness, public full-corpus release, or
  live-browser benchmark improvement
- **AND** they MUST NOT treat `json_valid_rate`, train exact match, or soft
  slot F1 as model recovery

#### Scenario: Publish blocked status safely
- **WHEN** SSH, GPU placement, remote dependency, stale-code, or prompt-flag
  checks block the rerun
- **THEN** the evidence pack MUST record a blocked status and reason without
  private host details, private paths, raw logs, checkpoints, adapters, tokens,
  or private corpus rows
