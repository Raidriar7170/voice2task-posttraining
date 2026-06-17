## ADDED Requirements

### Requirement: Publish current-train-split SFT retry held-out evidence
The system SHALL publish separate public-safe dev/test strict evaluation
evidence for the current-train-split SFT retry adapter.

#### Scenario: Report observed current retry metrics
- **WHEN** retry training and dev/test prediction-only evaluation complete
- **THEN** the evidence MUST report strict dev/test metrics using the existing
  contract ladder
- **AND** it MUST compare observed metrics against the latest current-manifest
  prediction-only baseline for `public-sample-20260616T165835Z`
- **AND** it MUST keep strict `contract_exact_match` and strict `slot_f1` as
  public headline metrics while labeling `slot_f1_soft` diagnostic-only

#### Scenario: Report blocked or failed current retry
- **WHEN** the retry cannot safely complete
- **THEN** the evidence MUST record a blocked or failed status without
  fabricating predictions, metrics, adapters, or model-quality claims

#### Scenario: Preserve current retry public evidence boundaries
- **WHEN** retry evidence is prepared for commit
- **THEN** leak scan MUST reject raw private rows, absolute local paths, private
  remote paths, host details, SSH details, secrets, tokens, raw logs,
  checkpoints, adapters, caches, and oversized generated corpora
- **AND** reports MUST NOT claim production readiness, private-corpus
  generalization, public checkpoint release, public adapter release, or
  live-browser benchmark improvement
