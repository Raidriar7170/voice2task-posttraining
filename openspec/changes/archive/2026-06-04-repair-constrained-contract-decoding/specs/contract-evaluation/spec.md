## ADDED Requirements

### Requirement: Publish constrained-decoding diagnosis evidence
The system SHALL publish a public-safe local diagnosis for the constrained contract decoding repair that classifies required-field rerun raw and retry failures without treating the diagnosis as model-quality evidence.

#### Scenario: Classify required-field rerun failures
- **WHEN** required-field rerun raw and retry decoded summaries are available
- **THEN** the diagnosis MUST report prediction count, raw attempt schema-valid count, retry attempt schema-valid count, validated output schema-valid count, parse status counts, legacy enum/path-like route symptoms, prose-or-Markdown wrapper symptoms, and whether invalid predictions remain invalid

#### Scenario: Bound constrained-decoding interpretation
- **WHEN** public reports or Human Briefs describe the constrained decoding repair
- **THEN** they MUST state that the phase is local decoder/output-shape hardening and MUST NOT claim checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, live-browser benchmark improvement, or A100 model recovery

#### Scenario: Validate diagnosis public safety
- **WHEN** constrained-decoding diagnosis evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths
