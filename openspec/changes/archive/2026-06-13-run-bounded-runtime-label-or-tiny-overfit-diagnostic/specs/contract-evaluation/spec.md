## ADDED Requirements

### Requirement: Publish runtime-label and tiny-overfit diagnostic evidence
The system SHALL publish a public-safe evidence pack that explains whether current public-sample SFT failures are ready for fresh runtime-label inspection, tiny-overfit probing, preference-signal diagnosis, or another bounded follow-up.

#### Scenario: Generate runtime-label tiny-overfit evidence pack
- **WHEN** the diagnostic is run against the current public manifest and prior public-safe artifacts
- **THEN** it MUST write machine-readable JSON and human-readable Markdown that include evidence kind, current manifest ID, current learning-signal status, prior repair metrics, runtime-label freshness, tiny-overfit freshness, recommendation, claims, and artifact policy

#### Scenario: Keep diagnostic evidence public-safe
- **WHEN** runtime-label/tiny-overfit diagnostic evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, host details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound diagnostic interpretation
- **WHEN** public reports or Human Briefs describe the runtime-label/tiny-overfit diagnostic
- **THEN** they MUST state that the evidence does not prove model recovery, held-out generalization, private-corpus generalization, checkpoint release, adapter release, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Preserve stale evidence boundaries
- **WHEN** prior runtime-label or tiny-overfit artifacts are stale for the current manifest
- **THEN** the evidence pack MUST identify the source manifest mismatch
- **AND** it MUST recommend a fresh current-manifest check rather than treating stale artifacts as current proof
