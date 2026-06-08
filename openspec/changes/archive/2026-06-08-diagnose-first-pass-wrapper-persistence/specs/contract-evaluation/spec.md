## ADDED Requirements

### Requirement: Publish first-pass wrapper persistence diagnosis
The system SHALL publish a public-safe local diagnosis explaining persistent Markdown-wrapped output after first-pass output-boundary visibility is confirmed, while preserving strict parser, privacy, and non-claim boundaries.

#### Scenario: Generate wrapper persistence diagnosis
- **WHEN** the diagnosis is generated from the A100 first-pass output-boundary rerun artifacts
- **THEN** it MUST record prompt boundary visibility, strict schema-valid counts, Markdown wrapper counts, raw and retry parse status counts, finish-state counts, and comparison against the source rerun summary
- **AND** it MUST state that EOS-observed generation completion does not imply strict schema-valid output
- **AND** it MUST NOT alter predictions, repair embedded JSON, relax parser behavior, re-score predictions, or launch a new A100 job

#### Scenario: Bound wrapper persistence claims
- **WHEN** reports, manifests, Human Briefs, or archived OpenSpec artifacts describe the diagnosis
- **THEN** they MUST state that it is local evidence over a three-row train-split A100 rerun
- **AND** they MUST NOT claim held-out generalization, model-quality improvement, model recovery, production readiness, checkpoint release, adapter release, public full-corpus release, live-browser benchmark improvement, semantic-equivalence scoring, slot normalization, prediction repair, metric relaxation, or re-score

#### Scenario: Preserve public-safety boundary
- **WHEN** wrapper persistence diagnosis artifacts are committed
- **THEN** they MUST include leak-scan evidence
- **AND** they MUST NOT include private config paths, raw remote logs, private filesystem paths, host details, SSH details, tokens, secrets, caches, checkpoints, adapters, or private corpus rows
