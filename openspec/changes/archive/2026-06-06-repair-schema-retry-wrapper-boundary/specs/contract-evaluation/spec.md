## ADDED Requirements

### Requirement: Publish schema retry wrapper-boundary evidence
The system SHALL publish public-safe local evidence for schema retry wrapper-boundary hardening that connects the repair to prior A100 diagnosis without changing strict metrics or claiming model recovery.

#### Scenario: Generate retry wrapper-boundary manifest
- **WHEN** local retry-wrapper repair evidence is prepared
- **THEN** the manifest MUST record the source A100 diagnosis, prompt boundary constraints, generated artifacts, validation commands, leak-scan results, and non-claim boundaries

#### Scenario: Bound retry wrapper-boundary claims
- **WHEN** evidence, reports, tests, specs, or Human Briefs describe this phase
- **THEN** they MUST state that no A100 execution, training, private prediction rerun, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, checkpoint release, adapter release, held-out generalization claim, model-quality claim, or live-browser benchmark improvement claim is made

#### Scenario: Validate retry wrapper-boundary privacy
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, private overrides, and private remote paths
