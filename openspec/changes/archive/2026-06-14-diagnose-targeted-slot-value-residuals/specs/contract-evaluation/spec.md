## ADDED Requirements

### Requirement: Publish targeted slot value residual diagnosis
The system SHALL publish a public-safe diagnosis for the remaining targeted family coverage held-out residuals without changing predictions, metrics, or evaluator semantics.

#### Scenario: Classify remaining value residuals
- **WHEN** targeted family coverage dev/test gold rows, predictions, alignment diagnostics, and manifest evidence are available
- **THEN** the diagnosis MUST classify each remaining mismatching row by split, row id, source family, field path, and value-drift bucket
- **AND** it MUST aggregate residual counts by split, field path, source family, and drift bucket

#### Scenario: Preserve strict evaluation boundaries
- **WHEN** the targeted residual report is generated
- **THEN** it MUST state that strict `contract_exact_match` remains the primary metric
- **AND** it MUST NOT repair predictions, replace predictions, relax evaluator rules, or promote semantic equivalence or soft slot F1 to the primary metric

#### Scenario: Bound next-step recommendation
- **WHEN** the diagnosis recommends a next step
- **THEN** it MUST prefer a bounded slot value generalization/data-design diagnosis before broad scaling, DPO, or production claims
- **AND** it MUST state that the evidence does not prove held-out generalization recovery, private-corpus generalization, adapter release, checkpoint release, production readiness, or live-browser benchmark improvement

#### Scenario: Validate public safety
- **WHEN** targeted residual diagnosis artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, model snapshots, oversized generated corpora, and private remote paths
