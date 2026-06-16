## ADDED Requirements

### Requirement: Publish separate SFT v3 retry evidence
The system SHALL publish separate public-safe evidence for the post-SSH-recovery
SFT v3 retry, distinct from the previous blocked preflight record.

#### Scenario: Report observed retry metrics
- **WHEN** retry training and dev/test prediction-only evaluation complete
- **THEN** the evidence MUST report strict dev/test metrics using the existing
  contract ladder
- **AND** it MUST compare those metrics against the current formal public
  held-out baseline
- **AND** it MUST state that the previous blocked phase had no metrics

#### Scenario: Report blocked or failed retry
- **WHEN** the retry cannot safely complete
- **THEN** the evidence MUST record a blocked or failed status without
  fabricating predictions, metrics, adapters, or model-quality claims

#### Scenario: Preserve retry evidence boundaries
- **WHEN** retry evidence is prepared for commit
- **THEN** leak scan MUST reject raw private rows, absolute local paths, private
  remote paths, host details, SSH details, secrets, tokens, raw logs,
  checkpoints, adapters, caches, and oversized generated corpora
- **AND** reports MUST keep strict `contract_exact_match` and strict `slot_f1`
  as public headline metrics while labeling `slot_f1_soft` diagnostic-only
