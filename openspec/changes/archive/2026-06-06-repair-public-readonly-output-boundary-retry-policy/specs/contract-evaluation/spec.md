## ADDED Requirements

### Requirement: Publish output-boundary retry-policy repair evidence
The system SHALL publish public-safe local evidence for the public-readonly output-boundary and retry-prompt repair while preserving strict metrics and prior A100 negative evidence.

#### Scenario: Generate local repair manifest
- **WHEN** the local prompt/retry policy repair is complete
- **THEN** the manifest MUST link the prior A100 public-readonly rerun evidence, record prompt constraint flags for single-root object and retry JSON-only guidance, and state that no A100 execution, training, private prediction, prediction repair, or evaluator metric change occurred

#### Scenario: Bound repair interpretation
- **WHEN** public documentation or Human Briefs describe the repair
- **THEN** they MUST state that this phase only prepares a later rerun and does not prove model recovery, held-out generalization, production readiness, checkpoint release, adapter release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Validate repair evidence boundaries
- **WHEN** the repair evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths
