## ADDED Requirements

### Requirement: Publish first-pass fence-suppression evidence
The system SHALL publish public-safe local evidence for first-pass Markdown fence suppression while preserving strict-metric, privacy, and non-claim boundaries.

#### Scenario: Generate local fence-suppression evidence pack
- **WHEN** the local fence-suppression behavior-change phase completes
- **THEN** the evidence pack MUST include a manifest, machine-readable summary, human-readable summary, leak-scan results, source links to the prior A100 first-pass output-boundary rerun and wrapper-persistence diagnosis, focused test evidence, validation commands, and explicit non-claims

#### Scenario: Bound interpretation of local suppression evidence
- **WHEN** public documentation or Human Briefs describe the fence-suppression phase
- **THEN** they MUST state that the phase performs no A100 execution, training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, held-out generalization claim, model recovery claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim

#### Scenario: Preserve prior A100 evidence interpretation
- **WHEN** the evidence pack references the prior A100 first-pass output-boundary rerun or wrapper-persistence diagnosis
- **THEN** it MUST state that prior strict schema-valid output remained `0/3`, strict exact match remained `0.0`, Markdown-wrapped predictions remained `3/3`, and this local phase does not prove any change in trained-adapter output behavior until a later real A100 rerun is performed
