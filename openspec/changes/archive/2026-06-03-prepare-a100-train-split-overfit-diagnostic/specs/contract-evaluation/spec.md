## ADDED Requirements

### Requirement: Publish train-split overfit diagnostic evidence
The system SHALL publish public-safe train-split overfit diagnostic evidence that separates train-internal recovery from held-out generalization and live-browser claims.

#### Scenario: Generate train-split diagnostic manifest
- **WHEN** train-split diagnostic predictions, metrics, objective inspection, prompt snapshot, raw decoded summary, generation trace, and leak-scan results are available
- **THEN** the manifest MUST link those artifacts and record `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, release status, and claim boundaries

#### Scenario: Report diagnostic interpretation
- **WHEN** a human-readable train-split diagnostic report is generated
- **THEN** it MUST state whether train-internal schema/route/slot recovery was observed and MUST state that this does not prove dev/test generalization, production readiness, checkpoint release, adapter release, or live-browser benchmark improvement

#### Scenario: Validate diagnostic evidence boundaries
- **WHEN** diagnostic evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths
