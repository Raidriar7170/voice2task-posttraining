## ADDED Requirements

### Requirement: Report slot value case-design evidence with strict metric boundaries
The system SHALL report slot value generalization case designs as design-only evidence and not as model-quality evidence.

#### Scenario: Bound case-design interpretation
- **WHEN** reports or Human Briefs describe slot value generalization case designs
- **THEN** they MUST state that the design does not prove model recovery, held-out generalization, private-corpus generalization, adapter release, checkpoint release, production readiness, or live-browser benchmark improvement
- **AND** they MUST state that soft slot F1 and semantic equivalence remain diagnostic-only

#### Scenario: Validate public safety
- **WHEN** slot value generalization case-design artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, model snapshots, oversized generated corpora, and private remote paths
