## ADDED Requirements

### Requirement: Publish merged adapter restore evidence
The system SHALL publish public-safe evidence for the merged slot-value adapter
restore/regeneration prerequisite.

#### Scenario: Record adapter availability evidence
- **WHEN** restore or regeneration evidence is written
- **THEN** it MUST record the restore status, acquisition method, dataset
  manifest ID, source runtime, required adapter-file checks, and sanitized
  dependency/preflight status

#### Scenario: Record blocked prerequisite status
- **WHEN** SSH, GPU placement, dependency, output-root, or training runtime
  checks block adapter restoration/regeneration
- **THEN** the evidence pack MUST record a blocked status and reason without
  private host details, raw private paths, raw logs, adapters, checkpoints,
  tokens, or private corpus rows

#### Scenario: Bound prerequisite interpretation
- **WHEN** public reports or Human Briefs describe the adapter prerequisite
- **THEN** they MUST state that this phase produces no new train/dev/test
  prediction metrics
- **AND** they MUST NOT claim model recovery, adapter release, checkpoint
  release, production readiness, private-corpus generalization, or live-browser
  benchmark improvement
