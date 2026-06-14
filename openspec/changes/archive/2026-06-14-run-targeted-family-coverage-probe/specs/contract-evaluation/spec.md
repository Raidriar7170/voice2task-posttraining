## ADDED Requirements

### Requirement: Publish targeted family coverage probe evidence
The system SHALL publish a public-safe evidence pack for the targeted family coverage probe that separates train learnability from held-out generalization and release claims.

#### Scenario: Generate targeted probe manifest
- **WHEN** targeted family coverage train/dev/test predictions and diagnostics are available
- **THEN** the manifest MUST record selected train source IDs, selected train row IDs, split metrics, primary held-out splits, comparison artifacts, evidence status, and non-claim boundaries
- **AND** it MUST identify whether dev/test strict exact improved from the current tiny-adapter held-out baseline

#### Scenario: Compare targeted probe with prior evidence
- **WHEN** the report interprets targeted probe results
- **THEN** it MUST compare against the current tiny-adapter held-out prediction evidence and the earlier broad public held-out residual repair evidence
- **AND** it MUST state whether the targeted source-family selection produced train memorization, held-out exact-match movement, both, or neither

#### Scenario: Bound targeted probe interpretation
- **WHEN** public documentation or Human Briefs describe targeted family coverage evidence
- **THEN** they MUST state that the evidence does not prove checkpoint release, adapter release, private-corpus generalization, production readiness, public full-corpus release, or live-browser benchmark improvement
- **AND** they MUST NOT promote soft slot F1 or semantic equivalence to the primary metric

#### Scenario: Validate targeted probe public safety
- **WHEN** targeted family coverage evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, model snapshots, oversized generated corpora, and private remote paths
