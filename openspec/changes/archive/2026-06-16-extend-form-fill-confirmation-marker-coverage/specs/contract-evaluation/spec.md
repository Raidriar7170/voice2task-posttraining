## ADDED Requirements

### Requirement: Publish form-fill confirmation-marker coverage extension design
The system SHALL publish a public-safe confirmation-marker coverage extension design before materializing additional confirmation-marker candidate rows or launching training.

#### Scenario: Design extension from committed coverage evidence
- **WHEN** the confirmation-marker coverage extension design is generated
- **THEN** the evidence MUST record the source coverage artifact, source policy artifact, source manifest id, policy source-family counts, existing represented field labels, proposed candidate cases, represented source families, represented field labels, uncovered source families, and source count consistency
- **AND** it MUST state that it reads only committed public-safe artifacts

#### Scenario: Preserve design-only boundaries
- **WHEN** confirmation-marker extension design evidence is generated
- **THEN** it MUST state that no new candidate rows, seed traces, public sample splits, SFT rows, DPO pairs, held-out gold labels, prompts, evaluator metrics, predictions, checkpoints, adapters, or training jobs were created or changed
- **AND** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain diagnostic-only

#### Scenario: Bound the next materialization candidate
- **WHEN** the extension design recommends follow-up work
- **THEN** the recommendation MUST be labeled as a bounded next OpenSpec candidate for candidate materialization
- **AND** it MUST NOT materialize data, change prompts, change evaluator semantics, repair predictions, launch training, or claim held-out recovery in the same phase

#### Scenario: Validate extension design public safety
- **WHEN** confirmation-marker extension design artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora
