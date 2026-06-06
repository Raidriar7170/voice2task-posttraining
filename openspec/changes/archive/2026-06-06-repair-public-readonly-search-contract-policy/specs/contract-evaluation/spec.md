## ADDED Requirements

### Requirement: Publish public-readonly search contract policy evidence
The system SHALL publish public-safe local evidence for public-readonly search contract policy hardening that links back to the prior row-level mismatch diagnosis without claiming model recovery.

#### Scenario: Generate local policy evidence
- **WHEN** the public-readonly search policy evidence pack is generated
- **THEN** it MUST record the source prior phase `reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis/`
- **AND** it MUST report the source row mismatch family counts for missing `confirmation_required`, invalid `task_type` enum, and schema-valid task/route/safety/slot mismatch
- **AND** it MUST record prompt constraint flags for public-readonly search policy visibility, `public_readonly` safety reason visibility, search query slot guidance visibility, and task-type-not-route-enum guidance visibility

#### Scenario: Bound local policy evidence claims
- **WHEN** reports, Human Briefs, loop reports, or archived OpenSpec artifacts describe this phase
- **THEN** they MUST state that it is local prompt/policy hardening only
- **AND** they MUST NOT claim A100 execution, training, prediction rerun, decoder repair, schema repair, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Keep policy evidence public-safe
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths
